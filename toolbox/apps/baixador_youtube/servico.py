"""Download de vídeos do YouTube com yt-dlp (sem dependência de Qt).

Portado do projeto download_yt: mesma escolha de formatos (H.264 + AAC sempre
que possível), cancelamento limpando os .part e mensagens de erro traduzidas.
Diferença: usa o FFmpeg embarcado da TOOLBOX, sem precisar instalar nada.
"""

import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from yt_dlp import YoutubeDL

from toolbox.nucleo.arquivo import tamanho_legivel
from toolbox.nucleo.erros import Cancelado, ErroUsuario
from toolbox.nucleo.ffmpeg import caminho_ffmpeg
from toolbox.nucleo.link import extrair_links  # noqa: F401 — usado pelo controlador e pelos testes

# Alturas que fazem sentido oferecer; filtradas contra o que o vídeo realmente tem.
ALTURAS_CONHECIDAS = [2160, 1440, 1080, 720, 480, 360, 240, 144]
APELIDOS_ALTURA = {2160: "4K", 1440: "2K", 1080: "Full HD", 720: "HD"}

# Identificadores de qualidade usados pela interface.
MELHOR = "melhor"
AUDIO = "audio"
QUALIDADES_LOTE = [MELHOR, "1080", "720", "480", "360", AUDIO]

INTERVALO_PROGRESSO = 0.15  # s — o yt-dlp chama o hook dezenas de vezes por segundo
ANALISES_SIMULTANEAS = 4    # links da fila analisados ao mesmo tempo antes de baixar


class _SemLog:
    """Logger mudo: impede o yt-dlp de despejar mensagens no console."""

    def debug(self, msg): pass
    def info(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass


BASE = {"quiet": True, "no_warnings": True, "logger": _SemLog()}


def mensagem_amigavel(exc: Exception) -> str:
    texto = str(exc).replace("ERROR: ", "").strip()
    # O yt-dlp prefixa tudo com "[extrator] id: " — ruído para o usuário.
    texto = re.sub(r"^\[[^\]]+\]\s*[\w-]{0,20}:\s*", "", texto)
    baixo = texto.lower()

    if "private video" in baixo:
        return "Esse vídeo é privado."
    if "unavailable" in baixo or "removed" in baixo:
        return "Vídeo indisponível ou removido."
    if "truncated" in baixo or "incomplete youtube id" in baixo:
        return "Link incompleto. Copie a URL inteira do vídeo."
    if "age" in baixo and "restrict" in baixo:
        return "Vídeo com restrição de idade — não é possível baixar sem login."
    if "not a valid url" in baixo or "unsupported url" in baixo or "is not a valid" in baixo:
        return "Esse link não parece ser uma URL válida do YouTube."
    if any(p in baixo for p in ("urlopen error", "getaddrinfo", "connection", "network")):
        return "Sem conexão com a internet."
    if "sign in to confirm" in baixo or "login required" in baixo:
        return "O YouTube pediu login para esse vídeo."
    if "page needs to be reloaded" in baixo:
        return "O YouTube mudou algo no site. Use \"Atualizar motor\" e tente de novo."
    return texto if len(texto) <= 160 else texto[:157] + "..."


def formatar_duracao(segundos) -> str:
    if not segundos:
        return ""
    segundos = int(segundos)
    horas, resto = divmod(segundos, 3600)
    minutos, seg = divmod(resto, 60)
    return f"{horas}:{minutos:02d}:{seg:02d}" if horas else f"{minutos}:{seg:02d}"


def opcoes_qualidade(alturas: list[int]) -> list[dict]:
    """Opções para a tela: as resoluções reais do vídeo + apenas áudio."""
    opcoes = [
        {"id": str(h), "nome": f"{h}p", "descricao": APELIDOS_ALTURA.get(h, "")}
        for h in alturas
    ]
    opcoes.append({"id": AUDIO, "nome": "Apenas áudio", "descricao": "MP3 320 kb/s"})
    return opcoes


def analisar(url: str) -> dict:
    """Consulta o vídeo/playlist sem baixar nada. Levanta ErroUsuario com mensagem pronta."""
    url = (url or "").strip()
    if not url:
        raise ErroUsuario("Cole o link do vídeo primeiro.")

    try:
        # 1ª passada: rasa e rápida, só para descobrir se é playlist.
        with YoutubeDL({**BASE, "extract_flat": "in_playlist"}) as ydl:
            raso = ydl.extract_info(url, download=False)

        e_playlist = raso.get("_type") == "playlist"
        n_itens = 0
        url_referencia = url
        titulo = raso.get("title") or "(sem título)"

        if e_playlist:
            entradas = [e for e in (raso.get("entries") or []) if e]
            n_itens = len(entradas)
            if not entradas:
                raise ErroUsuario("Playlist vazia ou inacessível.")
            # As qualidades saem do primeiro vídeo, como amostra da playlist.
            url_referencia = entradas[0].get("url") or entradas[0].get("id")

        # 2ª passada: completa, só no vídeo de referência, para ler os formatos.
        with YoutubeDL({**BASE, "noplaylist": True}) as ydl:
            info = ydl.extract_info(url_referencia, download=False)

        if not e_playlist:
            titulo = info.get("title") or titulo

        alturas_disponiveis = {f.get("height") for f in (info.get("formats") or []) if f.get("height")}
        alturas = [h for h in ALTURAS_CONHECIDAS if h in alturas_disponiveis] or [720]

        return {
            "titulo": titulo,
            "canal": (raso.get("uploader") if e_playlist else info.get("uploader")) or "",
            "duracao": formatar_duracao(info.get("duration")),
            "miniatura": info.get("thumbnail") or "",
            "e_playlist": e_playlist,
            "n_itens": n_itens,
            "alturas": alturas,
        }
    except ErroUsuario:
        raise
    except Exception as exc:  # DownloadError, ExtractorError, rede caindo, parsing inesperado
        raise ErroUsuario(mensagem_amigavel(exc)) from exc


def analisar_item(url: str, qualidade: str) -> dict:
    """Análise rápida para a fila: título e tamanho estimado na qualidade escolhida (uma consulta só).

    Retorna {"titulo", "e_playlist", "n_itens", "bytes"}; "bytes" é None quando não dá para saber
    (playlists, transmissões ao vivo, formatos sem tamanho informado).
    """
    formato = montar_opcoes(qualidade, ".", False, None)["format"]
    try:
        with YoutubeDL({**BASE, "extract_flat": "in_playlist", "format": formato}) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:  # noqa: BLE001
        raise ErroUsuario(mensagem_amigavel(exc)) from exc

    if info.get("_type") == "playlist":
        entradas = [e for e in (info.get("entries") or []) if e]
        if not entradas:
            raise ErroUsuario("Playlist vazia ou inacessível.")
        return {"titulo": info.get("title") or "(sem título)", "e_playlist": True,
                "n_itens": len(entradas), "bytes": None}

    # Vídeo + áudio separados: o tamanho é a soma das duas faixas.
    tamanhos = [f.get("filesize") or f.get("filesize_approx") for f in (info.get("requested_formats") or [info])]
    return {"titulo": info.get("title") or "(sem título)", "e_playlist": False, "n_itens": 0,
            "bytes": int(sum(tamanhos)) if tamanhos and all(tamanhos) else None}


def montar_opcoes(qualidade: str, pasta, baixar_playlist: bool, hook) -> dict:
    if baixar_playlist:
        saida = os.path.join(pasta, "%(playlist_title)s", "%(playlist_index)02d - %(title)s.%(ext)s")
    else:
        saida = os.path.join(pasta, "%(title)s.%(ext)s")

    opcoes = {
        **BASE,
        "outtmpl": saida,
        "noplaylist": not baixar_playlist,
        "progress_hooks": [hook] if hook else [],
        "noprogress": True,
        "ignoreerrors": baixar_playlist,  # um vídeo morto não derruba a playlist
        "retries": 3,
        "ffmpeg_location": caminho_ffmpeg(),
        "windowsfilenames": True,
    }

    if qualidade == AUDIO:
        opcoes["format"] = "bestaudio/best"
        opcoes["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "320",
        }]
    elif qualidade == MELHOR:
        # Sem forçar H.264: acima de 1080p o YouTube só serve VP9/AV1, e preferir
        # H.264 limitaria a 1080p em silêncio.
        opcoes["format"] = "bestvideo+bestaudio/best"
        opcoes["merge_output_format"] = "mp4"
    else:
        altura = int(qualidade)
        # H.264 + AAC toca em qualquer lugar (Windows, TVs, editores). Se a
        # resolução pedida só existir em VP9/AV1, os fallbacks assumem.
        opcoes["format"] = (
            f"bestvideo[height<={altura}][vcodec^=avc1]+bestaudio[acodec^=mp4a]/"
            f"bestvideo[height<={altura}]+bestaudio/"
            f"best[height<={altura}]/best"
        )
        opcoes["merge_output_format"] = "mp4"
    return opcoes


def descrever_progresso(d: dict, fracao: float | None = None) -> tuple[float | None, str]:
    """(fração, texto) a partir de um dict de progresso do yt-dlp. Fração None = total desconhecido.

    `fracao` substitui a da faixa atual (ex.: progresso do vídeo inteiro, somando vídeo e áudio).
    """
    total = d.get("total_bytes") or d.get("total_bytes_estimate")
    baixado = d.get("downloaded_bytes") or 0
    if fracao is None:
        fracao = min(baixado / total, 1.0) if total else None

    partes = [f"{fracao * 100:.0f}%" if fracao is not None else tamanho_legivel(baixado)]
    if d.get("speed"):
        partes.append(f"{tamanho_legivel(int(d['speed']))}/s")
    if d.get("eta"):
        partes.append(f"faltam {formatar_duracao(d['eta']) or '0:00'}")

    # Em alta resolução vídeo e áudio vêm separados e a barra enche duas vezes.
    info = d.get("info_dict") or {}
    vcodec, acodec = info.get("vcodec"), info.get("acodec")
    if vcodec and vcodec != "none" and acodec == "none":
        partes.append("faixa de vídeo")
    elif vcodec == "none":
        partes.append("faixa de áudio")
    return fracao, " · ".join(partes)


def _arquivos_finais(info: dict | None) -> list[Path]:
    if not info:
        return []
    if info.get("_type") == "playlist":
        return [p for entrada in (info.get("entries") or []) for p in _arquivos_finais(entrada)]
    return [Path(d["filepath"]) for d in (info.get("requested_downloads") or []) if d.get("filepath")]


def baixar(url: str, qualidade: str, pasta, baixar_playlist: bool = False,
           ao_progresso=None, cancelado=lambda: False, tamanho_estimado: int | None = None) -> list[Path]:
    """Baixa o vídeo (ou a playlist). `ao_progresso` recebe {"fracao", "texto"}. Retorna os arquivos.

    A fração é do vídeo inteiro: em alta resolução vídeo e áudio vêm em faixas separadas e a barra
    não volta a zero na segunda. `tamanho_estimado` (de `analisar_item`) deixa a conta certa desde o início.
    """
    if not Path(pasta).is_dir():
        raise ErroUsuario("A pasta de destino não existe mais. Escolha outra.")

    parciais = set()
    ultimo_envio = 0.0
    faixas: dict[str, tuple[int, int]] = {}  # arquivo -> (baixado, total)

    def fracao_do_video(d) -> float | None:
        total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
        baixado = total if d.get("status") == "finished" else (d.get("downloaded_bytes") or 0)
        info = d.get("info_dict") or {}
        if baixar_playlist and info.get("playlist_index") and info.get("n_entries"):
            # Playlist: cada vídeo é uma fatia igual da barra.
            atual = baixado / total if total else 0
            return min(1.0, (info["playlist_index"] - 1 + atual) / info["n_entries"])
        faixas[d.get("filename") or d.get("tmpfilename") or ""] = (baixado, total)
        denominador = max(tamanho_estimado or 0, sum(t for _, t in faixas.values()))
        return min(1.0, sum(b for b, _ in faixas.values()) / denominador) if denominador else None

    def hook(d):
        nonlocal ultimo_envio
        # Guardamos os .part para limpar se o usuário cancelar.
        if d.get("tmpfilename"):
            parciais.add(d["tmpfilename"])
        if cancelado():
            raise Cancelado()
        if not ao_progresso:
            return
        if d.get("status") not in ("finished", "downloading"):
            return
        fracao = fracao_do_video(d)
        if d["status"] == "finished":
            completo = fracao is None or fracao >= 0.98
            ao_progresso({"fracao": fracao, "texto": "Finalizando com o FFmpeg…" if completo else "Faixa baixada…"})
        elif time.monotonic() - ultimo_envio >= INTERVALO_PROGRESSO:
            ultimo_envio = time.monotonic()
            fracao, texto = descrever_progresso(d, fracao)
            ao_progresso({"fracao": fracao, "texto": texto})

    def limpar_parciais():
        for caminho in parciais:
            try:
                if caminho.endswith(".part") and os.path.exists(caminho):
                    os.remove(caminho)
            except OSError:
                pass  # arquivo travado pelo sistema: não vale falhar por isso

    try:
        with YoutubeDL(montar_opcoes(qualidade, pasta, baixar_playlist, hook)) as ydl:
            info = ydl.extract_info(url, download=True)
    except Cancelado:
        limpar_parciais()
        raise
    except Exception as exc:
        # O cancelamento às vezes sobe embrulhado num DownloadError.
        if cancelado():
            limpar_parciais()
            raise Cancelado() from exc
        raise ErroUsuario(mensagem_amigavel(exc)) from exc

    arquivos = _arquivos_finais(info)
    if not arquivos and not baixar_playlist:
        raise ErroUsuario("O download terminou sem gerar arquivo.")
    return arquivos


def _analisar_todos(links, qualidade, ao_evento, cancelado) -> list:
    """Analisa todos os links (alguns ao mesmo tempo). Cada posição: dict da análise, ErroUsuario ou None."""
    resultados: list = [None] * len(links)

    def analisar_um(i):
        if cancelado():
            return i, None
        ao_evento({"tipo": "item", "i": i, "estado": "analisando…", "tom": "ativo"})
        try:
            return i, analisar_item(links[i], qualidade)
        except ErroUsuario as exc:
            return i, exc

    with ThreadPoolExecutor(max_workers=ANALISES_SIMULTANEAS) as executor:
        for futuro in as_completed([executor.submit(analisar_um, i) for i in range(len(links))]):
            i, resultado = futuro.result()
            resultados[i] = resultado
            if isinstance(resultado, ErroUsuario):
                ao_evento({"tipo": "item", "i": i, "estado": str(resultado), "tom": "erro"})
            elif resultado:
                titulo = resultado["titulo"]
                if resultado["e_playlist"]:
                    titulo += f"  (playlist, {resultado['n_itens']} vídeos)"
                ao_evento({"tipo": "titulo", "i": i, "titulo": titulo})
                tamanho = f" · {tamanho_legivel(resultado['bytes'])}" if resultado["bytes"] else ""
                ao_evento({"tipo": "item", "i": i, "estado": "na fila" + tamanho, "tom": "normal"})
    return resultados


def pesos_da_fila(analises: list[dict]) -> list[float]:
    """Peso de cada item no progresso total: o tamanho estimado.

    Sem tamanho (playlist, ao vivo), vale a média dos vídeos conhecidos (vezes o nº de vídeos da playlist).
    """
    conhecidos = [a["bytes"] for a in analises if a["bytes"]]
    media = sum(conhecidos) / len(conhecidos) if conhecidos else 1.0
    return [float(a["bytes"] or media * max(1, a["n_itens"])) for a in analises]


def processar_lote(links: list[str], qualidade: str, pasta, so_conferir: bool,
                   ao_evento, cancelado=lambda: False) -> dict:
    """Analisa todos os links e depois baixa um após o outro; um link com erro não para a fila.

    Analisar antes permite mostrar o progresso total pelo tamanho real de cada vídeo
    e apontar os links com problema logo no início.

    Eventos enviados a `ao_evento`:
      {"tipo": "item", "i", "estado", "tom"}   tom: normal | ativo | sucesso | erro
      {"tipo": "titulo", "i", "titulo"}
      {"tipo": "progresso", "i", "fracao", "texto"}   progresso do item
      {"tipo": "total", "fracao"}                     progresso da fila inteira (por tamanho)
      {"tipo": "geral", "texto"}
    Retorna {"ok", "falhas", "so_conferir", "cancelado"}.
    """
    total = len(links)
    ao_evento({"tipo": "geral", "texto": f"Analisando {total} link{'s' if total > 1 else ''}…"})
    analises = _analisar_todos(links, qualidade, ao_evento, cancelado)
    falhas = sum(isinstance(a, ErroUsuario) for a in analises)
    validos = [(i, a) for i, a in enumerate(analises) if isinstance(a, dict)]

    if cancelado():
        return {"ok": 0, "falhas": falhas, "so_conferir": so_conferir, "cancelado": True}
    if so_conferir:
        for i, _analise in validos:
            ao_evento({"tipo": "item", "i": i, "estado": "ok", "tom": "sucesso"})
        return {"ok": len(validos), "falhas": falhas, "so_conferir": True, "cancelado": False}

    pesos = pesos_da_fila([a for _, a in validos])
    soma = sum(pesos) or 1.0
    feito = 0.0
    ok = 0
    interrompido = False
    ao_evento({"tipo": "total", "fracao": 0.0})

    for n, ((i, analise), peso) in enumerate(zip(validos, pesos)):
        if cancelado():
            interrompido = True
            break
        ao_evento({"tipo": "geral", "texto": f"{n + 1} de {len(validos)}: {analise['titulo']}"})
        ao_evento({"tipo": "item", "i": i, "estado": "baixando…", "tom": "ativo"})

        def ao_progresso(p, i=i, peso=peso, feito=feito):
            ao_evento({"tipo": "progresso", "i": i, **p})
            if p.get("fracao") is not None:
                ao_evento({"tipo": "total", "fracao": min(1.0, (feito + peso * p["fracao"]) / soma)})

        try:
            baixar(links[i], qualidade, pasta, analise["e_playlist"], ao_progresso, cancelado,
                   tamanho_estimado=analise["bytes"])
        except Cancelado:
            ao_evento({"tipo": "item", "i": i, "estado": "cancelado", "tom": "normal"})
            interrompido = True
            break
        except ErroUsuario as exc:
            ao_evento({"tipo": "item", "i": i, "estado": str(exc), "tom": "erro"})
            falhas += 1
        else:
            ao_evento({"tipo": "item", "i": i, "estado": "concluído", "tom": "sucesso"})
            ok += 1
        feito += peso  # com erro também: a parte dele não vai mais ser baixada
        ao_evento({"tipo": "total", "fracao": min(1.0, feito / soma)})

    return {"ok": ok, "falhas": falhas, "so_conferir": False, "cancelado": interrompido}
