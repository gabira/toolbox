from toolbox.nucleo.link import TIPO_WEB, TIPO_YOUTUBE, descrever, e_youtube, extrair_links, rotulo_curto, tipo_links


def teste_extrair_links_de_texto_solto():
    texto = ("Olha esse (https://www.youtube.com/watch?v=abc123). Também youtu.be/xyz789, "
             "e de novo https://www.youtube.com/watch?v=abc123 e ftp://nada")
    assert extrair_links(texto) == ["https://www.youtube.com/watch?v=abc123", "https://youtu.be/xyz789"]
    assert extrair_links("texto sem link") == []


ID = "jNQXAC9IVRw"  # IDs de vídeo reais têm 11 caracteres


def teste_reconhece_links_do_youtube():
    assert e_youtube(f"https://www.youtube.com/watch?v={ID}")
    assert e_youtube(f"https://youtu.be/{ID}")
    assert e_youtube(f"https://youtube.com/shorts/{ID}")
    assert e_youtube(f"https://m.youtube.com/watch?v={ID}&t=10")
    assert e_youtube(f"https://music.youtube.com/watch?v={ID}")
    assert e_youtube("https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf")


def teste_recusa_o_que_nao_e_exatamente_youtube():
    assert not e_youtube("https://www.youtube.com/")
    assert not e_youtube("https://www.youtube.com/@canal")
    assert not e_youtube("https://www.youtube.com/watch?v=x")           # ID inválido
    assert not e_youtube("https://youtu.be/")
    assert not e_youtube(f"https://youtube.com.golpe.com/watch?v={ID}")  # domínio falso
    assert not e_youtube(f"https://naoyoutube.com/watch?v={ID}")
    assert not e_youtube(f"https://exemplo.com/watch?v={ID}")
    assert not e_youtube(f"ftp://youtube.com/watch?v={ID}")
    assert not e_youtube(f"https://i.ytimg.com/vi/{ID}/hqdefault.jpg")    # miniatura, não é vídeo


def teste_tipo_e_descricao():
    video = [f"https://www.youtube.com/watch?v={ID}"]
    assert tipo_links(video) == TIPO_YOUTUBE
    assert descrever(video) == "vídeo do YouTube"
    assert descrever(["https://www.youtube.com/playlist?list=PL1234567890"]) == "playlist do YouTube"
    assert descrever(video + [f"https://youtu.be/{ID[::-1]}"]) == "2 links do YouTube"
    assert tipo_links(["https://exemplo.com"]) == TIPO_WEB
    assert descrever(["https://exemplo.com"]) == "link (não é do YouTube)"
    assert rotulo_curto(f"https://www.youtube.com/watch?v={ID}") == f"youtube.com/watch?v={ID}"
