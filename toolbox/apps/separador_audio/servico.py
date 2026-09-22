"""Extração da faixa de áudio de um vídeo com FFmpeg (sem dependência de Qt).

"Qualidade ótima" = por padrão a faixa é copiada sem reencodar (`-c:a copy`)
para um contêiner compatível com o codec original, então não há perda nenhuma.
"""

import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from toolbox.nucleo.erros import Cancelado, ErroUsuario
from toolbox.nucleo.ffmpeg import SEM_JANELA, FaixaAudio, caminho_ffmpeg, sondar


@dataclass(frozen=True)
class Formato:
    id: str
    nome: str
    descricao: str
    argumentos: tuple[str, ...]
    extensao: str | None  # None = depende do codec original
    selo: str = ""


FORMATOS = {f.id: f for f in (
    Formato("original", "Original", "Cópia exata da faixa, sem perdas", ("-c:a", "copy"), None, "Recomendado"),
    Formato("flac", "FLAC", "Sem perdas, compactado", ("-c:a", "flac", "-compression_level", "8"), "flac"),
    Formato("wav", "WAV 24 bits", "Sem perdas, sem compressão", ("-c:a", "pcm_s24le"), "wav"),
    Formato("mp3", "MP3 320 kb/s", "Máxima compatibilidade", ("-c:a", "libmp3lame", "-b:a", "320k"), "mp3"),
)}

# Contêiner que recebe cada codec sem reencodar.
EXTENSAO_POR_CODEC = {
    "aac": "m4a", "alac": "m4a", "mp3": "mp3", "opus": "opus", "vorbis": "ogg",
    "flac": "flac", "ac3": "ac3", "eac3": "eac3",
    "pcm_s16le": "wav", "pcm_s24le": "wav", "pcm_s32le": "wav", "pcm_f32le": "wav",
    "pcm_f64le": "wav", "pcm_u8": "wav", "pcm_alaw": "wav", "pcm_mulaw": "wav",
}
EXTENSAO_UNIVERSAL = "mka"  # Matroska aceita praticamente qualquer codec

NOMES_CODEC = {
    "aac": "AAC", "mp3": "MP3", "opus": "Opus", "vorbis": "Vorbis", "flac": "FLAC",
    "alac": "ALAC", "ac3": "Dolby Digital (AC-3)", "eac3": "Dolby Digital Plus (E-AC-3)",
    "dts": "DTS", "truehd": "Dolby TrueHD",
}
NOMES_CANAIS = {"mono": "mono", "stereo": "estéreo"}


def extensao_original(codec: str) -> str:
    return EXTENSAO_POR_CODEC.get(codec, EXTENSAO_UNIVERSAL)


def extensao_saida(formato: Formato, codec: str) -> str:
    return formato.extensao or extensao_original(codec)


def nome_codec(codec: str) -> str:
    if codec.startswith("pcm_"):
        return "PCM"
    return NOMES_CODEC.get(codec, codec.upper())


def detalhes_faixa(faixa: FaixaAudio) -> list[str]:
    """Ex.: ["48 kHz", "estéreo", "160 kb/s"]."""
    detalhes = []
    if faixa.taxa_amostragem:
        khz = faixa.taxa_amostragem / 1000
        detalhes.append(f"{khz:g} kHz".replace(".", ","))
    if faixa.canais:
        canais = faixa.canais.split("(")[0]
        detalhes.append(NOMES_CANAIS.get(canais, canais))
    if faixa.bitrate_kbps:
        detalhes.append(f"{faixa.bitrate_kbps} kb/s")
    return detalhes


def formatar_duracao(segundos: float | None) -> str:
    if segundos is None:
        return ""
    total = int(round(segundos))
    horas, resto = divmod(total, 3600)
    minutos, seg = divmod(resto, 60)
    return f"{horas}:{minutos:02d}:{seg:02d}" if horas else f"{minutos}:{seg:02d}"


_INVALIDOS_WINDOWS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVADOS_WINDOWS = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
                       *(f"LPT{i}" for i in range(1, 10))}


def limpar_nome(nome: str | None, extensao: str = "") -> str:
    """Deixa o nome digitado válido como nome de arquivo do Windows ("" se não sobrar nada)."""
    nome = _INVALIDOS_WINDOWS.sub("", nome or "").strip()
    # Quem digita "musica.m4a" quer "musica", não "musica.m4a.m4a".
    if extensao and nome.lower().endswith("." + extensao.lower()):
        nome = nome[: -len(extensao) - 1]
    nome = nome.rstrip(". ")[:180]
    if nome.upper() in _RESERVADOS_WINDOWS:
        nome += "_"
    return nome


def caminho_livre(pasta: Path, nome_base: str, extensao: str) -> Path:
    """Nunca sobrescreve: "video.m4a", "video (2).m4a", "video (3).m4a"..."""
    candidato = pasta / f"{nome_base}.{extensao}"
    numero = 2
    while candidato.exists():
        candidato = pasta / f"{nome_base} ({numero}).{extensao}"
        numero += 1
    return candidato


def montar_comando(entrada: Path, saida: Path, formato: Formato, faixa: int = 0) -> list[str]:
    return [
        caminho_ffmpeg(), "-hide_banner", "-nostdin", "-loglevel", "error", "-n",
        "-i", str(entrada),
        "-map", f"0:a:{faixa}", "-vn", "-sn", "-dn",
        *formato.argumentos,
        "-map_metadata", "0",
        "-progress", "pipe:1", "-nostats",
        str(saida),
    ]


def extrair(entrada, pasta, id_formato: str = "original", ao_progresso=None,
            cancelado=lambda: False, faixa: int = 0, nome: str | None = None) -> Path:
    """Extrai a faixa de áudio `faixa` de `entrada` para `pasta`. Retorna o arquivo criado.

    `nome` (opcional) é o nome do arquivo de saída sem extensão; vazio = nome do vídeo.
    """
    entrada, pasta = Path(entrada), Path(pasta)
    if not entrada.is_file():
        raise ErroUsuario("O vídeo não foi encontrado.")
    if not pasta.is_dir():
        raise ErroUsuario("A pasta de destino não existe.")

    info = sondar(entrada)
    if faixa >= len(info.faixas_audio):
        raise ErroUsuario("Este vídeo não tem trilha de áudio.")

    formato = FORMATOS[id_formato]
    extensao = extensao_saida(formato, info.faixas_audio[faixa].codec)
    saida = caminho_livre(pasta, limpar_nome(nome, extensao) or entrada.stem, extensao)
    comando = montar_comando(entrada, saida, formato, faixa)

    with tempfile.TemporaryFile() as erros:
        processo = subprocess.Popen(
            comando, stdout=subprocess.PIPE, stderr=erros, text=True,
            encoding="utf-8", errors="replace", creationflags=SEM_JANELA,
        )
        try:
            for linha in processo.stdout:
                if cancelado():
                    raise Cancelado()
                chave, _, valor = linha.strip().partition("=")
                if chave == "out_time_us" and valor.isdigit() and info.duracao_s and ao_progresso:
                    ao_progresso(min(1.0, int(valor) / 1_000_000 / info.duracao_s))
            processo.wait()
        except BaseException:
            processo.kill()
            processo.wait()
            saida.unlink(missing_ok=True)
            raise

        if processo.returncode != 0:
            saida.unlink(missing_ok=True)
            erros.seek(0)
            linhas = erros.read().decode("utf-8", "replace").strip().splitlines()
            detalhe = f"\n{linhas[-1]}" if linhas else ""
            raise ErroUsuario(f"O FFmpeg não conseguiu extrair o áudio.{detalhe}")

    if ao_progresso:
        ao_progresso(1.0)
    return saida
