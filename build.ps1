# Kodex Build Script for AutoHotkey v2
# Compiles kodex.ahk to kodex.exe and prepares for GitHub release

param(
    [switch]$BuildOnly,
    [switch]$Release,
    [string]$Version = "2.0.0"
)

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "    Kodex Build & Release Script" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Find AutoHotkey v2 Compiler
Write-Host "Searching for AutoHotkey v2 Compiler..." -ForegroundColor Yellow

$AHK2EXE = $null
$Paths = @(
    "C:\Program Files\AutoHotkey\Compiler\Ahk2Exe.exe",
    "C:\Program Files (x86)\AutoHotkey\Compiler\Ahk2Exe.exe",
    "$env:USERPROFILE\AppData\Local\AutoHotkey\Compiler\Ahk2Exe.exe"
)

foreach ($Path in $Paths) {
    if (Test-Path $Path) {
        $AHK2EXE = $Path
        Write-Host "✓ Found: $Path" -ForegroundColor Green
        break
    }
}

if (!$AHK2EXE) {
    Write-Host "✗ AutoHotkey v2 Compiler not found!" -ForegroundColor Red
    Write-Host "  Install from: https://www.autohotkey.com/" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Create output directory
$DistDir = "dist"
if (!(Test-Path $DistDir)) {
    New-Item -ItemType Directory -Path $DistDir | Out-Null
    Write-Host "✓ Created dist directory" -ForegroundColor Green
}

# Check for icon file
$IconFile = "kodex.ico"
if (!(Test-Path $IconFile)) {
    Write-Host "⚠ Warning: kodex.ico not found. Building without icon." -ForegroundColor Yellow
    $IconParam = ""
} else {
    Write-Host "✓ Found icon: $IconFile" -ForegroundColor Green
    $IconParam = "/icon `"$IconFile`""
}

Write-Host ""
Write-Host "Building kodex.exe..." -ForegroundColor Cyan

# Compile
$OutputExe = "$DistDir\kodex.exe"
$Command = "`"$AHK2EXE`" /in kodex.ahk /out `"$OutputExe`" $IconParam"

Write-Host "Executing: $Command" -ForegroundColor Gray
Invoke-Expression $Command

if ($LASTEXITCODE -eq 0 -and (Test-Path $OutputExe)) {
    $Size = (Get-Item $OutputExe).Length / 1MB
    Write-Host ""
    Write-Host "✓ Build successful!" -ForegroundColor Green
    Write-Host "  Output: $OutputExe" -ForegroundColor Green
    Write-Host "  Size: $([Math]::Round($Size, 2)) MB" -ForegroundColor Green
    
    # Create installer package
    Write-Host ""
    Write-Host "Creating installer package..." -ForegroundColor Cyan
    
    $ZipPath = "$DistDir\kodex-v$Version.zip"
    $Files = @(
        "kodex.exe",
        "README.md",
        "MIGRATION_GUIDE.md",
        "TICKET_TRACKER_README.md",
        ".github/copilot-instructions.md"
    )
    
    # Create temp staging directory
    $StagingDir = "$DistDir\kodex-v$Version"
    if (Test-Path $StagingDir) {
        Remove-Item $StagingDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $StagingDir | Out-Null
    
    # Copy files
    Copy-Item "dist\kodex.exe" "$StagingDir\"
    Copy-Item "README.md" "$StagingDir\"
    Copy-Item "MIGRATION_GUIDE.md" "$StagingDir\"
    Copy-Item "TICKET_TRACKER_README.md" "$StagingDir\"
    Copy-Item "kodex.ini" "$StagingDir\" -ErrorAction SilentlyContinue
    
    # Create zip
    if (Get-Command Compress-Archive -ErrorAction SilentlyContinue) {
        Compress-Archive -Path $StagingDir -DestinationPath $ZipPath -Force
        Write-Host "✓ Package created: $ZipPath" -ForegroundColor Green
        Write-Host ""
        Write-Host "Release package ready!" -ForegroundColor Cyan
        Write-Host "  Upload $ZipPath to GitHub releases" -ForegroundColor Gray
    }
    
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Test: .\$OutputExe" -ForegroundColor Gray
    Write-Host "  2. Upload files to GitHub:" -ForegroundColor Gray
    Write-Host "     - dist/kodex.exe (standalone)" -ForegroundColor Gray
    Write-Host "     - dist/kodex-v$Version.zip (with docs)" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "✗ Build failed!" -ForegroundColor Red
    Write-Host "  Check AutoHotkey installation and try again." -ForegroundColor Yellow
    exit 1
}
