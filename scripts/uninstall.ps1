$ErrorActionPreference='Stop'
$project=Split-Path $PSScriptRoot -Parent
$config=Get-Content -LiteralPath "$project\runtime\config.json" -Raw | ConvertFrom-Json
$key="HKCU:\Software\Mozilla\NativeMessagingHosts\$($config.hostName)"
if ((Test-Path $key) -and (Get-Item $key).GetValue('') -eq "$project\runtime\native-manifest.json") { Remove-Item -LiteralPath $key }
Write-Output 'Host desregistrado. Desinstala Thunderbird Local Private MCP desde Complementos. Los planes y archivos se conservan.'
