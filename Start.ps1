param(
    [switch]$SetupOnly
)

$ErrorActionPreference = "Stop"

function Test-PythonInstalled {
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return $true
    }

    if (Get-Command py -ErrorAction SilentlyContinue) {
        return $true
    }

    return $false
}

function Invoke-SystemPython {
    param(
        [string[]]$PythonArgs
    )

    if (Get-Command python -ErrorAction SilentlyContinue) {
        & python @PythonArgs
        return
    }

    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 @PythonArgs
        return
    }

    throw "Python não encontrado no sistema."
}

function Ensure-PythonInstalled {
    if (Test-PythonInstalled) {
        return
    }

    Write-Host "Python 3.11+ não encontrado no sistema."
    $answer = Read-Host "Deseja instalar agora via winget? (S/N)"

    if ($answer -notmatch "^(s|sim|y|yes)$") {
        throw "Python é obrigatório para continuar. Instale o Python 3.11+ e execute novamente."
    }

    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "winget não está disponível neste Windows. Instale o Python manualmente em https://www.python.org/downloads/windows/ e execute novamente."
    }

    Write-Host "Instalando Python 3.11 via winget..."
    & winget install --id Python.Python.3.11 -e --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao instalar Python via winget. Instale manualmente e execute novamente."
    }

    if (-not (Test-PythonInstalled)) {
        throw "Python foi instalado, mas não está disponível nesta sessão. Abra um novo terminal e execute novamente."
    }
}

function Ensure-PipInVenv {
    param(
        [string]$PythonExe
    )

    & $PythonExe -m pip --version *> $null
    if ($LASTEXITCODE -eq 0) {
        return
    }

    Write-Host "pip não encontrado no .venv. Tentando recuperar com ensurepip..."
    & $PythonExe -m ensurepip --upgrade
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao executar ensurepip no ambiente virtual."
    }

    & $PythonExe -m pip --version *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao recuperar o pip no ambiente virtual. Recrie o .venv e tente novamente."
    }
}

function Expand-DotEnvFromUnifiedZip {
    param(
        [string]$ZipPath
    )

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [System.IO.Compression.ZipFile]::OpenRead($ZipPath)

    try {
        $entry = $zip.GetEntry(".env")
        if (-not $entry) {
            return $false
        }

        $destPath = Join-Path (Resolve-Path ".") ".env"
        $entryStream = $entry.Open()

        try {
            $fileStream = [System.IO.File]::Create($destPath)
            try {
                $entryStream.CopyTo($fileStream)
            } finally {
                $fileStream.Dispose()
            }
        } finally {
            $entryStream.Dispose()
        }

        return $true
    } finally {
        $zip.Dispose()
    }
}

function Write-DefaultEnvFile {
    $destPath = Join-Path (Resolve-Path ".") ".env"
    $content = "DATABASE_URI=sqlite:///urls.db`nFLASK_DEBUG=False`nAPI_KEY=`n"
    [System.IO.File]::WriteAllText($destPath, $content, [System.Text.UTF8Encoding]::new($false))
}

Write-Host "[0/4] Verificando Python no sistema..."
Ensure-PythonInstalled

Write-Host "[1/4] Criando ambiente virtual (.venv), se necessário..."
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Criando novo ambiente virtual..."
    Invoke-SystemPython -PythonArgs @("-m", "venv", ".venv")
}

Write-Host "[2/4] Instalando dependências..."
Ensure-PipInVenv -PythonExe ".\.venv\Scripts\python.exe"
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt

Write-Host "[3/4] Garantindo arquivo .env..."
if (-not (Test-Path ".env")) {
    if (Test-Path "env_venv.zip") {
        Write-Host "Extraindo apenas .env de env_venv.zip..."
        if (Expand-DotEnvFromUnifiedZip -ZipPath "env_venv.zip") {
            Write-Host ".env extraído com sucesso"
        } else {
            Write-Host "Arquivo .env não encontrado no env_venv.zip. Criando .env padrão..."
            Write-DefaultEnvFile
        }
    } else {
        Write-Host "Criando .env padrão..."
        Write-DefaultEnvFile
    }
} else {
    $envPath = Resolve-Path ".env"
    $content = Get-Content $envPath -Raw
    if ($content -notmatch "(?m)^DATABASE_URI=") {
        $newContent = $content.TrimEnd() + "`r`nDATABASE_URI=sqlite:///urls.db`r`n"
        [System.IO.File]::WriteAllText($envPath, $newContent, [System.Text.UTF8Encoding]::new($false))
    }
}

Write-Host "[4/4] Validando aplicação..."
& ".\.venv\Scripts\python.exe" -c "from dotenv import load_dotenv; import os; load_dotenv(); from main import app; c=app.test_client(); print('DATABASE_URI=', os.getenv('DATABASE_URI')); print('HOME_STATUS=', c.get('/').status_code)"

if ($SetupOnly) {
    Write-Host "Configuração concluída. Para iniciar: .\Start.ps1"
    exit 0
}

Write-Host "Iniciando aplicação em http://127.0.0.1:5000 ..."
& ".\.venv\Scripts\python.exe" main.py

pause