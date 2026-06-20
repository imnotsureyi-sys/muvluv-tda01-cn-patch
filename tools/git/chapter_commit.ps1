param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("TDA00", "TDA01", "TDA02", "TDA03", "Glossary", "Docs", "Tools")]
    [string]$Scope,

    [Parameter(Mandatory=$true)]
    [string]$Summary,

    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$repoRoot = git rev-parse --show-toplevel
Set-Location $repoRoot

$branch = (git branch --show-current).Trim()

if ($Scope -like "TDA*") {
    $expected = "chapter/" + $Scope.ToLower()
    if ($branch -ne $expected) {
        Write-Error "Current branch is '$branch', but $Scope changes should be committed on '$expected'."
    }
}

$status = git status --short
if (-not $status) {
    Write-Host "No changes to commit."
    exit 0
}

$message = "$Scope`: $Summary"

Write-Host "Repository: $repoRoot"
Write-Host "Branch:     $branch"
Write-Host "Commit:     $message"
Write-Host ""
Write-Host "Pending changes:"
git status --short
Write-Host ""

if ($DryRun) {
    Write-Host "Dry run only. No files staged or committed."
    exit 0
}

git add .gitmessage.txt README.md CHANGELOG.md RELEASE_PROCESS.md docs glossary handoff chapters outputs/glossary outputs/tda_text work tools release-notes

$staged = git diff --cached --name-only
if (-not $staged) {
    Write-Host "Nothing staged after applying project path rules."
    exit 0
}

git commit -m $message
