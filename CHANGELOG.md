# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). Datas no fuso de Brasília.

## [0.0.1] - 2026-09-22
### Adicionado
- Estrutura base em Python + PySide6 (QML), app nativo sem web/servidor.
- Hub central "TOOLBOX" com entrada de arquivo compartilhada (clique ou arrastar e soltar).
- Registro automático de apps em `toolbox/apps/<id>/` via `manifesto.json`, com filtro por tipo de arquivo.
- Bolhas dos apps em órbita, com mesma distância entre si para qualquer quantidade.
- Animações: bolhas saem do hub em sequência; ao trocar o arquivo recolhem e só as compatíveis voltam;
  ao abrir um app a bolha expande até cobrir a janela e a toolbox vira ícone no canto (Esc ou clique para voltar).
- `iniciar.bat` para uso diário (prepara `.venv` só quando necessário) e `iniciar.bat --dev` com recarga do QML.
