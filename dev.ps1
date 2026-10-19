# ============================================================
#  Arranque rapido en desarrollo - Osorno Runners
#  Uso:  npm run dev        (servidor + Tailwind en modo watch)
#        npm start          (solo servidor, sin recompilar CSS)
#
#  Atajos: Ctrl+C detiene ambos procesos.
# ============================================================

param(
    [switch]$NoWatch,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $raiz

$python = Join-Path $raiz "venv\Scripts\python.exe"
$url = "http://127.0.0.1:8000"

function Escribir($texto, $color = "Gray") {
    Write-Host $texto -ForegroundColor $color
}

# --- 1. Verificaciones minimas -------------------------------------------
if (-not (Test-Path $python)) {
    Escribir "ERROR: no existe el entorno virtual en .\venv" "Red"
    Escribir "Crealo con:" "Yellow"
    Escribir "  python -m venv venv" "White"
    Escribir "  .\venv\Scripts\Activate.ps1" "White"
    Escribir "  pip install -r requirements.txt" "White"
    exit 1
}

if (-not (Test-Path (Join-Path $raiz ".env"))) {
    Copy-Item (Join-Path $raiz ".env.example") (Join-Path $raiz ".env")
    Escribir "Aviso: se creo .env a partir de .env.example. Revisa SECRET_KEY." "Yellow"
}

& $python -c "import fastapi, uvicorn" 2>$null
if ($LASTEXITCODE -ne 0) {
    Escribir "ERROR: faltan dependencias de Python. Ejecuta:" "Red"
    Escribir "  .\venv\Scripts\python.exe -m pip install -r requirements.txt" "White"
    exit 1
}

# --- 2. MySQL (XAMPP) -----------------------------------------------------
$mysqlActivo = Test-NetConnection -ComputerName localhost -Port 3306 -WarningAction SilentlyContinue |
    Select-Object -ExpandProperty TcpTestSucceeded
if (-not $mysqlActivo) {
    Escribir "Aviso: MySQL no responde en localhost:3306." "Yellow"
    Escribir "Abre el Panel de Control de XAMPP y pulsa Start en MySQL." "Yellow"
}

# --- 3. Tailwind en modo watch (opcional) --------------------------------
$css = $null
if (-not $NoWatch) {
    Escribir "Compilando Tailwind en modo watch..." "Cyan"
    $css = Start-Process -FilePath "cmd.exe" `
        -ArgumentList "/c", "npm run css:dev" `
        -WorkingDirectory $raiz -NoNewWindow -PassThru
}

# --- 4. Servidor ---------------------------------------------------------
Escribir ""
Escribir "  Osorno Runners -> $url" "Green"
Escribir "  Detener con Ctrl+C" "Gray"
Escribir ""

if (-not $NoBrowser) {
    Start-Job -ScriptBlock {
        param($destino)
        Start-Sleep -Seconds 3
        Start-Process $destino
    } -ArgumentList $url | Out-Null
}

try {
    & $python -m uvicorn app.main:app --reload
}
finally {
    if ($css -and -not $css.HasExited) {
        Escribir "Deteniendo Tailwind..." "Gray"
        taskkill /PID $css.Id /T /F 2>$null | Out-Null
    }
}
