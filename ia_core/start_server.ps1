Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Ir a la carpeta del script
Push-Location $PSScriptRoot

Write-Host "Lanzando servidor Flask en nueva ventana..."

# Construir comando para ejecutar en la nueva ventana (activa venv y arranca Flask sin reloader)
$psCommand = "cd `"$PSScriptRoot`"; & `".\\.venv\\Scripts\\Activate.ps1`"; python -c \"import api_chat; api_chat.app.run(debug=False, host='127.0.0.1', port=5000)\""

Start-Process powershell -ArgumentList '-NoExit','-Command',$psCommand -WindowStyle Normal

# Esperar unos segundos para que el servidor arranque y abrir el navegador en el endpoint de salud
Start-Sleep -Seconds 4
try {
	Start-Process "http://127.0.0.1:5000/api/health"
} catch {
	Write-Host "No se pudo abrir el navegador automáticamente. Abre http://127.0.0.1:5000/api/health manualmente."
}

# Volver al directorio anterior
Pop-Location
