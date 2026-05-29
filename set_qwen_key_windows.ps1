$ErrorActionPreference = "Stop"

$key = Read-Host "Paste your Qwen/DashScope API key"
if (-not $key.Trim()) {
    throw "Qwen API key cannot be empty."
}

[Environment]::SetEnvironmentVariable("QWEN_API_KEY", $key.Trim(), "User")
[Environment]::SetEnvironmentVariable("DASHSCOPE_API_KEY", $key.Trim(), "User")
Write-Host "Qwen API key saved to Windows user environment variables."
