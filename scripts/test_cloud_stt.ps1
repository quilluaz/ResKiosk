param(
    [string]$HubUrl = "http://localhost:8000",
    [string]$AudioPath = ""
)

if (-not (Test-Path $AudioPath)) {
    Write-Host "AudioPath is required and must point to a .wav file."
    exit 1
}

$uri = "$HubUrl/cloud/stt/transcribe"

$form = @{
    session_id = "test-session"
    kiosk_id = "test-kiosk"
    hint_language = "en"
    auto_detect = "true"
    audio = Get-Item $AudioPath
}

try {
    $resp = Invoke-RestMethod -Method Post -Uri $uri -Form $form
    $resp | ConvertTo-Json -Depth 5
} catch {
    Write-Error $_
    exit 1
}

