param([Parameter(ValueFromRemainingArguments=$true)][string[]]$ResearchArguments)
$ResearchPython = 'C:\Users\aidan\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (-not (Test-Path -LiteralPath $ResearchPython)) { throw 'Bundled Python runtime unavailable. Load workspace dependencies in the app.' }
& $ResearchPython -B (Join-Path $PSScriptRoot 'research.py') @ResearchArguments
exit $LASTEXITCODE
