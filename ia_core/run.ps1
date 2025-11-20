# run.ps1 - Activa/crea venv, instala dependencias, asegura nltk y arranca el servidor
# Uso: Ejecutar desde PowerShell: .\run.ps1

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Situarnos en la carpeta del script (ia_core)
Push-Location $PSScriptRoot

# Verificar que python está disponible
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python no está disponible en PATH. Instala Python 3.8+ y vuelve a intentar."
    Pop-Location
    exit 1
}

$venvPath = Join-Path $PSScriptRoot ".venv"

# Crear entorno virtual si no existe
if (-not (Test-Path $venvPath)) {
    Write-Host "Creando entorno virtual en .venv..."
    python -m venv .venv
}

# Activar entorno virtual
Write-Host "Activando entorno virtual..."
& "$venvPath\Scripts\Activate.ps1"

# Actualizar pip
Write-Host "Actualizando pip..."
python -m pip install --upgrade pip

# Instalar dependencias
$reqFile = Join-Path $PSScriptRoot "requirements.txt"
if (Test-Path $reqFile) {
    Write-Host "Instalando dependencias desde requirements.txt..."
    pip install -r $reqFile
} else {
    Write-Host "requirements.txt no encontrado. Instalando dependencias mínimas (flask, requests, nltk, flask-cors)..."
    pip install flask requests nltk flask-cors
}

# Asegurar vader_lexicon de nltk
Write-Host "Comprobando/descargando 'vader_lexicon' de nltk..."
$py = @'
import nltk
try:
    nltk.data.find('sentiment/vader_lexicon')
    print('vader_lexicon OK')
except LookupError:
    print('Descargando vader_lexicon...')
    nltk.download('vader_lexicon')
    print('vader_lexicon descargado')
'@
$py | python

# Inicializar/crear la base de datos (opcional, seguro de ejecutar varias veces)
Write-Host "Inicializando base de datos (si es necesario)..."
python -c "import db_manager; db_manager.create_connection(); print('DB asegurada')"

# Iniciar servidor
Write-Host "Iniciando servidor Flask (api_chat.py). Usa Ctrl+C para detener."
python api_chat.py

# Volver al directorio anterior
Pop-Location
