"""Compacta um PDF num processo à parte: python -m toolbox.apps.compactador.pdf <entrada> <saida> <nivel>

O MuPDF não para no meio do salvamento (juntar objetos repetidos leva até ~1 min num PDF grande)
e um PDF malformado pode derrubar o processo. Aqui, "Parar" encerra o processo na hora e uma falha
não leva a TOOLBOX junto.
Saída: linhas "progresso <fração>" e, no fim, "ok <aviso>" ou "erro <mensagem>".
"""

import sys


def _opcoes_imagens(nivel):
    """Como o `rewrite_images` padrão, mas com reamostragem bicúbica: a média só divide
    por números inteiros (um scan de 240 dpi nunca chegaria a 150) — e só troca se ficar menor."""
    import pymupdf

    m = pymupdf.mupdf
    opcoes = m.PdfImageRewriterOptions()
    for tipo in ("color_lossy", "color_lossless", "gray_lossy", "gray_lossless"):
        setattr(opcoes, f"{tipo}_image_recompress_method", m.FZ_RECOMPRESS_JPEG)
        setattr(opcoes, f"{tipo}_image_recompress_quality", str(nivel.qualidade))
        setattr(opcoes, f"{tipo}_image_subsample_method", m.FZ_SUBSAMPLE_BICUBIC)
        setattr(opcoes, f"{tipo}_image_subsample_threshold", nivel.limite_dpi)
        setattr(opcoes, f"{tipo}_image_subsample_to", nivel.alvo_dpi)
    # Preto e branco (fax/scan de texto): resolução maior, senão as letras borram.
    opcoes.bitonal_image_recompress_method = m.FZ_RECOMPRESS_FAX
    opcoes.bitonal_image_subsample_method = m.FZ_SUBSAMPLE_AVERAGE
    opcoes.bitonal_image_subsample_threshold = nivel.limite_dpi * 2
    opcoes.bitonal_image_subsample_to = nivel.alvo_dpi * 2
    opcoes.recompress_when = m.FZ_RECOMPRESS_WHEN_SMALLER
    return opcoes


def compactar(entrada: str, saida: str, nivel) -> str:
    """Grava a versão compactada em `saida` e devolve um aviso ("" se nenhum)."""
    import pymupdf

    from toolbox.nucleo.erros import ErroUsuario

    pymupdf.TOOLS.mupdf_display_errors(False)  # avisos de PDFs malformados não interessam ao usuário
    try:
        documento = pymupdf.open(entrada)
    except Exception as erro:  # noqa: BLE001
        raise ErroUsuario("Não foi possível abrir este PDF (arquivo danificado?).") from erro
    with documento:
        if documento.needs_pass:
            raise ErroUsuario("PDF protegido por senha: abra e salve sem senha antes de compactar.")
        # A cópia modificada invalida a assinatura digital (o original continua valendo).
        aviso = "A assinatura digital não vale na cópia" if documento.get_sigflags() > 0 else ""
        print("progresso 0.05", flush=True)
        documento.rewrite_images(options=_opcoes_imagens(nivel))
        print("progresso 0.4", flush=True)
        documento.subset_fonts()
        print("progresso 0.45", flush=True)
        documento.save(saida, garbage=4, deflate=True, clean=True, use_objstms=1,
                       encryption=pymupdf.PDF_ENCRYPT_KEEP)
    return aviso


if __name__ == "__main__":
    from toolbox.apps.compactador.servico import NIVEIS
    from toolbox.nucleo.erros import ErroUsuario

    sys.stdout.reconfigure(encoding="utf-8")
    try:
        print("ok", compactar(sys.argv[1], sys.argv[2], NIVEIS[sys.argv[3]]), flush=True)
    except ErroUsuario as erro:
        print("erro", erro, flush=True)
