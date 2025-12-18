<#
Script: set_telegram_token.ps1
Propósito: Pedir de forma segura el token del bot de Telegram en la máquina local,
establecerlo en la variable de entorno de la sesión y opcionalmente persistirlo
usando `setx`. Nunca envíes este token por mensajes.

Uso:
1. Abre PowerShell.
2. Navega a la carpeta del script: `cd C:\Users\carlos\Desktop\MindCare1\ia_core\scripts`
3. Ejecuta: `.\\set_telegram_token.ps1`

El script te preguntará si quieres ejecutar el servidor inmediatamente.
#>

Write-Host "Script para configurar TELEGRAM_BOT_TOKEN localmente`n" -ForegroundColor Cyan

# Pedir token como SecureString
$secure = Read-Host -Prompt 'Introduce el token del bot (se ocultará al escribir)' -AsSecureString

if (-not $secure) {
    Write-Host "No se proporcionó token. Saliendo." -ForegroundColor Yellow
    exit 1
}

# Convertir SecureString a texto para uso en variables de entorno en esta sesión
[IntPtr]$bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
$token = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
[System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)

Write-Host "Token recibido en la sesión actual.`n" -ForegroundColor Green

# Preguntar si desea persistir el token (setx)
$persist = Read-Host -Prompt '¿Guardar el token de forma permanente en el sistema (setx)? (s/n)'
if ($persist -and $persist.ToLower().StartsWith('s')) {
    try {
        setx TELEGRAM_BOT_TOKEN "$token" | Out-Null
        Write-Host "Token guardado permanentemente para el usuario actual. Cierra y vuelve a abrir la terminal para que tenga efecto en nuevas sesiones." -ForegroundColor Green
    } catch {
        Write-Host "Error guardando token con setx: $_" -ForegroundColor Red
    }
}

# Establecer variable en la sesión actual
$env:TELEGRAM_BOT_TOKEN = $token

Write-Host "La variable de entorno \$env:TELEGRAM_BOT_TOKEN se ha establecido en la sesión actual." -ForegroundColor Green

# Preguntar si desea arrancar el servidor ahora
$run = Read-Host -Prompt '¿Deseas arrancar ahora el servidor (python api_chat.py)? (s/n)'
if ($run -and $run.ToLower().StartsWith('s')) {
    Write-Host "Arrancando servidor... Ctrl+C para detener." -ForegroundColor Cyan
    # Cambiar directorio al backend y ejecutar
    Push-Location ..\
    try {
        python api_chat.py
    } finally {
        Pop-Location
    }
}

Write-Host "Listo. No compartas este token en chats ni repositorios públicos." -ForegroundColor Yellow
