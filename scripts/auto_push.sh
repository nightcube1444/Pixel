#!/bin/bash

# Go to project root automatically
cd "$(dirname "$0")/.." || exit 1

git add .

git diff --cached --quiet && echo "No changes to commit" && exit 0

git commit -m "auto update $(date)"
git push
