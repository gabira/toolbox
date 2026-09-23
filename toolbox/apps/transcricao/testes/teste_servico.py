import os
import zipfile

import pytest

from toolbox.apps.transcricao import servico
from toolbox.apps.transcricao.servico import Palavra, Segmento, Transcricao


def _conversa() -> tuple[list[Segmento], list[tuple[float, float, int]]]:
    """Três falas; a voz nº 7 fala primeiro, depois a nº 2, depois a nº 7 de novo."""
    segmentos = [
        Segmento(0.0, 2.0, " Bom dia a todos.", [Palavra(0.0, 0.6, " Bom"), Palavra(0.6, 1.1, " dia"),
                                                  Palavra(1.1, 1.4, " a"), Palavra(1.4, 1.9, " todos.")]),
        Segmento(2.1, 4.0, " Tudo certo.", [Palavra(2.1, 2.9, " Tudo"), Palavra(2.9, 3.9, " certo.")]),
        Segmento(4.2, 5.0, " Ótimo.", [Palavra(4.2, 5.0, " Ótimo.")]),
    ]
    trechos = [(0.0, 1.95, 7), (2.05, 3.95, 2), (4.3, 5.0, 7)]  # a última palavra começa um pouco antes
    return segmentos, trechos


def teste_cada_voz_vira_uma_pessoa_na_ordem_em_que_fala():
    segmentos, trechos = _conversa()
    turnos = servico.separar_falantes(segmentos, trechos)
    assert [(t.falante, t.texto) for t in turnos] == [
        ("Pessoa 1", "Bom dia a todos."), ("Pessoa 2", "Tudo certo."), ("Pessoa 1", "Ótimo.")]


def teste_palavra_fora_de_qualquer_trecho_fica_com_quem_estava_falando():
    segmentos = [Segmento(0, 3, " Oi tudo", [Palavra(0.0, 0.5, " Oi"), Palavra(2.6, 3.0, " tudo")])]
    turnos = servico.separar_falantes(segmentos, [(0.0, 0.5, 4)])  # "tudo" está a 2 s do trecho
    assert [(t.falante, t.texto) for t in turnos] == [("Pessoa 1", "Oi tudo")]


def teste_paragrafos_quebram_na_pausa_longa():
    segmentos = [Segmento(0, 2, " Um."), Segmento(2.5, 4, " Dois."), Segmento(9, 10, " Três.")]
    assert [b.texto for b in servico.paragrafos(segmentos)] == ["Um. Dois.", "Três."]


def teste_arquivos_de_saida(tmp_path):
    segmentos, trechos = _conversa()
    resultado = Transcricao(segmentos, servico.separar_falantes(segmentos, trechos), "pt", 5.0, True)

    txt = servico.salvar_txt(resultado, tmp_path / "r.txt").read_text(encoding="utf-8")
    assert txt == "Pessoa 1: Bom dia a todos.\n\nPessoa 2: Tudo certo.\n\nPessoa 1: Ótimo.\n"

    srt = servico.salvar_srt(resultado, tmp_path / "r.srt").read_text(encoding="utf-8")
    assert srt.startswith("1\n00:00:00,000 --> 00:00:02,000\n[Pessoa 1] Bom dia a todos.\n\n2\n00:00:02,100 --> ")
    assert "[Pessoa 2] Tudo certo." in srt

    docx = servico.salvar_docx(resultado, tmp_path / "r.docx", "Reunião & cia", "detalhes")
    with zipfile.ZipFile(docx) as pacote:
        assert {"[Content_Types].xml", "_rels/.rels", "word/document.xml"} <= set(pacote.namelist())
        documento = pacote.read("word/document.xml").decode("utf-8")
    assert "Reunião &amp; cia" in documento and "Pessoa 2: " in documento and "[00:02]" in documento


def teste_texto_sem_separar_sai_em_paragrafos(tmp_path):
    segmentos = [Segmento(0, 2, " Um."), Segmento(9, 10, " Dois.")]
    resultado = Transcricao(segmentos, servico.paragrafos(segmentos), "pt", 10.0, False)
    assert servico.salvar_txt(resultado, tmp_path / "r.txt").read_text(encoding="utf-8") == "Um.\n\nDois.\n"
    assert "[Pessoa" not in servico.salvar_srt(resultado, tmp_path / "r.srt").read_text(encoding="utf-8")


@pytest.mark.skipif(os.environ.get("TOOLBOX_TESTES_WHISPER") != "1",
                    reason="usa os modelos reais (baixa ~520 MB na 1ª vez); rode com TOOLBOX_TESTES_WHISPER=1")
def teste_transcricao_real(tmp_path):
    import subprocess

    fala = tmp_path / "fala.wav"
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
                    f"$s.SetOutputToWaveFile('{fala}'); $s.Speak('Bom dia. Hoje vamos revisar o orçamento.')"],
                   check=True)
    if not servico.modelo_baixado("small"):
        servico.baixar_modelo("small")
    if not servico.vozes_baixadas():
        servico.baixar_vozes()
    resultado = servico.transcrever(fala, "small", "pt", separar=True)
    assert "orçamento" in servico.texto_corrido(resultado).lower()
    assert not resultado.com_falantes  # uma voz só: sem "Pessoa 1:"
