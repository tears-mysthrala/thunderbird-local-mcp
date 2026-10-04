param([Parameter(Mandatory)][string]$ProfilePath, [string[]]$AccountIds, [string]$PythonPath = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe")
$ErrorActionPreference = 'Stop'
$project = Split-Path $PSScriptRoot -Parent
$profile = (Resolve-Path -LiteralPath $ProfilePath).Path
if (!(Test-Path -LiteralPath "$profile\prefs.js") -or !(Test-Path -LiteralPath $PythonPath)) { throw 'Perfil o Python inexistente' }
$runtime = Join-Path $project 'runtime'
New-Item -ItemType Directory -Path $runtime -Force | Out-Null
$sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
& icacls $runtime /inheritance:r /grant:r "*${sid}:(OI)(CI)F" '*S-1-5-18:(OI)(CI)F' | Out-Null
if ($LASTEXITCODE) { throw 'No se pudo proteger runtime' }
$configFile = Join-Path $runtime 'config.json'
if (Test-Path -LiteralPath $configFile) {
 $config = Get-Content -LiteralPath $configFile -Raw | ConvertFrom-Json
 if ($config.profilePath -ne $profile) { throw 'Instalacion vinculada a otro perfil' }
} else {
 if (!$AccountIds -or $AccountIds.Count -eq 0) { throw 'Indica cuentas permitidas con -AccountIds' }
 $binding = [guid]::NewGuid().ToString()
 $token = $binding.Replace('-','')
 $config = [ordered]@{ profileId=$binding; profilePath=$profile; profileBinding='installation'; extensionId="thunderbird-mcp-$token@mkdl.local"; hostName='mkdl.thunderbird.local'; pipe="\\.\pipe\mkdl-thunderbird-$token"; database=(Join-Path $runtime 'actions.sqlite'); accountIds=$AccountIds }
 $config | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $configFile -Encoding utf8
}
$installationGuid=[guid]::Parse($config.profileId)
$installationToken=$installationGuid.ToString().Replace('-','')
if ($config.extensionId -ne "thunderbird-mcp-$installationToken@mkdl.local" -or $config.pipe -ne "\\.\pipe\mkdl-thunderbird-$installationToken" -or !$config.accountIds.Count) { throw 'Identidad de instalacion incoherente' }
if ($AccountIds -and (Compare-Object $AccountIds $config.accountIds)) { throw 'No cambiar scope durante reinstalacion' }
$config.hostName='mkdl.thunderbird.local'
$config | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $configFile -Encoding utf8
$manifest = [ordered]@{manifest_version=3;name='Thunderbird Local Private MCP';version='0.1.2';description='Local MCP: lectura y acciones aprobadas. Sin envio.';browser_specific_settings=@{gecko=@{id=$config.extensionId;strict_min_version='147.0';update_url='https://raw.githubusercontent.com/tears-mysthrala/thunderbird-local-mcp/main/updates.json'}};background=@{page='background.html'};permissions=@('nativeMessaging','accountsRead','accountsFolders','messagesRead','messagesImport','messagesUpdate','messagesMove','messagesTagsList','addressBooks','compose','compose.save')}
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath "$project\extension\manifest.json" -Encoding utf8
@("@echo off", ('"{0}" -u "{1}" %*' -f $PythonPath,"$project\native\host.py")) | Set-Content -LiteralPath "$runtime\host.bat" -Encoding ascii
$hostManifest = @{name=$config.hostName;description='Thunderbird local named pipe broker';path="$runtime\host.bat";type='stdio';allowed_extensions=@($config.extensionId)}
$hostManifest | ConvertTo-Json | Set-Content -LiteralPath "$runtime\native-manifest.json" -Encoding utf8
$registry = "HKCU:\Software\Mozilla\NativeMessagingHosts\$($config.hostName)"
if (Test-Path $registry) {
 $existing = (Get-Item $registry).GetValue('')
 if ($existing -ne "$runtime\native-manifest.json") { throw 'Registro ocupado por otra instalacion' }
}
New-Item -Path $registry -Force | Out-Null
Set-Item -Path $registry -Value "$runtime\native-manifest.json"
& $PythonPath "$PSScriptRoot\package.py" $project
if ($LASTEXITCODE) { throw 'Error empaquetando XPI' }
@{mcpServers=@{thunderbird_local=@{command=(Get-Command node).Source;args=@("$project\src\server.js")}}} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath "$runtime\mcp-client.json" -Encoding utf8
Write-Output "Host registrado para el usuario actual. XPI: $project\dist\thunderbird-local-mcp-0.1.2.xpi"
Write-Output 'Instalar el XPI desde Complementos > Instalar complemento desde archivo en el perfil seleccionado.'
