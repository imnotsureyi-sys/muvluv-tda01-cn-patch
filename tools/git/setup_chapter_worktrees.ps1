param(
    [string]$BaseDir = "C:\Users\Administrator\Documents\MuvLuvSeries-worktrees",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$repoRoot = git rev-parse --show-toplevel
Set-Location $repoRoot

$chapters = @(
    @{ Name = "tda00"; Branch = "chapter/tda00" },
    @{ Name = "tda01"; Branch = "chapter/tda01" },
    @{ Name = "tda02"; Branch = "chapter/tda02" },
    @{ Name = "tda03"; Branch = "chapter/tda03" }
)

Write-Host "Repository: $repoRoot"
Write-Host "Worktree base: $BaseDir"
Write-Host ""

foreach ($chapter in $chapters) {
    $path = Join-Path $BaseDir $chapter.Name
    $branch = $chapter.Branch
    $branchExists = $null

    try {
        $branchExists = git rev-parse --verify $branch 2>$null
    } catch {
        $branchExists = $null
    }

    if (-not $branchExists) {
        Write-Host "Skip $($chapter.Name): branch $branch does not exist locally."
        continue
    }

    if (Test-Path -LiteralPath $path) {
        Write-Host "Exists: $path"
        continue
    }

    $cmd = "git worktree add `"$path`" $branch"
    if ($DryRun) {
        Write-Host "[dry-run] $cmd"
    } else {
        New-Item -ItemType Directory -Force -Path $BaseDir | Out-Null
        git worktree add $path $branch
    }
}

Write-Host ""
git worktree list
