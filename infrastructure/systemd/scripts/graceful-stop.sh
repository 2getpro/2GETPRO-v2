#!/bin/bash
# Graceful stop script for 2GETPRO v2

set -e

echo "Initiating graceful shutdown..."

# Get the main process PID
MAIN_PID=$1

if [ -z "$MAIN_PID" ]; then
    echo "ERROR: No PID provided"
    exit 1
fi

# Send SIGTERM to allow graceful shutdown
echo "Sending SIGTERM to process $MAIN_PID..."
kill -TERM "$MAIN_PID"

# Wait for process to terminate (max 20 seconds)
TIMEOUT=20
COUNTER=0

while kill -0 "$MAIN_PID" 2>/dev/null; do
    if [ $COUNTER -ge $TIMEOUT ]; then
        echo "WARNING: Process did not terminate gracefully, forcing shutdown..."
        kill -KILL "$MAIN_PID"
        exit 0
    fi
    
    echo "Waiting for process to terminate... ($COUNTER/$TIMEOUT)"
    sleep 1
    COUNTER=$((COUNTER + 1))
done

echo "Process terminated gracefully"
exit 0