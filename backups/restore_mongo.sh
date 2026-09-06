#!/bin/bash
# MongoDB Restore Script for Lumenly
# This script restores a MongoDB database from a mongodump backup

set -e  # Exit on error

# Configuration
BACKUP_DIR="/Users/mohsenrassam/Desktop/Lumenly/backups/mongo"
LOG_DIR="/Users/mohsenrassam/Desktop/Lumenly/backups/logs"
LOG_FILE="$LOG_DIR/mongo_restore_$(date +%Y%m%d_%H%M%S).log"

# Database configuration
MONGO_HOST="${MONGO_HOST:-localhost}"
MONGO_PORT="${MONGO_PORT:-27017}"
MONGO_DB="${MONGO_DB:-lumenly}"

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

# Check if backup path is provided
if [ $# -eq 0 ]; then
    error_exit "Usage: $0 <backup_path> [--force]"
fi

BACKUP_PATH="$1"

# Check for force flag
if [ "$2" = "--force" ]; then
    FORCE_RESTORE=true
fi

# Verify backup path exists
if [ ! -d "$BACKUP_PATH" ]; then
    error_exit "Backup path not found: $BACKUP_PATH"
fi

# Verify database directory exists within backup
if [ ! -d "$BACKUP_PATH/$MONGO_DB" ]; then
    error_exit "Database directory not found in backup: $BACKUP_PATH/$MONGO_DB"
fi

log "Starting MongoDB restore"
log "Backup path: $BACKUP_PATH"
log "Database: $MONGO_DB"
log "Host: $MONGO_HOST:$MONGO_PORT"
log "Force restore: $FORCE_RESTORE"

# Safety check: confirm restore unless forced
if [ "$FORCE_RESTORE" != "true" ]; then
    log "WARNING: This will DROP and RECREATE the database '$MONGO_DB'"
    log "Current data will be LOST"
    read -p "Are you sure you want to proceed? (yes/no): " confirmation
    if [ "$confirmation" != "yes" ]; then
        log "Restore cancelled by user"
        exit 0
    fi
fi

# Drop existing database (if it exists)
log "Dropping existing database (if exists)..."
if mongosh --host "$MONGO_HOST" \
           --port "$MONGO_PORT" \
           --eval "db.getSiblingDB('$MONGO_DB').dropDatabase()" \
           >> "$LOG_FILE" 2>&1; then
    log "Database dropped successfully"
else
    log "Database may not exist or drop failed (continuing)"
fi

# Restore from backup
log "Restoring from backup..."
if mongorestore --host "$MONGO_HOST" \
                --port "$MONGO_PORT" \
                --db "$MONGO_DB" \
                "$BACKUP_PATH/$MONGO_DB" \
                >> "$LOG_FILE" 2>&1; then
    log "Restore completed successfully"
else
    error_exit "Restore failed. Check log file: $LOG_FILE"
fi

# Verify restore by checking collections exist
log "Verifying restore..."
COLLECTION_COUNT=$(mongosh --host "$MONGO_HOST" \
                         --port "$MONGO_PORT" \
                         --eval "db.getSiblingDB('$MONGO_DB').getCollectionNames().length" \
                         --quiet \
                         2>/dev/null || echo "0")

if [ "$COLLECTION_COUNT" -eq 0 ]; then
    error_exit "Restore verification failed: No collections found in database"
fi

log "Restore verification successful"
log "Collections restored: $COLLECTION_COUNT"

# Verify critical collections exist
CRITICAL_COLLECTIONS=("journal_entries" "goals" "habits" "user_documents" "compliance_events")
for collection in "${CRITICAL_COLLECTIONS[@]}"; do
    if mongosh --host "$MONGO_HOST" \
               --port "$MONGO_PORT" \
               --eval "db.getSiblingDB('$MONGO_DB').$collection.countDocuments()" \
               --quiet \
               >> "$LOG_FILE" 2>&1; then
        log "Collection '$collection' verified"
    else
        log "WARNING: Collection '$collection' not found"
    fi
done

# Verify user_documents have user_id references (tenant isolation check)
log "Verifying tenant isolation (user_id references)..."
DOC_COUNT=$(mongosh --host "$MONGO_HOST" \
                   --port "$MONGO_PORT" \
                   --eval "db.getSiblingDB('$MONGO_DB').user_documents.countDocuments({user_id: {\$exists: true}})" \
                   --quiet \
                   2>/dev/null || echo "0")

TOTAL_DOCS=$(mongosh --host "$MONGO_HOST" \
                     --port "$MONGO_PORT" \
                     --eval "db.getSiblingDB('$MONGO_DB').user_documents.countDocuments()" \
                     --quiet \
                     2>/dev/null || echo "0")

if [ "$DOC_COUNT" -eq "$TOTAL_DOCS" ] && [ "$TOTAL_DOCS" -gt 0 ]; then
    log "Tenant isolation verified: All user_documents have user_id"
elif [ "$TOTAL_DOCS" -eq 0 ]; then
    log "No user_documents found (empty database)"
else
    log "WARNING: Some user_documents missing user_id"
fi

log "MongoDB restore completed successfully"
log "Log file: $LOG_FILE"

exit 0
