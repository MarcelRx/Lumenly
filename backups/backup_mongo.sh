#!/bin/bash
# MongoDB Backup Script for Lumenly
# This script creates a logical backup of MongoDB using mongodump

set -e  # Exit on error

# Configuration
BACKUP_DIR="/Users/mohsenrassam/Desktop/Lumenly/backups/mongo"
LOG_DIR="/Users/mohsenrassam/Desktop/Lumenly/backups/logs"
LOG_FILE="$LOG_DIR/mongo_backup_$(date +%Y%m%d_%H%M%S).log"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="$BACKUP_DIR/lumenly_mongo_$TIMESTAMP"
START_TIME=$(date +%s)

# Database configuration
MONGO_HOST="${MONGO_HOST:-localhost}"
MONGO_PORT="${MONGO_PORT:-27017}"
MONGO_DB="${MONGO_DB:-lumenly}"

# Retention configuration
DAILY_RETENTION_DAYS=7
WEEKLY_RETENTION_WEEKS=4
MONTHLY_RETENTION_MONTHS=3

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log "ERROR: $1"
    # Push failure metrics to Prometheus Pushgateway (if available)
    PROMETHEUS_PUSHGATEWAY="${PROMETHEUS_PUSHGATEWAY:-http://localhost:9091}"
    if command -v curl &> /dev/null; then
        cat <<EOF | curl -s --data-binary @- "$PROMETHEUS_PUSHGATEWAY/metrics/job/backup_mongo" > /dev/null 2>&1 || true
# TYPE backup_failure_total counter
backup_failure_total{database="mongodb"} 1
EOF
    fi
    exit 1
}

# Verify backup directory exists
if [ ! -d "$BACKUP_DIR" ]; then
    error_exit "Backup directory $BACKUP_DIR does not exist"
fi

log "Starting MongoDB backup"
log "Database: $MONGO_DB"
log "Host: $MONGO_HOST:$MONGO_PORT"
log "Backup path: $BACKUP_PATH"

# Perform backup using mongodump
log "Running mongodump..."
if mongodump --host "$MONGO_HOST" \
             --port "$MONGO_PORT" \
             --db "$MONGO_DB" \
             --out "$BACKUP_PATH" \
             >> "$LOG_FILE" 2>&1; then
    log "mongodump completed successfully"
else
    error_exit "mongodump failed. Check log file: $LOG_FILE"
fi

# Verify backup directory exists and contains data
if [ ! -d "$BACKUP_PATH" ]; then
    error_exit "Backup directory was not created: $BACKUP_PATH"
fi

# Check that the database directory exists within the backup
if [ ! -d "$BACKUP_PATH/$MONGO_DB" ]; then
    error_exit "Database directory not found in backup: $BACKUP_PATH/$MONGO_DB"
fi

# Count collections in backup
COLLECTION_COUNT=$(find "$BACKUP_PATH/$MONGO_DB" -name "*.bson" -type f | wc -l)
if [ "$COLLECTION_COUNT" -eq 0 ]; then
    error_exit "No collections found in backup"
fi

log "Backup directory created successfully"
log "Collections backed up: $COLLECTION_COUNT"

# Calculate backup size (cross-platform compatible)
if [[ "$OSTYPE" == "darwin"* ]]; then
    BACKUP_SIZE=$(du -sk "$BACKUP_PATH" | cut -f1)
    BACKUP_SIZE=$((BACKUP_SIZE * 1024))  # Convert KB to bytes
else
    BACKUP_SIZE=$(du -sb "$BACKUP_PATH" | cut -f1)
fi
log "Backup size: $BACKUP_SIZE bytes"

# Set appropriate permissions (readable by owner, executable for directories)
find "$BACKUP_PATH" -type f -exec chmod 600 {} \;
find "$BACKUP_PATH" -type d -exec chmod 700 {} \;
log "Backup file permissions set to 600, directory permissions set to 700"

# Cleanup old backups (retention policy)
log "Applying retention policy..."

# Clean up daily backups older than DAILY_RETENTION_DAYS
find "$BACKUP_DIR" -name "lumenly_mongo_*" -type d -mtime +$DAILY_RETENTION_DAYS -exec rm -rf {} + 2>/dev/null || true
log "Cleaned up daily backups older than $DAILY_RETENTION_DAYS days"

# Count remaining backups
BACKUP_COUNT=$(find "$BACKUP_DIR" -name "lumenly_mongo_*" -type d | wc -l)
log "Remaining backups: $BACKUP_COUNT"

# Push metrics to Prometheus Pushgateway (if available)
PROMETHEUS_PUSHGATEWAY="${PROMETHEUS_PUSHGATEWAY:-http://localhost:9091}"
if command -v curl &> /dev/null; then
    BACKUP_DURATION=$(($(date +%s) - START_TIME))
    cat <<EOF | curl -s --data-binary @- "$PROMETHEUS_PUSHGATEWAY/metrics/job/backup_mongo" > /dev/null 2>&1 || true
# TYPE backup_success_total counter
backup_success_total{database="mongodb"} 1
# TYPE backup_duration_seconds gauge
backup_duration_seconds{database="mongodb"} $BACKUP_DURATION
# TYPE backup_size_bytes gauge
backup_size_bytes{database="mongodb"} $BACKUP_SIZE
EOF
    log "Metrics pushed to Prometheus Pushgateway"
fi

log "MongoDB backup completed successfully"
log "Backup path: $BACKUP_PATH"
log "Log file: $LOG_FILE"

exit 0
