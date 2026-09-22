from toolbox.nucleo.ffmpeg import interpretar_relatorio

RELATORIO = """
Input #0, mov,mp4,m4a,3gp,3g2,mj2, from 'filme.mp4':
  Duration: 01:02:03.50, start: 0.000000, bitrate: 2150 kb/s
  Stream #0:0[0x1](und): Video: h264 (High) (avc1 / 0x31637661), yuv420p, 1920x1080, 1990 kb/s, 30 fps
  Stream #0:1[0x2](por): Audio: aac (LC) (mp4a / 0x6134706D), 48000 Hz, stereo, fltp, 160 kb/s (default)
  Stream #0:2[0x3](eng): Audio: ac3 (ac-3 / 0x332D6361), 48000 Hz, 5.1(side), fltp, 384 kb/s
At least one output file must be specified
"""


def teste_interpreta_duracao_e_faixas():
    info = interpretar_relatorio(RELATORIO)

    assert info.duracao_s == 3723.5
    assert info.tem_video
    assert len(info.faixas_audio) == 2
    principal = info.faixas_audio[0]
    assert (principal.codec, principal.taxa_amostragem, principal.canais, principal.bitrate_kbps) == (
        "aac", 48000, "stereo", 160)
    assert info.faixas_audio[1].canais == "5.1(side)"


def teste_video_sem_audio():
    info = interpretar_relatorio("  Stream #0:0: Video: vp9, yuv420p, 640x360")
    assert info.tem_video
    assert info.faixas_audio == []
    assert info.duracao_s is None
