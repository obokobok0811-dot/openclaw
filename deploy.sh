#!/bin/bash
# Usage: ./deploy.sh <PROJECT_ID> <SERVICE_NAME> <REGION>
PROJECT_ID=${1:-ferrous-quest-488111-f6}
SERVICE_NAME=${2:-oc-assistant}
REGION=${3:-us-central1}

gcloud builds submit --tag gcr.io/${PROJECT_ID}/${SERVICE_NAME}

gcloud run deploy ${SERVICE_NAME} --image gcr.io/${PROJECT_ID}/${SERVICE_NAME} --region ${REGION} --platform managed --allow-unauthenticated --project ${PROJECT_ID}
