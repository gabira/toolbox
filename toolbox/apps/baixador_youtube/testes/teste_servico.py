"""Testes sem internet: as chamadas ao YouTube são simuladas."""

from pathlib import Path

import pytest

from toolbox.apps.baixador_youtube import servico
from toolbox.nucleo.erros import Cancelado, ErroUsuario


def teste_extrair_links_sem_repetidos_e_sem_lixo():
    texto = """
        https://www.youtube.com/watch?v=aaa
        texto qualquer
        https://youtu.be/bbb   https://www.youtube.com/watch?v=aaa
        ftp://nao.serve
    """
    assert servico.extrair_links(texto) == ["https://www.youtube.com/watch?v=aaa", "https://youtu.be/bbb"]
    assert servico.extrair_links("") == []


def teste_mensagens_amigaveis():
    assert servico.mensagem_amigavel(Exception("ERROR: [youtube] abc: Private video")) == "Esse vídeo é privado."
    assert servico.mensagem_amigavel(Exception("Video unavailable")) == "Vídeo indisponível ou removido."
    assert "internet" in servico.mensagem_amigavel(Exception("urlopen error [Errno 11001] getaddrinfo failed"))
    assert len(servico.mensagem_amigavel(Exception("x" * 500))) == 160


def teste_formatos_por_qualidade(tmp_path):
    def gancho(_d): pass

    audio = servico.montar_opcoes(servico.AUDIO, tmp_path, False, gancho)
    assert audio["postprocessors"][0]["preferredcodec"] == "mp3"

    melhor = servico.montar_opcoes(servico.MELHOR, tmp_path, False, gancho)
    assert melhor["format"] == "bestvideo+bestaudio/best"

    fixa = servico.montar_opcoes("720", tmp_path, False, gancho)
    assert fixa["format"].startswith("bestvideo[height<=720][vcodec^=avc1]")
    assert fixa["ffmpeg_location"]  # usa o FFmpeg embarcado

    playlist = servico.montar_opcoes("720", tmp_path, True, gancho)
    assert "%(playlist_title)s" in playlist["outtmpl"] and playlist["ignoreerrors"]


def teste_opcoes_de_qualidade_para_a_tela():
    opcoes = servico.opcoes_qualidade([1080, 720])
    assert [o["id"] for o in opcoes] == ["1080", "720", servico.AUDIO]
    assert opcoes[0]["descricao"] == "Full HD"


def teste_descrever_progresso():
    fracao, texto = servico.descrever_progresso({
        "downloaded_bytes": 512 * 1024, "total_bytes": 1024 * 1024, "speed": 2 * 1024 * 1024,
        "eta": 65, "info_dict": {"vcodec": "avc1", "acodec": "none"},
    })
    assert fracao == 0.5
    assert texto == "50% · 2,0 MB/s · faltam 1:05 · faixa de vídeo"
    assert servico.descrever_progresso({"downloaded_bytes": 2048})[0] is None


def teste_arquivos_finais_de_video_e_playlist():
    video = {"requested_downloads": [{"filepath": "C:/v/a.mp4"}]}
    playlist = {"_type": "playlist", "entries": [video, None, {"requested_downloads": [{"filepath": "C:/v/b.mp4"}]}]}
    assert servico._arquivos_finais(video) == [Path("C:/v/a.mp4")]
    assert servico._arquivos_finais(playlist) == [Path("C:/v/a.mp4"), Path("C:/v/b.mp4")]


# --- fila de vários links ---

@pytest.fixture
def youtube_falso(monkeypatch):
    baixados = []

    def analisar(link):
        if "ruim" in link:
            raise ErroUsuario("Vídeo indisponível ou removido.")
        return {"titulo": f"Título {link[-1]}", "e_playlist": False, "n_itens": 0}

    def baixar(link, qualidade, pasta, playlist, ao_progresso, cancelado):
        if cancelado():
            raise Cancelado()
        ao_progresso({"fracao": 0.5, "texto": "50%"})
        baixados.append((link, qualidade))
        return [Path(pasta) / "video.mp4"]

    monkeypatch.setattr(servico, "analisar", analisar)
    monkeypatch.setattr(servico, "baixar", baixar)
    return baixados


def teste_lote_continua_depois_de_um_erro(youtube_falso, tmp_path):
    eventos = []
    resultado = servico.processar_lote(
        ["https://x/1", "https://x/ruim", "https://x/3"], "720", tmp_path, False, eventos.append)

    assert resultado == {"ok": 2, "falhas": 1, "so_conferir": False, "cancelado": False}
    assert youtube_falso == [("https://x/1", "720"), ("https://x/3", "720")]
    finais = {e["i"]: e["tom"] for e in eventos if e["tipo"] == "item"}
    assert finais == {0: "sucesso", 1: "erro", 2: "sucesso"}
    assert {"tipo": "titulo", "i": 0, "titulo": "Título 1"} in eventos


def teste_lote_so_conferir_nao_baixa(youtube_falso, tmp_path):
    resultado = servico.processar_lote(["https://x/1"], "720", tmp_path, True, lambda _e: None)
    assert resultado["ok"] == 1 and youtube_falso == []


def teste_lote_parar(youtube_falso, tmp_path):
    resultado = servico.processar_lote(["https://x/1", "https://x/2"], "720", tmp_path, False,
                                       lambda _e: None, cancelado=lambda: True)
    assert resultado["cancelado"] and youtube_falso == []
