from toolbox.nucleo.arquivo import compativel, detectar_tipo, nome_categoria, tamanho_legivel, tipo_mime


def teste_detectar_tipo_pelo_conteudo_ignora_extensao_errada(tmp_path):
    casos = {
        "na_verdade_png.jpg": (b"\x89PNG\r\n\x1a\n" + b"\0" * 20, "image/png"),
        "documento.bin": (b"%PDF-1.7\n", "application/pdf"),
        "filme.dat": (b"\0\0\0\x20ftypisom" + b"\0" * 20, "video/mp4"),
        "musica.dat": (b"\0\0\0\x20ftypM4A " + b"\0" * 20, "audio/mp4"),
        "clipe.webm": (b"\x1a\x45\xdf\xa3" + b"\0" * 20 + b"webm", "video/webm"),
    }
    for nome, (conteudo, esperado) in casos.items():
        caminho = tmp_path / nome
        caminho.write_bytes(conteudo)
        assert detectar_tipo(caminho) == esperado, nome


def teste_detectar_tipo_cai_na_extensao(tmp_path):
    caminho = tmp_path / "texto.mkv"
    caminho.write_bytes(b"conteudo qualquer")
    assert detectar_tipo(caminho) == "video/x-matroska"


def teste_tipo_mime_prioriza_extensoes_de_midia():
    assert tipo_mime("C:/videos/Aula.MKV") == "video/x-matroska"
    assert tipo_mime("gravacao.ts") == "video/mp2t"
    assert tipo_mime("foto.jpeg") == "image/jpeg"
    assert tipo_mime("sem_extensao") == "application/octet-stream"


def teste_compativel_aceita_curingas():
    assert compativel(["video/*"], "video/mp4")
    assert not compativel(["video/*"], "image/png")
    assert compativel(["image/png", "application/pdf"], "application/pdf")
    assert compativel(["*"], "qualquer/coisa")


def teste_nome_categoria():
    assert nome_categoria("video/mp4") == "vídeo"
    assert nome_categoria("application/pdf") == "PDF"
    assert nome_categoria("application/zip") == "arquivo"


def teste_tamanho_legivel():
    assert tamanho_legivel(512) == "512 B"
    assert tamanho_legivel(1536) == "1,5 KB"
    assert tamanho_legivel(25 * 1024 * 1024) == "25,0 MB"
