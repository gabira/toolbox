## Idioma
Português (pt-BR) em tudo: código, comentários, nomes, mensagens de UI, commits e respostas. Fuso de Brasília.

## Fluxo obrigatório de toda implementação

1. `git switch dev && git switch -c feat/<assunto>`.
2. Implementar.
3. Testar.
4. Atualizar `VERSION` e `CHANGELOG.md` conforme a regra de versionamento.
5. Merge em `dev` com commit resumindo a entrega.
6. Excluir a branch `feat/<assunto>`, local e remota (`git branch -d` e `git push origin --delete`).
   O histórico continua preservado dentro do merge; só `main` e `dev` ficam no repositório.

## Versionamento
`+0.0.1` bug/texto/cor/CSS · `+0.1.0` nova funcionalidade (página, aba, estrutura) · `+1.0.0` primeira versão ou mudança estrutural grande.