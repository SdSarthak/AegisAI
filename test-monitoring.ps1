$ErrorActionPreference = 'Stop'

# --- CONFIGURATION ---
$BaseUrl = "http://localhost:8000/api/v1"
$WebhookUrl = "YOUR WEBHOOK URL HERE"
$Username = "YOUR EMAIL HERE"
$Password = "YOUR PASSWORD HERE"

Write-Host "Starting AegisAI Monitoring End-to-End Test..." -ForegroundColor Cyan

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

# --- 0.5 CREATE SYSTEM ---
Write-Host "Creating a fresh AI System..."
$uniqueName = "Webhook Test System $(Get-Random)"
$sysBody = @{ name = $uniqueName; use_case = "hr_recruitment"; sector = "HR Tech" } | ConvertTo-Json

$system = Invoke-RestMethod -Uri "$BaseUrl/ai-systems/" `
    -Method Post `
    -Headers $Headers `
    -ContentType "application/json" `
    -Body $sysBody

$SysId = $system.id
Write-Host "System created with ID: $SysId" -ForegroundColor Green

# --- 1. ENABLE MONITORING ---
Write-Host "Enabling monitoring and attaching webhook..."
$patchBody = @{ monitoring_enabled = $true; webhook_url = $WebhookUrl } | ConvertTo-Json
$patchResp = Invoke-RestMethod -Uri "$BaseUrl/ai-systems/$SysId/monitoring" `
    -Method Patch `
    -Headers $Headers `
    -ContentType "application/json" `
    -Body $patchBody
Write-Host "Monitoring Enabled: $($patchResp.monitoring_enabled)" -ForegroundColor Green

# --- 2. ROTATE SECRET ---
Write-Host "Generating HMAC Webhook Secret..."
$secretResp = Invoke-RestMethod -Uri "$BaseUrl/ai-systems/$SysId/monitoring/rotate-secret" -Method Post -Headers $Headers
$HmacSecret = $secretResp.webhook_secret
Write-Host "SECRET GENERATED (Save this!): $HmacSecret" -ForegroundColor Yellow

# --- 3. FORCE SCAN ---
Write-Host "Forcing compliance scan..."
$ScanUrl = "$BaseUrl/ai-systems/admin/compliance/scan"
# 1. Update the questionnaire responses to trigger a higher risk level
# We use the $SysId variable that the script just generated
$driftBody = @{
    questionnaire_responses = @{ "hr_recruitment_screening" = $true } # This triggers high risk
} | ConvertTo-Json

Invoke-RestMethod -Uri "$BaseUrl/ai-systems/$SysId" `
    -Method Patch `
    -Headers $Headers `
    -ContentType "application/json" `
    -Body $driftBody

# 2. Force the scan
try {
    $scanResp = Invoke-RestMethod -Uri $ScanUrl -Method Post -Headers $Headers
} catch {
    # If the trailing slash is the issue
    $scanResp = Invoke-RestMethod -Uri $ScanUrl -Method Post -Headers $Headers
}

Write-Host "Scan complete. Events created: $($scanResp.events_created)" -ForegroundColor Green

# --- 4. GET EVENT HISTORY ---
Write-Host "Fetching drift event history..."
$eventsResp = Invoke-RestMethod -Uri "$BaseUrl/ai-systems/$SysId/drift-events" -Method Get -Headers $Headers

if ($eventsResp.items.Count -gt 0) {
    $eventsResp.items | Format-Table -Property id, drift_type, new_risk_level, detected_at
} else {
    Write-Host "No drift events found (Risk level hasn't changed)." -ForegroundColor DarkGray
}

Write-Host "Test sequence complete! Check $WebhookUrl to verify payload and signature." -ForegroundColor Cyan