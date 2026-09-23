"""Compactação de PDFs e imagens: o original fica intacto e a cópia menor vai ao lado.

PDF (em `pdf.py`, num processo à parte): PyMuPDF reduz só as imagens acima da resolução do
nível e recomprime em JPEG (texto e desenhos continuam vetoriais), tira fontes não usadas e
objetos repetidos.
Imagem: Pillow no mesmo formato (JPG continua JPG, PNG continua PNG), sem EXIF/GPS.
"""

import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from toolbox.nucleo.erros import Cancelado, ErroUsuario
from toolbox.nucleo.ffmpeg import SEM_JANELA
from toolbox.nucleo.nomes import caminho_livre

SUFIXO = " (compactado)"


@dataclass(frozen=True)
class Nivel:
    id: str
    nome: str
    descricao: str
    # PDF: imagens acima de `limite_dpi` descem para `alvo_dpi`, JPEG com `qualidade`
    limite_dpi: int
    alvo_dpi: int
    qualidade: int
    # Imagens soltas: qualidade e tamanho máximo (em pixels; 0 = mantém) das fotos JPG/WebP.
    # PNG (captura de tela, desenho) não é reduzido: o Forte só limita a 256 cores.
    qualidade_foto: int
    pixels_maximos: int
    reduzir_cores: bool


NIVEIS = {
    "leve": Nivel("leve", "Leve", "Quase sem perda", 330, 300, 85, 85, 0, False),
    "equilibrado": Nivel("equilibrado", "Equilibrado", "Bem menor, boa leitura",
                         165, 150, 75, 78, 2560 * 1920, False),
    "forte": Nivel("forte", "Forte", "O menor possível",
                   110, 100, 60, 65, 1600 * 1200, True),
}

TIPOS_PDF = {"application/pdf"}
TIPOS_IMAGEM = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}
TIPOS_ACEITOS = TIPOS_PDF | set(TIPOS_IMAGEM)


@dataclass
class Resultado:
    antes: int
    depois: int          # tamanho da cópia (ou do original, se não compensou)
    saida: Path | None   # None = já estava compacto, nada foi salvo
    aviso: str = ""


def destino_para(caminho: Path, pasta: Path | None = None) -> Path:
    """"foto.jpg" → "foto (compactado).jpg" (na pasta escolhida ou na do original), sem sobrescrever."""
    return caminho_livre(pasta or caminho.parent, caminho.stem + SUFIXO, caminho.suffix.lstrip(".") or "bin")


def compactar(caminho, tipo: str, id_nivel: str, pasta=None, ao_progresso=None, cancelado=None) -> Resultado:
    """Compacta um arquivo. `ao_progresso(fracao)` vai de 0 a 1 dentro deste arquivo."""
    caminho = Path(caminho)
    nivel = NIVEIS[id_nivel]
    ao_progresso = ao_progresso or (lambda _f: None)
    cancelado = cancelado or (lambda: False)
    if tipo in TIPOS_PDF:
        return _compactar_pdf(caminho, nivel, Path(pasta) if pasta else None, ao_progresso, cancelado)
    if tipo in TIPOS_IMAGEM:
        return _compactar_imagem(caminho, TIPOS_IMAGEM[tipo], nivel, Path(pasta) if pasta else None)
    raise ErroUsuario("Só PDFs e imagens JPG, PNG ou WebP podem ser compactados.")


def _guardar_se_menor(original: Path, dados_ou_temporario, pasta: Path | None, aviso="") -> Resultado:
    antes = original.stat().st_size
    temporario = dados_ou_temporario if isinstance(dados_ou_temporario, Path) else None
    depois = temporario.stat().st_size if temporario else len(dados_ou_temporario)
    if depois >= antes * 0.98:  # ganhar menos de 2% não vale uma cópia a mais
        if temporario:
            temporario.unlink(missing_ok=True)
        return Resultado(antes, antes, None)
    destino = destino_para(original, pasta)
    if temporario:
        os.replace(temporario, destino)
    else:
        destino.write_bytes(dados_ou_temporario)
    return Resultado(antes, depois, destino, aviso)


# ------------------------------------------------------------ PDF

RAIZ_PROJETO = Path(__file__).resolve().parents[3]


def _compactar_pdf(caminho: Path, nivel: Nivel, pasta: Path | None, ao_progresso, cancelado) -> Resultado:
    """Roda `pdf.py` num processo à parte (ver lá o porquê) e acompanha o progresso."""
    temporario = destino_para(caminho, pasta).with_suffix(".parcial")
    processo = subprocess.Popen(
        [sys.executable, "-m", "toolbox.apps.compactador.pdf",
         str(caminho.resolve()), str(temporario.resolve()), nivel.id],
        cwd=RAIZ_PROJETO, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
        errors="replace", creationflags=SEM_JANELA,
    )
    linhas: list[str] = []
    leitor = threading.Thread(target=lambda: linhas.extend(iter(processo.stdout.readline, "")), daemon=True)
    leitor.start()
    lidas = 0
    try:
        while processo.poll() is None or leitor.is_alive():
            if cancelado():
                processo.kill()
                processo.wait()
                raise Cancelado()
            for linha in linhas[lidas:]:
                if linha.startswith("progresso "):
                    ao_progresso(float(linha.split()[1]))
            lidas = len(linhas)
            time.sleep(0.1)
        final = next((l.strip() for l in reversed(linhas) if l.startswith(("ok", "erro"))), "")
        if final.startswith("erro"):
            raise ErroUsuario(final[5:])
        if processo.returncode != 0 or not final or not temporario.exists():
            raise ErroUsuario("Não foi possível compactar este PDF (arquivo danificado ou fora do padrão).")
    except BaseException:
        temporario.unlink(missing_ok=True)
        raise
    ao_progresso(1.0)
    return _guardar_se_menor(caminho, temporario, pasta, final[3:])


# ------------------------------------------------------------ imagens

def _compactar_imagem(caminho: Path, formato: str, nivel: Nivel, pasta: Path | None) -> Resultado:
    from PIL import Image, ImageOps

    Image.MAX_IMAGE_PIXELS = None  # arquivo do próprio usuário: imagens gigantes são justamente as que interessam
    try:
        imagem = Image.open(caminho)
        imagem.load()
    except Exception as erro:  # noqa: BLE001
        raise ErroUsuario("Não foi possível abrir esta imagem (arquivo danificado?).") from erro
    with imagem:
        if getattr(imagem, "n_frames", 1) > 1:
            raise ErroUsuario("Imagens animadas não são compactadas.")
        perfil_cor = imagem.info.get("icc_profile")
        dpi = imagem.info.get("dpi")
        # Aplica a rotação do EXIF nos pixels: sem EXIF, a foto não pode ficar deitada.
        imagem = ImageOps.exif_transpose(imagem)
        largura, altura = imagem.size
        if formato != "PNG" and nivel.pixels_maximos and largura * altura > nivel.pixels_maximos:
            # Pelo total de pixels, não pelo lado maior: um panorama não vira uma tira fina.
            escala = (nivel.pixels_maximos / (largura * altura)) ** 0.5
            imagem = imagem.resize((round(largura * escala), round(altura * escala)), Image.LANCZOS)

        extras = {"icc_profile": perfil_cor} if perfil_cor else {}
        if dpi:
            extras["dpi"] = dpi
        saida = BytesIO()
        if formato == "JPEG":
            if imagem.mode not in ("RGB", "L", "CMYK"):
                imagem = imagem.convert("RGB")
            imagem.save(saida, "JPEG", quality=nivel.qualidade_foto, optimize=True, progressive=True, **extras)
        elif formato == "WEBP":
            imagem.save(saida, "WEBP", quality=nivel.qualidade_foto, method=6, **extras)
        else:
            if nivel.reduzir_cores and imagem.mode not in ("P", "1", "L"):
                imagem = _reduzir_cores(imagem)
            imagem.save(saida, "PNG", optimize=True, **extras)
    return _guardar_se_menor(caminho, saida.getvalue(), pasta)


def _reduzir_cores(imagem):
    """PNG com até 256 cores. Transparência só "tudo ou nada" (ícone recortado) ganha uma cor
    reservada; bordas suaves (sombras, logos antisserrilhados) ficam como estão, sem manchas."""
    from PIL import Image

    transparente = imagem.mode in ("RGBA", "LA", "PA") or "transparency" in imagem.info
    if not transparente:
        return _paleta(imagem.convert("RGB"), 256)
    rgba = imagem.convert("RGBA")
    alfa = rgba.getchannel("A")
    if alfa.point(lambda a: 0 if a in (0, 255) else 255).getbbox():  # há semitransparência
        return imagem
    paleta = _paleta(rgba.convert("RGB"), 255)
    cores = paleta.getpalette()
    paleta.putpalette(cores + [0] * (768 - len(cores)))  # a cor 255 precisa existir na paleta
    paleta.paste(255, mask=alfa.point(lambda a: 255 if a == 0 else 0))
    paleta.info["transparency"] = 255
    return paleta


def _paleta(rgb, cores: int):
    """Paleta escolhida numa miniatura (com k-means, que acerta cores fortes como dourado e
    vermelho) e aplicada na imagem inteira: fiel como o k-means, rápido como sem ele."""
    from PIL import Image

    amostra = rgb.copy()
    amostra.thumbnail((512, 512))
    modelo = amostra.quantize(cores, method=Image.Quantize.MEDIANCUT, kmeans=3)
    return rgb.quantize(palette=modelo, dither=Image.Dither.FLOYDSTEINBERG)


# ------------------------------------------------------------ fila

def processar_fila(itens: list[tuple[str, str]], id_nivel: str, pasta=None, ao_evento=None, cancelado=None) -> dict:
    """Compacta (caminho, tipo) um por um; um erro num arquivo não para os outros.

    Eventos: {"i", "estado": "compactando"|"ok"|"erro", "fracao"?, "resultado"?, "mensagem"?}
    e {"total": fração da fila, pesada pelo tamanho de cada arquivo}.
    """
    ao_evento = ao_evento or (lambda _e: None)
    cancelado = cancelado or (lambda: False)
    tamanhos = [max(Path(c).stat().st_size, 1) for c, _t in itens]
    total, feito = sum(tamanhos), 0
    resultados: list[Resultado | None] = [None] * len(itens)
    for i, (caminho, tipo) in enumerate(itens):
        if cancelado():
            return {"resultados": resultados, "cancelado": True}

        def ao_progresso(fracao, i=i):
            ao_evento({"i": i, "estado": "compactando", "fracao": fracao})
            ao_evento({"total": (feito + fracao * tamanhos[i]) / total})

        ao_progresso(0.0)
        try:
            resultados[i] = compactar(caminho, tipo, id_nivel, pasta, ao_progresso, cancelado)
            ao_evento({"i": i, "estado": "ok", "resultado": resultados[i]})
        except Cancelado:
            return {"resultados": resultados, "cancelado": True}
        except ErroUsuario as erro:
            ao_evento({"i": i, "estado": "erro", "mensagem": str(erro)})
        except Exception as erro:  # noqa: BLE001 — arquivo estranho: avisa e segue a fila
            ao_evento({"i": i, "estado": "erro", "mensagem": f"Não foi possível compactar ({erro})"})
        feito += tamanhos[i]
        ao_evento({"total": feito / total})
    return {"resultados": resultados, "cancelado": False}
