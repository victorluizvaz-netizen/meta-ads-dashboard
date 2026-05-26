# setup_alertas.ps1
# Execute UMA VEZ como Administrador para agendar o runner no Windows.
# Clique com botão direito > "Executar como Administrador"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python    = (Get-Command pythonw -ErrorAction SilentlyContinue).Source
if (-not $Python) { $Python = (Get-Command python).Source }
$Runner    = Join-Path $ScriptDir "alertas_runner.py"
$TaskName  = "MetaAds_Alertas"

Write-Host ""
Write-Host "Configurando agendamento: $TaskName"
Write-Host "  Python : $Python"
Write-Host "  Script : $Runner"
Write-Host ""

# Remove tarefa anterior se existir
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

# Ação: executar o runner
$action = New-ScheduledTaskAction `
    -Execute $Python `
    -Argument "`"$Runner`"" `
    -WorkingDirectory $ScriptDir

# Gatilho: repetir a cada 60 minutos, das 06:00 às 23:00, todos os dias
$trigger = New-ScheduledTaskTrigger `
    -Daily `
    -At "06:00AM"

# Configurações: reiniciar até 3x em caso de falha, timeout de 10 min
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 5) `
    -MultipleInstances IgnoreNew

# Repetição a cada 60 minutos dentro do gatilho diário
$trigger.RepetitionPattern = $null
$CimTrigger = Get-ScheduledTask -TaskName "MetaAds_Alertas" -ErrorAction SilentlyContinue
# Cria a tarefa primeiro para depois adicionar repetição via XML
$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Highest

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Force | Out-Null

# Adiciona repetição a cada 60 minutos via XML (única forma confiável no PowerShell)
$xml = (Export-ScheduledTask -TaskName $TaskName)
$xml = $xml -replace '<Repetition/>', ''
$xml = $xml -replace '</StartBoundary>', '</StartBoundary><Repetition><Interval>PT60M</Interval><StopAtDurationEnd>false</StopAtDurationEnd></Repetition>'
$null = Register-ScheduledTask -TaskName $TaskName -Xml $xml -Force

if ($LASTEXITCODE -eq 0 -or $?) {
    Write-Host "Tarefa '$TaskName' criada com sucesso!" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Frequencia  : a cada 60 minutos (06:00-23:00)"
    Write-Host "  Recuperacao : reinicia ate 3x em caso de falha (intervalo 5 min)"
    Write-Host "  Timeout     : 10 minutos por execucao"
    Write-Host ""
    Write-Host "Para testar agora:"
    Write-Host "  python `"$Runner`""
    Write-Host ""
    Write-Host "Para remover o agendamento:"
    Write-Host "  Unregister-ScheduledTask -TaskName $TaskName -Confirm:`$false"
} else {
    Write-Host "Erro ao criar tarefa. Execute como Administrador." -ForegroundColor Red
}
