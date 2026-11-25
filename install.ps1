# Instalador Automático do Nacci.Edit (Windows PowerShell)
# Instala a skill simultaneamente no Antigravity e no Claude Code!

$ErrorActionPreference = "Stop"
$SourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$AgySkillDir = Join-Path $HOME ".gemini\config\skills\nacci-edit"
$ClaudeSkillDir = Join-Path $HOME ".claude\skills\nacci-edit"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  NACCI.EDIT - Instalador Oficial (Antigravity & Claude)  " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

foreach ($Target in @($AgySkillDir, $ClaudeSkillDir)) {
    if (-not (Test-Path $Target)) {
        New-Item -ItemType Directory -Force -Path $Target | Out-Null
    }
    Copy-Item -Path (Join-Path $SourceDir "SKILL.md") -Destination $Target -Force
    Copy-Item -Path (Join-Path $SourceDir "scripts") -Destination $Target -Recurse -Force
    Copy-Item -Path (Join-Path $SourceDir "clients") -Destination $Target -Recurse -Force
    Copy-Item -Path (Join-Path $SourceDir "references") -Destination $Target -Recurse -Force
    Copy-Item -Path (Join-Path $SourceDir ".env.example") -Destination $Target -Force
    Write-Host "[OK] Skill instalada em: $Target" -ForegroundColor Green
}

Write-Host ""
Write-Host "Verificando dependências locais (Python, FFmpeg, yt-dlp)..." -ForegroundColor Yellow
foreach ($cmd in @("python", "ffmpeg", "yt-dlp")) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) {
        Write-Host "  [OK] $cmd encontrado no sistema!" -ForegroundColor Green
    } else {
        Write-Host "  [OPCIONAL] $cmd não encontrado no PATH. Para instalar no Windows: winget install $cmd" -ForegroundColor DarkYellow
    }
}

Write-Host ""
Write-Host "[SUCESSO] Nacci.Edit está pronta para uso no Antigravity e no Claude Code!" -ForegroundColor Cyan
