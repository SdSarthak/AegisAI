$SysId = 4 # Your ID from the last run

$ErrorActionPreference = 'Stop'

# --- CONFIGURATION ---
$BaseUrl = "http://localhost:8000/api/v1"
$WebhookUrl = "YOUR WEBHOOK URL HERE"
$Username = "YOUR EMAIL HERE"
$Password = "YOUR PASSWORD HERE"

# --- 0. AUTHENTICATE ---
Write-Host "Authenticating..."
$loginBody = @{ username = $Username; password = $Password }
$loginResp = Invoke-RestMethod -Uri "$BaseUrl/auth/login" -Method Post -Body $loginBody

if (-not $loginResp.access_token) {
    Write-Host "Authentication failed! No token returned." -ForegroundColor Red
    exit 1
}

$Token = $loginResp.access_token.Trim()
$Headers = @{ "Authorization" = "Bearer $Token" }
Write-Host "Token acquired." -ForegroundColor Green

$driftBody = @{ 
    # Change this value to force the classifier to change its mind
    questionnaire_responses = @{ "hr_recruitment_screening" = $true } 
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/ai-systems/$SysId" `
    -Method Patch `
    -Headers $Headers `
    -ContentType "application/json" `
    -Body $driftBody

Write-Host "Drift injected. Running scan..." -ForegroundColor Green