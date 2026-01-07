# Azure resource setup for DocuMind AI
# Usage: pwsh ./azure_setup.ps1 -SubscriptionId "<sub>" -Location "eastus" -ResourceGroup "documind-rg" -NamePrefix "documind" -BlobContainer "documents"
param(
    [string]$SubscriptionId = "",
    [string]$Location = "eastus",
    [string]$ResourceGroup = "documind-rg",
    [string]$NamePrefix = "documind",
    [string]$BlobContainer = "documents",
    [string]$ChatDeploymentName = "gpt-4o",
    [string]$ChatModel = "gpt-4o",
    [string]$ChatModelVersion = "2024-08-06",
    [string]$EmbeddingDeploymentName = "text-embedding-3-large",
    [string]$EmbeddingModel = "text-embedding-3-large",
    [string]$EmbeddingModelVersion = "1"
)

function Require-AzCli {
    if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
        Write-Error "Azure CLI (az) is required. Install from https://learn.microsoft.com/cli/azure/install-azure-cli" -ErrorAction Stop
    }
}

function New-SafeName([string]$prefix, [int]$randomDigits, [int]$maxLength, [string]$suffix = "") {
    $base = ($prefix.ToLower() -replace "[^a-z0-9]", "")
    if ($base.Length -lt 3) { $base = "doc" + $base }
    $rand = Get-Random -Minimum 1000 -Maximum ([math]::Pow(10, $randomDigits))
    $name = "$base$rand$suffix"
    return $name.Substring(0, [Math]::Min($maxLength, $name.Length))
}

Require-AzCli

if ($SubscriptionId) {
    az account set --subscription $SubscriptionId | Out-Null
}

$storageName = New-SafeName -prefix $NamePrefix -randomDigits 4 -maxLength 24
$searchName = New-SafeName -prefix $NamePrefix -randomDigits 3 -maxLength 60 -suffix "-search"
$aoaiName   = New-SafeName -prefix $NamePrefix -randomDigits 3 -maxLength 24 -suffix "aoai"

Write-Host "Using names:" -ForegroundColor Cyan
Write-Host "  Resource Group : $ResourceGroup"
Write-Host "  Storage Account: $storageName"
Write-Host "  Blob Container : $BlobContainer"
Write-Host "  Search Service : $searchName"
Write-Host "  Azure OpenAI   : $aoaiName"
Write-Host "  Location       : $Location"

az group create --name $ResourceGroup --location $Location --output none

az storage account create `
  --name $storageName `
  --resource-group $ResourceGroup `
  --location $Location `
  --sku Standard_LRS `
  --kind StorageV2 `
  --https-only true `
  --output none

$storageConn = az storage account show-connection-string --name $storageName --resource-group $ResourceGroup --query connectionString -o tsv
az storage container create --name $BlobContainer --account-name $storageName --auth-mode key --output none

az search service create `
  --name $searchName `
  --resource-group $ResourceGroup `
  --location $Location `
  --sku standard `
  --partition-count 1 `
  --replica-count 1 `
  --output none
$searchKey = az search admin-key show --service-name $searchName --resource-group $ResourceGroup --query primaryKey -o tsv

az cognitiveservices account create `
  --name $aoaiName `
  --resource-group $ResourceGroup `
  --location $Location `
  --kind OpenAI `
  --sku S0 `
  --yes `
  --output none
$aoaiEndpoint = az cognitiveservices account show --name $aoaiName --resource-group $ResourceGroup --query properties.endpoint -o tsv
$aoaiKey = az cognitiveservices account keys list --name $aoaiName --resource-group $ResourceGroup --query key1 -o tsv

Write-Host "Deploying models (if available in region)..." -ForegroundColor Cyan
az cognitiveservices account deployment create `
  --resource-group $ResourceGroup `
  --name $aoaiName `
  --deployment-name $ChatDeploymentName `
  --model-format OpenAI `
  --model-name $ChatModel `
  --model-version $ChatModelVersion `
  --scale-settings-scale-type Standard `
  --output none

az cognitiveservices account deployment create `
  --resource-group $ResourceGroup `
  --name $aoaiName `
  --deployment-name $EmbeddingDeploymentName `
  --model-format OpenAI `
  --model-name $EmbeddingModel `
  --model-version $EmbeddingModelVersion `
  --scale-settings-scale-type Standard `
  --output none

Write-Host "\nDone. Set these in backend/.env:" -ForegroundColor Green
Write-Host "AZURE_OPENAI_ENDPOINT=$aoaiEndpoint"
Write-Host "AZURE_OPENAI_KEY=$aoaiKey"
Write-Host "AZURE_OPENAI_CHAT_DEPLOYMENT=$ChatDeploymentName"
Write-Host "AZURE_OPENAI_EMBED_DEPLOYMENT=$EmbeddingDeploymentName"
Write-Host "AZURE_SEARCH_ENDPOINT=https://$searchName.search.windows.net"
Write-Host "AZURE_SEARCH_KEY=$searchKey"
Write-Host "AZURE_SEARCH_INDEX=<your-index-name>  # run backend/index_setup.py to create"
Write-Host "AZURE_BLOB_CONN_STRING=$storageConn"
Write-Host "AZURE_BLOB_CONTAINER=$BlobContainer"
