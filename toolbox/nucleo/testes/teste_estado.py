"""Quais apps aparecem no hub para cada tipo de entrada (com os apps reais da TOOLBOX)."""

import pytest
from PySide6.QtGui import QGuiApplication

from toolbox.nucleo.estado import Nucleo
from toolbox.nucleo.registro import descobrir_apps

YOUTUBE = "Baixar do YouTube"


@pytest.fixture(scope="module")
def nucleo():
    _app = QGuiApplication.instance() or QGuiApplication([])
    return Nucleo(descobrir_apps())


def _visiveis(nucleo) -> list[str]:
    return [app["nome"] for app in nucleo.appsVisiveis]


def teste_sem_entrada_mostra_todos(nucleo):
    nucleo.limparEntrada()
    assert len(_visiveis(nucleo)) == nucleo.totalApps


def teste_imagem_png_nao_mostra_o_youtube(nucleo, tmp_path):
    png = tmp_path / "foto.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\0" * 32)
    nucleo.definirArquivo(str(png))

    assert nucleo.tipoEntrada == "arquivo"
    assert nucleo.resumoEntrada.startswith("imagem PNG")
    assert YOUTUBE not in _visiveis(nucleo)
    assert "Para PDF" in _visiveis(nucleo)


def teste_link_do_youtube_mostra_so_o_youtube(nucleo):
    assert nucleo.definirTexto("https://www.youtube.com/watch?v=jNQXAC9IVRw") == ""
    assert nucleo.tipoEntrada == "link"
    assert _visiveis(nucleo) == [YOUTUBE]


def teste_link_de_outro_site_nao_mostra_nada(nucleo):
    nucleo.definirTexto("https://www.exemplo.com/video/123")
    assert nucleo.tipoEntrada == "link"
    assert _visiveis(nucleo) == []
    assert nucleo.resumoEntrada == "link (não é do YouTube)"


def teste_caminho_de_arquivo_colado_vale_como_arquivo(nucleo, tmp_path):
    # Nome com cara de link não engana: o arquivo existe, então é arquivo.
    png = tmp_path / "youtube.com_watch.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\0" * 32)
    nucleo.definirTexto(f'"{png}"')
    assert nucleo.tipoEntrada == "arquivo"
    assert YOUTUBE not in _visiveis(nucleo)
