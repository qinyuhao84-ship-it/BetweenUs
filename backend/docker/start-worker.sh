#!/bin/sh
set -eu
exec celery -A app.workers.celery_app.celery_app worker --loglevel=info
