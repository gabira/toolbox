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
}

TIPO_DESCONHECIDO = "application/octet-stream"

NOMES_CATEGORIA = {
    "video": "vídeo",
    "audio": "áudio",
    "image": "imagem",
    "application/pdf": "PDF",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "Word",
}


def tipo_mime(caminho: str | Path) -> str:
    extensao = Path(caminho).suffix.lower()
    if extensao in TIPOS_CONHECIDOS:
        return TIPOS_CONHECIDOS[extensao]
    tipo, _ = mimetypes.guess_type(str(caminho))
    return tipo or TIPO_DESCONHECIDO


def compativel(tipos_aceitos: list[str], mime: str) -> bool:
    """Aceita curingas no estilo "video/*"."""
    return any(fnmatch(mime, padrao) for padrao in tipos_aceitos)


def nome_categoria(mime: str) -> str:
    if mime in NOMES_CATEGORIA:
        return NOMES_CATEGORIA[mime]
    return NOMES_CATEGORIA.get(mime.split("/")[0], "arquivo")


def tamanho_legivel(bytes_: int) -> str:
    valor = float(bytes_)
    for unidade in ("B", "KB", "MB", "GB"):
        if valor < 1024 or unidade == "GB":
            texto = f"{valor:.0f}" if unidade == "B" else f"{valor:.1f}"
            return f"{texto.replace('.', ',')} {unidade}"
        valor /= 1024
    return ""
