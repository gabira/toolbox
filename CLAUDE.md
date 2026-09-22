# TOOLBOX

App desktop nativo e leve (Windows): hub circular com input de arquivo compartilhado e apps plugáveis em volta.
Stack: **Python 3.11+ + PySide6 (QML)**. Sem web, sem servidor, sem processo em segundo plano.

## Idioma
Português (pt-BR) em tudo: código, comentários, nomes, mensagens de UI, commits e respostas. Fuso de Brasília.

## Executar
- `iniciar.bat` — uso normal (cria `.venv` e instala dependências só na 1ª vez ou quando `requirements*.txt` mudar).
- `iniciar.bat --dev` — console com logs + recarga automática do QML ao salvar.
- Gerar `.exe`/instalador **somente quando o usuário pedir**.

## Estrutura (inspirada nos "apps" do Django)
- `toolbox/nucleo/` — compartilhado: registro de apps, tipo de arquivo, config, FFmpeg, tarefas em thread.
- `toolbox/ui/` — janela, hub (animações), componentes e tema.
- `toolbox/apps/<id>/` — cada app é autocontido: `manifesto.json`, `controlador.py` (QObject exposto ao QML), `servico.py` (regra de negócio, sem Qt), `Tela.qml`, `icone.svg`, `testes/`.
- **Novo app** = nova pasta em `toolbox/apps/`. O hub descobre sozinho; `tipos_aceitos` (ex.: `["video/*"]`) define quando ele aparece.
  Apps que trabalham com link/texto usam `"precisa_arquivo": false` e aparecem sempre (selo LINK).
- O tipo do arquivo é detectado pelo conteúdo (`nucleo.arquivo.detectar_tipo`), com a extensão como reserva.
- Toda `Tela.qml` recebe `controlador` e `cor` (do manifesto); o arquivo compartilhado está em `nucleo.arquivo` (reagir a `nucleo.onArquivoAlterado`).
- Trabalho demorado vai em `nucleo.tarefa.Tarefa` (thread); `servico.py` levanta `nucleo.erros.ErroUsuario`/`Cancelado`.
- Modelos de referência: `toolbox/apps/separador_audio/` (arquivo) e `toolbox/apps/baixador_youtube/` (link, fila com `QAbstractListModel`).
- Componentes de UI prontos em `toolbox/ui/componentes/` (Botao, CampoTexto, AreaTexto, SeletorAbas, CaixaMarcar, OpcaoSelecao, Cartao, BarraProgresso).

## Fluxo obrigatório de toda implementação
1. `git switch dev && git switch -c feat/<assunto>`.
2. Implementar.
3. Testar (ver regra de testes).
4. Atualizar `VERSION` e `CHANGELOG.md` conforme a regra de versionamento.
5. Merge em `dev` (`git merge --no-ff`) com commit resumindo a entrega.

## Versionamento
- `VERSION` é a fonte única (lida por `toolbox/__init__.py` e exibida na UI).
- Começou em `0.0.1`. **`1.0.0` somente ao gerar o primeiro `.exe`.**
- `+0.0.1` bug/texto/cor/CSS · `+0.1.0` nova funcionalidade (app, tela, estrutura) · `+1.0.0` primeiro `.exe` ou mudança estrutural grande (após 1.0.0).

## Testes (enxutos)
- Rodar **só os testes da área alterada**: `.venv\Scripts\python -m pytest toolbox/apps/<id>` ou `-k <assunto>`.
- Suíte completa (`python -m pytest`) só quando `toolbox/nucleo/` mudar, antes do merge.
- Testes ficam dentro da pasta do módulo/app (`testes/teste_*.py`).
