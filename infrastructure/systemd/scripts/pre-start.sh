#!/bin/bash
# Pre-start script for 2GETPRO v2

set -e

WORKDIR="/opt/2getpro-v2"
LOG_DIR="/var/log/2getpro"

echo "Starting pre-start checks..."

# Check if working directory exists
if [ ! -d "$WORKDIR" ]; then
    echo "ERROR: Working directory $WORKDIR does not exist"
    exit 1
fi

# Check if .env file exists
if [ ! -f "$WORKDIR/.env.production" ]; then
    echo "ERROR: Environment file $WORKDIR/.env.production does not exist"
    exit 1
fi

# Create log directory if it doesn't exist
if [ ! -d "$LOG_DIR" ]; then
    echo "Creating log directory: $LOG_DIR"
    mkdir -p "$LOG_DIR"
    chown 2getpro:2getpro "$LOG_DIR"
fi

# Check database connectivity
echo "Checking database connectivity..."
if ! pg_isready -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" -U "${DB_USER:-2getpro_user}" > /dev/null 2>&1; then
    echo "WARNING: Database is not ready. Service will retry..."
fi

# Check Redis connectivity
echo "Checking Redis connectivity..."
if ! redis-cli -h "${REDIS_HOST:-localhost}" -p "${REDIS_PORT:-6379}" ping > /dev/null 2>&1; then
    echo "WARNING: Redis is not ready. Service will retry..."
fi

# Run database migrations
echo "Running database migrations..."
cd "$WORKDIR"
source venv/bin/activate
python -m alembic upgrade head || {
    echo "WARNING: Database migrations failed. Service will continue..."
}

echo "Pre-start checks completed successfully"
exit 0