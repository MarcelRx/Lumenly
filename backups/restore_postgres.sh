#!/bin/bash
# PostgreSQL Restore Script for Lumenly
# This script restores a PostgreSQL database from a pg_dump backup

set -e  # Exit on error

# Configuration
BACKUP_DIR="/Users/mohsenrassam/Desktop/Lumenly/backups/postgres"
LOG_DIR="/Users/mohsenrassam/Desktop/Lumenly/backups/logs"
LOG_FILE="$LOG_DIR/postgres_restore_$(date +%Y%m%d_%H%M%S).log"

# Database configuration
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5433}"
POSTGRES_USER="${POSTGRES_USER:-lumenly}"
POSTGRES_DB="${POSTGRES_DB:-lumenly}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-lumenly_secure_password_32chars}"

# Safety flag
FORCE_RESTORE="${FORCE_RESTORE:-false}"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log "ERROR: $1"
    exit 1
}

# Check if backup file is provided
if [ $# -eq 0 ]; then
    error_exit "Usage: $0 <backup_file.dump> [--force]"
fi

BACKUP_FILE="$1"

# Check for force flag
if [ "$2" = "--force" ]; then
    FORCE_RESTORE=true
fi

# Verify backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    error_exit "Backup file not found: $BACKUP_FILE"
fi

# Verify backup file is a valid PostgreSQL dump
if ! pg_restore -l "$BACKUP_FILE" > /dev/null 2>&1; then
    error_exit "Invalid PostgreSQL backup file: $BACKUP_FILE"
fi

log "Starting PostgreSQL restore"
log "Backup file: $BACKUP_FILE"
log "Database: $POSTGRES_DB"
log "Host: $POSTGRES_HOST:$POSTGRES_PORT"
log "Force restore: $FORCE_RESTORE"

# Safety check: confirm restore unless forced
if [ "$FORCE_RESTORE" != "true" ]; then
    log "WARNING: This will DROP and RECREATE the database '$POSTGRES_DB'"
    log "Current data will be LOST"
    read -p "Are you sure you want to proceed? (yes/no): " confirmation
    if [ "$confirmation" != "yes" ]; then
        log "Restore cancelled by user"
        exit 0
    fi
fi

# Set PGPASSWORD for pg_restore
export PGPASSWORD="$POSTGRES_PASSWORD"

# Drop existing database (if it exists)
log "Dropping existing database (if exists)..."
if psql -h "$POSTGRES_HOST" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_USER" \
        -d postgres \
        -c "DROP DATABASE IF EXISTS $POSTGRES_DB;" \
        >> "$LOG_FILE" 2>&1; then
    log "Database dropped successfully"
else
    error_exit "Failed to drop database. Check log file: $LOG_FILE"
fi

# Create new database
log "Creating new database..."
if psql -h "$POSTGRES_HOST" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_USER" \
        -d postgres \
        -c "CREATE DATABASE $POSTGRES_DB;" \
        >> "$LOG_FILE" 2>&1; then
    log "Database created successfully"
else
    error_exit "Failed to create database. Check log file: $LOG_FILE"
fi

# Restore from backup
log "Restoring from backup..."
if pg_restore -h "$POSTGRES_HOST" \
             -p "$POSTGRES_PORT" \
             -U "$POSTGRES_USER" \
             -d "$POSTGRES_DB" \
             -v \
             "$BACKUP_FILE" \
             >> "$LOG_FILE" 2>&1; then
    log "Restore completed successfully"
else
    error_exit "Restore failed. Check log file: $LOG_FILE"
fi

# Verify restore by checking tables exist
log "Verifying restore..."
export PGPASSWORD="$POSTGRES_PASSWORD"
TABLE_COUNT=$(psql -h "$POSTGRES_HOST" \
                  -p "$POSTGRES_PORT" \
                  -U "$POSTGRES_USER" \
                  -d "$POSTGRES_DB" \
                  -t \
                  -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" \
                  2>/dev/null | xargs || echo "0")

if [ "$TABLE_COUNT" -eq 0 ]; then
    error_exit "Restore verification failed: No tables found in database"
fi

log "Restore verification successful"
log "Tables restored: $TABLE_COUNT"

# Verify users table exists (critical for authentication)
export PGPASSWORD="$POSTGRES_PASSWORD"
if psql -h "$POSTGRES_HOST" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        -c "SELECT 1 FROM users LIMIT 1;" \
        >> "$LOG_FILE" 2>&1; then
    log "Users table verified"
else
    log "WARNING: Users table not found or empty"
fi

# Verify alembic_version table exists (critical for migrations)
if psql -h "$POSTGRES_HOST" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        -c "SELECT 1 FROM alembic_version LIMIT 1;" \
        >> "$LOG_FILE" 2>&1; then
    log "Alembic version table verified"
else
    log "WARNING: Alembic version table not found"
fi

# Unset PGPASSWORD for security
unset PGPASSWORD

log "PostgreSQL restore completed successfully"
log "Log file: $LOG_FILE"

exit 0
