"""O hub só mostra o Para PDF quando a conversão é possível neste computador."""

from toolbox.apps.para_pdf.servico import pode_converter


def aceita(_caminho, tipo: str) -> bool:
    return pode_converter(tipo)
