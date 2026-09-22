# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). Datas no fuso de Brasília.

## [0.8.1] - 2026-09-22
### Alterado
- Baixar do YouTube, "Vários vídeos": a barra de cima mostra o progresso da fila inteira, pesado pelo tamanho
  de cada vídeo; cada linha da fila mostra o próprio percentual.
- A fila agora analisa todos os links antes de baixar (4 ao mesmo tempo): links com problema aparecem logo
  no início e cada item mostra o tamanho estimado ("na fila · 11,3 MB").

### Corrigido
- Em alta resolução (vídeo e áudio em faixas separadas) o percentual voltava a zero no meio do download;
  agora soma as duas faixas e só sobe.
- O texto "Finalizando com o FFmpeg…" do vídeo anterior não fica mais aparecendo no início do próximo.

## [0.8.0] - 2026-09-22
### Adicionado
- App **Gravador**: grava o microfone e o som do computador (ex.: você e os participantes de uma videochamada)
  e salva tudo em um único arquivo — FLAC 24 bits (padrão), WAV 24 bits ou MP3 320 kb/s.
  - Captura do som do PC por loopback do WASAPI (sem Mixagem Estéreo nem driver virtual).
  - Silêncios do PC não tiram as faixas de sincronia; a mixagem mantém o volume de cada voz, com limitador.
  - Medidores de nível, cronômetro, escolha de microfone e saída, nome e pasta de destino.
  - A gravação continua ao voltar para o hub; fechar a janela gravando salva o arquivo.
- Dependência `PyAudioWPatch` (instalada sozinha pelo `iniciar.bat`).

### Alterado
- Selo LINK só aparece nas bolhas de apps que aceitam links.

## [0.7.2] - 2026-09-22
### Corrigido
- Com um arquivo no centro (ex.: imagem PNG), o "Baixar do YouTube" aparecia junto. Agora ele só aparece
  com o centro vazio ou com um link do YouTube.
- Links do YouTube só são aceitos com domínio exato e ID válido (vídeo de 11 caracteres, short, live ou playlist);
  domínios parecidos, páginas de canal e miniaturas são recusados.
- Um caminho de arquivo colado vale como arquivo antes de qualquer tentativa de ler como link.

### Alterado
- Resumo da entrada mais claro: "imagem PNG · 1,5 KB", "vídeo MKV · 1,2 GB", "link (não é do YouTube)".

## [0.7.1] - 2026-09-22
### Alterado
- Centro do hub sem o símbolo "T" (fica só a palavra TOOLBOX, a entrada e a dica); o "T" continua como ícone do canto.
- Ícone da janela, da barra de tarefas e do atalho: só o símbolo "T", sem texto.
- Abertura com o logo 50% mais longa.

### Corrigido
- Barra de tarefas do Windows mostrava o ícone do Python: o processo agora tem identidade própria (AppUserModelID).

## [0.7.0] - 2026-09-22
### Adicionado
- App **Para PDF**: aparece só quando o arquivo pode virar PDF neste computador.
  - Imagens (JPG, PNG, BMP, GIF, TIFF, WEBP): sem perda de qualidade — o JPEG entra no PDF byte a byte;
    várias imagens viram várias páginas (adicionar, reordenar, remover); página do tamanho da imagem ou A4.
  - Word, RTF, ODT, Excel, CSV, ODS, PowerPoint e ODP: pelo Microsoft Office instalado ou, sem ele, LibreOffice.
  - Texto, Markdown e HTML: pelo motor de texto do Qt, em folha A4.
  - Nome de saída opcional, pasta (padrão: a do arquivo original), "Abrir PDF" e "Abrir pasta".
- Filtro opcional por app (`apps/<id>/filtro.py`) para o hub mostrar um app só quando ele consegue tratar a entrada.
- Detecção de documentos do Office (inclusive .doc/.xls/.ppt antigos) e RTF pelo conteúdo.
- Dependências novas: Pillow e img2pdf.

### Alterado
- Funções de nome de arquivo de saída movidas para `nucleo/nomes.py` (usadas por mais de um app).

## [0.6.0] - 2026-09-22
### Adicionado
- Entrada híbrida no centro: aceita arquivo **ou** link. Cole/digite um link do YouTube na pílula
  (analisa sozinho ao colar) ou use Ctrl+V em qualquer lugar do hub — funciona também com arquivo
  copiado no Explorer. Arrastar um link do navegador também vale.
- Aviso "Link copiado": ao copiar um link do YouTube, a TOOLBOX oferece usá-lo ("Usar link" / "Agora não").
- Links têm tipo como os arquivos (`link/youtube`); com um link, só os apps que o aceitam aparecem.
- O Baixar do YouTube recebe o link do centro e já analisa; vários links abrem a aba "Vários vídeos" preenchida.
- Link ou texto não reconhecido: a pílula treme e mostra o motivo.

### Alterado
- Sinal `nucleo.arquivoAlterado` → `nucleo.entradaAlterada`; `limparArquivo` → `limparEntrada`.

## [0.5.0] - 2026-09-22
### Adicionado
- Identidade visual com o logo oficial em `toolbox/ui/imagens/` (completo, só símbolo, só texto).
- Abertura animada: o logo completo aparece e dá lugar ao hub (clique para pular).
- Círculo central com o símbolo "T" e a palavra "TOOLBOX" do logo; o "T" vira o ícone do canto no app aberto.
- Ícone `toolbox.ico` (16 a 256 px) na janela e na barra de tarefas.
- `criar-atalho.bat`: cria o atalho "TOOLBOX" na Área de Trabalho com o ícone.

### Removido
- Ícone provisório do cubo.

## [0.4.0] - 2026-09-22
### Adicionado
- App **Baixar do YouTube** (portado do projeto download_yt), sempre disponível no hub por usar link:
  - Aba "Um vídeo": analisa o link, mostra miniatura, título, canal e só as resoluções que o vídeo tem;
    playlists detectadas com opção de baixar inteira; "Usar na TOOLBOX" envia o vídeo baixado ao hub.
  - Aba "Vários vídeos": lista de links (um por linha), qualidade como teto, "Só conferir", "Parar"
    e fila com o estado de cada link — um link com erro não para os outros.
  - MP4 com H.264 + AAC sempre que possível; "Apenas áudio" em MP3 320 kb/s.
  - Usa o FFmpeg embarcado (não precisa instalar) e reaproveita a pasta salva do app antigo.
  - Botão "Atualizar motor" (yt-dlp) para quando o YouTube mudar o site.
- Apps sem arquivo (`"precisa_arquivo": false`) aparecem sempre no hub, com selo LINK.
- Componentes `SeletorAbas`, `AreaTexto` e `CaixaMarcar`.
- Dependência nova: `yt-dlp` (instalada automaticamente pelo `iniciar.bat`).

## [0.3.0] - 2026-09-22
### Adicionado
- Separador de áudio: campo opcional de nome do arquivo de saída, já preenchido com o nome do vídeo,
  com a extensão ao lado, botão "Nome original" e prévia "Será salvo como…".
- Nomes inválidos no Windows são corrigidos automaticamente (caracteres proibidos, nomes reservados).
- Componente `CampoTexto` reutilizável.

## [0.2.0] - 2026-09-22
### Adicionado
- Animação "Analisando arquivo" ao carregar um arquivo: anel girando, arco de varredura, cubo pulsando
  e texto animado; só depois os apps compatíveis saem do hub.
- Detecção do tipo pelo conteúdo do arquivo (assinatura dos primeiros bytes), com a extensão como reserva.

## [0.1.0] - 2026-09-22
### Adicionado
- App **Separador de áudio** (aparece para arquivos de vídeo):
  - Detecta a faixa de áudio (codec, taxa, canais, bitrate, duração).
  - Formato "Original" copia a faixa sem reencodar (sem perdas) no contêiner certo (AAC→.m4a, Opus→.opus etc.).
  - Opções FLAC, WAV 24 bits e MP3 320 kb/s.
  - Pasta de destino e formato lembrados entre usos; nunca sobrescreve arquivos existentes.
  - Barra de progresso, cancelamento (remove o arquivo parcial) e botão "Abrir pasta".
- `nucleo/erros.py` com exceções compartilhadas; tarefas em thread são canceladas ao fechar a janela.

### Corrigido
- Erros de QML no console ao fechar o programa (ordem de destruição do motor QML).

## [0.0.1] - 2026-09-22
### Adicionado
- Estrutura base em Python + PySide6 (QML), app nativo sem web/servidor.
- Hub central "TOOLBOX" com entrada de arquivo compartilhada (clique ou arrastar e soltar).
- Registro automático de apps em `toolbox/apps/<id>/` via `manifesto.json`, com filtro por tipo de arquivo.
- Bolhas dos apps em órbita, com mesma distância entre si para qualquer quantidade.
- Animações: bolhas saem do hub em sequência; ao trocar o arquivo recolhem e só as compatíveis voltam;
  ao abrir um app a bolha expande até cobrir a janela e a toolbox vira ícone no canto (Esc ou clique para voltar).
- `iniciar.bat` para uso diário (prepara `.venv` só quando necessário) e `iniciar.bat --dev` com recarga do QML.
