# Validação e migração — 25/09/2026

Base revisada: commit `43bb88a01aced48369c09254dbf00c528ad740b4`, branch main. O código Python corresponde ao original local analisado, desconsiderando espaços finais. Não havia testes ou arquivo de dependências; os guias citavam um script com sufixo `_fixed` ausente do repositório.

## Resultado

- 15 testes automatizados aprovados no Windows/Python 3.13.
- Sintaxe dos dois módulos Python validada.
- Interface de linha de comando validada com `--help`.
- Código, documentação e inicializadores integrados na pasta scripts existente.
- Adicionados requirements.txt, .gitignore e .env.example sem credenciais.
- Removidos da árvore atual .env, logs, CSVs e estados de execução que estavam versionados. Os arquivos antigos continuam acessíveis pelo histórico; não houve reescrita de commits.

Casos cobertos: parsing completo; rejeição de abreviações; identidade/estado da live; prioridade do aria-label; horários inválidos; meia-noite; múltiplos horários; snapshots distintos; exclusão mútua; estado antigo; estado corrompido; falha SMTP incerta; retomada após aceite; preservação de linhas novas; teste manual não destrutivo; independência de envio em falha do coletor; aspas na configuração; anexo ausente.

## Limites desta validação

SMTP e Selenium foram simulados nos testes. Não foram enviados e-mails nem comparadas contagens reais do YouTube nesta validação. Não foi instalado serviço Windows nem alterado o Agendador. Os documentos Word foram mantidos como material histórico; os guias Markdown foram atualizados.

## Migração

Antes de atualizar um checkout existente com git pull, copie .env, estados, CSVs e logs para fora do checkout: arquivos anteriormente versionados serão removidos por esta atualização. O instalador para C:\scripts não remove configuração ou dados locais existentes.

Se a senha SMTP publicada na versão anterior era real, revogue-a no provedor e configure uma nova localmente. Retirar o arquivo da árvore atual não remove a credencial do histórico público.

As melhorias futuras recomendadas são serviço Windows, monitor externo de ausência de coleta, rotação/retenção de logs e snapshots e avaliação da API oficial do YouTube. Nenhuma dessas capacidades deve ser presumida como instalada.
