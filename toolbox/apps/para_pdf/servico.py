"""Conversão de arquivos para PDF (sem interface).

- Imagens: img2pdf — a imagem entra no PDF sem ser recomprimida (JPEG é copiado byte a byte).
  Imagens com transparência ou em formatos que o PDF não aceita direto (WEBP, BMP) viram PNG
  sem perda sobre fundo branco.
- Texto, Markdown e HTML: motor de texto do Qt (QTextDocument → QPdfWriter).
- Word, Excel, PowerPoint e OpenDocument: Microsoft Office instalado (via PowerShell/COM)
  ou, se não houver, LibreOffice.
"""

import os
import shutil
import subprocess
import tempfile
import time
from functools import cache
from io import BytesIO
from pathlib import Path

from toolbox.nucleo.erros import Cancelado, ErroUsuario
from toolbox.nucleo.ffmpeg import SEM_JANELA

TIPOS_IMAGEM = {"image/jpeg", "image/png", "image/bmp", "image/gif", "image/tiff", "image/webp"}
TIPOS_TEXTO = {"text/plain": "texto", "text/markdown": "markdown", "text/html": "html"}
TIPOS_OFFICE = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "word",
    "application/msword": "word",
    "application/rtf": "word",
    "application/vnd.oasis.opendocument.text": "word",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "excel",
    "application/vnd.ms-excel": "excel",
    "application/vnd.oasis.opendocument.spreadsheet": "excel",
    "text/csv": "excel",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "powerpoint",
    "application/vnd.ms-powerpoint": "powerpoint",
    "application/vnd.oasis.opendocument.presentation": "powerpoint",
}

NOMES_CATEGORIA = {
    "imagem": "Imagem", "texto": "Texto", "markdown": "Texto Markdown", "html": "Página HTML",
    "word": "Documento", "excel": "Planilha", "powerpoint": "Apresentação",
}
PROGRAMAS_OFFICE = {"word": "Microsoft Word", "excel": "Microsoft Excel", "powerpoint": "Microsoft PowerPoint"}

TEMPO_MAXIMO_OFFICE = 300  # s

PAGINA_IMAGEM = "imagem"   # página do tamanho exato da imagem
PAGINA_A4 = "a4"           # imagem ajustada numa folha A4 com margem


def categoria(tipo: str) -> str | None:
    if tipo in TIPOS_IMAGEM:
        return "imagem"
    if tipo in TIPOS_TEXTO:
        return TIPOS_TEXTO[tipo]
    return TIPOS_OFFICE.get(tipo)


# ------------------------------------------------------------ programas instalados

@cache
def office_instalado(programa: str) -> bool:
    """True se o Word/Excel/PowerPoint está registrado para automação (COM)."""
    try:
        import winreg
        nome = {"word": "Word.Application", "excel": "Excel.Application",
                "powerpoint": "PowerPoint.Application"}[programa]
        winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, nome))
        return True
    except (ImportError, OSError, KeyError):
        return False


@cache
def caminho_libreoffice() -> str | None:
    candidatos = [
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "LibreOffice/program/soffice.exe",
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "LibreOffice/program/soffice.exe",
    ]
    for candidato in candidatos:
        if candidato.is_file():
            return str(candidato)
    return shutil.which("soffice")


def motor(cat: str | None) -> tuple[str, str] | None:
    """(motor, rótulo para a tela) que converte a categoria, ou None se nada consegue."""
    if cat == "imagem":
        return ("imagem", "Sem perda de qualidade")
    if cat in ("texto", "markdown", "html"):
        return ("texto", "Página A4")
    if cat in PROGRAMAS_OFFICE:
        if office_instalado(cat):
            return ("office", f"Via {PROGRAMAS_OFFICE[cat]}")
        if caminho_libreoffice():
            return ("libreoffice", "Via LibreOffice")
    return None


def pode_converter(tipo: str) -> bool:
    return motor(categoria(tipo)) is not None


# ------------------------------------------------------------ imagens

def _preparar_imagem(caminho: Path):
    """Caminho (vai direto, sem recompressão) ou bytes PNG (quando precisa de ajuste)."""
    from PIL import Image, ImageOps

    with Image.open(caminho) as img:
        transparente = img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info
        direto = (
            (img.format == "JPEG" and img.mode in ("RGB", "L", "CMYK"))
            or (img.format in ("PNG", "TIFF", "GIF") and img.mode in ("RGB", "L", "1", "P") and not transparente)
        )
        if direto:
            return str(caminho)

        img = ImageOps.exif_transpose(img)
        if transparente:
            rgba = img.convert("RGBA")
            final = Image.new("RGB", rgba.size, "white")
            final.paste(rgba, mask=rgba.getchannel("A"))
        else:
            final = img.convert("RGB")
        buffer = BytesIO()
        final.save(buffer, "PNG")
        return buffer.getvalue()


def dimensoes_imagem(caminho) -> tuple[int, int] | None:
    try:
        from PIL import Image
        with Image.open(caminho) as img:
            return img.size
    except Exception:  # noqa: BLE001 — arquivo corrompido ou formato estranho: só não mostra
        return None


def _imagens_para_pdf(imagens: list[Path], saida: Path, pagina: str, ao_progresso, cancelado) -> None:
    import img2pdf

    preparadas = []
    for i, caminho in enumerate(imagens):
        if cancelado():
            raise Cancelado()
        try:
            preparadas.append(_preparar_imagem(caminho))
        except Exception as erro:  # noqa: BLE001
            raise ErroUsuario(f"Não consegui ler a imagem {caminho.name}.") from erro
        if ao_progresso:
            ao_progresso(0.8 * (i + 1) / len(imagens))

    opcoes = {"title": imagens[0].stem, "creator": "TOOLBOX"}
    if pagina == PAGINA_A4:
        a4 = (img2pdf.mm_to_pt(210), img2pdf.mm_to_pt(297))
        margem = img2pdf.mm_to_pt(10)
        opcoes["layout_fun"] = img2pdf.get_layout_fun(a4, None, (margem, margem), img2pdf.FitMode.into, True)
    try:
        dados = img2pdf.convert(preparadas, **opcoes)
    except Exception:  # noqa: BLE001 — algum formato que o img2pdf recusou: vai tudo como PNG
        dados = img2pdf.convert([p if isinstance(p, bytes) else _forcar_png(Path(p)) for p in preparadas],
                                **opcoes)
    saida.write_bytes(dados)


def _forcar_png(caminho: Path) -> bytes:
    from PIL import Image
    with Image.open(caminho) as img:
        buffer = BytesIO()
        img.convert("RGB").save(buffer, "PNG")
        return buffer.getvalue()


# ------------------------------------------------------------ texto

def _ler_texto(caminho: Path) -> str:
    bruto = caminho.read_bytes()
    for codificacao in ("utf-8-sig", "cp1252"):
        try:
            return bruto.decode(codificacao)
        except UnicodeDecodeError:
            continue
    return bruto.decode("utf-8", "replace")


def _texto_para_pdf(caminho: Path, cat: str, saida: Path) -> None:
    from PySide6.QtCore import QMarginsF
    from PySide6.QtGui import QFont, QPageLayout, QPageSize, QPdfWriter, QTextDocument

    texto = _ler_texto(caminho)
    documento = QTextDocument()
    documento.setDefaultFont(QFont("Segoe UI", 11))
    if cat == "markdown":
        documento.setMarkdown(texto)
    elif cat == "html":
        documento.setHtml(texto)
    else:
        documento.setPlainText(texto)

    escritor = QPdfWriter(str(saida))
    escritor.setPageSize(QPageSize(QPageSize.A4))
    escritor.setPageMargins(QMarginsF(20, 20, 20, 20), QPageLayout.Millimeter)
    escritor.setTitle(caminho.stem)
    escritor.setCreator("TOOLBOX")
    documento.print_(escritor)
    del escritor  # fecha o arquivo


# ------------------------------------------------------------ Office / LibreOffice

# Os caminhos vão por variável de ambiente: nada de aspas quebrando o script.
_SCRIPTS_OFFICE = {
    "word": r"""
$app = New-Object -ComObject Word.Application
$app.Visible = $false
$app.DisplayAlerts = 0
try {
    $doc = $app.Documents.Open($env:TB_ENTRADA, $false, $true, $false)
    $doc.ExportAsFixedFormat($env:TB_SAIDA, 17)
    $doc.Close(0)
} finally { $app.Quit() }
""",
    "excel": r"""
$app = New-Object -ComObject Excel.Application
$app.Visible = $false
$app.DisplayAlerts = $false
try {
    $pasta = $app.Workbooks.Open($env:TB_ENTRADA, 0, $true)
    $pasta.ExportAsFixedFormat(0, $env:TB_SAIDA)
    $pasta.Close($false)
} finally { $app.Quit() }
""",
    "powerpoint": r"""
$app = New-Object -ComObject PowerPoint.Application
try {
    $apresentacao = $app.Presentations.Open($env:TB_ENTRADA, -1, 0, 0)
    $apresentacao.SaveAs($env:TB_SAIDA, 32)
    $apresentacao.Close()
} finally { $app.Quit() }
""",
}


def _esperar(processo: subprocess.Popen, cancelado, nome_programa: str) -> str:
    """Espera o processo terminar (ou o usuário cancelar). Retorna o stderr."""
    inicio = time.monotonic()
    while processo.poll() is None:
        if cancelado():
            processo.kill()
            raise Cancelado()
        if time.monotonic() - inicio > TEMPO_MAXIMO_OFFICE:
            processo.kill()
            raise ErroUsuario(f"O {nome_programa} demorou demais para responder.")
        time.sleep(0.2)
    return (processo.stderr.read() or b"").decode("utf-8", "replace") if processo.stderr else ""


def _office_para_pdf(caminho: Path, cat: str, saida: Path, cancelado) -> None:
    processo = subprocess.Popen(
        ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-Command", _SCRIPTS_OFFICE[cat]],
        env={**os.environ, "TB_ENTRADA": str(caminho.resolve()), "TB_SAIDA": str(saida.resolve())},
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, creationflags=SEM_JANELA,
    )
    erros = _esperar(processo, cancelado, PROGRAMAS_OFFICE[cat])
    if processo.returncode != 0 or not saida.is_file():
        linha = next((l.strip() for l in erros.splitlines() if l.strip()), "")
        raise ErroUsuario(f"O {PROGRAMAS_OFFICE[cat]} não conseguiu converter o arquivo."
                          + (f"\n{linha[:200]}" if linha else ""))


def _libreoffice_para_pdf(caminho: Path, saida: Path, cancelado) -> None:
    with tempfile.TemporaryDirectory() as temporaria:
        perfil = Path(temporaria) / "perfil"  # perfil isolado: funciona mesmo com o LibreOffice aberto
        processo = subprocess.Popen(
            [caminho_libreoffice(), "--headless", "--norestore",
             f"-env:UserInstallation={perfil.as_uri()}",
             "--convert-to", "pdf", "--outdir", temporaria, str(caminho)],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, creationflags=SEM_JANELA,
        )
        _esperar(processo, cancelado, "LibreOffice")
        gerado = Path(temporaria) / f"{caminho.stem}.pdf"
        if not gerado.is_file():
            raise ErroUsuario("O LibreOffice não conseguiu converter o arquivo.")
        shutil.move(str(gerado), saida)


# ------------------------------------------------------------ entrada principal

def converter(entradas: list, tipo: str, saida, pagina: str = PAGINA_IMAGEM,
              ao_progresso=None, cancelado=lambda: False) -> Path:
    """Converte `entradas` (várias só para imagens) em `saida` (.pdf). Retorna o PDF criado."""
    entradas = [Path(e) for e in entradas]
    saida = Path(saida)
    if not entradas or not all(e.is_file() for e in entradas):
        raise ErroUsuario("O arquivo não foi encontrado.")
    if not saida.parent.is_dir():
        raise ErroUsuario("A pasta de destino não existe.")

    cat = categoria(tipo)
    escolhido = motor(cat)
    if escolhido is None:
        if cat in PROGRAMAS_OFFICE:
            raise ErroUsuario(f"Para converter este arquivo é preciso ter o {PROGRAMAS_OFFICE[cat]} "
                              "ou o LibreOffice instalado.")
        raise ErroUsuario("Este tipo de arquivo não pode ser convertido em PDF.")

    try:
        if escolhido[0] == "imagem":
            _imagens_para_pdf(entradas, saida, pagina, ao_progresso, cancelado)
        elif escolhido[0] == "texto":
            _texto_para_pdf(entradas[0], cat, saida)
        elif escolhido[0] == "office":
            _office_para_pdf(entradas[0], cat, saida, cancelado)
        else:
            _libreoffice_para_pdf(entradas[0], saida, cancelado)
    except BaseException:
        saida.unlink(missing_ok=True)  # nada de PDF pela metade
        raise

    if ao_progresso:
        ao_progresso(1.0)
    return saida
