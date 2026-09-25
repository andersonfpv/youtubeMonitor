# Instalação e migração no Windows

1. Baixe o repositório. Instale Python 3.10+ e Chrome.
2. Para substituir a instalação existente, desabilite temporariamente a tarefa antiga e aguarde o Python terminar. Guarde configuração e dados locais.
3. Abra `scripts\instalar.bat`. Ele copia código e inicializadores para `C:\scripts`, com backup dos arquivos anteriores. Não altera `.env`, CSV ou estados. O instalador pode exigir permissão de escrita nessa pasta.
4. Na raiz do repositório, prepare o Python de produção:

```powershell
py -3 -m venv C:\scripts\venv
C:\scripts\venv\Scripts\python.exe -m pip install -r requirements.txt
```

5. Em instalação nova, copie `scripts\.env.example` para `C:\scripts\.env` e preencha localmente. Em instalação existente, mantenha o `.env` e revise as opções usando o exemplo. Não reutilize uma senha que tenha sido exposta no GitHub.
6. Escolha **uma** forma: reabilitar a tarefa antiga ou abrir `C:\scripts\iniciar_continuo.bat`.

Para outro Python, defina MONITOR_PYTHON com o caminho absoluto. Os inicializadores usam esse valor ou o venv ao lado do script.

## Validação operacional

Use `--collect-only` com as URLs atuais, compare o contador com a mesma live no mesmo momento e confira raw_counter_text. Um campo vazio significa indisponibilidade, não audiência zero. Faça envio manual apenas quando quiser realmente enviar e-mail; ele não limpa dados. Confira o próximo relatório agendado no log, incluindo horário previsto e atraso.

## Agendador existente

O VBS pode permanecer como ação: agora espera o processo terminar e devolve seu código de saída. Configure execução mesmo sem login, recuperação de início perdido e uma única instância. Revise bateria/suspensão e habilite Histórico. Com intervalo de três minutos, a verificação do envio só começa quando a tarefa roda; para maior pontualidade, use o modo contínuo.

## Sem Agendador

O modo contínuo não exige tarefa periódica, mas a janela deve ficar aberta e o computador acordado. Para iniciar no boot e reiniciar após falha, configurar como serviço Windows via WinSW. Isso exige instalação administrativa e validação do Chrome, rede e permissões sob a conta do serviço. Para independência do computador local, usar servidor sempre ligado.

Recuperação de envio incerto, opções e limitações: [operação](operacao.md). Documentos Word da pasta são históricos, não instruções desta versão.
