param(
    [string]$UnrealPakPath,
    [string]$OutputDirectory,
    [switch]$KeepStaging
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ScriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$ContentRoot = (Resolve-Path (Join-Path $ScriptDirectory "..\..")).Path
$BprueCompatRoot = Join-Path $ContentRoot "Compat\WeaponPacks\GameLite"
$OxaCompatRoot = Join-Path $ContentRoot "Compat\WeaponPacksOXA\GameLite"
$StagingRoot = Join-Path $ScriptDirectory "staging"
$PakListPath = Join-Path $StagingRoot "paklist.txt"

if (-not $OutputDirectory) { $OutputDirectory = Join-Path $ScriptDirectory "output" }

$PakName = "BPRUpgradesExpanded_WeaponPacks_Compat.pak"
$PakPath = Join-Path $OutputDirectory $PakName
$MountRoot = "../../../Stalker2/Content/GameLite"
$Sources = @(
    @{ Name = "BPRUE-MK17"; Root = Join-Path $BprueCompatRoot "MK17" },
    @{ Name = "BPRUE-ModernAK"; Root = Join-Path $BprueCompatRoot "ModernAK" },
    @{ Name = "OXA-MK17"; Root = Join-Path $OxaCompatRoot "MK17" },
    @{ Name = "OXA-ModernAK"; Root = Join-Path $OxaCompatRoot "ModernAK" },
    @{ Name = "OXA-Shared"; Root = Join-Path $OxaCompatRoot "Shared" }
)

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

Write-Host "=== BPRUpgradesExpanded Weapon Packs x OXA Compat PAK Build ==="
Write-Host "Content root : $ContentRoot"
Write-Host "BPRUE compat : $BprueCompatRoot"
Write-Host "OXA compat   : $OxaCompatRoot"

foreach ($root in @($BprueCompatRoot, $OxaCompatRoot)) {
    if (-not (Test-Path -LiteralPath $root -PathType Container)) {
        throw "Weapon-pack compatibility output does not exist: $root. Run both external weapon-pack generators first."
    }
}

$packageEntries = @()
foreach ($source in $Sources) {
    $sourceRoot = $source.Root
    $sourceName = $source.Name
    if (-not (Test-Path -LiteralPath $sourceRoot -PathType Container)) {
        throw "Expected compatibility source '$sourceName' does not exist: $sourceRoot"
    }

    $sourceFiles = @(Get-ChildItem -LiteralPath $sourceRoot -File -Recurse | Sort-Object FullName)
    if ($sourceFiles.Count -eq 0) {
        throw "Compatibility source '$sourceName' contains no generated CFG files."
    }

    foreach ($file in $sourceFiles) {
        $relativePath = $file.FullName.Substring($sourceRoot.Length).TrimStart('\', '/')
        $relativePath = To-PakPath -Path $relativePath
        $packageEntries += [PSCustomObject]@{
            File = $file
            Layer = $sourceName
            RelativePath = $relativePath
        }
    }
}

$UnrealPak = Find-UnrealPak -ExplicitPath $UnrealPakPath
Write-Host "UnrealPak    : $UnrealPak"
Write-Host "Files        : $($packageEntries.Count)"
foreach ($source in $Sources) {
    $name = $source.Name
    Write-Host ("  {0,-16}: {1}" -f $name, @($packageEntries | Where-Object Layer -eq $name).Count)
}

if (Test-Path -LiteralPath $StagingRoot) { Remove-Item -LiteralPath $StagingRoot -Recurse -Force }
New-Item -ItemType Directory -Path $StagingRoot -Force | Out-Null
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null

# Flatten BPRUE and OXA compatibility sources into one real GameLite tree. When multiple
# layers target the same CFG path, concatenate the generated CFG fragments.
$mergedEntries = @()
foreach ($group in ($packageEntries | Group-Object RelativePath)) {
    $relativePath = $group.Name
    $stagedPath = Join-Path $StagingRoot $relativePath
    $stagedDirectory = Split-Path -Parent $stagedPath
    if ($stagedDirectory) { New-Item -ItemType Directory -Path $stagedDirectory -Force | Out-Null }

    $parts = @($group.Group | Sort-Object Layer)
    $content = foreach ($part in $parts) {
        "// ---- BPRUE WeaponPack OXA layer: $($part.Layer) ----"
        Get-Content -LiteralPath $part.File.FullName -Raw
        ""
    }
    $content -join [Environment]::NewLine | Set-Content -LiteralPath $stagedPath -Encoding UTF8

    $mergedEntries += [PSCustomObject]@{
        RelativePath = $relativePath
        Layers = ($parts.Layer -join ", ")
        StagedPath = $stagedPath
    }
}

$pakEntries = foreach ($entry in $mergedEntries) {
    $source = To-PakPath -Path $entry.StagedPath
    $destination = "$MountRoot/$($entry.RelativePath)"
    '"{0}" "{1}"' -f $source, $destination
}

$pakEntries | Set-Content -LiteralPath $PakListPath -Encoding UTF8
if (Test-Path -LiteralPath $PakPath) { Remove-Item -LiteralPath $PakPath -Force }

Write-Host ""
Write-Host "Creating $PakName ..."
& $UnrealPak $PakPath "-Create=$PakListPath"
if ($LASTEXITCODE -ne 0) { throw "UnrealPak failed while creating the PAK (exit code $LASTEXITCODE)." }
if (-not (Test-Path -LiteralPath $PakPath -PathType Leaf)) { throw "Expected PAK was not created: $PakPath" }

Write-Host ""
Write-Host "Validating PAK contents ..."
$listOutput = @(& $UnrealPak $PakPath -List 2>&1 | ForEach-Object { $_.ToString() })
if ($LASTEXITCODE -ne 0) {
    $listOutput | ForEach-Object { Write-Host $_ }
    throw "UnrealPak failed while validating the generated PAK."
}

# UnrealPak -List reports paths relative to the deepest common mount point.
# Derive that mount point and strip its GameLite-relative prefix before validating.
$mountLine = $listOutput | Where-Object { $_ -like '*with mount point "*' } | Select-Object -First 1
if (-not $mountLine) { throw "Could not determine PAK mount point from UnrealPak -List output." }
$mountMatch = [regex]::Match($mountLine, 'with mount point "([^"]+)"')
if (-not $mountMatch.Success) { throw "Could not parse PAK mount point from UnrealPak -List output: $mountLine" }
$listedMount = (To-PakPath -Path $mountMatch.Groups[1].Value).TrimEnd('/')
$mountPrefix = (To-PakPath -Path $MountRoot).TrimEnd('/')
if (-not $listedMount.StartsWith($mountPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Unexpected PAK mount point: $listedMount"
}
$mountRelative = $listedMount.Substring($mountPrefix.Length).Trim('/')

$missingPaths = @($mergedEntries | Where-Object {
    $expected = (To-PakPath -Path $_.RelativePath).TrimStart('/')
    if ($mountRelative -and $expected.StartsWith("$mountRelative/", [System.StringComparison]::OrdinalIgnoreCase)) {
        $expected = $expected.Substring($mountRelative.Length + 1)
    }
    -not ($listOutput | Where-Object { $_.Replace("\\", "/") -like "*$expected*" })
})
if ($missingPaths.Count -gt 0) {
    Write-Host "Missing GameLite-relative entries:"
    $missingPaths | ForEach-Object { Write-Host "  [$($_.Layers)] $($_.RelativePath)" }
    throw "Generated PAK is missing $($missingPaths.Count) expected file(s)."
}

# Staging-only layer names must never appear inside the actual PAK.
foreach ($layer in $Layers) {
    if ($listOutput | Where-Object { $_.Replace("\", "/") -like "*/$layer/GameData/*" }) {
        throw "Staging layer '$layer' leaked into the PAK hierarchy."
    }
}

$pakInfo = Get-Item -LiteralPath $PakPath
Write-Host ""
Write-Host "SUCCESS"
Write-Host "PAK          : $($pakInfo.FullName)"
Write-Host "Size         : $([math]::Round($pakInfo.Length / 1KB, 2)) KiB"
Write-Host "Source files : $($packageEntries.Count)"
Write-Host "Packed files : $($mergedEntries.Count)"
Write-Host "Mount root   : $MountRoot"

if (-not $KeepStaging) { Remove-Item -LiteralPath $StagingRoot -Recurse -Force }
else { Write-Host "Staging kept : $StagingRoot" }
