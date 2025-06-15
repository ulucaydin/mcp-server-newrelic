#!/bin/bash

# Script to update Track 2 progress after task completion
# Usage: ./scripts/update-progress.sh <task-id> [notes]

set -e

PROGRESS_FILE="docs/TRACK2_PROGRESS.md"
IMPL_LOG="docs/IMPLEMENTATION_LOG.md"
TODO_FILE=".track2-todo.json"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if task ID provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: Please provide a task ID${NC}"
    echo "Usage: $0 <task-id> [notes]"
    exit 1
fi

TASK_ID=$1
NOTES=${2:-""}
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

# Function to update progress
update_progress() {
    echo -e "${YELLOW}Updating progress for task: $TASK_ID${NC}"
    
    # Add completion entry
    echo "" >> $PROGRESS_FILE
    echo "### $TIMESTAMP - Task Complete" >> $PROGRESS_FILE
    echo "- ✅ Completed: $TASK_ID" >> $PROGRESS_FILE
    if [ ! -z "$NOTES" ]; then
        echo "- Notes: $NOTES" >> $PROGRESS_FILE
    fi
    
    # Commit changes
    git add $PROGRESS_FILE $IMPL_LOG
    git commit -m "chore: complete task $TASK_ID

- Task: $TASK_ID
- Timestamp: $TIMESTAMP
- Notes: $NOTES"
    
    echo -e "${GREEN}✅ Progress updated and committed!${NC}"
}

# Function to show current todos
show_todos() {
    echo -e "${YELLOW}Current Todo List:${NC}"
    echo "-------------------"
    grep "⬜" $PROGRESS_FILE | head -10 || echo "No pending tasks found"
}

# Function to calculate progress
calculate_progress() {
    TOTAL=$(grep -c "✅\|⬜" $PROGRESS_FILE || echo 0)
    COMPLETE=$(grep -c "✅" $PROGRESS_FILE || echo 0)
    
    if [ $TOTAL -gt 0 ]; then
        PERCENT=$((COMPLETE * 100 / TOTAL))
        echo -e "${GREEN}Progress: $COMPLETE/$TOTAL ($PERCENT%)${NC}"
    fi
}

# Main execution
echo "Track 2 Progress Updater"
echo "========================"

# Update progress
update_progress

# Show updated stats
echo ""
calculate_progress
echo ""
show_todos

echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "1. Update test coverage if applicable"
echo "2. Update documentation if needed"
echo "3. Start next task from the todo list"