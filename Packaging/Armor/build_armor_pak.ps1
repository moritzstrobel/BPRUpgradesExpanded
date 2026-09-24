param(
    [string]$UnrealPakPath,
    [string]$OutputDirectory,
    [switch]$KeepStaging
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ScriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$ContentRoot = (Resolve-Path (Join-Path $ScriptDirectory "..\..")).Path
$ArmorSourceRoot = Join-Path $ContentRoot "Armor\GameLite"
$StagingRoot = Join-Path $ScriptDirectory "staging"
$PakListPath = Join-Path $StagingRoot "paklist.txt"

if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $ScriptDirectory "output"
}

$PakName = "BPRUpgradesExpanded_Armor.pak"
$PakPath = Join-Path $OutputDirectory $PakName
$ContentMountRoot = "../../../Stalker2/Content"

function Find-UnrealPak {
    param([string]$ExplicitPath)
    if ($ExplicitPath) {
        if (-not (Test-Path -LiteralPath $ExplicitPath -PathType Leaf)) {
            throw "UnrealPak.exe was not found at the supplied path: $ExplicitPath"
        }
        return (Resolve-Path -LiteralPath $ExplicitPath).Path
    }
    $candidates = @(
        "G:\Epic Games\STALKER2ZoneKit\Engine\Binaries\Win64\UnrealPak.exe",
        "C:\Program Files\Epic Games\STALKER2ZoneKit\Engine\Binaries\Win64\UnrealPak.exe",
        "C:\Program Files\Epic Games\Stalker2ZoneKit\Engine\Binaries\Win64\UnrealPak.exe"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    $command = Get-Command "UnrealPak.exe" -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    throw "Could not find UnrealPak.exe. Pass it explicitly with -UnrealPakPath '...\UnrealPak.exe'."
}

function To-PakPath {
    param([string]$Path)
    return $Path.Replace("\", "/")
}

Write-Host "=== BPRUpgradesExpanded Armor PAK Build ==="
Write-Host "Armor source : $ArmorSourceRoot"

if (-not (Test-Path -LiteralPath $ArmorSourceRoot -PathType Container)) {
    throw "Armor source directory does not exist. Run Python/CFGGenerators/Armor/generate_armor_upgrades.py first: $ArmorSourceRoot"
}

$sourceFiles = @(Get-ChildItem -LiteralPath $ArmorSourceRoot -File -Recurse | Sort-Object FullName)
if ($sourceFiles.Count -eq 0) { throw "Armor package contains no source files." }

$UnrealPak = Find-UnrealPak -ExplicitPath $UnrealPakPath
if (Test-Path -LiteralPath $StagingRoot) { Remove-Item -LiteralPath $StagingRoot -Recurse -Force }
New-Item -ItemType Directory -Path $StagingRoot -Force | Out-Null
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null

$packageEntries = foreach ($file in $sourceFiles) {
    $relative = $file.FullName.Substring($ArmorSourceRoot.Length).TrimStart('\', '/')
    [PSCustomObject]@{
        File = $file
        RelativePath = "GameLite/$(To-PakPath -Path $relative)"
    }
}

$pakEntries = foreach ($entry in $packageEntries) {
    $stagedPath = Join-Path $StagingRoot $entry.RelativePath
    $dir = Split-Path -Parent $stagedPath
    if ($dir) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    Copy-Item -LiteralPath $entry.File.FullName -Destination $stagedPath -Force
    $source = To-PakPath -Path $stagedPath
    $destination = "$ContentMountRoot/$($entry.RelativePath)"
    '"{0}" "{1}"' -f $source, $destination
}

$pakEntries | Set-Content -LiteralPath $PakListPath -Encoding UTF8
if (Test-Path -LiteralPath $PakPath) { Remove-Item -LiteralPath $PakPath -Force }

Write-Host "Creating $PakName from $($sourceFiles.Count) file(s) ..."
& $UnrealPak $PakPath "-Create=$PakListPath"
if ($LASTEXITCODE -ne 0) { throw "UnrealPak failed while creating the PAK (exit code $LASTEXITCODE)." }
if (-not (Test-Path -LiteralPath $PakPath -PathType Leaf)) { throw "Expected PAK was not created: $PakPath" }

$listOutput = @(& $UnrealPak $PakPath -List 2>&1 | ForEach-Object { $_.ToString() })
if ($LASTEXITCODE -ne 0) { throw "UnrealPak failed while validating the generated PAK." }

$missing = @($packageEntries | Where-Object {
    $expected = (To-PakPath -Path $_.RelativePath)
    -not ($listOutput | Where-Object { $_.Replace("\", "/") -like "*$expected*" })
})
if ($missing.Count -gt 0) {
    $missing | ForEach-Object { Write-Host "Missing: $($_.RelativePath)" }
    throw "Generated Armor PAK is missing $($missing.Count) expected file(s)."
}

$pakInfo = Get-Item -LiteralPath $PakPath
Write-Host "SUCCESS"
Write-Host "PAK          : $($pakInfo.FullName)"
Write-Host "Size         : $([math]::Round($pakInfo.Length / 1KB, 2)) KiB"
Write-Host "Packed files : $($sourceFiles.Count)"
Write-Host "Mount root   : $ContentMountRoot"

if (-not $KeepStaging) { Remove-Item -LiteralPath $StagingRoot -Recurse -Force }
else { Write-Host "Staging kept : $StagingRoot" }
