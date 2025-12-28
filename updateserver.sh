#!/bin/bash


REPO_DIR="/home/gooberf/scripts/dashboard"
BRANCH="main"
SERVICE_NAME="dashboard.service"
GIT_REMOTE="origin"

set -e

cd "$REPO_DIR" || {
  echo "Repo directory not found: $REPO_DIR"
  exit 1
}

echo "Fetching latest changes..."
git fetch "$GIT_REMOTE"

LOCAL_HASH=$(git rev-parse "$BRANCH")
REMOTE_HASH=$(git rev-parse "$GIT_REMOTE/$BRANCH")

if [ "$LOCAL_HASH" != "$REMOTE_HASH" ]; then
  echo "Updates found. Pulling changes..."
  git pull "$GIT_REMOTE" "$BRANCH"

  echo "Restarting systemd service: $SERVICE_NAME"
  systemctl restart "$SERVICE_NAME"

  echo "Update applied and service restarted."
else
  echo "No updates found. Nothing to do."
fi
