[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("delegated", "client-credentials")]
    [string]$Command,

    [string]$TenantId = $env:ENTRA_TENANT_ID,
    [string]$ClientId = $env:ENTRA_CLIENT_ID,
    [string]$Audience = $env:ENTRA_MCP_AUDIENCE,
    [string[]]$Scope = @(),
    [string]$ClientSecretEnvironmentVariable = "ENTRA_CLIENT_SECRET"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($Audience)) {
    $Audience = "api://enterprise-mcp-nonprod"
}
$Audience = $Audience.TrimEnd("/")

function Assert-RequiredValue {
    param(
        [string]$Name,
        [string]$Value
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        throw "$Name is required. Pass the parameter or set the matching environment variable."
    }
}

function Get-ObjectPropertyValue {
    param(
        [object]$InputObject,
        [string]$Name,
        [object]$DefaultValue = $null
    )

    $property = $InputObject.PSObject.Properties[$Name]
    if ($null -eq $property) {
        return $DefaultValue
    }
    return $property.Value
}

function Get-HttpErrorBody {
    param([System.Management.Automation.ErrorRecord]$ErrorRecord)

    if ($null -ne $ErrorRecord.ErrorDetails -and
        -not [string]::IsNullOrWhiteSpace($ErrorRecord.ErrorDetails.Message)) {
        return $ErrorRecord.ErrorDetails.Message
    }

    $responseProperty = $ErrorRecord.Exception.PSObject.Properties["Response"]
    if ($null -eq $responseProperty -or $null -eq $responseProperty.Value) {
        return $null
    }

    $response = $responseProperty.Value
    if ($response.PSObject.Methods.Name -notcontains "GetResponseStream") {
        return $null
    }

    try {
        $stream = $response.GetResponseStream()
        if ($null -eq $stream) {
            return $null
        }

        $reader = New-Object -TypeName System.IO.StreamReader -ArgumentList $stream
        try {
            return $reader.ReadToEnd()
        }
        finally {
            $reader.Dispose()
        }
    }
    catch {
        return $null
    }
}

function Invoke-OAuthFormPost {
    param(
        [string]$Uri,
        [hashtable]$Body,
        [switch]$ReturnOAuthError
    )

    try {
        return Invoke-RestMethod `
            -Uri $Uri `
            -Method Post `
            -ContentType "application/x-www-form-urlencoded" `
            -Body $Body
    }
    catch {
        $errorBody = Get-HttpErrorBody -ErrorRecord $_
        $oauthError = $null

        if (-not [string]::IsNullOrWhiteSpace($errorBody)) {
            try {
                $oauthError = $errorBody | ConvertFrom-Json
            }
            catch {
                $oauthError = $null
            }
        }

        if ($ReturnOAuthError -and $null -ne $oauthError) {
            return $oauthError
        }
        if (-not [string]::IsNullOrWhiteSpace($errorBody)) {
            throw "OAuth request to $Uri failed: $errorBody"
        }
        throw
    }
}

function Get-DelegatedAccessToken {
    param(
        [string]$Tenant,
        [string]$ApplicationClientId,
        [string[]]$RequestedScopes
    )

    if ($RequestedScopes.Count -eq 0) {
        $RequestedScopes = @(
            "$Audience/mcp.invoke",
            "openid",
            "profile",
            "offline_access"
        )
    }

    $deviceCodeUri = "https://login.microsoftonline.com/$Tenant/oauth2/v2.0/devicecode"
    $tokenUri = "https://login.microsoftonline.com/$Tenant/oauth2/v2.0/token"
    $deviceResponse = Invoke-OAuthFormPost -Uri $deviceCodeUri -Body @{
        client_id = $ApplicationClientId
        scope     = $RequestedScopes -join " "
    }

    $message = [string](Get-ObjectPropertyValue -InputObject $deviceResponse -Name "message")
    $deviceCode = [string](Get-ObjectPropertyValue -InputObject $deviceResponse -Name "device_code")
    Assert-RequiredValue -Name "device authorization message" -Value $message
    Assert-RequiredValue -Name "device_code" -Value $deviceCode

    # Keep device instructions off stdout so callers can capture only the token.
    [Console]::Error.WriteLine($message)

    $expiresIn = [int](Get-ObjectPropertyValue -InputObject $deviceResponse -Name "expires_in" -DefaultValue 900)
    $interval = [int](Get-ObjectPropertyValue -InputObject $deviceResponse -Name "interval" -DefaultValue 5)
    $expiresAt = [DateTimeOffset]::UtcNow.AddSeconds($expiresIn)

    while ([DateTimeOffset]::UtcNow -lt $expiresAt) {
        Start-Sleep -Seconds $interval
        $tokenResponse = Invoke-OAuthFormPost -Uri $tokenUri -ReturnOAuthError -Body @{
            grant_type = "urn:ietf:params:oauth:grant-type:device_code"
            client_id  = $ApplicationClientId
            device_code = $deviceCode
        }

        $accessToken = [string](Get-ObjectPropertyValue -InputObject $tokenResponse -Name "access_token")
        if (-not [string]::IsNullOrWhiteSpace($accessToken)) {
            return $accessToken
        }

        $errorCode = [string](Get-ObjectPropertyValue -InputObject $tokenResponse -Name "error")
        if ($errorCode -eq "authorization_pending") {
            continue
        }
        if ($errorCode -eq "slow_down") {
            $interval += 5
            continue
        }
        if ($errorCode -eq "authorization_declined") {
            throw "The user declined the Entra sign-in request."
        }
        if ($errorCode -eq "expired_token") {
            throw "The Entra device code expired before sign-in completed."
        }

        $details = $tokenResponse | ConvertTo-Json -Compress -Depth 5
        throw "Entra device-code token request failed: $details"
    }

    throw "The Entra device code expired before sign-in completed."
}

function Get-ApplicationAccessToken {
    param(
        [string]$Tenant,
        [string]$ApplicationClientId,
        [string]$ClientSecret,
        [string[]]$RequestedScopes
    )

    if ($RequestedScopes.Count -gt 1) {
        throw "client-credentials accepts one scope. Use the Enterprise MCP audience followed by /.default."
    }
    $requestedScope = if ($RequestedScopes.Count -eq 1) {
        $RequestedScopes[0]
    }
    elseif (-not [string]::IsNullOrWhiteSpace($env:ENTRA_TOKEN_SCOPE)) {
        $env:ENTRA_TOKEN_SCOPE
    }
    else {
        "$Audience/.default"
    }

    $tokenUri = "https://login.microsoftonline.com/$Tenant/oauth2/v2.0/token"
    $tokenResponse = Invoke-OAuthFormPost -Uri $tokenUri -Body @{
        grant_type    = "client_credentials"
        client_id     = $ApplicationClientId
        client_secret = $ClientSecret
        scope         = $requestedScope
    }
    $accessToken = [string](Get-ObjectPropertyValue -InputObject $tokenResponse -Name "access_token")
    Assert-RequiredValue -Name "access_token" -Value $accessToken
    return $accessToken
}

Assert-RequiredValue -Name "TenantId / ENTRA_TENANT_ID" -Value $TenantId
Assert-RequiredValue -Name "ClientId / ENTRA_CLIENT_ID" -Value $ClientId

if ($Command -eq "delegated") {
    $token = Get-DelegatedAccessToken `
        -Tenant $TenantId `
        -ApplicationClientId $ClientId `
        -RequestedScopes $Scope
}
else {
    $clientSecret = [Environment]::GetEnvironmentVariable($ClientSecretEnvironmentVariable)
    Assert-RequiredValue -Name $ClientSecretEnvironmentVariable -Value $clientSecret
    $token = Get-ApplicationAccessToken `
        -Tenant $TenantId `
        -ApplicationClientId $ClientId `
        -ClientSecret $clientSecret `
        -RequestedScopes $Scope
}

Write-Output $token
