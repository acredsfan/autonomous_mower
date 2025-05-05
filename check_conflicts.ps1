# PowerShell script to check for merge conflicts
Write-Host "Checking for merge conflicts..."
$conflictFiles = @()

# Check for conflict markers in files
Get-ChildItem -Path . -Recurse -File | ForEach-Object {
    $content = Get-Content $_.FullName -ErrorAction SilentlyContinue
    if ($content -match "<<<<<<< HEAD") {
        $conflictFiles += $_.FullName
        Write-Host "Found conflict in: $($_.FullName)"
    }
}

if ($conflictFiles.Count -eq 0) {
    Write-Host "No conflicts found."
} else {
    Write-Host "Found $($conflictFiles.Count) files with conflicts."
}
