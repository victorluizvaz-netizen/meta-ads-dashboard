# setup_alertas.ps1
# Execute este script UMA VEZ como Administrador para agendar o runner no Windows.
# Depois disso, o alertas_runner.py roda automaticamente a cada 30 minutos.
#
# Para executar: clique com botão direito > "Executar como Administrador"
# Ou no PowerShell: Set-ExecutionPolicy RemoteSigned -Scope CurrentUser

$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python     = (Get-Command pythonw -ErrorAction SilentlyContinue).Source
if (-not $Python) { $Python = (Get-Command python).Source }
$Runner     = Join-Path $ScriptDir "alertas_runner.py"
$TaskName   = "MetaAds_Alertas"

Write-Host ""
Write-Host "Configurando agendamento: $TaskName"
Write-Host "  Python : $Python"
Write-Host "  Script : $Runner"
Write-Host ""

# Remove tarefa anterior se existir
schtasks /delete /tn $TaskName /f 2>$null | Out-Null

# Cria tarefa: a cada 30 minutos, das 06:00 às 23:00, todos os dias
schtasks /create `
    /tn $TaskName `
    /tr "`"$Python`" `"$Runner`"" `
    /sc MINUTE `
    /mo 30 `
    /st 06:00 `
    /et 23:30 `
    /f `
    /rl HIGHEST | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "Tarefa '$TaskName' criada com sucesso!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Horario  : 06:00 ate 23:30, a cada 30 minutos"
    Write-Host "Relatorio: diario as 08:00 (dados do dia anterior)"
    Write-Host ""
    Write-Host "Para testar agora:"
    Write-Host "  python `"$Runner`""
    Write-Host ""
    Write-Host "Para remover o agendamento:"
    Write-Host "  schtasks /delete /tn $TaskName /f"
} else {
    Write-Host "Erro ao criar tarefa. Execute como Administrador." -ForegroundColor Red
}
