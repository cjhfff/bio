# Windows Task Scheduler Setup Script
# Set daily task to run at 8:30 AM

$TaskName = "BioPaperPushDaily"
$ScriptPath = "C:\Users\d\Desktop\worksapce\bio\run_daily.bat"
$WorkingDir = "C:\Users\d\Desktop\worksapce\bio"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setting Windows Scheduled Task" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if batch file exists
if (-not (Test-Path $ScriptPath)) {
    Write-Host "Error: Batch file not found: $ScriptPath" -ForegroundColor Red
    Write-Host "Please ensure run_daily.bat exists" -ForegroundColor Red
    exit 1
}

# Check if task already exists
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Existing task found, will delete and recreate..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Create task action
$action = New-ScheduledTaskAction -Execute $ScriptPath -WorkingDirectory $WorkingDir

# Create trigger (daily at 8:30 AM)
$trigger = New-ScheduledTaskTrigger -Daily -At "8:30AM"

# Create task settings
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

# Create task principal (run as current user)
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Highest

# Register task
try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal `
        -Description "Daily bio paper push task at 8:30 AM" `
        -Force
    
    Write-Host "Task created successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Task Details:" -ForegroundColor Cyan
    Write-Host "  Task Name: $TaskName" -ForegroundColor White
    Write-Host "  Schedule: Daily at 8:30 AM" -ForegroundColor White
    Write-Host "  Script: $ScriptPath" -ForegroundColor White
    Write-Host "  Working Dir: $WorkingDir" -ForegroundColor White
    Write-Host ""
    Write-Host "Manage Task:" -ForegroundColor Cyan
    Write-Host "  View: Get-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
    Write-Host "  Delete: Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false" -ForegroundColor Gray
    Write-Host "  Run Now: Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
    Write-Host "  History: Get-ScheduledTaskInfo -TaskName '$TaskName'" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Or use GUI:" -ForegroundColor Cyan
    Write-Host "  1. Open Task Scheduler (taskschd.msc)" -ForegroundColor White
    Write-Host "  2. Find task '$TaskName'" -ForegroundColor White
    Write-Host "  3. View, edit, run or delete task" -ForegroundColor White
    Write-Host ""
    
} catch {
    Write-Host "Task creation failed: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Possible reasons:" -ForegroundColor Yellow
    Write-Host "  1. Need admin rights (run PowerShell as Administrator)" -ForegroundColor White
    Write-Host "  2. Task Scheduler service not running" -ForegroundColor White
    Write-Host ""
    Write-Host "Manual setup:" -ForegroundColor Cyan
    Write-Host "  1. Open Task Scheduler (Win+R, type taskschd.msc)" -ForegroundColor White
    Write-Host "  2. Create Basic Task" -ForegroundColor White
    Write-Host "  3. Name: $TaskName" -ForegroundColor White
    Write-Host "  4. Trigger: Daily at 8:30" -ForegroundColor White
    Write-Host "  5. Action: Start program -> $ScriptPath" -ForegroundColor White
    Write-Host "  6. Start in: $WorkingDir" -ForegroundColor White
    exit 1
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan

