#!/bin/sh
set -eu
cd "$(dirname "$0")"
cp -n .env.example .env || true
echo "请先编辑 deploy/china/.env，然后执行 docker compose up -d --build"
