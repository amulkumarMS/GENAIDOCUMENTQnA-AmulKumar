#!/usr/bin/env bash
# Azure resource setup for DocuMind AI
# Usage: bash azure_setup.sh -s <subscription> -l eastus -g documind-rg -p documind -c documents
set -euo pipefail

SUBSCRIPTION=""
LOCATION="eastus"
RESOURCE_GROUP="documind-rg"
NAME_PREFIX="documind"
BLOB_CONTAINER="documents"
CHAT_DEPLOYMENT="gpt-4o"
CHAT_MODEL="gpt-4o"
CHAT_MODEL_VERSION="2024-08-06"
EMBED_DEPLOYMENT="text-embedding-3-large"
EMBED_MODEL="text-embedding-3-large"
EMBED_MODEL_VERSION="1"

while getopts "s:l:g:p:c:" opt; do
  case $opt in
    s) SUBSCRIPTION="$OPTARG" ;;
    l) LOCATION="$OPTARG" ;;
    g) RESOURCE_GROUP="$OPTARG" ;;
    p) NAME_PREFIX="$OPTARG" ;;
    c) BLOB_CONTAINER="$OPTARG" ;;
  esac
done

if ! command -v az >/dev/null 2>&1; then
  echo "Azure CLI (az) is required" >&2
  exit 1
fi

if [ -n "$SUBSCRIPTION" ]; then
  az account set --subscription "$SUBSCRIPTION" >/dev/null
fi

safe_name() {
  local prefix="$1" random_digits="$2" max_len="$3" suffix="$4"
  local base
  base=$(echo "$prefix" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9')
  [ ${#base} -lt 3 ] && base="doc${base}"
  local rand
  rand=$(shuf -i 1000-$((10**random_digits - 1)) -n 1)
  local name="${base}${rand}${suffix}"
  echo "${name:0:$max_len}"
}

STORAGE_NAME=$(safe_name "$NAME_PREFIX" 4 24 "")
SEARCH_NAME=$(safe_name "$NAME_PREFIX" 3 60 "-search")
AOAI_NAME=$(safe_name "$NAME_PREFIX" 3 24 "aoai")

printf "Using names:\n  Resource Group : %s\n  Storage Account: %s\n  Blob Container : %s\n  Search Service : %s\n  Azure OpenAI   : %s\n  Location       : %s\n" "$RESOURCE_GROUP" "$STORAGE_NAME" "$BLOB_CONTAINER" "$SEARCH_NAME" "$AOAI_NAME" "$LOCATION"

az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none

az storage account create \
  --name "$STORAGE_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --https-only true \
  --output none

STORAGE_CONN=$(az storage account show-connection-string --name "$STORAGE_NAME" --resource-group "$RESOURCE_GROUP" --query connectionString -o tsv)
az storage container create --name "$BLOB_CONTAINER" --account-name "$STORAGE_NAME" --auth-mode key --output none

az search service create \
  --name "$SEARCH_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --sku standard \
  --partition-count 1 \
  --replica-count 1 \
  --output none
SEARCH_KEY=$(az search admin-key show --service-name "$SEARCH_NAME" --resource-group "$RESOURCE_GROUP" --query primaryKey -o tsv)

az cognitiveservices account create \
  --name "$AOAI_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --kind OpenAI \
  --sku S0 \
  --yes \
  --output none
AOAI_ENDPOINT=$(az cognitiveservices account show --name "$AOAI_NAME" --resource-group "$RESOURCE_GROUP" --query properties.endpoint -o tsv)
AOAI_KEY=$(az cognitiveservices account keys list --name "$AOAI_NAME" --resource-group "$RESOURCE_GROUP" --query key1 -o tsv)

echo "Deploying models (if available in region)..."
az cognitiveservices account deployment create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AOAI_NAME" \
  --deployment-name "$CHAT_DEPLOYMENT" \
  --model-format OpenAI \
  --model-name "$CHAT_MODEL" \
  --model-version "$CHAT_MODEL_VERSION" \
  --scale-settings-scale-type Standard \
  --output none

az cognitiveservices account deployment create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AOAI_NAME" \
  --deployment-name "$EMBED_DEPLOYMENT" \
  --model-format OpenAI \
  --model-name "$EMBED_MODEL" \
  --model-version "$EMBED_MODEL_VERSION" \
  --scale-settings-scale-type Standard \
  --output none

echo "\nDone. Set these in backend/.env:"
echo "AZURE_OPENAI_ENDPOINT=$AOAI_ENDPOINT"
echo "AZURE_OPENAI_KEY=$AOAI_KEY"
echo "AZURE_OPENAI_CHAT_DEPLOYMENT=$CHAT_DEPLOYMENT"
echo "AZURE_OPENAI_EMBED_DEPLOYMENT=$EMBED_DEPLOYMENT"
echo "AZURE_SEARCH_ENDPOINT=https://$SEARCH_NAME.search.windows.net"
echo "AZURE_SEARCH_KEY=$SEARCH_KEY"
echo "AZURE_SEARCH_INDEX=<your-index-name>  # run backend/index_setup.py to create"
echo "AZURE_BLOB_CONN_STRING=$STORAGE_CONN"
echo "AZURE_BLOB_CONTAINER=$BLOB_CONTAINER"
