#!/usr/bin/env bash
# Point the web app at a Docker image, restart it, wait until it answers, then run
# the smoke test. Used by both GitHub workflows (deploy and rollback); it also works
# by hand after `az login`.
#
# Usage: WEBAPP_NAME=<app> RESOURCE_GROUP=rg-ecom-mini bash scripts/deploy.sh <registry>/ecom-api:<tag>
set -euo pipefail

image="$1"
url="https://${WEBAPP_NAME}.azurewebsites.net"

echo "Deploying $image"
az webapp config container set \
  --name "$WEBAPP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --container-image-name "$image" \
  --output none
az webapp restart --name "$WEBAPP_NAME" --resource-group "$RESOURCE_GROUP" --output none

# Give the restart time to stop the old container, so the checks below reach the
# new one. A first start of a new image on F1 takes about 2 minutes.
sleep 30
for attempt in $(seq 1 36); do
  if curl --silent --fail --max-time 30 --output /dev/null "$url/health"; then
    echo "Healthy after $attempt check(s); running the smoke test"
    exec python3 scripts/smoke_test.py "$url"
  fi
  echo "Check $attempt: not ready yet"
  sleep 10
done

echo "The app did not become healthy in time" >&2
exit 1
