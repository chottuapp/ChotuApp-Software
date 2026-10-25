#requires -Version 5.1
[CmdletBinding()]
param([string]$AccessFolder = 'D:\ChotuRunner\CloudBuildAccess')
$ErrorActionPreference = 'Stop'
$sourceRepo = 'chottuapp/ChotuProject-development'
$buildRepo = 'chottuapp/ChotuApp-Software'
$environment = 'chotu-cloud-build'
function Invoke-ChotuGh([string[]]$GhArgs) {
    & gh @GhArgs
    if ($LASTEXITCODE -ne 0) { throw 'GitHub step failed. Do not paste tokens or keys in chat; send only the error.' }
}
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { throw 'GitHub CLI is required; your earlier runner setup already used it.' }
if (-not (Get-Command ssh-keygen -ErrorAction SilentlyContinue)) { throw 'Windows OpenSSH ssh-keygen is required. Nothing was installed on the PC.' }
& gh auth status
if ($LASTEXITCODE -ne 0) {
    Invoke-ChotuGh -GhArgs @('auth','login','--hostname','github.com','--web','--git-protocol','https')
}
foreach ($repo in @($sourceRepo,$buildRepo)) {
    $info = (Invoke-ChotuGh -GhArgs @('api',"repos/$repo")) | ConvertFrom-Json
    if (-not $info.permissions.admin) { throw 'Use your own GitHub account with administrator access to both Chotu repositories.' }
}
$null = New-Item -ItemType Directory -Path $AccessFolder -Force
$identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
& icacls $AccessFolder /inheritance:r /grant:r "${identity}:(OI)(CI)F" 'SYSTEM:(OI)(CI)F' > $null
if ($LASTEXITCODE -ne 0) { throw 'Could not restrict the new credential folder; no key was generated.' }
$keyPath = Join-Path $AccessFolder 'source-read-only-ed25519'
if (-not (Test-Path -LiteralPath $keyPath)) {
    $arguments = '-q -t ed25519 -N "" -f "' + $keyPath + '" -C "chotu-cloud-build-read-only"'
    $process = Start-Process -FilePath (Get-Command ssh-keygen).Source -ArgumentList $arguments -Wait -NoNewWindow -PassThru
    if ($process.ExitCode -ne 0) { throw 'Read-only key generation failed.' }
}
if (-not (Test-Path -LiteralPath ($keyPath+'.pub'))) { throw 'The matching public key is missing. Existing private key was preserved.' }
$publicKey = [IO.File]::ReadAllText($keyPath+'.pub').Trim()
$keyParts = $publicKey -split '\s+'
if ($keyParts.Count -lt 2 -or $keyParts[0] -ne 'ssh-ed25519') { throw 'Unexpected public key format.' }
$normalizedKey = $keyParts[0]+' '+$keyParts[1]
$keys = (Invoke-ChotuGh -GhArgs @('api',"repos/$sourceRepo/keys?per_page=100")) | ConvertFrom-Json
$matching = @($keys | Where-Object { $parts=$_.key -split '\s+'; ($parts[0]+' '+$parts[1]) -eq $normalizedKey })
if ($matching.Count -eq 0) {
    $body = @{title='Chotu cloud app build - read only';key=$publicKey;read_only=$true} | ConvertTo-Json -Compress
    $body | & gh api --method POST "repos/$sourceRepo/keys" --input - > $null
    if ($LASTEXITCODE -ne 0) { throw 'Read-only source deploy-key registration failed.' }
} elseif (-not $matching[0].read_only) { throw 'Existing key has write access. It was not reused for cloud builds.' }
# This environment is dedicated to this manual cloud build workflow.
Invoke-ChotuGh -GhArgs @('api','--method','PUT',"repos/$buildRepo/environments/$environment") > $null
[IO.File]::ReadAllText($keyPath) | & gh secret set CHOTU_APP_SOURCE_KEY --repo $buildRepo --env $environment
if ($LASTEXITCODE -ne 0) { throw 'Secure GitHub environment-secret upload failed.' }
$sourceSha = ((Invoke-ChotuGh -GhArgs @('api',"repos/$sourceRepo/commits/feature/drive-catalog-sync",'--jq','.sha')) -join '').Trim()
if ($sourceSha -notmatch '^[a-f0-9]{40}$') { throw 'Could not verify the reviewed private source commit.' }
Invoke-ChotuGh -GhArgs @('workflow','run','chotu-private-app-cloud.yml','--repo',$buildRepo,'--ref','main','-f',"source_sha=$sourceSha")
Write-Host 'SUCCESS: restricted cloud-build access configured and web build requested.'
Write-Host 'Builds now run on GitHub cloud computers, not this laptop. Keep the old PC runner disabled.'
Write-Host 'No app source was made public. No paid budget or Amazon hosting setting was changed. No live deployment was performed.'
Write-Host ('Status: https://github.com/'+$buildRepo+'/actions/workflows/chotu-private-app-cloud.yml')
