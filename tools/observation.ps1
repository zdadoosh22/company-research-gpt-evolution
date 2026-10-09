param([Parameter(ValueFromRemainingArguments=$true)][string[]]$ObservationArguments)
$ResearchPython = 'C:\Users\aidan\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (-not (Test-Path -LiteralPath $ResearchPython)) { throw 'Bundled runtime unavailable.' }
& $ResearchPython -B (Join-Path $PSScriptRoot 'observation.py') @ObservationArguments
exit $LASTEXITCODE
