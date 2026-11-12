<#
.SYNOPSIS
  Installs the Prompt Counter skill for Cursor, Claude Code, Codex and any agent
  that reads ~/.agents/skills.

.EXAMPLE
  irm https://raw.githubusercontent.com/johnban-coder/prompt-counter/main/install.ps1 | iex

.EXAMPLE
  .\install.ps1 -Targets cursor,claude          # only some tools
  .\install.ps1 -Project C:\code\my-app         # also install inside a repo (.cursor/.claude/.agents/.github)
#>
[CmdletBinding()]
param(
    [string[]]$Targets = @("cursor", "claude", "codex", "agents"),
    [string]$Project,
    [string]$Ref = "main"
)

$ErrorActionPreference = "Stop"
$Repo = "johnban-coder/prompt-counter"
$SkillName = "prompt-count"

function Get-SourceDir {
    if ($PSScriptRoot -and (Test-Path (Join-Path $PSScriptRoot "SKILL.md"))) {
        return $PSScriptRoot
    }
    $tmp = Join-Path ([IO.Path]::GetTempPath()) ("prompt-counter-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $tmp | Out-Null
    $zip = Join-Path $tmp "src.zip"
    Write-Host "Downloading $Repo@$Ref ..."
    Invoke-WebRequest -Uri "https://github.com/$Repo/archive/refs/heads/$Ref.zip" -OutFile $zip
    Expand-Archive -Path $zip -DestinationPath $tmp
    return (Get-ChildItem -Directory $tmp | Where-Object { Test-Path (Join-Path $_.FullName "SKILL.md") } | Select-Object -First 1).FullName
}

function Install-Skill([string]$Source, [string]$Dest) {
    New-Item -ItemType Directory -Force -Path $Dest | Out-Null
    Copy-Item (Join-Path $Source "SKILL.md") $Dest -Force
    Copy-Item (Join-Path $Source "scripts") $Dest -Recurse -Force
    Copy-Item (Join-Path $Source "LICENSE") $Dest -Force -ErrorAction SilentlyContinue
    Write-Host "  installed -> $Dest"
}

$home_ = [Environment]::GetFolderPath("UserProfile")
$map = @{
    cursor = Join-Path $home_ ".cursor\skills\$SkillName"
    claude = Join-Path $home_ ".claude\skills\$SkillName"
    codex  = Join-Path $home_ ".codex\skills\$SkillName"
    agents = Join-Path $home_ ".agents\skills\$SkillName"
}

$src = Get-SourceDir
# Accept both -Targets cursor,claude and -Targets "cursor,claude" (e.g. via powershell -File).
$Targets = @($Targets | ForEach-Object { $_ -split "[,\s]+" } | Where-Object { $_ })
Write-Host "Prompt Counter — installing skill '$SkillName'"
foreach ($t in $Targets) {
    if (-not $map.ContainsKey($t)) { Write-Warning "unknown target '$t' (cursor, claude, codex, agents)"; continue }
    Install-Skill $src $map[$t]
}

if ($Project) {
    foreach ($rel in @(".cursor\skills", ".claude\skills", ".agents\skills", ".github\skills")) {
        Install-Skill $src (Join-Path (Join-Path $Project $rel) $SkillName)
    }
}

try { $py = (python --version) 2>&1 } catch { $py = $null }
if (-not $py) { Write-Warning "Python 3.10+ not found on PATH — the skill needs it to run." }

Write-Host ""
Write-Host "Done. Open a chat and type:  /prompt-count"
Write-Host "Later:  /prompt-count help   or   /prompt-count update"
