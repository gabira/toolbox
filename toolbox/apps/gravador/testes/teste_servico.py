import math
import struct
import subprocess
from datetime import datetime

from toolbox.apps.gravador import servico
from toolbox.nucleo.ffmpeg import caminho_ffmpeg, sondar


def teste_nome_e_tempo():
    assert servico.nome_padrao(datetime(2026, 9, 22, 14, 5)) == "Gravação 2026-09-22 14h05"
    assert servico.formatar_tempo(65.9) == "01:05"
    assert servico.formatar_tempo(3723) == "1:02:03"


# --- preenchimento de silêncio (o loopback não entrega nada quando o PC está mudo) ---

class _AudioFalso:
    def open(self, **_):
        return self

    def stop_stream(self):
        pass

    def close(self):
        pass


def teste_buraco_no_loopback_vira_silencio(tmp_path, monkeypatch):
    relogio = [0.0]
    monkeypatch.setattr(servico.time, "monotonic", lambda: relogio[0])
    info = {"defaultSampleRate": 1000, "maxInputChannels": 1, "index": 0}
    fonte = servico._Fonte(_AudioFalso(), type("pa", (), {"paFloat32": 1}), info, tmp_path / "s.f32", 0.0)
    bloco = struct.pack("<20f", *[0.5] * 20)  # 20 quadros = 20 ms

    for fim in (0.02, 0.04):                   # dois blocos em sequência, sem buraco
        relogio[0] = fim
        fonte._receber(bloco, 20, None, 0)
    relogio[0] = 1.02                          # quase 1 s sem dados (PC em silêncio)
    fonte._receber(bloco, 20, None, 0)
    assert fonte.nivel > 0.4

    faixa = fonte.encerrar(duracao=2.0)        # e mudo de novo até parar
    quadros = faixa.caminho.stat().st_size // 4
    assert quadros == 2000                     # 2 s exatos: a faixa não perde a sincronia
    amostras = struct.unpack(f"<{quadros}f", faixa.caminho.read_bytes())
    assert amostras[30] == 0.5 and amostras[500] == 0.0 and amostras[1010] == 0.5 and amostras[1500] == 0.0


# --- mixagem real com o FFmpeg ---

def _faixa_crua(caminho, taxa, canais, trechos):
    """`trechos`: lista de (segundos, com_tom). Grava float 32 cru, como a captura."""
    amostras = []
    for segundos, com_tom in trechos:
        for i in range(int(segundos * taxa)):
            valor = 0.3 * math.sin(2 * math.pi * 440 * i / taxa) if com_tom else 0.0
            amostras.extend([valor] * canais)
    caminho.write_bytes(struct.pack(f"<{len(amostras)}f", *amostras))
    return servico.Faixa(caminho, taxa, canais)


def teste_junta_microfone_e_computador_em_um_arquivo(tmp_path):
    # Você fala no 1º segundo; o participante fala no 2º (taxas e canais diferentes).
    mic = _faixa_crua(tmp_path / "mic.f32", 44100, 1, [(1, True), (1, False)])
    sistema = _faixa_crua(tmp_path / "sistema.f32", 48000, 2, [(1, False), (1.5, True)])

    saida = servico.mixar([mic, sistema], tmp_path, "flac", "reunião")

    assert saida.name == "reunião.flac"
    info = sondar(saida)
    assert abs(info.duracao_s - 2.5) < 0.05
    assert info.faixas_audio[0].taxa_amostragem == 48000
    assert info.faixas_audio[0].canais.startswith("stereo")
    relatorio = subprocess.run(
        [caminho_ffmpeg(), "-hide_banner", "-i", str(saida), "-af", "silencedetect=n=-40dB:d=0.3",
         "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8").stderr
    assert "silence_start" not in relatorio  # as duas vozes estão no arquivo
    assert not mic.caminho.exists() and not sistema.caminho.exists()  # temporários apagados


def teste_so_uma_fonte_nao_usa_amix(tmp_path):
    faixa = servico.Faixa(tmp_path / "s.f32", 48000, 2)
    comando = servico.montar_comando([faixa], tmp_path / "s.mp3", servico.FORMATOS["mp3"])
    filtro = comando[comando.index("-filter_complex") + 1]
    assert "amix" not in filtro and filtro.endswith("[saida]")
