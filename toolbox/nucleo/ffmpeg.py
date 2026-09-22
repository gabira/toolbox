"""Acesso ao FFmpeg embarcado (imageio-ffmpeg) e leitura das faixas de mídia.

O pacote traz só o executável ffmpeg (sem ffprobe), então a sondagem é feita
lendo o relatório de `ffmpeg -i`.
"""

import re
import subprocess
import sys
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

# Evita que janelas de console pisquem quando o app roda com pythonw.
SEM_JANELA = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

_RE_DURACAO = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")
_RE_FLUXO = re.compile(r"Stream #\d+:\d+.*?: (Audio|Video): (\w+)(.*)")
_RE_TAXA = re.compile(r"(\d+) Hz")
_RE_BITRATE = re.compile(r"(\d+) kb/s")


@cache
def caminho_ffmpeg() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


@dataclass
class FaixaAudio:
    codec: str
    taxa_amostragem: int | None = None
    canais: str | None = None
    bitrate_kbps: int | None = None


@dataclass
class InfoMidia:
    duracao_s: float | None = None
    tem_video: bool = False
    faixas_audio: list[FaixaAudio] = field(default_factory=list)


def interpretar_relatorio(texto: str) -> InfoMidia:
    info = InfoMidia()
    if achado := _RE_DURACAO.search(texto):
        h, m, s = achado.groups()
        info.duracao_s = int(h) * 3600 + int(m) * 60 + float(s)

    for linha in texto.splitlines():
        achado = _RE_FLUXO.search(linha)
        if not achado:
            continue
        tipo, codec, resto = achado.groups()
        if tipo == "Video":
            info.tem_video = True
            continue
        faixa = FaixaAudio(codec=codec)
        partes = [p.strip() for p in resto.split(",")]
        for i, parte in enumerate(partes):
            if taxa := _RE_TAXA.fullmatch(parte):
                faixa.taxa_amostragem = int(taxa.group(1))
                if i + 1 < len(partes):
                    faixa.canais = partes[i + 1]
        if bitrate := _RE_BITRATE.search(resto):
            faixa.bitrate_kbps = int(bitrate.group(1))
        info.faixas_audio.append(faixa)
    return info


def sondar(caminho: str | Path) -> InfoMidia:
    resultado = subprocess.run(
        [caminho_ffmpeg(), "-hide_banner", "-nostdin", "-i", str(caminho)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        creationflags=SEM_JANELA,
    )
    # Sem arquivo de saída o ffmpeg sempre termina com erro; o relatório vem no stderr.
    return interpretar_relatorio(resultado.stderr)
