import os
import zipfile

import pikepdf
import pytest
from PIL import Image

from toolbox.apps.para_pdf import servico
from toolbox.nucleo.erros import Cancelado, ErroUsuario

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def teste_categorias():
    assert servico.categoria("image/png") == "imagem"
    assert servico.categoria("text/markdown") == "markdown"
    assert servico.categoria(DOCX) == "word"
    assert servico.categoria("text/csv") == "excel"
    assert servico.categoria("application/pdf") is None
    assert servico.categoria("video/mp4") is None


def teste_documento_sem_office_nem_libreoffice_nao_converte(monkeypatch):
    monkeypatch.setattr(servico, "office_instalado", lambda _p: False)
    monkeypatch.setattr(servico, "caminho_libreoffice", lambda: None)
    assert not servico.pode_converter(DOCX)
    assert servico.pode_converter("image/jpeg")  # imagens e texto não dependem de nada instalado


def teste_prefere_office_e_cai_no_libreoffice(monkeypatch):
    monkeypatch.setattr(servico, "caminho_libreoffice", lambda: "soffice.exe")
    monkeypatch.setattr(servico, "office_instalado", lambda _p: True)
    assert servico.motor("word") == ("office", "Via Microsoft Word")
    monkeypatch.setattr(servico, "office_instalado", lambda _p: False)
    assert servico.motor("word") == ("libreoffice", "Via LibreOffice")


# --- imagens ---

@pytest.fixture
def imagens(tmp_path):
    jpg, png = tmp_path / "foto.jpg", tmp_path / "logo.png"
    Image.new("RGB", (600, 400), "#3366cc").save(jpg, quality=90)
    Image.new("RGBA", (300, 300), (255, 0, 0, 128)).save(png)
    return jpg, png


def _imagens_do_pdf(caminho):
    with pikepdf.open(caminho) as pdf:
        paginas = [[round(float(x)) for x in p.mediabox] for p in pdf.pages]
        imagens = [next(iter(p.images.values())) for p in pdf.pages]
        return paginas, [(str(i.Filter), i.read_raw_bytes()) for i in imagens]


def teste_jpeg_entra_sem_recompressao(imagens, tmp_path):
    jpg, png = imagens
    saida = servico.converter([jpg, png], "image/jpeg", tmp_path / "album.pdf")

    paginas, imgs = _imagens_do_pdf(saida)
    assert len(paginas) == 2
    assert imgs[0] == ("/DCTDecode", jpg.read_bytes())   # JPEG byte a byte
    assert imgs[1][0] == "/FlateDecode"                   # PNG com transparência: sem perda


def teste_folha_a4(imagens, tmp_path):
    # Imagem deitada (600×400): a folha A4 gira para paisagem sozinha.
    saida = servico.converter([imagens[0]], "image/jpeg", tmp_path / "a4.pdf", servico.PAGINA_A4)
    assert _imagens_do_pdf(saida)[0] == [[0, 0, 842, 595]]


def teste_cancelar_nao_deixa_pdf(imagens, tmp_path):
    with pytest.raises(Cancelado):
        servico.converter([imagens[0]], "image/jpeg", tmp_path / "x.pdf", cancelado=lambda: True)
    assert not (tmp_path / "x.pdf").exists()


# --- texto ---

def teste_markdown_para_pdf(tmp_path):
    from PySide6.QtGui import QGuiApplication
    _app = QGuiApplication.instance() or QGuiApplication([])  # o motor de texto do Qt precisa de fontes

    nota = tmp_path / "nota.md"
    nota.write_text("# Título\n\nTexto com **negrito** e acentuação.\n", encoding="utf-8")
    saida = servico.converter([nota], "text/markdown", tmp_path / "nota.pdf")
    with pikepdf.open(saida) as pdf:
        assert len(pdf.pages) == 1
        assert [round(float(x)) for x in pdf.pages[0].mediabox][2:] == [595, 842]


def teste_tipo_nao_suportado(tmp_path):
    arquivo = tmp_path / "video.mp4"
    arquivo.write_bytes(b"\0")
    with pytest.raises(ErroUsuario, match="não pode ser convertido"):
        servico.converter([arquivo], "video/mp4", tmp_path / "v.pdf")


# --- Office (lento: abre o Word; rode com TOOLBOX_TESTES_OFFICE=1) ---

@pytest.mark.skipif(os.environ.get("TOOLBOX_TESTES_OFFICE") != "1" or not servico.office_instalado("word"),
                    reason="teste lento, só com TOOLBOX_TESTES_OFFICE=1 e Word instalado")
def teste_docx_pelo_word(tmp_path):
    docx = tmp_path / "doc.docx"
    with zipfile.ZipFile(docx, "w") as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        z.writestr("_rels/.rels", '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        z.writestr("word/document.xml", '<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Olá</w:t></w:r></w:p></w:body></w:document>')
    saida = servico.converter([docx], DOCX, tmp_path / "doc.pdf")
    assert saida.stat().st_size > 1000
