param(
    [string]$UnrealPakPath,
    [string]$OutputDirectory,
    [switch]$KeepStaging
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ScriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$ContentRoot = (Resolve-Path (Join-Path $ScriptDirectory "..\..")).Path
$EditionsSourceRoot = Join-Path $ContentRoot "Editions\GameLite"
$StagingRoot = Join-Path $ScriptDirectory "staging"
$PakListPath = Join-Path $StagingRoot "paklist.txt"

if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $ScriptDirectory "output"
}

$PakName = "BPRUpgradesExpanded_Editions.pak"
$PakPath = Join-Path $OutputDirectory $PakName
$ContentMountRoot = "../../../Stalker2/Content"
$EditionPacks = @("Deluxe", "PreOrder", "Ultimate")

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
    if ($command) {
        return $command.Source
    }

    throw "Could not find UnrealPak.exe. Pass it explicitly with -UnrealPakPath '...\UnrealPak.exe'."
}

function To-PakPath {
    param([string]$Path)
    return $Path.Replace("\", "/")
}

Write-Host "=== BPRUpgradesExpanded Editions PAK Build ==="
Write-Host "Content root : $ContentRoot"
Write-Host "Edition source: $EditionsSourceRoot"

if (-not (Test-Path -LiteralPath $EditionsSourceRoot -PathType Container)) {
    throw "Editions source directory does not exist: $EditionsSourceRoot"
}

$sourceFiles = @()
foreach ($pack in $EditionPacks) {
    $packRoot = Join-Path $EditionsSourceRoot "DLCGameData\$pack"
    if (-not (Test-Path -LiteralPath $packRoot -PathType Container)) {
        throw "Expected Edition pack directory does not exist: $packRoot"
    }
    $packFiles = @(Get-ChildItem -LiteralPath $packRoot -File -Recurse |
        Where-Object { $_.Name -ne ".gitkeep" } |
        Sort-Object FullName)
    if ($packFiles.Count -eq 0) {
        throw "Edition pack '$pack' contains no generated source files. Run Python/generate_all_cfg.py first."
    }
    $sourceFiles += $packFiles
}

$npcPatch = Join-Path $EditionsSourceRoot "GameData\NPCPrototypes\NPCPrototypes_patch_BPRUE_Editions.cfg"
if (-not (Test-Path -LiteralPath $npcPatch -PathType Leaf)) {
    throw "Edition technician patch is missing: $npcPatch. Run Python/generate_all_cfg.py first."
}
$sourceFiles += Get-Item -LiteralPath $npcPatch

if ($sourceFiles.Count -eq 0) {
    throw "Editions package contains no source files."
}

$UnrealPak = Find-UnrealPak -ExplicitPath $UnrealPakPath
Write-Host "UnrealPak    : $UnrealPak"
Write-Host "Files        : $($sourceFiles.Count)"

if (Test-Path -LiteralPath $StagingRoot) {
    Remove-Item -LiteralPath $StagingRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $StagingRoot -Force | Out-Null
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null

$packageEntries = foreach ($file in $sourceFiles) {
    $relativePath = $file.FullName.Substring($EditionsSourceRoot.Length).TrimStart('\', '/')
    $relativePath = To-PakPath -Path $relativePath

    [PSCustomObject]@{
        File = $file
        RelativePath = "GameLite/$relativePath"
    }
}

$pakEntries = foreach ($entry in $packageEntries) {
    $stagedPath = Join-Path $StagingRoot $entry.RelativePath
    $stagedDirectory = Split-Path -Parent $stagedPath
    if ($stagedDirectory) {
        New-Item -ItemType Directory -Path $stagedDirectory -Force | Out-Null
    }
    Copy-Item -LiteralPath $entry.File.FullName -Destination $stagedPath -Force

    $source = To-PakPath -Path $stagedPath
    $destination = "$ContentMountRoot/$($entry.RelativePath)"
    '"{0}" "{1}"' -f $source, $destination
}

$pakEntries | Set-Content -LiteralPath $PakListPath -Encoding UTF8

if (Test-Path -LiteralPath $PakPath) {
    Remove-Item -LiteralPath $PakPath -Force
}

Write-Host ""
Write-Host "Creating $PakName ..."
& $UnrealPak $PakPath "-Create=$PakListPath"
if ($LASTEXITCODE -ne 0) {
    throw "UnrealPak failed while creating the PAK (exit code $LASTEXITCODE)."
}
if (-not (Test-Path -LiteralPath $PakPath -PathType Leaf)) {
    throw "UnrealPak returned successfully but the expected PAK was not created: $PakPath"
}

Write-Host ""
Write-Host "Validating PAK contents ..."
$listOutput = @(& $UnrealPak $PakPath -List 2>&1 | ForEach-Object { $_.ToString() })
if ($LASTEXITCODE -ne 0) {
    $listOutput | ForEach-Object { Write-Host $_ }
    throw "UnrealPak failed while listing the generated PAK (exit code $LASTEXITCODE)."
}

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
    -not ($listOutput | Where-Object {
        $line = $_.Replace("\", "/")
        $line -like "*$expected*"
    })
})

if ($missingPaths.Count -gt 0) {
    Write-Host "UnrealPak -List output:"
    $listOutput | ForEach-Object { Write-Host "  $_" }
    Write-Host "Missing PAK-relative entries:"
    $missingPaths | ForEach-Object { Write-Host "  $_" }
    throw "Generated PAK is missing $($missingPaths.Count) expected file(s)."
}

$npcNeedle = "GameLite/GameData/NPCPrototypes/NPCPrototypes_patch_BPRUE_Editions.cfg"
if (-not ($packageEntries.RelativePath -contains $npcNeedle)) {
    throw "Edition technician patch was not included in the package."
}

foreach ($pack in $EditionPacks) {
    $needle = "DLCGameData/$pack/"
    if (-not ($packageEntries.RelativePath | Where-Object { $_ -like "*$needle*" })) {
        throw "No packaged files found for required Edition pack '$pack'."
    }
}

$pakInfo = Get-Item -LiteralPath $PakPath
Write-Host ""
Write-Host "SUCCESS"
Write-Host "PAK          : $($pakInfo.FullName)"
Write-Host "Size         : $([math]::Round($pakInfo.Length / 1KB, 2)) KiB"
Write-Host "Packed files : $($sourceFiles.Count)"
Write-Host "Packs        : $($EditionPacks -join ', ')"
Write-Host "Mount root   : $ContentMountRoot"

if (-not $KeepStaging) {
    Remove-Item -LiteralPath $StagingRoot -Recurse -Force
} else {
    Write-Host "Staging kept : $StagingRoot"
}
