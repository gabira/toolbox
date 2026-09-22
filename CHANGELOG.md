# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). Datas no fuso de Brasília.

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
