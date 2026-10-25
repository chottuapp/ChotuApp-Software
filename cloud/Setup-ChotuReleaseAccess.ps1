#requires -Version 5.1
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$sourceRepo='chottuapp/ChotuProject-development'
$buildRepo='chottuapp/ChotuApp-Software'
$environment='chotu-cloud-release'
$taskName='ChotuApp Free GitHub Runner'
function Invoke-ChotuGh([string[]]$GhArgs) {
    for($attempt=0;$attempt -lt 4;$attempt++) {
        $errorFile=[IO.Path]::GetTempFileName()
        try {
            $prior=$ErrorActionPreference
            try { $ErrorActionPreference='Continue';$raw=& gh @GhArgs 2>$errorFile;$code=$LASTEXITCODE }
            finally { $ErrorActionPreference=$prior }
            if($code -eq 0) { return $raw }
            $detail=[IO.File]::ReadAllText($errorFile)
            if($detail -notmatch '(?i)timeout|TLS|connection|resolve|EOF|HTTP 5' -or $attempt -eq 3) { throw ('GitHub step failed: '+$detail) }
            Start-Sleep -Seconds (3*($attempt+1))
        } finally { Remove-Item -LiteralPath $errorFile -ErrorAction SilentlyContinue }
    }
}
function Get-ChotuJson([string[]]$GhArgs) { return ((Invoke-ChotuGh -GhArgs $GhArgs) -join "`n") | ConvertFrom-Json }
function Send-ChotuJson([string]$Endpoint,[string]$Method,[object]$Body) {
    $file=[IO.Path]::GetTempFileName()
    try { [IO.File]::WriteAllText($file,($Body|ConvertTo-Json -Depth 8 -Compress),(New-Object Text.UTF8Encoding($false))); Invoke-ChotuGh -GhArgs @('api','--method',$Method,$Endpoint,'--input',$file) > $null }
    finally { Remove-Item -LiteralPath $file -ErrorAction SilentlyContinue }
}
if(-not (Get-Command gh -ErrorAction SilentlyContinue)) { throw 'Use the PC where GitHub CLI is already signed in.' }
$task=Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
if($task.Description -ne 'Chotu managed WSL runner v1; limited Linux user; no Amazon hosting changes.') { throw 'Unexpected scheduled task; nothing was started.' }
if($task.State -ne 'Disabled') { throw 'This one-time transfer expects the old PC runner to be disabled. No task was changed.' }
$readKey='D:\ChotuRunner\CloudBuildAccess\source-read-only-ed25519'
if(-not (Test-Path -LiteralPath $readKey)) { throw 'The restricted cloud-source key from the successful cloud setup is missing.' }
foreach($repo in @($sourceRepo,$buildRepo)) {
    $info=Get-ChotuJson -GhArgs @('api',"repos/$repo")
    if(-not $info.permissions.admin) { throw 'Your local GitHub login needs repository administrator access.' }
}
$existingEnvironment=$null
try { $existingEnvironment=Get-ChotuJson -GhArgs @('api',"repos/$buildRepo/environments/$environment") }
catch { if($_.Exception.Message -notmatch '404|Not Found') { throw } }
if(-not $existingEnvironment) {
    Send-ChotuJson "repos/$buildRepo/environments/$environment" 'PUT' @{deployment_branch_policy=@{protected_branches=$false;custom_branch_policies=$true}}
    Send-ChotuJson "repos/$buildRepo/environments/$environment/deployment-branch-policies" 'POST' @{name='main';type='branch'}
}
# Existing reviewers/protection rules are deliberately preserved.
$public=Get-ChotuJson -GhArgs @('api',"repos/$buildRepo/environments/$environment/secrets/public-key")
if([Convert]::FromBase64String($public.key).Length -ne 32 -or $public.key_id -notmatch '^\d+$') { throw 'Invalid GitHub release environment encryption key.' }
$started=[DateTimeOffset]::UtcNow
$download=Join-Path ([IO.Path]::GetTempPath()) ('chotu-sealed-relay-'+[Guid]::NewGuid().ToString('N'))
$null=New-Item -ItemType Directory -Path $download
try {
    Write-Host 'Temporarily starting the old runner ONLY to encrypt credentials. No Flutter, builds or server changes will run.'
    Enable-ScheduledTask -TaskName $taskName > $null
    Start-ScheduledTask -TaskName $taskName
    Invoke-ChotuGh -GhArgs @('workflow','run','deploy-staging.yml','--repo',$sourceRepo,'--ref','feature/drive-catalog-sync','-f','operation=cloud-secrets-relay','-f',('relay_public_key='+$public.key),'-f',('relay_key_id='+$public.key_id))
    $runId=$null
    $deadline=(Get-Date).AddMinutes(3)
    while(-not $runId -and (Get-Date) -lt $deadline) {
        $runs=Get-ChotuJson -GhArgs @('api',"repos/$sourceRepo/actions/workflows/deploy-staging.yml/runs?event=workflow_dispatch&branch=feature/drive-catalog-sync&per_page=10")
        foreach($run in $runs.workflow_runs) {
            if([DateTimeOffset]::Parse($run.created_at) -lt $started.AddSeconds(-2)) { continue }
            $jobs=Get-ChotuJson -GhArgs @('api',"repos/$sourceRepo/actions/runs/$($run.id)/jobs?per_page=100")
            if(@($jobs.jobs|Where-Object {$_.name -eq 'cloud-secrets-relay' -and $_.conclusion -ne 'skipped'}).Count -eq 1) { $runId=$run.id;break }
        }
        if(-not $runId) { Start-Sleep -Seconds 5 }
    }
    if(-not $runId) { throw 'Could not identify the encrypted relay run. The PC runner will be stopped again.' }
    $deadline=(Get-Date).AddMinutes(8)
    do {
        $run=Get-ChotuJson -GhArgs @('api',"repos/$sourceRepo/actions/runs/$runId")
        Write-Host ('Light credential transfer: '+$run.status)
        if($run.status -eq 'completed') { break }
        Start-Sleep -Seconds 10
    } while((Get-Date) -lt $deadline)
    if($run.status -ne 'completed' -or $run.conclusion -ne 'success') { throw ('Encrypted relay did not succeed. No cloud deployment was requested. Run: https://github.com/'+$sourceRepo+'/actions/runs/'+$runId) }
    Invoke-ChotuGh -GhArgs @('run','download',[string]$runId,'--repo',$sourceRepo,'--name','sealed-cloud-release','--dir',$download)
} finally {
    Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    Disable-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue > $null
    & wsl.exe --terminate Ubuntu-24.04 > $null
    Write-Host 'PC runner disabled and its Ubuntu instance stopped again. All compilation remains in GitHub cloud.'
}
$sealed=Get-Content -Raw -LiteralPath (Join-Path $download 'sealed-cloud-release.json') | ConvertFrom-Json
if($sealed.repository -ne $buildRepo -or $sealed.environment -ne $environment -or $sealed.key_id -ne $public.key_id) { throw 'Encrypted package destination mismatch.' }
$latest=Get-ChotuJson -GhArgs @('api',"repos/$buildRepo/environments/$environment/secrets/public-key")
if($latest.key_id -ne $public.key_id -or $latest.key -ne $public.key) { throw 'GitHub rotated its encryption key; rerun this safe setup.' }
$allowed=@('STAGING_SSH_PRIVATE_KEY','FIREBASE_SERVICE_ACCOUNT_CHOTU_ADMIN_APP','ANDROID_KEYSTORE_BASE64','ANDROID_KEY_PROPERTIES')
foreach($record in $sealed.secrets) {
    if($allowed -notcontains $record.name -or $record.key_id -ne $public.key_id) { throw 'Unexpected encrypted credential record.' }
    $null=[Convert]::FromBase64String($record.encrypted_value)
    Send-ChotuJson "repos/$buildRepo/environments/$environment/secrets/$($record.name)" 'PUT' @{key_id=$record.key_id;encrypted_value=$record.encrypted_value}
}
foreach($required in @('STAGING_SSH_PRIVATE_KEY','FIREBASE_SERVICE_ACCOUNT_CHOTU_ADMIN_APP')) {
    if(@($sealed.secrets|Where-Object {$_.name -eq $required}).Count -ne 1) { throw 'Required encrypted release credential missing.' }
}
[IO.File]::ReadAllText($readKey) | & gh secret set CHOTU_APP_SOURCE_KEY --repo $buildRepo --env $environment
if($LASTEXITCODE -ne 0) { throw 'Restricted release-source access upload failed.' }
Remove-Item -LiteralPath (Join-Path $download 'sealed-cloud-release.json') -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $download -ErrorAction SilentlyContinue
Write-Host 'SUCCESS: encrypted cloud release access configured. No live deployment has run yet; send this success output so the tested release can be published.'
