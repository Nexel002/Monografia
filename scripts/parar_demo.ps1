<#
.SYNOPSIS
  Pára a API e o dashboard que o iniciar_demo.ps1 arrancou.
#>
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$ficheiroPids = Join-Path $raiz ".demo\pids.json"

if (-not (Test-Path $ficheiroPids)) {
    Write-Host "Não há nenhuma demonstração registada (falta .demo\pids.json). Nada a parar." -ForegroundColor Yellow
    exit 0
}

$estado = Get-Content $ficheiroPids -Raw | ConvertFrom-Json
foreach ($par in @(@("API", $estado.api, $estado.portaApi), @("Dashboard", $estado.dashboard, $estado.portaFront))) {
    $nome, $processoId, $porta = $par
    # /T mata também os filhos (uv -> python, npx -> node)
    & taskkill /PID $processoId /T /F 2>$null | Out-Null
    # Por segurança, qualquer coisa ainda à escuta nessa porta e deste projecto (o PID guardado pode ter mudado)
    $ligacao = Get-NetTCPConnection -LocalPort $porta -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($ligacao) {
        $p = Get-CimInstance Win32_Process -Filter "ProcessId=$($ligacao.OwningProcess)"
        if ($p.CommandLine -and ($p.CommandLine.Contains("gestao_trafego") -or $p.CommandLine.Contains($raiz))) { & taskkill /PID $ligacao.OwningProcess /T /F 2>$null | Out-Null }
    }
    Write-Host "$nome parado (porta $porta)."
}
Remove-Item $ficheiroPids -Force
Write-Host "Feito." -ForegroundColor Green
