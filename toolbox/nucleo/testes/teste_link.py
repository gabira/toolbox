from toolbox.nucleo.link import TIPO_WEB, TIPO_YOUTUBE, descrever, e_youtube, extrair_links, rotulo_curto, tipo_links


def teste_extrair_links_de_texto_solto():
    texto = ("Olha esse (https://www.youtube.com/watch?v=abc123). Também youtu.be/xyz789, "
             "e de novo https://www.youtube.com/watch?v=abc123 e ftp://nada")
    assert extrair_links(texto) == ["https://www.youtube.com/watch?v=abc123", "https://youtu.be/xyz789"]
    assert extrair_links("texto sem link") == []


def teste_reconhece_links_do_youtube():
    assert e_youtube("https://www.youtube.com/watch?v=abc123")
    assert e_youtube("https://youtu.be/abc123")
    assert e_youtube("https://youtube.com/shorts/abc123")
    assert e_youtube("https://m.youtube.com/watch?v=abc123&t=10")
    assert e_youtube("https://www.youtube.com/playlist?list=PL123")
    assert not e_youtube("https://www.youtube.com/")
    assert not e_youtube("https://www.youtube.com/@canal")
    assert not e_youtube("https://exemplo.com/watch?v=abc")


def teste_tipo_e_descricao():
    video = ["https://www.youtube.com/watch?v=abc"]
    assert tipo_links(video) == TIPO_YOUTUBE
    assert descrever(video) == "vídeo do YouTube"
    assert descrever(["https://www.youtube.com/playlist?list=PL1"]) == "playlist do YouTube"
    assert descrever(video + ["https://youtu.be/def"]) == "2 links do YouTube"
    assert tipo_links(["https://exemplo.com"]) == TIPO_WEB
    assert rotulo_curto("https://www.youtube.com/watch?v=abc") == "youtube.com/watch?v=abc"
