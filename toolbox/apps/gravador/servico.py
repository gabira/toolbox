"""Gravação do microfone + som do computador (loopback WASAPI) em um único arquivo.

Cada fonte é gravada crua (float 32 bits, taxa nativa do dispositivo) num arquivo
temporário. Ao parar, o FFmpeg junta as duas faixas no formato escolhido.
O WASAPI não entrega nada pelo loopback enquanto o PC está em silêncio, então os
buracos são preenchidos com zeros pelo relógio — assim as faixas não perdem a sincronia.
"""

import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from toolbox.nucleo.erros import ErroUsuario
from toolbox.nucleo.ffmpeg import SEM_JANELA, caminho_ffmpeg
from toolbox.nucleo.nomes import caminho_livre, limpar_nome

SUFIXO_LOOPBACK = " [Loopback]"
BURACO_MINIMO_S = 0.2  # intervalos maiores que isso sem dados viram silêncio


@dataclass(frozen=True)
class Formato:
    id: str
    nome: str
    descricao: str
    argumentos: tuple[str, ...]
    extensao: str
    selo: str = ""


FORMATOS = {f.id: f for f in (
    Formato("flac", "FLAC", "Sem perdas, compactado",
            ("-c:a", "flac", "-compression_level", "8", "-sample_fmt", "s32", "-bits_per_raw_sample", "24"),
            "flac", "Recomendado"),
    Formato("wav", "WAV 24 bits", "Sem perdas, sem compressão", ("-c:a", "pcm_s24le"), "wav"),
    Formato("mp3", "MP3 320 kb/s", "Menor e compatível com tudo", ("-c:a", "libmp3lame", "-b:a", "320k"), "mp3"),
)}


@dataclass(frozen=True)
class Dispositivo:
    nome: str
    padrao: bool = False


@dataclass(frozen=True)
class Faixa:
    """Arquivo cru gravado de uma fonte."""
    caminho: Path
    taxa: int
    canais: int


def nome_padrao(agora: datetime | None = None) -> str:
    return (agora or datetime.now()).strftime("Gravação %Y-%m-%d %Hh%M")


def formatar_tempo(segundos: float) -> str:
    total = int(segundos)
    horas, resto = divmod(total, 3600)
    minutos, seg = divmod(resto, 60)
    return f"{horas}:{minutos:02d}:{seg:02d}" if horas else f"{minutos:02d}:{seg:02d}"


# ------------------------------------------------------------------ dispositivos

def _pyaudio():
    import pyaudiowpatch

    return pyaudiowpatch


def _wasapi(pa, audio):
    return audio.get_host_api_info_by_type(pa.paWASAPI)


def listar_dispositivos() -> tuple[list[Dispositivo], list[Dispositivo]]:
    """(microfones, saídas de som) do WASAPI, com o padrão do Windows marcado."""
    pa = _pyaudio()
    audio = pa.PyAudio()
    try:
        api = _wasapi(pa, audio)
        try:
            padrao_mic = audio.get_device_info_by_index(api["defaultInputDevice"])["name"]
        except OSError:
            padrao_mic = ""  # nenhum microfone ligado
        try:
            padrao_saida = audio.get_default_wasapi_loopback()["name"].removesuffix(SUFIXO_LOOPBACK)
        except (OSError, LookupError):
            padrao_saida = ""
        microfones, saidas = [], []
        for info in audio.get_device_info_generator_by_host_api(host_api_index=api["index"]):
            if info.get("isLoopbackDevice"):
                nome = info["name"].removesuffix(SUFIXO_LOOPBACK)
                saidas.append(Dispositivo(nome, nome == padrao_saida))
            elif info["maxInputChannels"] > 0:
                microfones.append(Dispositivo(info["name"], info["name"] == padrao_mic))
        return microfones, saidas
    finally:
        audio.terminate()


# ------------------------------------------------------------------ gravação

class _Fonte:
    """Um fluxo de entrada gravando num arquivo cru, com nível e preenchimento de silêncio."""

    def __init__(self, audio, pa, info: dict, caminho: Path, inicio: float):
        self.taxa = int(info["defaultSampleRate"])
        self.canais = max(1, min(2, info["maxInputChannels"]))
        self.caminho = caminho
        self.nivel = 0.0
        self._bytes_quadro = 4 * self.canais
        self._inicio = inicio
        self._quadros = 0
        self._ultimo = 0.0  # instante (desde o início) do último bloco recebido
        self._trava = threading.Lock()
        self._arquivo = open(caminho, "wb")
        self._fluxo = audio.open(
            format=pa.paFloat32, channels=self.canais, rate=self.taxa, input=True,
            input_device_index=info["index"], frames_per_buffer=self.taxa // 50,
            stream_callback=self._receber,
        )

    def _silencio_ate(self, quadros_esperados: int) -> None:
        falta = quadros_esperados - self._quadros
        if falta > 0:
            self._arquivo.write(bytes(falta * self._bytes_quadro))
            self._quadros += falta

    def _receber(self, dados, quadros, _tempo, _status):
        with self._trava:
            if self._arquivo.closed:
                return None, 1  # paComplete
            agora = time.monotonic() - self._inicio
            # Só um buraco de verdade (fluxo parado) vira silêncio; o atraso normal entre blocos não.
            if agora - self._ultimo > BURACO_MINIMO_S + quadros / self.taxa:
                self._silencio_ate(int(agora * self.taxa) - quadros)
            self._ultimo = agora
            self._arquivo.write(dados)
            self._quadros += quadros
            amostras = memoryview(dados).cast("f")
            self.nivel = max(self.nivel * 0.85, min(1.0, max(map(abs, amostras), default=0.0)))
        return None, 0  # paContinue

    def encerrar(self, duracao: float) -> Faixa:
        try:
            self._fluxo.stop_stream()
            self._fluxo.close()
        except OSError:
            pass  # dispositivo desconectado no meio da gravação
        with self._trava:
            if duracao - self._ultimo > BURACO_MINIMO_S:
                self._silencio_ate(int(duracao * self.taxa))  # PC em silêncio até o fim
            self._arquivo.close()
        return Faixa(self.caminho, self.taxa, self.canais)


class Gravacao:
    """Grava o microfone e/ou o som do computador ao mesmo tempo.

    `microfone`/`saida` são nomes de dispositivo ("" = não gravar aquela fonte;
    None = padrão do Windows).
    """

    def __init__(self, pasta_temporaria: Path, microfone: str | None = None, saida: str | None = None):
        pa = _pyaudio()
        self._pa = pa
        self._audio = pa.PyAudio()
        self._fontes: dict[str, _Fonte] = {}
        self._silencio = None
        self._inicio = time.monotonic()
        pasta_temporaria.mkdir(parents=True, exist_ok=True)
        marca = datetime.now().strftime("%Y%m%d-%H%M%S")
        try:
            info_mic = self._achar_microfone(microfone)
            info_saida = self._achar_loopback(saida)
            if not info_mic and not info_saida:
                raise ErroUsuario("Nenhum microfone nem saída de som disponível para gravar.")
            if info_saida:
                self._manter_loopback_acordado(info_saida)
                self._fontes["sistema"] = _Fonte(
                    self._audio, pa, info_saida, pasta_temporaria / f"{marca}-sistema.f32", self._inicio)
            if info_mic:
                self._fontes["mic"] = _Fonte(
                    self._audio, pa, info_mic, pasta_temporaria / f"{marca}-mic.f32", self._inicio)
        except BaseException:
            self.parar()
            raise

    def _dispositivos(self):
        api = _wasapi(self._pa, self._audio)
        return list(self._audio.get_device_info_generator_by_host_api(host_api_index=api["index"]))

    def _achar_microfone(self, nome: str | None) -> dict | None:
        if nome == "":
            return None
        mics = [d for d in self._dispositivos() if d["maxInputChannels"] > 0 and not d.get("isLoopbackDevice")]
        if nome is None:
            padrao = _wasapi(self._pa, self._audio)["defaultInputDevice"]
            return next((d for d in mics if d["index"] == padrao), mics[0] if mics else None)
        return next((d for d in mics if d["name"] == nome), None)

    def _achar_loopback(self, nome: str | None) -> dict | None:
        if nome == "":
            return None
        if nome is None:
            try:
                return self._audio.get_default_wasapi_loopback()
            except (OSError, LookupError):
                return None
        return next((d for d in self._dispositivos()
                     if d.get("isLoopbackDevice") and d["name"] == nome + SUFIXO_LOOPBACK), None)

    def _manter_loopback_acordado(self, info_loopback: dict) -> None:
        """Toca silêncio na mesma saída: o loopback continua entregando dados."""
        nome = info_loopback["name"].removesuffix(SUFIXO_LOOPBACK)
        saida = next((d for d in self._dispositivos()
                      if d["maxOutputChannels"] > 0 and d["name"] == nome), None)
        if not saida:
            return
        canais = max(1, min(2, saida["maxOutputChannels"]))
        taxa = int(saida["defaultSampleRate"])
        vazio = bytes(4 * canais * (taxa // 50))
        try:
            self._silencio = self._audio.open(
                format=self._pa.paFloat32, channels=canais, rate=taxa, output=True,
                output_device_index=saida["index"], frames_per_buffer=taxa // 50,
                stream_callback=lambda *_: (vazio, 0),
            )
        except OSError:
            self._silencio = None  # sem problema: o relógio preenche os buracos

    @property
    def fontes(self) -> set[str]:
        return set(self._fontes)

    @property
    def duracao(self) -> float:
        return time.monotonic() - self._inicio

    def nivel(self, fonte: str) -> float:
        return self._fontes[fonte].nivel if fonte in self._fontes else 0.0

    def parar(self) -> dict[str, Faixa]:
        duracao = self.duracao
        faixas = {nome: fonte.encerrar(duracao) for nome, fonte in self._fontes.items()}
        self._fontes = {}
        if self._silencio:
            try:
                self._silencio.stop_stream()
                self._silencio.close()
            except OSError:
                pass
            self._silencio = None
        if self._audio:
            self._audio.terminate()
            self._audio = None
        return faixas


# ------------------------------------------------------------------ mixagem

def _entrada(faixa: Faixa) -> list[str]:
    return ["-f", "f32le", "-ar", str(faixa.taxa), "-ac", str(faixa.canais), "-i", str(faixa.caminho)]


def _para_estereo(indice: int, faixa: Faixa, taxa: int, rotulo: str) -> str:
    mono = "pan=stereo|c0=c0|c1=c0," if faixa.canais == 1 else ""
    return f"[{indice}:a]{mono}aresample={taxa},aformat=sample_fmts=fltp:channel_layouts=stereo[{rotulo}]"


def montar_comando(faixas: list[Faixa], saida: Path, formato: Formato) -> list[str]:
    """Uma ou duas faixas cruas → um arquivo estéreo na maior taxa entre elas."""
    taxa = max(f.taxa for f in faixas)
    entradas = [arg for faixa in faixas for arg in _entrada(faixa)]
    rotulos = [f"f{i}" for i in range(len(faixas))]
    filtros = [_para_estereo(i, faixa, taxa, rotulo) for i, (faixa, rotulo) in enumerate(zip(faixas, rotulos))]
    if len(faixas) > 1:
        # normalize=0: cada voz mantém o volume original; o limitador evita estourar quando se sobrepõem.
        filtros.append("".join(f"[{r}]" for r in rotulos)
                       + f"amix=inputs={len(faixas)}:duration=longest:normalize=0,alimiter=limit=0.98[saida]")
    else:
        filtros[0] = filtros[0].replace(f"[{rotulos[0]}]", "[saida]")
    return [
        caminho_ffmpeg(), "-hide_banner", "-nostdin", "-loglevel", "error", "-n",
        *entradas, "-filter_complex", ";".join(filtros), "-map", "[saida]",
        *formato.argumentos, str(saida),
    ]


def mixar(faixas: list[Faixa], pasta, id_formato: str = "flac", nome: str | None = None) -> Path:
    """Junta as faixas gravadas em um arquivo em `pasta`. Apaga os temporários se der certo."""
    pasta = Path(pasta)
    faixas = [f for f in faixas if f.caminho.is_file() and f.caminho.stat().st_size > 0]
    if not faixas:
        raise ErroUsuario("Nada foi gravado.")
    if not pasta.is_dir():
        raise ErroUsuario("A pasta de destino não existe.")
    formato = FORMATOS[id_formato]
    saida = caminho_livre(pasta, limpar_nome(nome, formato.extensao) or nome_padrao(), formato.extensao)

    with tempfile.TemporaryFile() as erros:
        processo = subprocess.run(montar_comando(faixas, saida, formato), stdout=subprocess.DEVNULL,
                                  stderr=erros, creationflags=SEM_JANELA)
        if processo.returncode != 0:
            saida.unlink(missing_ok=True)
            erros.seek(0)
            linhas = erros.read().decode("utf-8", "replace").strip().splitlines()
            detalhe = f"\n{linhas[-1]}" if linhas else ""
            pasta_crua = faixas[0].caminho.parent
            raise ErroUsuario(f"Não foi possível salvar a gravação. Os arquivos brutos estão em {pasta_crua}.{detalhe}")

    for faixa in faixas:
        faixa.caminho.unlink(missing_ok=True)
    return saida
