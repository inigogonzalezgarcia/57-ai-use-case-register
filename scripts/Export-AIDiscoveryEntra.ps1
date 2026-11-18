<#
.SYNOPSIS
    Lists the enterprise apps in Entra ID that look like AI tools, with how many users are assigned, into discovered.csv.
.DESCRIPTION
    Read-only. Reads the service principals of the tenant with Microsoft Graph PowerShell, keeps the ones whose name or publisher
    matches the keywords, counts the users and groups assigned to each, and writes discovered.csv (Source, Name, Publisher, Owner,
    Department, Users, DataSeen, LastActivity) for `python -m aireg review`. With -IncludeSignInActivity it also reads the last
    sign-in of each app from the beta report endpoint (needs AuditLog.Read.All). It changes nothing in the tenant.
.EXAMPLE
    .\Export-AIDiscoveryEntra.ps1 -OutputFolder .\data
.EXAMPLE
    .\Export-AIDiscoveryEntra.ps1 -Keywords 'GPT','Copilot','Transcrib','Note','Writer','Chat' -IncludeSignInActivity -OutputFolder .\data
#>
[CmdletBinding()]
param(
    [string[]] $Keywords = @('\bAI\b', 'GPT', 'Copilot', 'Assistant', 'Transcri', 'Note ?Tak', 'Chat', 'Writer', 'Translat', 'LLM'),
    [switch] $IncludeMicrosoft,
    [switch] $IncludeSignInActivity,
    [string] $OutputFolder = '.'
)
$ErrorActionPreference = 'Stop'
$scopes = @('Application.Read.All')
if ($IncludeSignInActivity) { $scopes += 'AuditLog.Read.All' }
Connect-MgGraph -Scopes $scopes -NoWelcome

$microsoft = 'f8cdef31-a31e-4b4a-93e4-5f571e91255a'   # the tenant Microsoft's own first-party apps belong to
$pattern = ($Keywords -join '|')
$apps = Get-MgServicePrincipal -All -Property Id, AppId, DisplayName, PublisherName, AppOwnerOrganizationId, ServicePrincipalType |
    Where-Object { $_.ServicePrincipalType -eq 'Application' -and ($IncludeMicrosoft -or $_.AppOwnerOrganizationId -ne $microsoft) } |
    Where-Object { $_.DisplayName -match $pattern -or $_.PublisherName -match $pattern }

$rows = foreach ($sp in $apps) {
    $assigned = Get-MgServicePrincipalAppRoleAssignedTo -ServicePrincipalId $sp.Id -All
    $last = ''
    if ($IncludeSignInActivity) {
        $uri = "https://graph.microsoft.com/beta/reports/servicePrincipalSignInActivities?`$filter=appId eq '$($sp.AppId)'"
        $act = (Invoke-MgGraphRequest -Method GET -Uri $uri).value | Select-Object -First 1
        if ($act.lastSignInActivity.lastSignInDateTime) { $last = ([datetime]$act.lastSignInActivity.lastSignInDateTime).ToString('yyyy-MM-dd') }
    }
    [pscustomobject]@{
        Source       = 'Enterprise apps'
        Name         = $sp.DisplayName
        Publisher    = $sp.PublisherName
        Owner        = ''
        Department   = ''
        Users        = @($assigned | Where-Object PrincipalType -eq 'User').Count + @($assigned | Where-Object PrincipalType -eq 'Group').Count
        DataSeen     = ''
        LastActivity = $last
    }
}
New-Item -ItemType Directory -Force -Path $OutputFolder | Out-Null
$out = Join-Path $OutputFolder 'discovered.csv'
$rows | Sort-Object Name | Export-Csv -Path $out -NoTypeInformation -Encoding UTF8
Write-Host "$(@($rows).Count) AI-looking enterprise apps written to $out (a group assignment counts as one; add Copilot Studio agents and cloud app discovery with the same columns)"
