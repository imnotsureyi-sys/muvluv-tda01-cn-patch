from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
VERSION = "beta0.1"
VERSION_LABEL = "Beta 0.1"
STAMP = "xmlsafe_20260617i"
FONT_SOURCE = Path.home() / "AppData/Local/ancr/tda01/data/root/assets/data/gui/font/SourceHanSansSC-Bold.otf"
FONT_FILES = (
    "Font.cfg",
    "Font_en.cfg",
    "Font_ja.cfg",
    "Font_jp.cfg",
    "Font_zh_hans.cfg",
    "Font_zh_hant.cfg",
)

TITLES = {
    "tda01": {
        "name": "TDA01 Episode 01",
        "app_id": "1407090",
        "source": ROOT / f"outputs/repack_tda01_{STAMP}",
        "package": f"MuvLuv_TDA01_CN_Patch_{VERSION}",
    },
    "tda02": {
        "name": "TDA02",
        "app_id": "1342410",
        "source": ROOT / f"outputs/repack_tda02_{STAMP}",
        "package": f"MuvLuv_TDA02_CN_Patch_{VERSION}",
    },
    "tda03": {
        "name": "TDA03 Episode 03",
        "app_id": "789830",
        "source": ROOT / f"outputs/repack_tda03_{STAMP}",
        "package": f"MuvLuv_TDA03_CN_Patch_{VERSION}",
    },
}


INSTALL_BAT = """@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
"""

UNINSTALL_BAT = """@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall.ps1"
"""


def install_ps1(key: str, name: str) -> str:
    return f"""param(
    [string]$CacheRootOverride = "",
    [string]$StateRootOverride = "",
    [switch]$NoPause
)

$ErrorActionPreference = "Stop"
$PatchKey = "{key}"
$PatchName = "{name}"

function Wait-Exit {{
    param([int]$Code = 0)
    if (-not $NoPause) {{
        Write-Host ""
        Read-Host "Press Enter to close"
    }}
    exit $Code
}}

function Copy-DirectoryContents {{
    param([string]$Source, [string]$Destination)
    if (-not (Test-Path -LiteralPath $Destination)) {{
        New-Item -ItemType Directory -Path $Destination | Out-Null
    }}
    Get-ChildItem -LiteralPath $Source -Force | Copy-Item -Destination $Destination -Recurse -Force
}}

function Get-CachePath {{
    param([string]$Key)
    if ($CacheRootOverride) {{
        return (Join-Path $CacheRootOverride "$Key\\data\\root\\assets\\data_spec\\adv\\game\\scr\\localized")
    }}
    return (Join-Path $env:LOCALAPPDATA "ancr\\$Key\\data\\root\\assets\\data_spec\\adv\\game\\scr\\localized")
}}

function Get-FontPath {{
    param([string]$Key)
    if ($CacheRootOverride) {{
        return (Join-Path $CacheRootOverride "$Key\\data\\root\\assets\\data\\gui\\font")
    }}
    return (Join-Path $env:LOCALAPPDATA "ancr\\$Key\\data\\root\\assets\\data\\gui\\font")
}}

$PatchRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ManifestPath = Join-Path $PatchRoot "manifest.json"
$Payload = Join-Path (Join-Path $PatchRoot "payload") $PatchKey
$FontPayload = Join-Path $PatchRoot "font_payload"
if ($StateRootOverride) {{
    $StateRoot = $StateRootOverride
}} else {{
    $StateRoot = Join-Path $env:LOCALAPPDATA ("MuvLuvTDAChinesePatch_" + $PatchKey)
}}
$StateFile = Join-Path $StateRoot "install-state.json"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$BackupRoot = Join-Path $StateRoot ("backup-" + $Stamp)
$Cache = Get-CachePath $PatchKey
$FontDir = Get-FontPath $PatchKey

Write-Host ("Muv-Luv Unlimited: THE DAY AFTER Chinese Patch {VERSION_LABEL} - " + $PatchName)
Write-Host "Please close the game before installing."
Write-Host ""

if (-not (Test-Path -LiteralPath $ManifestPath)) {{
    Write-Host "manifest.json was not found. The patch package is incomplete."
    Wait-Exit 1
}}
if (-not (Test-Path -LiteralPath $Payload)) {{
    Write-Host "Patch payload was not found. The patch package is incomplete."
    Wait-Exit 1
}}
if (-not (Test-Path -LiteralPath $FontPayload)) {{
    Write-Host "Font payload was not found. The patch package is incomplete."
    Wait-Exit 1
}}
$Manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
New-Item -ItemType Directory -Path $StateRoot -Force | Out-Null
New-Item -ItemType Directory -Path $BackupRoot -Force | Out-Null
$Backup = Join-Path $BackupRoot $PatchKey
$FontBackup = Join-Path $BackupRoot ($PatchKey + "_font")
New-Item -ItemType Directory -Path $Backup -Force | Out-Null
New-Item -ItemType Directory -Path $FontBackup -Force | Out-Null

$CacheWasMissing = -not (Test-Path -LiteralPath $Cache)
if ($CacheWasMissing) {{
    Write-Host "Localized cache folder was not found. Creating it now."
    Write-Host ("Target path: " + $Cache)
    New-Item -ItemType Directory -Path $Cache -Force | Out-Null
}}

Copy-DirectoryContents -Source $Cache -Destination $Backup
if (-not (Test-Path -LiteralPath $FontDir)) {{
    Write-Host "Font cache folder was not found. Creating it now."
    Write-Host ("Font path: " + $FontDir)
    New-Item -ItemType Directory -Path $FontDir -Force | Out-Null
}}
Copy-DirectoryContents -Source $FontDir -Destination $FontBackup
Copy-DirectoryContents -Source $Payload -Destination $Cache
Copy-DirectoryContents -Source $FontPayload -Destination $FontDir

$Files = $Manifest.titles.PSObject.Properties[$PatchKey].Value.scripts
foreach ($File in $Files) {{
    $Target = Join-Path $Cache ($File.path -replace '/', '\\')
    if (-not (Test-Path -LiteralPath $Target)) {{
        throw ("Missing file after install: " + $File.path)
    }}
    $Hash = (Get-FileHash -LiteralPath $Target -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($Hash -ne $File.sha256) {{
        throw ("Hash check failed: " + $File.path)
    }}
}}
$FontFiles = $Manifest.titles.PSObject.Properties[$PatchKey].Value.fonts
foreach ($File in $FontFiles) {{
    $Target = Join-Path $FontDir ($File.path -replace '/', '\\')
    if (-not (Test-Path -LiteralPath $Target)) {{
        throw ("Missing font file after install: " + $File.path)
    }}
    $Hash = (Get-FileHash -LiteralPath $Target -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($Hash -ne $File.sha256) {{
        throw ("Font hash check failed: " + $File.path)
    }}
}}

$State = [PSCustomObject]@{{
    version = $Manifest.version
    installedAt = (Get-Date).ToString("s")
    key = $PatchKey
    name = $PatchName
    cache = $Cache
    cacheWasMissing = $CacheWasMissing
    font = $FontDir
    backup = $Backup
    fontBackup = $FontBackup
    backupRoot = $BackupRoot
    files = @($Files | ForEach-Object {{ $_.path }})
    fontFiles = @($FontFiles | ForEach-Object {{ $_.path }})
}}
$State | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $StateFile -Encoding UTF8

Write-Host ""
Write-Host "Install complete."
Write-Host ("Original files were backed up to: " + $Backup)
Wait-Exit 0
"""


def uninstall_ps1(key: str, name: str) -> str:
    return f"""param(
    [string]$StateFileOverride = "",
    [switch]$NoPause
)

$ErrorActionPreference = "Stop"
$PatchKey = "{key}"
$PatchName = "{name}"

function Wait-Exit {{
    param([int]$Code = 0)
    if (-not $NoPause) {{
        Write-Host ""
        Read-Host "Press Enter to close"
    }}
    exit $Code
}}

function Copy-DirectoryContents {{
    param([string]$Source, [string]$Destination)
    if (-not (Test-Path -LiteralPath $Destination)) {{
        New-Item -ItemType Directory -Path $Destination | Out-Null
    }}
    Get-ChildItem -LiteralPath $Source -Force | Copy-Item -Destination $Destination -Recurse -Force
}}

function Clear-LocalizedDirectory {{
    param([string]$Path)
    $Normalized = ([System.IO.Path]::GetFullPath($Path)).TrimEnd('\\')
    $Suffix = "data\\root\\assets\\data_spec\\adv\\game\\scr\\localized"
    if (-not $Normalized.EndsWith($Suffix, [System.StringComparison]::OrdinalIgnoreCase)) {{
        throw ("Refusing to clear unexpected path: " + $Path)
    }}
    if (Test-Path -LiteralPath $Path) {{
        Get-ChildItem -LiteralPath $Path -Force | Remove-Item -Recurse -Force
    }}
}}

function Clear-FontPatchFiles {{
    param([string]$Path, [object[]]$Files)
    $Normalized = ([System.IO.Path]::GetFullPath($Path)).TrimEnd('\\')
    $Suffix = "data\\root\\assets\\data\\gui\\font"
    if (-not $Normalized.EndsWith($Suffix, [System.StringComparison]::OrdinalIgnoreCase)) {{
        throw ("Refusing to clear unexpected font path: " + $Path)
    }}
    if (Test-Path -LiteralPath $Path) {{
        foreach ($File in $Files) {{
            $Target = Join-Path $Path ($File -replace '/', '\\')
            if (Test-Path -LiteralPath $Target) {{
                Remove-Item -LiteralPath $Target -Force
            }}
        }}
    }}
}}

$StateRoot = Join-Path $env:LOCALAPPDATA ("MuvLuvTDAChinesePatch_" + $PatchKey)
$StateFile = Join-Path $StateRoot "install-state.json"
if ($StateFileOverride) {{
    $StateFile = $StateFileOverride
}}

Write-Host ("Muv-Luv Unlimited: THE DAY AFTER Chinese Patch Restore - " + $PatchName)
Write-Host "Please close the game before restoring."
Write-Host ""

if (-not (Test-Path -LiteralPath $StateFile)) {{
    Write-Host "Install state was not found. Automatic restore is not available."
    Write-Host ("State path: " + $StateFile)
    Wait-Exit 1
}}

$State = Get-Content -LiteralPath $StateFile -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not (Test-Path -LiteralPath $State.backup)) {{
    Write-Host ("Backup was not found: " + $State.backup)
    Wait-Exit 1
}}

Clear-LocalizedDirectory -Path $State.cache
Copy-DirectoryContents -Source $State.backup -Destination $State.cache
if ($State.font -and $State.fontBackup) {{
    Clear-FontPatchFiles -Path $State.font -Files @($State.fontFiles)
    Copy-DirectoryContents -Source $State.fontBackup -Destination $State.font
}}

Write-Host ""
Write-Host "Restore complete."
Write-Host ("Backup files remain at: " + $State.backup)
Wait-Exit 0
"""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def relative_posix(path: Path, base: Path) -> str:
    return path.relative_to(base).as_posix()


def write_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding=encoding, newline="\r\n")


def readme_text(name: str) -> str:
    return (
        f"Muv-Luv Unlimited: THE DAY AFTER Chinese Patch v{VERSION}\n"
        f"Target / 适用作品: {name}\n\n"
        "中文说明\n"
        "========\n\n"
        "这个补丁做了什么？\n"
        "- 将 TDA 本地缓存中的脚本替换为中文脚本；如果脚本缓存目录不存在，安装器会自动创建。\n"
        "- 自带思源黑体中文字体，并覆盖字体配置，避免简体字显示成方块。\n"
        "- 安装前会自动备份原文件，卸载时可以恢复。\n"
        "- 不修改 Steam 原始游戏文件，不修改 exe，不碰存档。\n\n"
        "怎么安装？\n"
        "1. 关闭游戏。\n"
        "2. 解压整个补丁文件夹。\n"
        "3. 双击运行 install.bat。\n"
        "4. 安装完成后，从 Steam 启动对应章节游玩。\n\n"
        "怎么卸载/恢复？\n"
        "- 双击运行 uninstall.bat，会恢复安装时备份的原文件。\n\n"
        "注意事项\n"
        "- 每个压缩包只对应一个章节：TDA01 / TDA02 / TDA03。\n"
        "- 不要只复制 payload 文件夹，直接运行 install.bat 即可。\n"
        "- 如果 Steam 验证游戏完整性或游戏更新后中文消失，重新运行 install.bat。\n"
        "- 存档通常在 Steam/userdata 等位置，本补丁不会操作存档。\n\n"
        "English Guide\n"
        "=============\n\n"
        "What does this patch do?\n"
        "- It replaces TDA's local script cache with Chinese script files. If the script cache folder does not exist, the installer creates it.\n"
        "- It includes a Simplified Chinese Source Han Sans font and font configs to prevent missing glyph boxes.\n"
        "- The installer backs up the original files before copying the patch, and the uninstaller can restore them.\n"
        "- It does not modify Steam's original game files, does not patch the exe, and does not touch save data.\n\n"
        "How to install\n"
        "1. Close the game.\n"
        "2. Extract the whole patch folder.\n"
        "3. Double-click install.bat.\n"
        "4. After installation finishes, launch the episode from Steam and play.\n\n"
        "How to uninstall / restore\n"
        "- Double-click uninstall.bat. It restores the files backed up during installation.\n\n"
        "Notes\n"
        "- Each archive is for one episode only: TDA01 / TDA02 / TDA03.\n"
        "- Do not copy only the payload folder. Run install.bat instead.\n"
        "- If Steam verifies the game files or the game updates and the Chinese text disappears, run install.bat again.\n"
        "- Save files are normally stored under Steam/userdata or similar locations. This patch does not modify save data.\n"
    )


def readme_text(name: str) -> str:
    return (
        f"Muv-Luv Unlimited: THE DAY AFTER Chinese Patch v{VERSION}\n"
        f"Target / 适用作品: {name}\n\n"
        "中文说明\n"
        "========\n\n"
        "这个补丁做了什么？\n"
        "- 将 TDA 本地缓存中的脚本替换为中文脚本；如果缓存目录不存在，安装器会自动创建。\n"
        "- 自带思源黑体中文字库和字体配置，避免简体字显示成方块。\n"
        "- 安装前会自动备份原文件，卸载时可以恢复。\n"
        "- 不修改 Steam 原始游戏文件，不修改 exe，不碰存档。\n\n"
        "怎么安装？\n"
        "1. 关闭游戏。\n"
        "2. 解压整个补丁文件夹。\n"
        "3. 双击运行 install.bat。\n"
        "4. 安装完成后，从 Steam 启动对应章节游玩。\n\n"
        "怎么卸载/恢复？\n"
        "- 双击运行 uninstall.bat，会恢复安装时备份的原文件。\n\n"
        "注意事项\n"
        "- 每个压缩包只对应一个章节：TDA01 / TDA02 / TDA03。\n"
        "- 不要只复制 payload 文件夹，直接运行 install.bat 即可。\n"
        "- 如果 Steam 验证游戏完整性或游戏更新后中文消失，重新运行 install.bat。\n"
        "- 存档通常在 Steam/userdata 等位置，本补丁不会操作存档。\n\n"
        "English Guide\n"
        "=============\n\n"
        "What does this patch do?\n"
        "- It replaces TDA's local script cache with Chinese script files. If the cache folder does not exist, the installer creates it.\n"
        "- It includes a Simplified Chinese Source Han Sans font and font configs to prevent missing glyph boxes.\n"
        "- The installer backs up the original files before copying the patch, and the uninstaller can restore them.\n"
        "- It does not modify Steam's original game files, does not patch the exe, and does not touch save data.\n\n"
        "How to install\n"
        "1. Close the game.\n"
        "2. Extract the whole patch folder.\n"
        "3. Double-click install.bat.\n"
        "4. After installation finishes, launch the episode from Steam and play.\n\n"
        "How to uninstall / restore\n"
        "- Double-click uninstall.bat. It restores the files backed up during installation.\n\n"
        "Notes\n"
        "- Each archive is for one episode only: TDA01 / TDA02 / TDA03.\n"
        "- Do not copy only the payload folder. Run install.bat instead.\n"
        "- If Steam verifies the game files or the game updates and the Chinese text disappears, run install.bat again.\n"
        "- Save files are normally stored under Steam/userdata or similar locations. This patch does not modify save data.\n"
    )


def readme_text(name: str) -> str:
    return (
        f"Muv-Luv Unlimited: THE DAY AFTER 简体中文补丁 {VERSION_LABEL}\n"
        f"Target / 适用作品: {name}\n\n"
        "中文说明\n"
        "========\n\n"
        "版本定位\n"
        "- 这是非官方、非商业的同人简体中文测试补丁，仅供正版 Steam 玩家交流使用。\n"
        "- 本版本命名为 Beta 0.1，仍在测试中，欢迎玩家带截图、章节、台词上下文反馈问题。\n"
        "- 本补丁不包含游戏本体，不提供破解，不修改 exe，不修改 Steam 原始游戏文件，不碰存档。\n\n"
        "翻译和校对说明\n"
        f"- 当前压缩包只包含 {name}，请不要和其他章节混用。\n"
        "- 当前重建原则是以游戏日文字幕槽为准写入中文，不以英文文本为翻译依据。\n"
        "- 制作者本人不懂日语，本版本没有经过完整的日中人工校对。\n"
        "- 这是测试版，仍需要玩家反馈截图、章节、台词上下文来继续修正。\n\n"
        "特别致谢\n"
        "- 特别感谢“主任保护协会”提供了 AGES 引擎的汉化思路，并允许在发布时注明感谢。\n"
        "- 感谢“主任保护协会”此前公开的 Steam 版 Muv-Luv ATE 汉化补丁，为本补丁的本地脚本缓存处理方式提供了重要参考。\n"
        "- 感谢所有提供截图、术语建议、错字反馈和实机测试的玩家。\n\n"
        "这个补丁做了什么？\n"
        "- 将 TDA 本地缓存中的脚本替换为中文脚本；如果缓存目录不存在，安装器会自动创建。\n"
        "- 自带思源黑体中文字库和字体配置，避免简体字显示成方块。\n"
        "- 安装前会自动备份原文件，卸载时可以恢复。\n\n"
        "怎么安装？\n"
        "1. 关闭游戏。\n"
        "2. 解压整个补丁文件夹。\n"
        "3. 双击运行 install.bat。\n"
        "4. 安装完成后，从 Steam 启动对应章节游玩。\n\n"
        "怎么卸载/恢复？\n"
        "- 双击运行 uninstall.bat，会恢复安装时备份的原文件。\n\n"
        "已知风险\n"
        "- 可能仍有错译、语病、术语不统一、繁体字/日文汉字残留。\n"
        "- 可能仍有文本和语音、说话人名称、上下文顺序不匹配的问题。\n"
        "- 极少数位置可能出现空字幕、乱码、缺字，或类似 Text ID Not Found 的缺失文本提示。\n"
        "- 如果安装后仍看到旧文本，通常是旧缓存没有被当前补丁覆盖，建议关闭游戏后重新运行 install.bat。\n"
        "- 每个压缩包只对应一个章节：TDA01 / TDA02 / TDA03，请不要混用。\n\n"
        "English Summary\n"
        "===============\n\n"
        f"This is an unofficial, non-commercial Simplified Chinese fan patch for {name}, released as {VERSION_LABEL} for testing and feedback.\n\n"
        "- It replaces TDA's local script cache with Chinese script files and includes a Simplified Chinese font/config payload.\n"
        "- It does not include the game, does not provide a crack, does not patch the exe, and does not modify save data.\n"
        "- The Chinese text is aligned to the Japanese subtitle slots, not translated from the English script.\n"
        "- The maintainer does not know Japanese, and this version has not received full Japanese-to-Chinese human proofreading.\n"
        f"- This archive contains only {name}; do not mix it with other episodes.\n"
        "- Known risks include mistranslations, wording issues, remaining traditional/Japanese kanji, speaker/text/voice mismatches, blank text, missing glyphs, or Text ID Not Found-like messages.\n\n"
        "Credits\n"
        "- Special thanks to 主任保护协会 for sharing the AGES engine localization approach and allowing this acknowledgement.\n"
        "- Thanks to the public Steam Muv-Luv ATE Chinese patch by 主任保护协会, which provided important reference for the local script-cache workflow.\n"
    )


def font_config_text() -> str:
    return """<?xml version="1.0" encoding="utf-8"?>
<FontConfigDocument xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <FontParamList>
    <FontParam>
      <Label>Common</Label>
      <FamilyName>beatfont1</FamilyName>
      <Bold>true</Bold>
      <File>SourceHanSansSC-Bold.otf</File>
    </FontParam>
    <FontParam>
      <Label>Message</Label>
      <FamilyName>message</FamilyName>
      <Bold>true</Bold>
      <File>SourceHanSansSC-Bold.otf</File>
      <LineBreak>1.05</LineBreak>
    </FontParam>
    <FontParam>
      <Label>Speaker</Label>
      <FamilyName>speaker</FamilyName>
      <Bold>true</Bold>
      <File>SourceHanSansSC-Bold.otf</File>
    </FontParam>
    <FontParam>
      <Label>Hud</Label>
      <FamilyName>hud</FamilyName>
      <Bold>true</Bold>
      <File>SourceHanSansSC-Bold.otf</File>
    </FontParam>
  </FontParamList>
</FontConfigDocument>
"""


def build_package(key: str, meta: dict[str, object]) -> Path:
    package_dir = DIST / str(meta["package"])
    source = Path(meta["source"])
    if not source.exists():
        raise FileNotFoundError(source)
    if package_dir.exists():
        shutil.rmtree(package_dir)

    payload_dir = package_dir / "payload" / key
    shutil.copytree(source, payload_dir)

    font_payload_dir = package_dir / "font_payload"
    font_payload_dir.mkdir(parents=True, exist_ok=True)
    if not FONT_SOURCE.exists():
        raise FileNotFoundError(FONT_SOURCE)
    shutil.copy2(FONT_SOURCE, font_payload_dir / FONT_SOURCE.name)
    for font_file in FONT_FILES:
        write_text(font_payload_dir / font_file, font_config_text(), encoding="utf-8")

    script_files = []
    for item in sorted(payload_dir.rglob("*")):
        if item.is_file():
            script_files.append(
                {
                    "path": relative_posix(item, payload_dir),
                    "sha256": sha256(item),
                    "bytes": item.stat().st_size,
                }
            )

    font_files = []
    for item in sorted(font_payload_dir.rglob("*")):
        if item.is_file():
            font_files.append(
                {
                    "path": relative_posix(item, font_payload_dir),
                    "sha256": sha256(item),
                    "bytes": item.stat().st_size,
                }
            )

    manifest = {
        "version": VERSION,
        "createdBy": "Codex",
        "description": "Muv-Luv Unlimited: THE DAY AFTER Chinese localization patch",
        "titles": {key: {"scripts": script_files, "fonts": font_files}},
    }
    write_text(package_dir / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    write_text(package_dir / "install.ps1", install_ps1(key, str(meta["name"])), encoding="utf-8")
    write_text(package_dir / "uninstall.ps1", uninstall_ps1(key, str(meta["name"])), encoding="utf-8")
    write_text(package_dir / "install.bat", INSTALL_BAT, encoding="ascii")
    write_text(package_dir / "uninstall.bat", UNINSTALL_BAT, encoding="ascii")
    write_text(
        package_dir / "README.txt",
        (
            f"Muv-Luv Unlimited: THE DAY AFTER Chinese Patch v{VERSION}\n"
            f"Target / 适用作品: {meta['name']}\n\n"
            "中文说明\n"
            "========\n\n"
            "这个补丁做了什么？\n"
            "- 将游戏已经解包到本机缓存里的日文本地化脚本替换为中文脚本。\n"
            "- 安装前会自动备份原文件，卸载时可以恢复。\n"
            "- 不修改 Steam 原始游戏文件，不修改 exe，不碰存档。\n\n"
            "怎么安装？\n"
            "1. 先从 Steam 启动一次对应章节，开始游戏并看到第一句台词后退出游戏。\n"
            "2. 解压整个补丁文件夹，双击运行 install.bat。\n"
            "3. 安装完成后，再从 Steam 启动游戏游玩。\n\n"
            "怎么卸载/恢复？\n"
            "- 双击运行 uninstall.bat，会恢复安装时备份的原文件。\n\n"
            "注意事项\n"
            "- 必须先启动一次游戏并进入正文看到台词，再运行 install.bat。\n"
            "- 每个压缩包只对应一个章节：TDA01 / TDA02 / TDA03。\n"
            "- 请不要只复制 payload 文件夹，直接运行 install.bat 即可。\n"
            "- 如果 Steam 验证游戏完整性或游戏更新后中文消失，重新运行 install.bat。\n"
            "- 存档通常在 Steam/userdata 等位置，本补丁不会操作存档。\n\n"
            "English Guide\n"
            "=============\n\n"
            "What does this patch do?\n"
            "- It replaces the localized Japanese script files already unpacked into the local game cache with Chinese script files.\n"
            "- The installer backs up the original files before copying the patch, and the uninstaller can restore them.\n"
            "- It does not modify Steam's original game files, does not patch the exe, and does not touch save data.\n\n"
            "How to install\n"
            "1. Launch this episode once from Steam, start the story until the first dialogue line appears, then quit the game.\n"
            "2. Extract the whole patch folder, then double-click install.bat.\n"
            "3. After installation finishes, launch the game from Steam and play.\n\n"
            "How to uninstall / restore\n"
            "- Double-click uninstall.bat. It restores the files backed up during installation.\n\n"
            "Notes\n"
            "- You must start the story and reach the first dialogue line once before running install.bat.\n"
            "- Each archive is for one episode only: TDA01 / TDA02 / TDA03.\n"
            "- Do not copy only the payload folder. Run install.bat instead.\n"
            "- If Steam verifies the game files or the game updates and the Chinese text disappears, run install.bat again.\n"
            "- Save files are normally stored under Steam/userdata or similar locations. This patch does not modify save data.\n"
        ),
        encoding="utf-8",
    )
    write_text(package_dir / "README.txt", readme_text(str(meta["name"])), encoding="utf-8")

    zip_path = Path(str(package_dir) + ".zip")
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for item in sorted(package_dir.rglob("*")):
            if item.is_file():
                zf.write(item, item.relative_to(package_dir.parent).as_posix())
    return zip_path


def main() -> int:
    DIST.mkdir(parents=True, exist_ok=True)
    for key, meta in TITLES.items():
        zip_path = build_package(key, meta)
        with zipfile.ZipFile(zip_path) as zf:
            bad = zf.testzip()
        print(f"{key}: {zip_path} testzip={bad}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
