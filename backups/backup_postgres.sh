#!/bin/bash
# PostgreSQL Backup Script for Lumenly
# This script creates a logical backup of PostgreSQL using pg_dump

set -e  # Exit on error

# Configuration
BACKUP_DIR="/Users/mohsenrassam/Desktop/Lumenly/backups/postgres"
LOG_DIR="/Users/mohsenrassam/Desktop/Lumenly/backups/logs"
LOG_FILE="$LOG_DIR/postgres_backup_$(date +%Y%m%d_%H%M%S).log"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/lumenly_postgres_$TIMESTAMP.dump"
START_TIME=$(date +%s)

# Database configuration (read from environment or use defaults)
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5433}"
POSTGRES_USER="${POSTGRES_USER:-lumenly}"
POSTGRES_DB="${POSTGRES_DB:-lumenly}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-lumenly_secure_password_32chars}"

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
        cat <<EOF | curl -s --data-binary @- "$PROMETHEUS_PUSHGATEWAY/metrics/job/backup_postgres" > /dev/null 2>&1 || true
# TYPE backup_failure_total counter
backup_failure_total{database="postgresql"} 1
EOF
    fi
    exit 1
}

# Verify backup directory exists
if [ ! -d "$BACKUP_DIR" ]; then
    error_exit "Backup directory $BACKUP_DIR does not exist"
fi

log "Starting PostgreSQL backup"
log "Database: $POSTGRES_DB"
log "Host: $POSTGRES_HOST:$POSTGRES_PORT"
log "Backup file: $BACKUP_FILE"

# Set PGPASSWORD for pg_dump (avoid passing password in command line)
export PGPASSWORD="$POSTGRES_PASSWORD"

# Perform backup using pg_dump
log "Running pg_dump..."
if pg_dump -h "$POSTGRES_HOST" \
           -p "$POSTGRES_PORT" \
           -U "$POSTGRES_USER" \
           -d "$POSTGRES_DB" \
           -F c \
           -f "$BACKUP_FILE" \
           -v \
           >> "$LOG_FILE" 2>&1; then
    log "pg_dump completed successfully"
else
    error_exit "pg_dump failed. Check log file: $LOG_FILE"
fi

# Unset PGPASSWORD for security
unset PGPASSWORD

# Verify backup file exists and is non-zero
if [ ! -f "$BACKUP_FILE" ]; then
    error_exit "Backup file was not created: $BACKUP_FILE"
fi

BACKUP_SIZE=$(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE" 2>/dev/null)
if [ "$BACKUP_SIZE" -eq 0 ]; then
    error_exit "Backup file is empty: $BACKUP_FILE"
fi

log "Backup file created successfully"
log "Backup size: $BACKUP_SIZE bytes"

# Verify backup integrity by listing contents
log "Verifying backup integrity..."
if pg_restore -l "$BACKUP_FILE" > /dev/null 2>&1; then
    log "Backup integrity verified"
else
    error_exit "Backup integrity check failed"
fi

# Set appropriate permissions
chmod 600 "$BACKUP_FILE"
log "Backup file permissions set to 600"

# Cleanup old backups (retention policy)
log "Applying retention policy..."

# Clean up daily backups older than DAILY_RETENTION_DAYS
find "$BACKUP_DIR" -name "lumenly_postgres_*.dump" -type f -mtime +$DAILY_RETENTION_DAYS -delete
log "Cleaned up daily backups older than $DAILY_RETENTION_DAYS days"

# Note: Weekly and monthly retention would require more sophisticated logic
# For now, we keep all backups within the daily retention window

# Count remaining backups
BACKUP_COUNT=$(find "$BACKUP_DIR" -name "lumenly_postgres_*.dump" -type f | wc -l)
log "Remaining backups: $BACKUP_COUNT"

# Push metrics to Prometheus Pushgateway (if available)
PROMETHEUS_PUSHGATEWAY="${PROMETHEUS_PUSHGATEWAY:-http://localhost:9091}"
if command -v curl &> /dev/null; then
    BACKUP_DURATION=$(($(date +%s) - START_TIME))
    cat <<EOF | curl -s --data-binary @- "$PROMETHEUS_PUSHGATEWAY/metrics/job/backup_postgres" > /dev/null 2>&1 || true
# TYPE backup_success_total counter
backup_success_total{database="postgresql"} 1
# TYPE backup_duration_seconds gauge
backup_duration_seconds{database="postgresql"} $BACKUP_DURATION
# TYPE backup_size_bytes gauge
backup_size_bytes{database="postgresql"} $BACKUP_SIZE
EOF
    log "Metrics pushed to Prometheus Pushgateway"
fi

log "PostgreSQL backup completed successfully"
log "Backup file: $BACKUP_FILE"
log "Log file: $LOG_FILE"

exit 0
