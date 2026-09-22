"""Identificação do tipo de arquivo e compatibilidade com os apps."""

import mimetypes
from fnmatch import fnmatch
from pathlib import Path

# O registro do Windows costuma devolver tipos errados ou vazios para mídia
# (ex.: .ts vira "text/vnd.trolltech.linguist"), então as extensões comuns
# têm prioridade sobre o mimetypes.
TIPOS_CONHECIDOS = {
    # vídeo
    ".mp4": "video/mp4", ".m4v": "video/x-m4v", ".mkv": "video/x-matroska",
    ".webm": "video/webm", ".mov": "video/quicktime", ".avi": "video/x-msvideo",
    ".wmv": "video/x-ms-wmv", ".flv": "video/x-flv", ".ts": "video/mp2t",
    ".mts": "video/mp2t", ".m2ts": "video/mp2t", ".3gp": "video/3gpp",
    ".mpg": "video/mpeg", ".mpeg": "video/mpeg", ".ogv": "video/ogg",
    # áudio
    ".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".aac": "audio/aac",
    ".wav": "audio/wav", ".flac": "audio/flac", ".ogg": "audio/ogg",
    ".opus": "audio/opus", ".wma": "audio/x-ms-wma",
    # imagem
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".gif": "image/gif", ".bmp": "image/bmp", ".webp": "image/webp",
    ".tif": "image/tiff", ".tiff": "image/tiff",
    # documentos
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".rtf": "application/rtf",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".ods": "application/vnd.oasis.opendocument.spreadsheet",
    ".csv": "text/csv",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".ppt": "application/vnd.ms-powerpoint",
    ".odp": "application/vnd.oasis.opendocument.presentation",
    # texto
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".html": "text/html",
    ".htm": "text/html",
}

TIPO_DESCONHECIDO = "application/octet-stream"

NOMES_CATEGORIA = {
    "video": "vídeo",
    "audio": "áudio",
    "image": "imagem",
    "text": "texto",
    "application/pdf": "PDF",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "documento do Word",
    "application/msword": "documento do Word",
    "application/rtf": "documento RTF",
    "application/vnd.oasis.opendocument.text": "documento de texto",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "planilha do Excel",
    "application/vnd.ms-excel": "planilha do Excel",
    "application/vnd.oasis.opendocument.spreadsheet": "planilha",
    "text/csv": "planilha CSV",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "apresentação do PowerPoint",
    "application/vnd.ms-powerpoint": "apresentação do PowerPoint",
    "application/vnd.oasis.opendocument.presentation": "apresentação",
    "text/html": "página HTML",
    "text/markdown": "texto Markdown",
}


def tipo_mime(caminho: str | Path) -> str:
    extensao = Path(caminho).suffix.lower()
    if extensao in TIPOS_CONHECIDOS:
        return TIPOS_CONHECIDOS[extensao]
    tipo, _ = mimetypes.guess_type(str(caminho))
    return tipo or TIPO_DESCONHECIDO


def _tipo_pelo_conteudo(cabecalho: bytes, extensao: str) -> str | None:
    """Reconhece o formato pela assinatura dos primeiros bytes."""
    inicio = cabecalho[:4]
    if cabecalho.startswith(b"%PDF"):
        return "application/pdf"
    if cabecalho.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if cabecalho.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if cabecalho[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if inicio in (b"II*\x00", b"MM\x00*"):
        return "image/tiff"
    if inicio == b"RIFF":
        return {b"WEBP": "image/webp", b"WAVE": "audio/wav", b"AVI ": "video/x-msvideo"}.get(cabecalho[8:12])
    if cabecalho[4:8] == b"ftyp":
        marca = cabecalho[8:12]
        if marca in (b"M4A ", b"M4B "):
            return "audio/mp4"
        if marca in (b"heic", b"heix", b"mif1"):
            return "image/heic"
        return "video/quicktime" if marca == b"qt  " else "video/mp4"
    if inicio == b"\x1a\x45\xdf\xa3":  # Matroska / WebM
        if extensao == ".mka":
            return "audio/x-matroska"
        return "video/webm" if b"webm" in cabecalho[:64] else "video/x-matroska"
    if inicio == b"\x30\x26\xb2\x75":  # ASF
        return "audio/x-ms-wma" if extensao == ".wma" else "video/x-ms-wmv"
    if cabecalho.startswith(b"FLV"):
        return "video/x-flv"
    if inicio == b"\x00\x00\x01\xba":
        return "video/mpeg"
    if len(cabecalho) > 188 and cabecalho[0] == 0x47 and cabecalho[188] == 0x47:
        return "video/mp2t"
    if inicio == b"OggS":
        return "video/ogg" if extensao == ".ogv" else "audio/ogg"
    if inicio == b"fLaC":
        return "audio/flac"
    if cabecalho.startswith(b"ID3") or cabecalho[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return "audio/mpeg"
    if inicio == b"PK\x03\x04":  # ZIP: .docx, .xlsx, .odt etc. são ZIPs
        return TIPOS_CONHECIDOS.get(extensao, "application/zip")
    if cabecalho.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):  # OLE2: .doc, .xls, .ppt antigos
        return TIPOS_CONHECIDOS.get(extensao, "application/x-ole-storage")
    if cabecalho.startswith(b"{\\rtf"):
        return "application/rtf"
    return None


def detectar_tipo(caminho: str | Path) -> str:
    """Tipo pelo conteúdo; se a assinatura não for reconhecida, pela extensão."""
    try:
        with open(caminho, "rb") as arquivo_aberto:
            cabecalho = arquivo_aberto.read(512)
    except OSError:
        cabecalho = b""
    return _tipo_pelo_conteudo(cabecalho, Path(caminho).suffix.lower()) or tipo_mime(caminho)


def compativel(tipos_aceitos: list[str], mime: str) -> bool:
    """Aceita curingas no estilo "video/*"."""
    return any(fnmatch(mime, padrao) for padrao in tipos_aceitos)


FORMATOS_MIDIA = {
    "image/jpeg": "JPEG", "image/png": "PNG", "image/gif": "GIF", "image/bmp": "BMP",
    "image/webp": "WEBP", "image/tiff": "TIFF", "image/heic": "HEIC",
    "video/mp4": "MP4", "video/x-m4v": "M4V", "video/x-matroska": "MKV", "video/webm": "WEBM",
    "video/quicktime": "MOV", "video/x-msvideo": "AVI", "video/x-ms-wmv": "WMV", "video/x-flv": "FLV",
    "video/mp2t": "TS", "video/3gpp": "3GP", "video/mpeg": "MPEG", "video/ogg": "OGV",
    "audio/mpeg": "MP3", "audio/mp4": "M4A", "audio/aac": "AAC", "audio/wav": "WAV",
    "audio/flac": "FLAC", "audio/ogg": "OGG", "audio/opus": "OPUS", "audio/x-ms-wma": "WMA",
}


def nome_categoria(mime: str) -> str:
    if mime in NOMES_CATEGORIA:
        return NOMES_CATEGORIA[mime]
    return NOMES_CATEGORIA.get(mime.split("/")[0], "arquivo")


def descrever_tipo(mime: str) -> str:
    """Ex.: "imagem PNG", "vídeo MKV", "documento do Word"."""
    formato = FORMATOS_MIDIA.get(mime)
    return f"{nome_categoria(mime)} {formato}" if formato else nome_categoria(mime)


def tamanho_legivel(bytes_: int) -> str:
    valor = float(bytes_)
    for unidade in ("B", "KB", "MB", "GB"):
        if valor < 1024 or unidade == "GB":
            texto = f"{valor:.0f}" if unidade == "B" else f"{valor:.1f}"
            return f"{texto.replace('.', ',')} {unidade}"
        valor /= 1024
    return ""
