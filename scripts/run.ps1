$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

if (-not (Test-Path (Join-Path $repoRoot ".env"))) {
    Copy-Item (Join-Path $repoRoot ".env.example") (Join-Path $repoRoot ".env")
    Write-Host "Created .env from .env.example — set GOOGLE_API_KEY and PORTFOLIO_API_URL."
}

Push-Location $repoRoot
try {
    if (-not (Test-Path ".venv")) {
        python -m venv .venv
        .\.venv\Scripts\pip install -r requirements.txt
    }
    .\.venv\Scripts\uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
}
finally {
    Pop-Location
}
