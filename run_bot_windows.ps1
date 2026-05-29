$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

$botEnv = @{}

foreach ($name in @("TELEGRAM_BOT_API_KEY", "ADMIN_USER_IDS")) {
    $value = [Environment]::GetEnvironmentVariable($name, "Process")
    if (-not $value) {
        $value = [Environment]::GetEnvironmentVariable($name, "User")
    }
    if ($value) {
        $botEnv[$name] = $value
    }
}

if (-not $botEnv["TELEGRAM_BOT_API_KEY"] -or -not $botEnv["ADMIN_USER_IDS"]) {
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $envLines = & wsl -d Ubuntu -u root -- bash -lc "docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' tg_gpt_bot" 2>$null
    $ErrorActionPreference = $previousErrorActionPreference
    if ($LASTEXITCODE -eq 0) {
        foreach ($line in $envLines) {
            if ($line -match '^(TELEGRAM_BOT_API_KEY|ADMIN_USER_IDS)=(.*)$') {
                $botEnv[$matches[1]] = $matches[2]
            }
        }
    }
}

foreach ($name in @("TELEGRAM_BOT_API_KEY", "ADMIN_USER_IDS")) {
    if (-not $botEnv[$name]) {
        throw "Missing $name in the old Docker container environment."
    }
}

$qwenKey = $env:QWEN_API_KEY
if (-not $qwenKey) {
    $qwenKey = [Environment]::GetEnvironmentVariable("QWEN_API_KEY", "User")
}
if (-not $qwenKey) {
    $qwenKey = [Environment]::GetEnvironmentVariable("DASHSCOPE_API_KEY", "User")
}
if (-not $qwenKey) {
    throw "Missing QWEN_API_KEY. Run set_qwen_key_windows.ps1 first."
}

$proxy = "http://127.0.0.1:7897"
$env:TELEGRAM_BOT_API_KEY = $botEnv["TELEGRAM_BOT_API_KEY"]
$env:ADMIN_USER_IDS = $botEnv["ADMIN_USER_IDS"]
$env:QWEN_API_KEY = $qwenKey
$env:DASHSCOPE_API_KEY = $qwenKey
$env:QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
$env:QWEN_MODELS = "qwen-turbo,qwen-plus,qwen-max,qwen-long,qwen-vl-plus,qwen-vl-max"
$env:TELEGRAM_PROXY = $proxy
$env:HTTP_PROXY = $proxy
$env:HTTPS_PROXY = $proxy
$env:http_proxy = $proxy
$env:https_proxy = $proxy

New-Item -ItemType Directory -Force -Path ".\logs" | Out-Null
& ".\.venv\Scripts\python.exe" -u ".\src\main.py" --db-path ".\data\bot.db" *> ".\logs\bot-latest.log"
