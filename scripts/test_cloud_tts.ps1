param(
    [string]$HubUrl = "http://localhost:8000",
    [string]$OutFile = "cloud_tts_test.mp3"
)

$uri = "$HubUrl/cloud/tts/synthesize"
$payload = @{
    text = "This is a cloud TTS test from ResKiosk."
    language = "en"
    voice = "nova"
} | ConvertTo-Json

try {
    $resp = Invoke-WebRequest -Method Post -Uri $uri -Body $payload -ContentType "application/json"
    [System.IO.File]::WriteAllBytes($OutFile, $resp.Content)
    Write-Host "Saved: $OutFile"
    Write-Host "X-TTS-Mode: $($resp.Headers['X-TTS-Mode'])"
} catch {
    Write-Error $_
    exit 1
}

