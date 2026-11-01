<#
.SYNOPSIS
    Automated check loop (pytest + CodeRabbit) and GitHub push utility.
.DESCRIPTION
    Runs tests, executes CodeRabbit review if installed (or checks config),
    creates an atomic git commit, and pushes to GitHub.
#>

param(
    [string]$CommitMessage = "",
    [string]$RemoteUrl = "",
    [string]$Branch = "master"
)

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "   CODE QUALITY CHECK & GITHUB PUSH LOOP " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# 1. Run Unit Tests
Write-Host "`n[1/4] Running test suite (pytest)..." -ForegroundColor Yellow
$testResult = .\venv\Scripts\pytest.exe
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Pytest suite failed! Aborting push to maintain code quality." -ForegroundColor Red
    exit 1
}
Write-Host "[+] All tests passed!" -ForegroundColor Green

# 2. Check CodeRabbit
Write-Host "`n[2/4] Checking CodeRabbit review..." -ForegroundColor Yellow
$crCmd = Get-Command "coderabbit" -ErrorAction SilentlyContinue
if (-not $crCmd) {
    $crCmd = Get-Command "cr" -ErrorAction SilentlyContinue
}

if ($crCmd) {
    Write-Host "[*] Running local CodeRabbit review..." -ForegroundColor Cyan
    & $crCmd.Source review --uncommitted
} else {
    Write-Host "[*] CodeRabbit CLI is not installed locally." -ForegroundColor Gray
    Write-Host "    (Repository contains .coderabbit.yaml which automatically reviews upon GitHub push/PR)." -ForegroundColor Gray
    Write-Host "    (To install CLI locally: irm https://cli.coderabbit.ai/install.ps1 | iex)" -ForegroundColor DarkGray
}

# 3. Git Staging & Commit
Write-Host "`n[3/4] Staging and committing changes..." -ForegroundColor Yellow
git add .
$status = git status --porcelain
if (-not $status) {
    Write-Host "[*] No new changes to commit." -ForegroundColor Cyan
} else {
    if (-not $CommitMessage) {
        $CommitMessage = Read-Host "Enter commit message (e.g., 'feat: complete Part 2 model training')"
    }
    if (-not $CommitMessage) {
        $CommitMessage = "chore: update project state and models"
    }
    git commit -m "$CommitMessage"
    Write-Host "[+] Committed: $CommitMessage" -ForegroundColor Green
}

# 4. GitHub Push
Write-Host "`n[4/4] Pushing to GitHub..." -ForegroundColor Yellow
$existingRemote = git remote get-url origin 2>$null

if (-not $existingRemote) {
    if (-not $RemoteUrl) {
        $RemoteUrl = Read-Host "No Git remote detected. Enter your GitHub repo URL (e.g. https://github.com/user/repo.git)"
    }
    if ($RemoteUrl) {
        git remote add origin $RemoteUrl
        Write-Host "[+] Added remote origin: $RemoteUrl" -ForegroundColor Green
    } else {
        Write-Host "[!] Skipping push: No remote URL provided." -ForegroundColor Yellow
        exit 0
    }
}

Write-Host "[*] Pushing to origin/$Branch..." -ForegroundColor Cyan
git push -u origin $Branch
if ($LASTEXITCODE -eq 0) {
    Write-Host "[+] Successfully pushed to GitHub!" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Git push failed. Verify your GitHub credentials and branch permissions." -ForegroundColor Yellow
}
