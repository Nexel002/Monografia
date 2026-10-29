<#
.SYNOPSIS
  Arranca a demonstração (API + dashboard) e abre o browser. Um clique, sem três terminais.

.DESCRIPTION
  1. confirma que há uv e Node;  2. importa os resultados guardados para o PostgreSQL embebido;
  3. arranca a API;  4. compila (se for preciso) e serve o dashboard;  5. abre o browser.
  Para parar: scripts\parar_demo.ps1 (ou parar_demo.bat).

.PARAMETER PortaApi      Porta da API (por omissão 8000).
.PARAMETER PortaFront    Porta do dashboard (por omissão 5174; é a que a API aceita por CORS).
.PARAMETER Reiniciar     Se já houver API/dashboard deste projecto a correr, pára-os e arranca de novo.
.PARAMETER Reconstruir   Obriga a compilar o dashboard outra vez.
.PARAMETER SemBrowser    Não abre o browser (para testes).
.PARAMETER Modo          «preview» (dashboard compilado, mais estável; por omissão) ou «dev» (com recarga automática).
#>
param(
    [int]$PortaApi = 8000,
    [int]$PortaFront = 5174,
    [switch]$Reiniciar,
    [switch]$Reconstruir,
    [switch]$SemBrowser,
    [ValidateSet("preview", "dev")][string]$Modo = "preview"
)

# «Continue» e não «Stop»: no PowerShell 5.1, o stderr de um programa nativo (uv, npm) com `2>&1` virava erro fatal
# mesmo com código de saída 0. Cada passo verifica o $LASTEXITCODE e chama Falhar() se correu mal.
$ErrorActionPreference = "Continue"
$raiz = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $raiz "backend"
$frontend = Join-Path $raiz "frontend"
$pastaDemo = Join-Path $raiz ".demo"
$pastaLogs = Join-Path $raiz "logs"
$ficheiroPids = Join-Path $pastaDemo "pids.json"

function Falhar([string]$mensagem) {
    Write-Host ""
    Write-Host "ERRO: $mensagem" -ForegroundColor Red
    exit 1
}

function Passo([string]$texto) { Write-Host "-> $texto" -ForegroundColor Cyan }

function Processo-Da-Porta([int]$porta) {
    $ligacao = Get-NetTCPConnection -LocalPort $porta -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $ligacao) { return $null }
    return Get-CimInstance Win32_Process -Filter "ProcessId=$($ligacao.OwningProcess)"
}

function Parar-Arvore([int]$processoId) {
    # taskkill /T mata também os filhos (uv -> python, npm -> node): sem isto ficavam processos órfãos
    & taskkill /PID $processoId /T /F 2>$null | Out-Null
}

function Esperar-Por([string]$url, [int]$segundos, [string]$nome) {
    $limite = (Get-Date).AddSeconds($segundos)
    while ((Get-Date) -lt $limite) {
        try {
            $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3
            if ($r.StatusCode -eq 200) { return }
        } catch { Start-Sleep -Seconds 2 }
    }
    Falhar "$nome não respondeu em $segundos s. Vê os registos em $pastaLogs."
}

# --- pré-requisitos ---------------------------------------------------------------------------
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { Falhar "Falta o 'uv' (gestor do Python). Instala-o em https://docs.astral.sh/uv/ e tenta de novo." }
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { Falhar "Falta o Node.js (npm). Instala-o em https://nodejs.org e tenta de novo." }
if (-not (Test-Path (Join-Path $frontend "node_modules"))) { Passo "A instalar as dependências do dashboard (só na primeira vez)..."; Push-Location $frontend; npm install | Out-Null; Pop-Location }

New-Item -ItemType Directory -Force -Path $pastaDemo, $pastaLogs -ErrorAction Stop | Out-Null

# --- portas: só se mexe em processos DESTE projecto ---------------------------------------------
foreach ($alvo in @(@{ Porta = $PortaApi; Marca = "gestao_trafego"; Nome = "A API" }, @{ Porta = $PortaFront; Marca = $frontend; Nome = "O dashboard" })) {
    $p = Processo-Da-Porta $alvo.Porta
    if (-not $p) { continue }
    $nosso = $p.CommandLine -and $p.CommandLine.Contains($alvo.Marca)
    if (-not $nosso) { Falhar "A porta $($alvo.Porta) está ocupada por outro programa ($($p.Name), PID $($p.ProcessId)). Fecha-o ou escolhe outra porta com -PortaApi / -PortaFront." }
    if ($Reiniciar) { Passo "$($alvo.Nome) já estava a correr (PID $($p.ProcessId)): a parar..."; Parar-Arvore $p.ProcessId; Start-Sleep -Seconds 2 }
    else { Falhar "$($alvo.Nome) deste projecto já está a correr na porta $($alvo.Porta) (PID $($p.ProcessId)), possivelmente com código antigo. Usa -Reiniciar para o arrancar de novo." }
}

# --- backend --------------------------------------------------------------------------------------
Passo "A preparar o backend (dependências Python)..."
Push-Location $backend
try {
    # --inexact: não remove pacotes que não estejam no lock; sem isto, com a API já a correr (ficheiros .pyd abertos) o sync falhava
    & uv sync --frozen --inexact 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { Falhar "Falhou o 'uv sync'. Corre-o à mão na pasta backend para ver o erro." }
    Passo "A importar os resultados para a base de dados (PostgreSQL embebido; na primeira vez demora)..."
    & uv run python -m gestao_trafego.dados.importar 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { Falhar "Falhou a importação dos resultados. Corre 'uv run python -m gestao_trafego.dados.importar' na pasta backend para ver o erro." }

    Passo "A arrancar a API na porta $PortaApi..."
    $env:ORIGENS_PERMITIDAS = "http://localhost:$PortaFront,http://127.0.0.1:$PortaFront"
    $api = Start-Process -FilePath "uv" -ArgumentList @("run", "uvicorn", "gestao_trafego.api.app:criar_app", "--factory", "--port", "$PortaApi") `
        -WorkingDirectory $backend -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $pastaLogs "api.log") -RedirectStandardError (Join-Path $pastaLogs "api.erros.log")
} finally { Pop-Location }
Esperar-Por "http://127.0.0.1:$PortaApi/api/saude" 150 "A API"

# --- frontend ---------------------------------------------------------------------------------------
$env:VITE_API_URL = "http://localhost:$PortaApi"  # é lida NO BUILD: por isso a compilação depende da porta da API
Push-Location $frontend
try {
    $marcaDoBuild = Join-Path $frontend "dist\.api_url"
    $precisaDeBuild = $Modo -eq "preview" -and ($Reconstruir -or -not (Test-Path (Join-Path $frontend "dist\index.html")) -or -not (Test-Path $marcaDoBuild) -or ((Get-Content $marcaDoBuild -Raw).Trim() -ne $env:VITE_API_URL))
    if ($precisaDeBuild) {
        Passo "A compilar o dashboard..."
        & npm run build 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) { Parar-Arvore $api.Id; Falhar "Falhou a compilação do dashboard. Corre 'npm run build' na pasta frontend para ver o erro." }
        Set-Content -Path $marcaDoBuild -Value $env:VITE_API_URL
    }
    Passo "A servir o dashboard na porta $PortaFront ($Modo)..."
    $comando = if ($Modo -eq "preview") { @("vite", "preview", "--port", "$PortaFront", "--strictPort", "--host", "127.0.0.1") } else { @("vite", "--port", "$PortaFront", "--strictPort", "--host", "127.0.0.1") }
    $front = Start-Process -FilePath "npx.cmd" -ArgumentList $comando -WorkingDirectory $frontend -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $pastaLogs "dashboard.log") -RedirectStandardError (Join-Path $pastaLogs "dashboard.erros.log")
} finally { Pop-Location }
Esperar-Por "http://127.0.0.1:$PortaFront/" 90 "O dashboard"

@{ api = $api.Id; dashboard = $front.Id; portaApi = $PortaApi; portaFront = $PortaFront } | ConvertTo-Json | Set-Content -Path $ficheiroPids

Write-Host ""
Write-Host "Tudo a correr." -ForegroundColor Green
Write-Host "  Dashboard:  http://localhost:$PortaFront"
Write-Host "  API:        http://localhost:$PortaApi/docs"
Write-Host "  Registos:   $pastaLogs"
Write-Host "  Para parar: scripts\parar_demo.ps1  (ou duplo clique em parar_demo.bat)"
if (-not $SemBrowser) { Start-Process "http://localhost:$PortaFront" }
