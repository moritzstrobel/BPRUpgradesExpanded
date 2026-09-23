param(
    [string]$UnrealPakPath,
    [string]$OutputDirectory,
    [switch]$KeepStaging
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ScriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$ContentRoot = (Resolve-Path (Join-Path $ScriptDirectory "..\..")).Path
$DlcSourceRoot = Join-Path $ContentRoot "GameLite\DLCGameData\DLC1"
$GeneratedSourceRoot = Join-Path $ScriptDirectory "generated"
$StagingRoot = Join-Path $ScriptDirectory "staging"
$PakListPath = Join-Path $StagingRoot "paklist.txt"

if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $ScriptDirectory "output"
}

$PakName = "BPRUpgradesExpanded_DLC1.pak"
$PakPath = Join-Path $OutputDirectory $PakName
$ContentMountRoot = "../../../Stalker2/Content"
$MountRoot = "$ContentMountRoot/GameLite/DLCGameData/DLC1"

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

Write-Host "=== BPRUpgradesExpanded DLC1 PAK Build ==="
Write-Host "Content root : $ContentRoot"
Write-Host "DLC1 source  : $DlcSourceRoot"
Write-Host "Generated    : $GeneratedSourceRoot"

if (-not (Test-Path -LiteralPath $DlcSourceRoot -PathType Container)) {
    throw "DLC1 source directory does not exist: $DlcSourceRoot"
}

$dlcSourceFiles = @(Get-ChildItem -LiteralPath $DlcSourceRoot -File -Recurse | Sort-Object FullName)
$generatedSourceFiles = @()
if (Test-Path -LiteralPath $GeneratedSourceRoot -PathType Container) {
    $generatedSourceFiles = @(Get-ChildItem -LiteralPath $GeneratedSourceRoot -File -Recurse | Sort-Object FullName)
}
$sourceFiles = @($dlcSourceFiles) + @($generatedSourceFiles)
if ($sourceFiles.Count -eq 0) {
    throw "DLC1 package contains no source files."
}

$UnrealPak = Find-UnrealPak -ExplicitPath $UnrealPakPath
Write-Host "UnrealPak    : $UnrealPak"
Write-Host "Files        : $($sourceFiles.Count)"

if (Test-Path -LiteralPath $StagingRoot) {
    Remove-Item -LiteralPath $StagingRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $StagingRoot -Force | Out-Null
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null

$packageEntries = @()
foreach ($file in $dlcSourceFiles) {
    $relativePath = $file.FullName.Substring($DlcSourceRoot.Length).TrimStart('\', '/')
    $packageEntries += [PSCustomObject]@{
        File = $file
        RelativePath = "GameLite/DLCGameData/DLC1/$(To-PakPath -Path $relativePath)"
    }
}
foreach ($file in $generatedSourceFiles) {
    $relativePath = $file.FullName.Substring($GeneratedSourceRoot.Length).TrimStart('\', '/')
    $packageEntries += [PSCustomObject]@{
        File = $file
        RelativePath = To-PakPath -Path $relativePath
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

# UnrealPak -List reports paths relative to the common mount point it selected.
# Derive that mount point from the listing instead of assuming GameLite: when the
# package contains only DLC1 files UnrealPak mounts directly at
# .../GameLite/DLCGameData/DLC1/, while mixed generated content can move the
# common mount higher up.
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

$pakInfo = Get-Item -LiteralPath $PakPath
Write-Host ""
Write-Host "SUCCESS"
Write-Host "PAK          : $($pakInfo.FullName)"
Write-Host "Size         : $([math]::Round($pakInfo.Length / 1KB, 2)) KiB"
Write-Host "Packed files : $($sourceFiles.Count)"
Write-Host "Mount root   : $ContentMountRoot"

if (-not $KeepStaging) {
    Remove-Item -LiteralPath $StagingRoot -Recurse -Force
} else {
    Write-Host "Staging kept : $StagingRoot"
}
