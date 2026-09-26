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
Write-Host "Content root : $ContentRoot"
Write-Host "Armor source : $ArmorSourceRoot"

if (-not (Test-Path -LiteralPath $ArmorSourceRoot -PathType Container)) {
    throw "Armor source directory does not exist. Run Python/CFGGenerators/Armor/generate_armor_upgrades.py first: $ArmorSourceRoot"
}

$requiredFiles = @(
    "GameData\UpgradePrototypes\UpgradePrototypes_patch_BPRUE_Armor.cfg",
    "GameData\ItemPrototypes\ArmorPrototypes\ArmorPrototypes_patch_BPRUE_Armor.cfg",
    "GameData\EffectPrototypes\EffectPrototypes_patch_BPRUE_Armor.cfg",
    "GameData\NPCPrototypes\NPCPrototypes_patch_BPRUE_Armor.cfg",
    "DLCGameData\Deluxe\ItemPrototypes\ItemPrototypes_patch_BPRUE_Armor.cfg",
    "DLCGameData\PreOrder\ItemPrototypes\ItemPrototypes_patch_BPRUE_Armor.cfg",
    "DLCGameData\Ultimate\ItemPrototypes\ItemPrototypes_patch_BPRUE_Armor.cfg"
)
foreach ($relative in $requiredFiles) {
    $required = Join-Path $ArmorSourceRoot $relative
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Required Armor file is missing: $required. Run Python/CFGGenerators/Armor/generate_armor_upgrades.py first."
    }
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
        RelativePath = "GameLite/" + (To-PakPath -Path $relative)
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

# UnrealPak chooses the deepest common mount point. Validate entries relative
# to the mount point reported by UnrealPak rather than assuming GameLite.
$mountLine = $listOutput | Where-Object { $_ -like '*with mount point "*' } | Select-Object -First 1
if (-not $mountLine) {
    throw "Could not determine PAK mount point from UnrealPak -List output."
}
$mountMatch = [regex]::Match($mountLine, 'with mount point "([^"]+)"')
if (-not $mountMatch.Success) {
    throw "Could not parse PAK mount point from UnrealPak -List output: $mountLine"
}
$listedMount = (To-PakPath -Path $mountMatch.Groups[1].Value).TrimEnd('/')
$contentPrefix = (To-PakPath -Path $ContentMountRoot).TrimEnd('/')
if (-not $listedMount.StartsWith($contentPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Unexpected PAK mount point: $listedMount"
}
$mountRelative = $listedMount.Substring($contentPrefix.Length).Trim('/')

$expectedRelativePaths = foreach ($entry in $packageEntries) {
    $relativePath = (To-PakPath -Path $entry.RelativePath).TrimStart('/')
    if ($mountRelative -and $relativePath.StartsWith("$mountRelative/", [System.StringComparison]::OrdinalIgnoreCase)) {
        $relativePath.Substring($mountRelative.Length + 1)
    } else {
        $relativePath
    }
}

$missingPaths = @($expectedRelativePaths | Where-Object {
    $expected = $_
    -not ($listOutput | Where-Object { $_.Replace("\\", "/") -like "*$expected*" })
})
if ($missingPaths.Count -gt 0) {
    Write-Host "UnrealPak -List output:"
    $listOutput | ForEach-Object { Write-Host "  $_" }
    Write-Host "Missing PAK-relative entries:"
    $missingPaths | ForEach-Object { Write-Host "  $_" }
    throw "Generated Armor PAK is missing $($missingPaths.Count) expected file(s)."
}

foreach ($relative in $requiredFiles) {
    $needle = "GameLite/" + (To-PakPath -Path $relative)
    if (-not ($packageEntries.RelativePath -contains $needle)) {
        throw "Required Armor entry was not included in the package: $needle"
    }
}

$pakInfo = Get-Item -LiteralPath $PakPath
Write-Host "SUCCESS"
Write-Host "PAK          : $($pakInfo.FullName)"
Write-Host "Size         : $([math]::Round($pakInfo.Length / 1KB, 2)) KiB"
Write-Host "Packed files : $($sourceFiles.Count)"
Write-Host "Mount root   : $ContentMountRoot"

if (-not $KeepStaging) { Remove-Item -LiteralPath $StagingRoot -Recurse -Force }
else { Write-Host "Staging kept : $StagingRoot" }
