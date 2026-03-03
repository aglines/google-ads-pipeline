# GCP Setup Guide

## Prerequisites

Before running any commands in this guide, ensure you have:

1. **gcloud CLI installed** - [Install guide](https://cloud.google.com/sdk/docs/install)
2. **Authenticated with gcloud** - Run `gcloud auth login` if not already authenticated
3. **A GCP billing account** - Required for any resource creation
4. **Project-level permissions** - Owner or Editor role on the target project

Verify your setup:

```bash
gcloud --version
gcloud auth list
```

---

## Authentication Strategy

This project uses **Application Default Credentials (ADC)** for authentication. ADC allows Google client libraries to automatically find credentials without storing paths in config files.

```bash
# Set up ADC for local development
gcloud auth application-default login
```

This stores credentials in the standard gcloud location (`~/.config/gcloud/application_default_credentials.json`). Google client libraries find these automatically. **Do not reference this path in .env or copy it elsewhere.**

If you require a service account for production workloads, use Workload Identity Federation or ensure the key already exists in a secure, access-controlled location outside any project repository.

---

## Existing Project Setup

If you already have a GCP project configured, run these commands to populate your `.env` file:

```bash
# Get your project ID
PROJECT_ID=$(gcloud config get-value project)

# Set your preferred region
REGION="us-central1"

# Create .env from template
cp .env.example .env

# Populate GCP values
sed -i "s|^GCP_PROJECT_ID=.*|GCP_PROJECT_ID=${PROJECT_ID}|" .env
sed -i "s|^GCP_REGION=.*|GCP_REGION=${REGION}|" .env
sed -i "s|^GCS_BUCKET_RAW_DATA=.*|GCS_BUCKET_RAW_DATA=${PROJECT_ID}-raw-data|" .env
sed -i "s|^GCS_BUCKET_PROCESSED=.*|GCS_BUCKET_PROCESSED=${PROJECT_ID}-processed-data|" .env

# Verify
grep -E "^GCP_|^GCS_" .env
```

### Discovery Commands

Use these to inspect your existing project:

```bash
# List all projects you have access to
gcloud projects list

# Show current active project
gcloud config get-value project

# List enabled APIs
gcloud services list --enabled

# List existing service accounts
gcloud iam service-accounts list

# Check if required APIs are enabled
gcloud services list --enabled --filter="NAME:(bigquery OR storage)"
```

---

## New Project Setup

For a fresh GCP project:

```bash
# Set variables
PROJECT_ID="your-project-id"
REGION="us-central1"

# Create project
gcloud projects create $PROJECT_ID

# Set as active project
gcloud config set project $PROJECT_ID

# Enable required APIs (after billing is linked - see Console Tasks below)
gcloud services enable bigquery.googleapis.com storage.googleapis.com

# Set up ADC
gcloud auth application-default login

# Create .env from template
cp .env.example .env

# Populate GCP values
sed -i "s|^GCP_PROJECT_ID=.*|GCP_PROJECT_ID=${PROJECT_ID}|" .env
sed -i "s|^GCP_REGION=.*|GCP_REGION=${REGION}|" .env
sed -i "s|^GCS_BUCKET_RAW_DATA=.*|GCS_BUCKET_RAW_DATA=${PROJECT_ID}-raw-data|" .env
sed -i "s|^GCS_BUCKET_PROCESSED=.*|GCS_BUCKET_PROCESSED=${PROJECT_ID}-processed-data|" .env

# Verify
grep -E "^GCP_|^GCS_" .env
```

---

## Console-Only Tasks

These actions cannot be performed via CLI and require the GCP Console:

| Task | Location | Notes |
|------|----------|-------|
| Link billing account | Project Settings > Billing | Required before enabling APIs |
| Create billing account | Billing > Manage billing accounts | If no billing account exists |
| Accept terms of service | First project creation | One-time per GCP account |

---

## Verification

After setup, verify everything is configured:

```bash
# Confirm project
gcloud config get-value project

# Confirm APIs enabled
gcloud services list --enabled --filter="NAME:(bigquery OR storage)"

# Confirm ADC works
gcloud auth application-default print-access-token > /dev/null && echo "ADC configured"

# Confirm .env populated
grep -E "^GCP_|^GCS_" .env
```
