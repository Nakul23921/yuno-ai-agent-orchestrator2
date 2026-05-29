$ErrorActionPreference = "Stop"

function Find-Python {
    $candidates = @(
        @{ Command = "py"; Args = @("-3") },
        @{ Command = "python"; Args = @() },
        @{ Command = "python3"; Args = @() },
        @{ Command = "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"; Args = @() }
    )

    foreach ($candidate in $candidates) {
        $cmd = $candidate.Command
        if ($cmd.EndsWith(".exe") -and -not (Test-Path $cmd)) {
            continue
        }
        try {
            & $cmd @($candidate.Args) --version *> $null
            return $candidate
        } catch {
            continue
        }
    }
    return $null
}

$python = Find-Python
if ($null -eq $python) {
    Write-Host "Python was not found." -ForegroundColor Red
    Write-Host "Install Python 3.11+ from https://www.python.org/downloads/ and check 'Add python.exe to PATH'."
    Write-Host "After installing, close this PowerShell window, open a new one, and run:"
    Write-Host "  python --version"
    exit 1
}

Write-Host "Running tests..." -ForegroundColor Green
& $python.Command @($python.Args) -m unittest discover -s tests
