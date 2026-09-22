from toolbox.nucleo.arquivo import compativel, nome_categoria, tamanho_legivel, tipo_mime


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
