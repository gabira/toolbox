"""Reconhecimento de links colados/arrastados na TOOLBOX.

Links viram um "tipo" no mesmo formato dos arquivos ("link/youtube", "link/web"),
então os apps declaram em `tipos_aceitos` que aceitam links do mesmo jeito que aceitam "video/*".
"""

import re
from urllib.parse import parse_qs, urlparse

TIPO_YOUTUBE = "link/youtube"
TIPO_WEB = "link/web"

HOSTS_YOUTUBE = {"youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be", "youtube-nocookie.com"}

# Links com http(s) ou links do YouTube colados sem o "https://".
_RE_LINK = re.compile(
    r"https?://[^\s<>\"']+"
    r"|(?<![\w.])(?:www\.|m\.|music\.)?(?:youtube\.com|youtu\.be)/[^\s<>\"']+",
    re.IGNORECASE,
)


def extrair_links(texto: str) -> list[str]:
    """Links do texto, na ordem, sem repetidos e sem pontuação grudada no fim."""
    vistos, links = set(), []
    for achado in _RE_LINK.findall(texto or ""):
        link = achado.rstrip(".,;:!?)]}")
        if not link.lower().startswith(("http://", "https://")):
            link = "https://" + link
        if link not in vistos:
            vistos.add(link)
            links.append(link)
    return links


def _host(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def e_youtube(url: str) -> bool:
    """True para links de vídeo, short, live ou playlist do YouTube."""
    host = _host(url)
    if host not in HOSTS_YOUTUBE:
        return False
    partes = urlparse(url)
    if host == "youtu.be":
        return len(partes.path.strip("/")) > 0
    consulta = parse_qs(partes.query)
    caminho = partes.path.rstrip("/")
    return (
        (caminho == "/watch" and "v" in consulta)
        or (caminho == "/playlist" and "list" in consulta)
        or caminho.startswith(("/shorts/", "/live/", "/embed/"))
    )


def tipo_links(links: list[str]) -> str:
    return TIPO_YOUTUBE if links and all(e_youtube(l) for l in links) else TIPO_WEB


def descrever(links: list[str]) -> str:
    """Resumo curto para a interface. Ex.: "vídeo do YouTube", "3 links do YouTube"."""
    if not links:
        return ""
    youtube = tipo_links(links) == TIPO_YOUTUBE
    if len(links) > 1:
        return f"{len(links)} links do YouTube" if youtube else f"{len(links)} links"
    if not youtube:
        return "link"
    caminho = urlparse(links[0]).path
    if caminho.startswith("/playlist"):
        return "playlist do YouTube"
    if caminho.startswith("/shorts/"):
        return "short do YouTube"
    return "vídeo do YouTube"


def rotulo_curto(url: str) -> str:
    """Ex.: "youtube.com/watch?v=jNQXAC9IVRw"."""
    partes = urlparse(url)
    rotulo = _host(url) + partes.path + (f"?{partes.query}" if partes.query else "")
    return rotulo.rstrip("/")
