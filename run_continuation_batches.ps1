param(
    [int]$BatchCount = 10,
    [int]$StartBatch = 0,
    [int]$BatchSize = 100,
    [int]$TotalPopulation = 3000,
    [int]$Seed = 42,
    [string]$Model = "qwen3.5-4b",
    [string]$ExcludeFile = "results\batches\qwen35_4b_1000\calls_all_1000_corrected.csv",
    [string]$OutputRoot = "results\batches\qwen35_4b_next"
)

$ErrorActionPreference = "Stop"

if ($BatchCount -lt 1) {
    throw "BatchCount must be at least 1."
}
if ($StartBatch -lt 0 -or $StartBatch -ge $BatchCount) {
    throw "StartBatch must be between 0 and BatchCount - 1."
}
if ($BatchSize -lt 1 -or $TotalPopulation -lt $BatchSize) {
    throw "TotalPopulation must be at least BatchSize."
}
if (-not (Test-Path $ExcludeFile)) {
    throw "Exclude file does not exist: $ExcludeFile"
}

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Virtual-environment Python was not found: $python"
}

for ($batchIndex = $StartBatch; $batchIndex -lt $BatchCount; $batchIndex++) {
    $partNumber = $batchIndex + 1
    $partName = "part_{0:D3}" -f $partNumber
    $outputDir = Join-Path $OutputRoot $partName

    Write-Host "Starting batch $partNumber/$BatchCount (batch-index $batchIndex): $outputDir"
    & $python (Join-Path $PSScriptRoot "compare_pilot.py") `
        --only-model $Model `
        --batch-mode `
        --listings $BatchSize `
        --total-listings $TotalPopulation `
        --batch-index $batchIndex `
        --seed $Seed `
        --exclude-listings-file $ExcludeFile `
        --max-reviews 5 `
        --max-promises 4 `
        --max-tokens 900 `
        --fast-mode `
        --output-dir $outputDir

    if ($LASTEXITCODE -ne 0) {
        throw "Batch $batchIndex failed with exit code $LASTEXITCODE. Rerun with -StartBatch $batchIndex."
    }

    Write-Host "Finished batch $partNumber/$BatchCount."
}

Write-Host "All requested continuation batches completed."
