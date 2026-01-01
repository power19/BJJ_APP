#!/bin/bash
# Backup script for Invictus BJJ configuration

set -e

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/bjj_backup_$TIMESTAMP.tar.gz"

echo "==================================="
echo "Invictus BJJ Backup Script"
echo "==================================="

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Files to backup
FILES_TO_BACKUP=(
    "config"
    "data"
)

# Check what exists
EXISTING_FILES=""
for file in "${FILES_TO_BACKUP[@]}"; do
    if [ -e "$file" ]; then
        EXISTING_FILES="$EXISTING_FILES $file"
    fi
done

if [ -z "$EXISTING_FILES" ]; then
    echo "No data to backup (config and data directories don't exist yet)"
    exit 0
fi

# Create backup
echo "Creating backup: $BACKUP_FILE"
tar -czf $BACKUP_FILE $EXISTING_FILES

# Show backup info
BACKUP_SIZE=$(du -h $BACKUP_FILE | cut -f1)
echo ""
echo "Backup created successfully!"
echo "  File: $BACKUP_FILE"
echo "  Size: $BACKUP_SIZE"

# Clean old backups (keep last 10)
echo ""
echo "Cleaning old backups (keeping last 10)..."
ls -t $BACKUP_DIR/bjj_backup_*.tar.gz 2>/dev/null | tail -n +11 | xargs -r rm

echo "Done!"
