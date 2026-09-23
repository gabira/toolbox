import pymupdf
import pytest
from PIL import Image, ImageChops

from toolbox.apps.compactador import servico
from toolbox.nucleo.erros import Cancelado, ErroUsuario


def _foto(largura=3000, altura=2000) -> Image.Image:
    """Gradiente com ruído: comprime como uma foto de verdade (não como uma cor lisa)."""
    ruido = Image.effect_noise((largura, altura), 60).convert("L")
    return Image.merge("RGB", (ruido, Image.linear_gradient("L").resize((largura, altura)), ruido))


def teste_jpg_fica_menor_sem_exif_e_em_pe(tmp_path):
    original = tmp_path / "foto.jpg"
    exif = Image.Exif()
    exif[0x0112] = 6  # orientação: girar 90° (foto tirada com o celular de pé)
    _foto().save(original, quality=97, exif=exif)

    resultado = servico.compactar(original, "image/jpeg", "equilibrado")

    assert resultado.saida == tmp_path / "foto (compactado).jpg"
    assert resultado.depois < resultado.antes == original.stat().st_size
    with Image.open(resultado.saida) as copia:
        assert copia.format == "JPEG"
        largura, altura = copia.size
        assert largura < altura and largura * altura <= 2560 * 1920  # em pé e no limite do nível
        assert 0x0112 not in copia.getexif()


@pytest.mark.parametrize("alfa", ["suave", "recorte"])
def teste_png_com_transparencia_continua_png(tmp_path, alfa):
    original = tmp_path / "logo.png"
    imagem = _foto(800, 600).convert("RGBA")
    mascara = Image.linear_gradient("L").resize((800, 600))
    if alfa == "recorte":
        mascara = mascara.point(lambda a: 255 if a > 128 else 0)
    imagem.putalpha(mascara)
    imagem.save(original, compress_level=0)

    resultado = servico.compactar(original, "image/png", "forte")

    with Image.open(resultado.saida) as copia:
        assert copia.format == "PNG" and copia.size == (800, 600)
        assert ImageChops.difference(copia.convert("RGBA").getchannel("A"), mascara).getbbox() is None


def teste_pdf_reduz_a_foto_e_mantem_o_texto(tmp_path):
    original = tmp_path / "relatorio.pdf"
    foto = tmp_path / "foto.png"
    _foto(2480, 1754).save(foto)  # 300 dpi em meia folha A4
    documento = pymupdf.open()
    pagina = documento.new_page()
    pagina.insert_text((72, 72), "Orçamento aprovado", fontsize=14)
    pagina.insert_image(pymupdf.Rect(0, 100, 595, 521), filename=foto)
    documento.save(original)

    resultado = servico.compactar(original, "application/pdf", "equilibrado")

    assert resultado.depois < resultado.antes / 3
    with pymupdf.open(resultado.saida) as copia:
        assert "Orçamento aprovado" in copia[0].get_text()
        largura = copia[0].get_images(full=True)[0][2]
        assert largura < 1300  # ~150 dpi


def teste_arquivo_ja_compacto_nao_gera_copia(tmp_path):
    original = tmp_path / "pequena.png"
    Image.new("RGB", (40, 40), "white").save(original, optimize=True)

    resultado = servico.compactar(original, "image/png", "leve")

    assert resultado.saida is None and resultado.depois == resultado.antes
    assert [p.name for p in tmp_path.iterdir()] == ["pequena.png"]


def teste_nome_da_copia_nunca_sobrescreve(tmp_path):
    original = tmp_path / "doc.pdf"
    (tmp_path / "doc (compactado).pdf").write_bytes(b"outra")
    assert servico.destino_para(original) == tmp_path / "doc (compactado) (2).pdf"
    assert servico.destino_para(original, tmp_path / "saida") == tmp_path / "saida" / "doc (compactado).pdf"


def teste_pdf_danificado_vira_mensagem(tmp_path):
    ruim = tmp_path / "ruim.pdf"
    ruim.write_bytes(b"isto nao e um pdf")
    with pytest.raises(ErroUsuario):
        servico.compactar(ruim, "application/pdf", "leve")


def teste_parar_no_meio_do_pdf_nao_deixa_arquivo_pela_metade(tmp_path):
    original = tmp_path / "doc.pdf"
    with pymupdf.open() as documento:
        documento.new_page().insert_text((72, 72), "Oi")
        documento.save(original)
    with pytest.raises(Cancelado):
        servico.compactar(original, "application/pdf", "leve", cancelado=lambda: True)
    assert [p.name for p in tmp_path.iterdir()] == ["doc.pdf"]
