"""Transcrição de áudio/vídeo em texto com o Whisper, rodando 100% no computador (sem Qt).

Motor: faster-whisper (CTranslate2) na CPU, int8. O modelo é baixado uma única vez
para %APPDATA%\\TOOLBOX\\modelos; depois tudo funciona offline — o áudio nunca sai da máquina.
Quem fala: reconhecimento de vozes do sherpa-onnx (segmentação pyannote + impressão de voz
CAM++), também local; cada voz diferente vira "Pessoa 1", "Pessoa 2"… em qualquer arquivo.
"""

import gc
import os
import subprocess
import tarfile
import time
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

from toolbox.nucleo import config
from toolbox.nucleo.arquivo import tamanho_legivel
from toolbox.nucleo.erros import Cancelado, ErroUsuario
from toolbox.nucleo.ffmpeg import SEM_JANELA, caminho_ffmpeg

os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
# Download pelo HTTP comum: o do Xet roda fora do Python e não deixa cancelar nem medir o progresso.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

PASTA_MODELOS = config.PASTA_DADOS / "modelos"
ARQUIVOS_MODELO = ["config.json", "preprocessor_config.json", "model.bin", "tokenizer.json", "vocabulary.*"]
MARCA_COMPLETO = ".completo"  # criado só quando o download termina inteiro

# Modelos de reconhecimento de voz (quem fala): ~35 MB, baixados junto com o 1º uso.
PASTA_VOZES = PASTA_MODELOS / "vozes"
_RELEASES = "https://github.com/k2-fsa/sherpa-onnx/releases/download"
ARQUIVOS_VOZES = {  # arquivo local: (endereço, membro dentro do .tar.bz2 ou "")
    "segmentacao.onnx": (f"{_RELEASES}/speaker-segmentation-models/sherpa-onnx-pyannote-segmentation-3-0.tar.bz2",
                         "sherpa-onnx-pyannote-segmentation-3-0/model.onnx"),
    "vozes.onnx": (f"{_RELEASES}/speaker-recongition-models/"
                   "3dspeaker_speech_campplus_sv_zh_en_16k-common_advanced.onnx", ""),
}
TAMANHO_VOZES = 35_000_000
VELOCIDADE_VOZES = 7.0  # segundos de áudio por segundo para separar as vozes (medido num i3)
LIMIAR_VOZES = 0.5      # quanto maior, mais fácil juntar duas vozes parecidas numa pessoa só
TAXA_VOZES = 16000


def nome_pessoa(numero: int) -> str:
    return f"Pessoa {numero}"


@dataclass(frozen=True)
class Modelo:
    id: str
    nome: str
    descricao: str
    repositorio: str
    tamanho: int          # bytes do download
    velocidade: float     # segundos de áudio por segundo de processamento (medido num i3 de 4 núcleos)
    selo: str = ""


MODELOS = {m.id: m for m in (
    Modelo("turbo", "Precisão", "Whisper large-v3-turbo", "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
           1_622_000_000, 1.2, "Recomendado"),
    Modelo("small", "Rapidez", "Whisper small", "Systran/faster-whisper-small", 486_000_000, 3.5),
)}

IDIOMAS = {"pt": "Português", "": "Detectar automaticamente"}


@dataclass
class Palavra:
    inicio: float
    fim: float
    texto: str


@dataclass
class Segmento:
    inicio: float
    fim: float
    texto: str
    palavras: list[Palavra] = field(default_factory=list)


@dataclass
class Bloco:
    """Parágrafo do resultado: um turno de fala (com falante) ou um trecho de texto corrido."""
    inicio: float
    fim: float
    texto: str
    falante: str = ""


@dataclass
class Transcricao:
    segmentos: list[Segmento]
    blocos: list[Bloco]
    idioma: str
    duracao: float
    com_falantes: bool


# ------------------------------------------------------------------ modelos

def pasta_modelo(id_modelo: str) -> Path:
    return PASTA_MODELOS / id_modelo


def modelo_baixado(id_modelo: str) -> bool:
    return (pasta_modelo(id_modelo) / MARCA_COMPLETO).is_file()


def baixar_modelo(id_modelo: str, ao_progresso=None, cancelado=lambda: False) -> Path:
    """Baixa o modelo (uma vez só). É a única parte da Transcrição que usa a internet."""
    from huggingface_hub import snapshot_download
    from tqdm.auto import tqdm

    modelo = MODELOS[id_modelo]
    destino = pasta_modelo(id_modelo)
    destino.mkdir(parents=True, exist_ok=True)
    ultimo = [0.0]
    bytes_por_barra: dict[int, int] = {}

    class Acompanhar(tqdm):
        """O hub chama update() enquanto baixa: dá para medir o progresso e cancelar."""

        def __init__(self, *args, **kwargs):
            kwargs["disable"] = True
            self._em_bytes = kwargs.get("unit") == "B"
            super().__init__(*args, **kwargs)

        def update(self, n=1):
            if cancelado():
                raise Cancelado()
            if self._em_bytes:  # há mais de uma barra de bytes para o mesmo download: vale a maior
                bytes_por_barra[id(self)] = bytes_por_barra.get(id(self), 0) + (n or 0)
            if ao_progresso and time.monotonic() - ultimo[0] > 0.3:
                ultimo[0] = time.monotonic()
                baixado = min(max(bytes_por_barra.values(), default=0), modelo.tamanho)
                ao_progresso({"fracao": baixado / modelo.tamanho,
                              "texto": f"{tamanho_legivel(baixado)} de {tamanho_legivel(modelo.tamanho)}"})
            return super().update(n)

    try:
        snapshot_download(modelo.repositorio, local_dir=destino, allow_patterns=ARQUIVOS_MODELO,
                          tqdm_class=Acompanhar)
    except Cancelado:
        raise
    except Exception as erro:  # noqa: BLE001 — rede, disco cheio, servidor fora
        if cancelado():
            raise Cancelado() from erro
        raise ErroUsuario("Não foi possível baixar o modelo. Confira a internet (só é preciso nesta 1ª vez) "
                          f"e o espaço em disco.\n{erro.__class__.__name__}") from erro
    (destino / MARCA_COMPLETO).write_text("ok", encoding="utf-8")
    return destino


def vozes_baixadas() -> bool:
    return (PASTA_VOZES / MARCA_COMPLETO).is_file()


def baixar_vozes(ao_progresso=None, cancelado=lambda: False) -> Path:
    """Baixa os modelos de reconhecimento de voz (uma vez só, ~35 MB)."""
    PASTA_VOZES.mkdir(parents=True, exist_ok=True)
    baixado, ultimo = 0, 0.0
    try:
        for nome, (endereco, membro) in ARQUIVOS_VOZES.items():
            temporario = PASTA_VOZES / (nome + ".parcial")
            with urllib.request.urlopen(endereco, timeout=30) as resposta, open(temporario, "wb") as destino:
                while bloco := resposta.read(256 * 1024):
                    if cancelado():
                        raise Cancelado()
                    destino.write(bloco)
                    baixado += len(bloco)
                    if ao_progresso and time.monotonic() - ultimo > 0.3:
                        ultimo = time.monotonic()
                        ao_progresso({"fracao": min(1.0, baixado / TAMANHO_VOZES),
                                      "texto": f"{tamanho_legivel(baixado)} de {tamanho_legivel(TAMANHO_VOZES)}"})
            if membro:  # o modelo de segmentação vem compactado
                with tarfile.open(temporario, "r:bz2") as pacote:
                    (PASTA_VOZES / nome).write_bytes(pacote.extractfile(membro).read())
                temporario.unlink()
            else:
                temporario.replace(PASTA_VOZES / nome)
    except Cancelado:
        raise
    except Exception as erro:  # noqa: BLE001 — rede, disco, arquivo corrompido
        if cancelado():
            raise Cancelado() from erro
        raise ErroUsuario("Não foi possível baixar o reconhecimento de voz. Confira a internet "
                          f"(só é preciso nesta 1ª vez).\n{erro.__class__.__name__}") from erro
    finally:
        for sobra in PASTA_VOZES.glob("*.parcial"):
            sobra.unlink(missing_ok=True)
    (PASTA_VOZES / MARCA_COMPLETO).write_text("ok", encoding="utf-8")
    return PASTA_VOZES


def estimar_segundos(duracao: float, id_modelo: str, separar: bool = False) -> float:
    return duracao / MODELOS[id_modelo].velocidade + (duracao / VELOCIDADE_VOZES if separar else 0)


# ------------------------------------------------------------------ quem fala

def _audio_16k(caminho: Path):
    """Áudio mono 16 kHz em float32, decodificado pelo FFmpeg."""
    import numpy as np

    saida = subprocess.run(
        [caminho_ffmpeg(), "-hide_banner", "-loglevel", "error", "-nostdin", "-i", str(caminho),
         "-vn", "-f", "f32le", "-ac", "1", "-ar", str(TAXA_VOZES), "-"],
        capture_output=True, creationflags=SEM_JANELA,
    )
    if saida.returncode != 0:
        raise ErroUsuario("Não foi possível ler o áudio para separar as vozes.")
    return np.frombuffer(saida.stdout, dtype="<f4")


def identificar_vozes(caminho, ao_progresso=None, cancelado=lambda: False) -> list[tuple[float, float, int]]:
    """Trechos (início, fim, nº da voz) de quem fala, sem saber antes quantas pessoas são."""
    import sherpa_onnx

    threads = os.cpu_count() or 4
    config_vozes = sherpa_onnx.OfflineSpeakerDiarizationConfig(
        segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
            pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(
                model=str(PASTA_VOZES / "segmentacao.onnx")),
            num_threads=threads),
        embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(PASTA_VOZES / "vozes.onnx"),
                                                              num_threads=threads),
        clustering=sherpa_onnx.FastClusteringConfig(num_clusters=-1, threshold=LIMIAR_VOZES),
        min_duration_on=0.3, min_duration_off=0.5,
    )
    if not config_vozes.validate():
        raise ErroUsuario("Os modelos de reconhecimento de voz estão incompletos. Apague a pasta "
                          f"{PASTA_VOZES} e tente de novo.")
    separador = sherpa_onnx.OfflineSpeakerDiarization(config_vozes)
    amostras = _audio_16k(Path(caminho))

    def acompanhar(feitos: int, total: int) -> int:
        if ao_progresso and total:
            ao_progresso({"fracao": feitos / total})
        return 1 if cancelado() else 0  # diferente de zero interrompe

    resultado = separador.process(amostras, callback=acompanhar).sort_by_start_time()
    if cancelado():
        raise Cancelado()
    return [(trecho.start, trecho.end, trecho.speaker) for trecho in resultado]


def _voz_da_palavra(palavra: Palavra, trechos: list[tuple[float, float, int]], inicio_busca: int) -> tuple[int | None, int]:
    """Voz com mais sobreposição na palavra (ou a do trecho mais próximo, até 1 s). Devolve (voz, onde parou)."""
    while inicio_busca < len(trechos) and trechos[inicio_busca][1] < palavra.inicio - 1.0:
        inicio_busca += 1  # trechos e palavras vêm em ordem: não precisa voltar
    melhor, maior, distancia_menor = None, 0.0, 1.0
    i = inicio_busca
    while i < len(trechos) and trechos[i][0] <= palavra.fim + 1.0:
        inicio, fim, voz = trechos[i]
        sobreposicao = min(fim, palavra.fim) - max(inicio, palavra.inicio)
        if sobreposicao > maior:
            melhor, maior = voz, sobreposicao
        elif maior == 0 and (distancia := max(inicio - palavra.fim, palavra.inicio - fim)) < distancia_menor:
            melhor, distancia_menor = voz, distancia
        i += 1
    return melhor, inicio_busca


def separar_falantes(segmentos: list[Segmento], trechos: list[tuple[float, float, int]]) -> list[Bloco]:
    """Cada palavra recebe a voz que falava naquele instante; palavras seguidas da mesma voz viram um turno.

    As vozes são numeradas na ordem em que aparecem: a primeira a falar é a "Pessoa 1".
    """
    numeros: dict[int, int] = {}
    turnos: list[Bloco] = []
    atual, busca = None, 0
    for segmento in segmentos:
        for palavra in segmento.palavras or [Palavra(segmento.inicio, segmento.fim, segmento.texto)]:
            voz, busca = _voz_da_palavra(palavra, trechos, busca)
            if voz is not None:
                atual = numeros.setdefault(voz, len(numeros) + 1)
            falante = nome_pessoa(atual or 1)
            if turnos and turnos[-1].falante == falante:
                turnos[-1].texto += palavra.texto
                turnos[-1].fim = palavra.fim
            else:
                turnos.append(Bloco(palavra.inicio, palavra.fim, palavra.texto, falante))
    for turno in turnos:
        turno.texto = turno.texto.strip()
    return [t for t in turnos if t.texto]


def paragrafos(segmentos: list[Segmento], pausa: float = 2.0, limite: int = 700) -> list[Bloco]:
    """Texto corrido: novo parágrafo depois de uma pausa longa ou quando o parágrafo fica grande."""
    blocos: list[Bloco] = []
    for segmento in segmentos:
        texto = segmento.texto.strip()
        if not texto:
            continue
        novo = (not blocos or segmento.inicio - blocos[-1].fim > pausa
                or (len(blocos[-1].texto) > limite and blocos[-1].texto.endswith((".", "?", "!"))))
        if novo:
            blocos.append(Bloco(segmento.inicio, segmento.fim, texto))
        else:
            blocos[-1].texto += " " + texto
            blocos[-1].fim = segmento.fim
    return blocos


# ------------------------------------------------------------------ transcrição

def transcrever(caminho, id_modelo: str = "turbo", idioma: str = "pt", separar: bool = True,
                ao_progresso=None, cancelado=lambda: False) -> Transcricao:
    """Transcreve localmente e, com `separar`, marca quem fala ("Pessoa 1", "Pessoa 2"…).

    `ao_progresso` recebe {"etapa": "texto", "fracao", "segundo", "duracao", "texto"} e depois
    {"etapa": "vozes", "fracao"} enquanto separa as vozes.
    """
    caminho = Path(caminho)
    if not caminho.is_file():
        raise ErroUsuario("O arquivo não foi encontrado.")
    if not modelo_baixado(id_modelo):
        raise ErroUsuario("Baixe o modelo antes de transcrever.")
    if separar and not vozes_baixadas():
        raise ErroUsuario("Baixe o reconhecimento de voz antes de separar quem fala.")

    from faster_whisper import WhisperModel

    modelo = WhisperModel(str(pasta_modelo(id_modelo)), device="cpu", compute_type="int8",
                          cpu_threads=os.cpu_count() or 4, local_files_only=True)
    try:
        try:
            pedacos, info = modelo.transcribe(str(caminho), language=idioma or None, vad_filter=True,
                                              word_timestamps=separar)
        except Exception as erro:  # noqa: BLE001 — arquivo sem áudio, formato estranho
            raise ErroUsuario(f"Não foi possível ler o áudio deste arquivo. {erro}") from erro
        if ao_progresso:  # modelo carregado; o 1º trecho leva alguns segundos para sair
            ao_progresso({"etapa": "texto", "fracao": 0.0, "segundo": 0.0, "duracao": info.duration, "texto": ""})
        segmentos = []
        for pedaco in pedacos:  # gerador: cada segmento é decodificado aqui
            if cancelado():
                raise Cancelado()
            palavras = [Palavra(p.start, p.end, p.word) for p in (pedaco.words or [])]
            segmentos.append(Segmento(pedaco.start, pedaco.end, pedaco.text, palavras))
            if ao_progresso and info.duration:
                ao_progresso({"etapa": "texto", "fracao": min(1.0, pedaco.end / info.duration), "segundo": pedaco.end,
                              "duracao": info.duration, "texto": pedaco.text.strip()})
    finally:
        del modelo
        gc.collect()  # devolve a memória do modelo (~1 GB) assim que termina

    if not segmentos:
        raise ErroUsuario("Não foi encontrada fala neste arquivo.")
    if separar:
        trechos = identificar_vozes(caminho, (lambda p: ao_progresso({"etapa": "vozes", **p})) if ao_progresso
                                    else None, cancelado)
        turnos = separar_falantes(segmentos, trechos)
        if len({t.falante for t in turnos}) > 1:
            return Transcricao(segmentos, turnos, info.language, info.duration, True)
    # Uma voz só (ou sem separar): texto corrido, sem "Pessoa 1:" em todo parágrafo.
    return Transcricao(segmentos, paragrafos(segmentos), info.language, info.duration, False)


# ------------------------------------------------------------------ saída

def formatar_tempo(segundos: float, milissegundos: bool = False) -> str:
    total_ms = int(round(segundos * 1000))
    horas, resto = divmod(total_ms, 3_600_000)
    minutos, resto = divmod(resto, 60_000)
    seg, ms = divmod(resto, 1000)
    if milissegundos:
        return f"{horas:02d}:{minutos:02d}:{seg:02d},{ms:03d}"
    return f"{horas}:{minutos:02d}:{seg:02d}" if horas else f"{minutos:02d}:{seg:02d}"


def texto_corrido(transcricao: Transcricao) -> str:
    if transcricao.com_falantes:
        return "\n\n".join(f"{b.falante}: {b.texto}" for b in transcricao.blocos) + "\n"
    return "\n\n".join(b.texto for b in transcricao.blocos) + "\n"


def salvar_txt(transcricao: Transcricao, destino: Path) -> Path:
    destino.write_text(texto_corrido(transcricao), encoding="utf-8")
    return destino


def salvar_srt(transcricao: Transcricao, destino: Path) -> Path:
    """Legenda: um trecho por segmento; com falantes, cada trecho vem marcado ("[Pessoa 1] …")."""
    linhas = []
    anterior = ""
    falantes = [(b.inicio, b.fim, b.falante) for b in transcricao.blocos] if transcricao.com_falantes else []
    for n, segmento in enumerate(transcricao.segmentos, 1):
        texto = segmento.texto.strip()
        if falantes:
            meio = (segmento.inicio + segmento.fim) / 2
            anterior = next((f for i, fim, f in falantes if i <= meio <= fim), anterior)
            texto = f"[{anterior}] {texto}" if anterior else texto
        linhas += [str(n), f"{formatar_tempo(segmento.inicio, True)} --> {formatar_tempo(segmento.fim, True)}",
                   texto, ""]
    destino.write_text("\n".join(linhas), encoding="utf-8")
    return destino


_TIPOS_DOCX = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    '</Types>'
)
_RELACOES_DOCX = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
    'Target="word/document.xml"/></Relationships>'
)


CORES_PESSOAS = ["1F6FEB", "C2185B", "2E7D32", "E65100", "6A1B9A", "00838F"]


def _trecho(texto: str, negrito=False, cor: str = "", tamanho: int = 0) -> str:
    estilo = "".join([
        '<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>',
        "<w:b/>" if negrito else "",
        f'<w:color w:val="{cor}"/>' if cor else "",
        f'<w:sz w:val="{tamanho * 2}"/>' if tamanho else "",
    ])
    return f'<w:r><w:rPr>{estilo}</w:rPr><w:t xml:space="preserve">{escape(texto)}</w:t></w:r>'


def _paragrafo(*trechos: str, espaco_depois: int = 160) -> str:
    return f'<w:p><w:pPr><w:spacing w:after="{espaco_depois}"/></w:pPr>{"".join(trechos)}</w:p>'


def salvar_docx(transcricao: Transcricao, destino: Path, titulo: str, detalhes: str) -> Path:
    """Documento do Word com título, detalhes e cada trecho com o horário (e o falante, se houver)."""
    corpo = [
        _paragrafo(_trecho(titulo, negrito=True, tamanho=18), espaco_depois=60),
        _paragrafo(_trecho(detalhes, cor="808080", tamanho=10), espaco_depois=320),
    ]
    for bloco in transcricao.blocos:
        cabecalho = [_trecho(f"[{formatar_tempo(bloco.inicio)}] ", cor="808080", tamanho=10)]
        if bloco.falante:
            cor = CORES_PESSOAS[(int(bloco.falante.split()[-1]) - 1) % len(CORES_PESSOAS)]
            cabecalho.append(_trecho(f"{bloco.falante}: ", negrito=True, cor=cor, tamanho=11))
        corpo.append(_paragrafo(*cabecalho, _trecho(bloco.texto, tamanho=11)))
    documento = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
        + "".join(corpo)
        + '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1418" w:right="1418" w:bottom="1418" w:left="1418" w:header="709" w:footer="709" w:gutter="0"/>'
        "</w:sectPr></w:body></w:document>"
    )
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as pacote:
        pacote.writestr("[Content_Types].xml", _TIPOS_DOCX)
        pacote.writestr("_rels/.rels", _RELACOES_DOCX)
        pacote.writestr("word/document.xml", documento)
    return destino
