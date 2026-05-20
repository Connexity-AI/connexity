param(
    [string]$ProjectName = "connexity",
    [string]$Workspace = $env:RAILWAY_WORKSPACE,
    [string]$FrontendServiceName = "frontend",
    [string]$PostgresServiceName = "Postgres",
    [string]$BackendServiceName = "backend",
    [string]$McpServiceName = "mcp-server",
    [string]$DotEnvPath = (Join-Path $PSScriptRoot "..\.env"),
    [string]$SiteUrl = $env:SITE_URL,
    [string]$ConnexityApiToken = $env:CONNEXITY_API_TOKEN,
    [string]$ConnexityEmail = $env:CONNEXITY_EMAIL,
    [string]$ConnexityPassword = $env:CONNEXITY_PASSWORD
)

$ErrorActionPreference = "Stop"

function Read-DotEnv {
    param([string]$Path)

    $values = @{}
    if (-not (Test-Path -LiteralPath $Path)) {
        return $values
    }

    foreach ($line in Get-Content -LiteralPath $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#")) {
            continue
        }

        $separator = $trimmed.IndexOf("=")
        if ($separator -lt 1) {
            continue
        }

        $key = $trimmed.Substring(0, $separator).Trim()
        $value = $trimmed.Substring($separator + 1).Trim()

        if (
            ($value.StartsWith('"') -and $value.EndsWith('"')) -or
            ($value.StartsWith("'") -and $value.EndsWith("'"))
        ) {
            if ($value.Length -ge 2) {
                $value = $value.Substring(1, $value.Length - 2)
            }
        }

        $values[$key] = $value
    }

    return $values
}

function Get-Setting {
    param(
        [hashtable]$DotEnv,
        [string]$Name,
        [string]$Default = ""
    )

    $current = [System.Environment]::GetEnvironmentVariable($Name)
    if (-not [string]::IsNullOrWhiteSpace($current)) {
        return $current.Trim()
    }

    if ($DotEnv.ContainsKey($Name) -and -not [string]::IsNullOrWhiteSpace($DotEnv[$Name])) {
        return $DotEnv[$Name].Trim()
    }

    return $Default
}

function New-RailwayReference {
    param(
        [string]$Namespace,
        [string]$VariableName
    )

    return '${{ ' + $Namespace + '.' + $VariableName + ' }}'
}

function New-RailwayUrlReference {
    param(
        [string]$Namespace,
        [string]$VariableName,
        [string]$Scheme = "https://",
        [string]$Suffix = ""
    )

    return $Scheme + (New-RailwayReference -Namespace $Namespace -VariableName $VariableName) + $Suffix
}

function Require-Setting {
    param(
        [string]$Name,
        [string]$Value
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        throw "Missing required setting: $Name"
    }

    if ($Value -eq "changethis") {
        throw "Setting $Name still uses the placeholder value 'changethis'. Please set a real value first."
    }
}

function Invoke-Railway {
    param([string[]]$Args)

    Write-Host ("railway " + ($Args -join " ")) -ForegroundColor Cyan
    & railway -y @Args
    if ($LASTEXITCODE -ne 0) {
        throw "railway $($Args -join ' ') failed with exit code $LASTEXITCODE"
    }
}

function Invoke-RailwayUpInDirectory {
    param(
        [string]$Directory,
        [string]$ServiceName
    )

    Push-Location (Resolve-Path (Join-Path $PSScriptRoot "..\$Directory"))
    try {
        Invoke-Railway @("up", "--path-as-root", "-s", $ServiceName, "-c")
    }
    finally {
        Pop-Location
    }
}

$dotEnv = Read-DotEnv -Path $DotEnvPath

if (-not (Get-Command railway -ErrorAction SilentlyContinue)) {
    throw "Railway CLI is not installed. Install it first, then rerun this script."
}

Require-Setting -Name "JWT_SECRET_KEY" -Value (Get-Setting -DotEnv $dotEnv -Name "JWT_SECRET_KEY")
Require-Setting -Name "ENCRYPTION_KEY" -Value (Get-Setting -DotEnv $dotEnv -Name "ENCRYPTION_KEY")

$jwtSecretKey = Get-Setting -DotEnv $dotEnv -Name "JWT_SECRET_KEY"
$encryptionKey = Get-Setting -DotEnv $dotEnv -Name "ENCRYPTION_KEY"
$openAiKey = Get-Setting -DotEnv $dotEnv -Name "OPENAI_API_KEY"
$anthropicKey = Get-Setting -DotEnv $dotEnv -Name "ANTHROPIC_API_KEY"

if ([string]::IsNullOrWhiteSpace($SiteUrl)) {
    $SiteUrl = Get-Setting -DotEnv $dotEnv -Name "SITE_URL"
}

$shouldGenerateFrontendDomain = $false
if ([string]::IsNullOrWhiteSpace($SiteUrl) -or $SiteUrl -match "localhost") {
    $SiteUrl = New-RailwayUrlReference -Namespace $FrontendServiceName -VariableName "RAILWAY_PUBLIC_DOMAIN"
    $shouldGenerateFrontendDomain = $true
}

$SiteUrl = $SiteUrl.TrimEnd("/")

$backendApiUrl = New-RailwayUrlReference -Namespace $BackendServiceName -VariableName "RAILWAY_PRIVATE_DOMAIN" -Scheme "http://" -Suffix ":8000/api/v1"
$frontendSiteUrl = $SiteUrl

Push-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))
try {
    if (-not (Test-Path -LiteralPath ".railway")) {
        $initArgs = @("init", "-n", $ProjectName)
        if (-not [string]::IsNullOrWhiteSpace($Workspace)) {
            $initArgs += @("-w", $Workspace)
        }
        Invoke-Railway $initArgs
    }

    Invoke-Railway @("add", "-d", "postgres")

    $frontendArgs = @(
        "add",
        "-s",
        $FrontendServiceName,
        "-v",
        "SITE_URL=$frontendSiteUrl",
        "-v",
        "API_URL=$backendApiUrl"
    )
    Invoke-Railway $frontendArgs

    $backendArgs = @(
        "add",
        "-s",
        $BackendServiceName,
        "-v",
        ('DATABASE_URL=${{ ' + $PostgresServiceName + '.DATABASE_URL }}'),
        "-v",
        "SITE_URL=$frontendSiteUrl",
        "-v",
        "JWT_SECRET_KEY=$jwtSecretKey",
        "-v",
        "ENCRYPTION_KEY=$encryptionKey",
        "-v",
        "ENVIRONMENT=production"
    )

    if (-not [string]::IsNullOrWhiteSpace($openAiKey)) {
        $backendArgs += @("-v", "OPENAI_API_KEY=$openAiKey")
    }

    if (-not [string]::IsNullOrWhiteSpace($anthropicKey)) {
        $backendArgs += @("-v", "ANTHROPIC_API_KEY=$anthropicKey")
    }

    Invoke-Railway $backendArgs

    $mcpArgs = @(
        "add",
        "-s",
        $McpServiceName,
        "-v",
        "CONNEXITY_API_URL=$backendApiUrl",
        "-v",
        "CONNEXITY_USE_SAVED_CLI_CREDENTIALS=false"
    )

    if (-not [string]::IsNullOrWhiteSpace($ConnexityApiToken)) {
        $mcpArgs += @("-v", "CONNEXITY_API_TOKEN=$ConnexityApiToken")
    }
    elseif (
        -not [string]::IsNullOrWhiteSpace($ConnexityEmail) -and
        -not [string]::IsNullOrWhiteSpace($ConnexityPassword)
    ) {
        $mcpArgs += @("-v", "CONNEXITY_EMAIL=$ConnexityEmail")
        $mcpArgs += @("-v", "CONNEXITY_PASSWORD=$ConnexityPassword")
    }
    else {
        Write-Warning (
            "No MCP auth variables were provided. The MCP service will deploy, " +
            "but you still need to set CONNEXITY_API_TOKEN (preferred) or " +
            "CONNEXITY_EMAIL / CONNEXITY_PASSWORD before it can talk to the backend."
        )
    }

    Invoke-Railway $mcpArgs

    Invoke-RailwayUpInDirectory -Directory "frontend" -ServiceName $FrontendServiceName
    if ($shouldGenerateFrontendDomain) {
        Invoke-Railway @("domain", "-s", $FrontendServiceName)
    }
    Invoke-RailwayUpInDirectory -Directory "backend" -ServiceName $BackendServiceName
    Invoke-RailwayUpInDirectory -Directory "mcp_server" -ServiceName $McpServiceName
}
finally {
    Pop-Location
}
