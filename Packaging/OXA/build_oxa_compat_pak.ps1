param(
    [string]$UnrealPakPath,
    [string]$OutputDirectory,
    [switch]$KeepStaging
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ScriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$ContentRoot = (Resolve-Path (Join-Path $ScriptDirectory "..\..")).Path
$CompatSourceRoot = Join-Path $ContentRoot "Compat\OXA\GameLite"
$StagingRoot = Join-Path $ScriptDirectory "staging"
$PakListPath = Join-Path $StagingRoot "paklist.txt"

if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $ScriptDirectory "output"
}

$PakName = "BPRUpgradesExpanded_OXA_Compat.pak"
$PakPath = Join-Path $OutputDirectory $PakName
$MountRoot = "../../../Stalker2/Content/GameLite"

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

Write-Host "=== BPRUpgradesExpanded OXA Compat PAK Build ==="
Write-Host "Content root : $ContentRoot"
Write-Host "Compat source: $CompatSourceRoot"

if (-not (Test-Path -LiteralPath $CompatSourceRoot -PathType Container)) {
    throw "OXA compatibility source directory does not exist: $CompatSourceRoot"
}

$sourceFiles = @(Get-ChildItem -LiteralPath $CompatSourceRoot -File -Recurse | Sort-Object FullName)
if ($sourceFiles.Count -eq 0) {
    throw "OXA compatibility package contains no source files."
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
    $relativePath = $file.FullName.Substring($CompatSourceRoot.Length).TrimStart('\', '/')
    $relativePath = To-PakPath -Path $relativePath

    [PSCustomObject]@{
        File = $file
        RelativePath = $relativePath
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
    $destination = "$MountRoot/$($entry.RelativePath)"
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

# The PAK is mounted at ../../../Stalker2/Content/GameLite/.
# UnrealPak -List reports file paths relative to that common mount point.
$missingPaths = @($packageEntries | Where-Object {
    $expected = $_.RelativePath
    -not ($listOutput | Where-Object {
        $line = $_.Replace("\", "/")
        $line -like "*$expected*"
    })
})

if ($missingPaths.Count -gt 0) {
    Write-Host "UnrealPak -List output:"
    $listOutput | ForEach-Object { Write-Host "  $_" }
    Write-Host "Missing GameLite-relative entries:"
    $missingPaths | ForEach-Object { Write-Host "  $($_.RelativePath)" }
    throw "Generated PAK is missing $($missingPaths.Count) expected file(s)."
}

$pakInfo = Get-Item -LiteralPath $PakPath
Write-Host ""
Write-Host "SUCCESS"
Write-Host "PAK          : $($pakInfo.FullName)"
Write-Host "Size         : $([math]::Round($pakInfo.Length / 1KB, 2)) KiB"
Write-Host "Packed files : $($sourceFiles.Count)"
Write-Host "Mount root   : $MountRoot"

if (-not $KeepStaging) {
    Remove-Item -LiteralPath $StagingRoot -Recurse -Force
} else {
    Write-Host "Staging kept : $StagingRoot"
}
