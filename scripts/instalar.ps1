$ErrorActionPreference = 'Stop'
$target = 'C:\scripts'
$names = @('monitor_youtube_live_multi.py', 'monitor_runtime.py', 'report_schedule.py', 'agenda_relatorios.py', 'agenda.html', 'app.py', 'app_service.py', 'dashboard_data.py', 'dashboard.py', 'dashboard.html', 'abrir_agenda.bat', 'abrir_dashboard.bat', 'rodar_monitor.bat', 'rodar_monitor_silent.vbs', 'iniciar_continuo.bat')
Write-Host 'Antes de continuar, desabilite a tarefa Monitor YouTube Live e aguarde a coleta atual terminar.'
Write-Host 'O instalador preserva .env, CSV e estados; nao inicia processos nem envia e-mails.'
$answer = Read-Host 'Digite INSTALAR para confirmar que a tarefa foi desabilitada'
if ($answer -cne 'INSTALAR') { throw 'Instalacao cancelada.' }
$running = Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python(w)?\.exe$' -and $_.CommandLine -match 'monitor_youtube_live_multi\.py' }
if ($running) { throw 'Ainda existe monitor Python ativo. Aguarde sua conclusao antes de instalar.' }
foreach ($name in $names) {
    if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot $name))) { throw "Arquivo ausente: $name" }
}
# Files may already have been extracted into the destination.
$sourceRoot = [System.IO.Path]::GetFullPath($PSScriptRoot).TrimEnd('\')
$targetRoot = [System.IO.Path]::GetFullPath($target).TrimEnd('\')
if ([string]::Equals($sourceRoot, $targetRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    Write-Host 'Os arquivos ja estao em C:\scripts. Nenhuma copia e necessaria.'
    Write-Host 'Este instalador nao criou backup da versao anterior a extracao.'
    Write-Host 'Pode testar a coleta ou iniciar o modo escolhido.'
    exit 0
}
$backup = Join-Path $target ('backup_monitor_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
New-Item -ItemType Directory -Path $backup -Force | Out-Null
foreach ($name in $names) {
    $destination = Join-Path $target $name
    if (Test-Path -LiteralPath $destination) { Copy-Item -LiteralPath $destination -Destination (Join-Path $backup $name) }
}
foreach ($name in $names) {
    $source = Join-Path $PSScriptRoot $name
    $destination = Join-Path $target $name
    Copy-Item -LiteralPath $source -Destination $destination -Force
    if ((Get-FileHash -LiteralPath $source).Hash -ne (Get-FileHash -LiteralPath $destination).Hash) { throw "Falha de verificacao: $name. Backup em $backup" }
}
Write-Host "Instalado. Backup: $backup"
Write-Host 'Escolha uma opcao: reabilitar a tarefa antiga OU abrir C:\scripts\iniciar_continuo.bat.'
Write-Host 'Consulte LEIA-ME.md antes de configurar operacao como servico.'
