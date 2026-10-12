# GeoRevive Africa - one-time setup for Windows (PowerShell 5.1 or 7)
# Run from the GeoRevive folder:   powershell -ExecutionPolicy Bypass -File .\setup.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    OK  $msg" -ForegroundColor Green }
function Write-Warn2($msg) { Write-Host "    !!  $msg" -ForegroundColor Yellow }

function New-RandomToken([int]$bytes = 18) {
    $b = New-Object byte[] $bytes
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b)
    return ([Convert]::ToBase64String($b)).Replace("+", "-").Replace("/", "_").TrimEnd("=")
}

# 1. Python 3.11 -------------------------------------------------------------
Write-Step "Checking Python 3.11"
$py = $null
try { $v = & py -3.11 --version 2>$null; if ($LASTEXITCODE -eq 0) { $py = @("py", "-3.11") } } catch {}
if (-not $py) {
    try { $v = & python --version 2>$null; if ($v -match "3\.11") { $py = @("python") } } catch {}
}
if (-not $py) {
    Write-Warn2 "Python 3.11 was not found."
    Write-Host  "    Install it from https://www.python.org/downloads/release/python-3119/ (tick 'Add python.exe to PATH'),"
    Write-Host  "    or run:  winget install --id Python.Python.3.11"
    exit 1
}
Write-Ok "$v"

# 2. Virtual environment + packages -----------------------------------------
Write-Step "Creating virtual environment (.venv) and installing Python packages (this can take several minutes)"
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    if ($py.Count -gt 1) { & $py[0] $py[1] -m venv .venv } else { & $py[0] -m venv .venv }
}
$venvPy = Join-Path $Root ".venv\Scripts\python.exe"
& $venvPy -m pip install --upgrade pip --quiet
& $venvPy -m pip install -e "backend[dev,llm]" --quiet
if ($LASTEXITCODE -ne 0) { Write-Warn2 "pip install failed - see messages above."; exit 1 }
Write-Ok "Python packages installed"

# 3. .env with generated secrets --------------------------------------------
Write-Step "Preparing .env (secrets stay on this computer)"
if (-not (Test-Path ".env")) {
    $lines = Get-Content ".env.example"
    $passwords = @{}
    $out = foreach ($line in $lines) {
        if ($line -match "^GEOREVIVE_SECRET_KEY=") { "GEOREVIVE_SECRET_KEY=$(New-RandomToken 32)" }
        elseif ($line -match "^(GEOREVIVE_(\w+)_PASSWORD)=$") {
            $pw = New-RandomToken 9
            $passwords[$Matches[2].ToLower()] = $pw
            "$($Matches[1])=$pw"
        }
        else { $line }
    }
    $out | Set-Content -Path ".env" -Encoding utf8
    Write-Ok ".env created. Demo account passwords (also stored in .env):"
    foreach ($k in $passwords.Keys) { Write-Host ("      {0,-10} {1}" -f $k, $passwords[$k]) }
} else {
    Write-Ok ".env already exists - left unchanged"
}

# 4. Tesseract OCR ------------------------------------------------------------
Write-Step "Checking Tesseract OCR"
$tess = Get-Command tesseract -ErrorAction SilentlyContinue
if (-not $tess -and (Test-Path "C:\Program Files\Tesseract-OCR\tesseract.exe")) { $tess = "C:\Program Files\Tesseract-OCR\tesseract.exe" }
if ($tess) {
    Write-Ok "Tesseract found"
} else {
    Write-Warn2 "Tesseract is not installed. GeoRevive will use its built-in fallback OCR engine (RapidOCR),"
    Write-Host  "    but Tesseract is recommended for best word boxes. To install it:"
    Write-Host  "      winget install --id UB-Mannheim.TesseractOCR"
    Write-Host  "    or download the installer from https://github.com/UB-Mannheim/tesseract/wiki"
    Write-Host  "    then re-run this script (or set TESSERACT_CMD in .env to tesseract.exe)."
}

# 5. Node.js + frontend build --------------------------------------------------
Write-Step "Checking Node.js and building the web interface"
$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) {
    Write-Warn2 "Node.js was not found. Install the LTS version from https://nodejs.org/ or: winget install OpenJS.NodeJS.LTS"
    exit 1
}
Write-Ok "Node $(node --version)"
Push-Location frontend
& npm.cmd install --no-fund --no-audit
& npm.cmd run build
$buildOk = ($LASTEXITCODE -eq 0)
Pop-Location
if (-not $buildOk) { Write-Warn2 "Frontend build failed - see messages above."; exit 1 }
Write-Ok "Web interface built (frontend\dist)"

# 6. Database -----------------------------------------------------------------
Write-Step "Initialising the database and demo accounts"
& $venvPy -c "from georevive.api.app import startup; startup(); print('database ready')"

Write-Host "`nSetup complete." -ForegroundColor Green
Write-Host "Next steps:"
Write-Host "  1. Download the open data:   .\.venv\Scripts\python.exe -m georevive.ingest --all"
Write-Host "  2. Start GeoRevive:          double-click 'Start GeoRevive.bat'"
