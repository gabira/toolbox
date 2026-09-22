import subprocess

import pytest

from toolbox.apps.separador_audio import servico
from toolbox.nucleo.erros import Cancelado, ErroUsuario
from toolbox.nucleo.ffmpeg import FaixaAudio, caminho_ffmpeg, sondar


# --- regras puras ---

def teste_extensao_original_por_codec():
    assert servico.extensao_original("aac") == "m4a"
    assert servico.extensao_original("opus") == "opus"
    assert servico.extensao_original("pcm_s16le") == "wav"
    assert servico.extensao_original("pcm_s16be") == "mka"  # WAV não aceita big-endian
    assert servico.extensao_original("truehd") == "mka"


def teste_extensao_saida_respeita_formato_escolhido():
    assert servico.extensao_saida(servico.FORMATOS["original"], "aac") == "m4a"
    assert servico.extensao_saida(servico.FORMATOS["mp3"], "aac") == "mp3"


def teste_comando_original_copia_sem_reencodar(tmp_path):
    comando = servico.montar_comando(tmp_path / "v.mp4", tmp_path / "v.m4a", servico.FORMATOS["original"])
    assert comando[comando.index("-c:a") + 1] == "copy"
    assert comando[comando.index("-map") + 1] == "0:a:0"
    assert "-vn" in comando and "-n" in comando


def teste_caminho_livre_nao_sobrescreve(tmp_path):
    (tmp_path / "aula.m4a").touch()
    (tmp_path / "aula (2).m4a").touch()
    assert servico.caminho_livre(tmp_path, "aula", "m4a").name == "aula (3).m4a"


def teste_limpar_nome():
    assert servico.limpar_nome('  Aula: parte 1/2?  ') == "Aula parte 12"
    assert servico.limpar_nome("musica.m4a", "m4a") == "musica"
    assert servico.limpar_nome("musica.mp3", "m4a") == "musica.mp3"
    assert servico.limpar_nome("final...") == "final"
    assert servico.limpar_nome("con") == "con_"
    assert servico.limpar_nome('<>:"') == ""
    assert servico.limpar_nome(None) == ""


def teste_descricoes_para_a_tela():
    faixa = FaixaAudio("aac", 44100, "stereo", 128)
    assert servico.detalhes_faixa(faixa) == ["44,1 kHz", "estéreo", "128 kb/s"]
    assert servico.nome_codec("pcm_s24le") == "PCM"
    assert servico.formatar_duracao(3723.4) == "1:02:03"
    assert servico.formatar_duracao(65) == "1:05"


# --- extração real (vídeos curtos gerados pelo FFmpeg) ---

def _gerar_video(pasta, com_audio=True):
    destino = pasta / "entrada.mp4"
    comando = [caminho_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y",
               "-f", "lavfi", "-i", "testsrc=size=160x120:rate=10:duration=2"]
    if com_audio:
        comando += ["-f", "lavfi", "-i", "sine=frequency=440:duration=2",
                    "-c:a", "aac", "-b:a", "96k"]
    comando += ["-c:v", "mpeg4", "-shortest", str(destino)]
    subprocess.run(comando, check=True)
    return destino


@pytest.fixture(scope="module")
def video(tmp_path_factory):
    return _gerar_video(tmp_path_factory.mktemp("video"))


def teste_extrai_original_sem_perdas(video, tmp_path):
    progresso = []
    saida = servico.extrair(video, tmp_path, "original", ao_progresso=progresso.append)

    assert saida == tmp_path / "entrada.m4a"
    info = sondar(saida)
    assert not info.tem_video
    assert [f.codec for f in info.faixas_audio] == ["aac"]
    assert progresso[-1] == 1.0


def teste_extrai_convertendo_para_mp3(video, tmp_path):
    saida = servico.extrair(video, tmp_path, "mp3")
    assert saida.suffix == ".mp3"
    assert sondar(saida).faixas_audio[0].codec == "mp3"


def teste_extrai_com_nome_escolhido(video, tmp_path):
    saida = servico.extrair(video, tmp_path, "original", nome="Minha música")
    assert saida == tmp_path / "Minha música.m4a"
    # Nome vazio volta para o nome do vídeo
    assert servico.extrair(video, tmp_path, "original", nome="  ").name == "entrada.m4a"


def teste_cancelar_remove_arquivo_parcial(video, tmp_path):
    with pytest.raises(Cancelado):
        servico.extrair(video, tmp_path, "flac", cancelado=lambda: True)
    assert list(tmp_path.iterdir()) == []


def teste_video_sem_audio_gera_erro_claro(tmp_path):
    mudo = _gerar_video(tmp_path, com_audio=False)
    with pytest.raises(ErroUsuario, match="não tem trilha de áudio"):
        servico.extrair(mudo, tmp_path, "original")
