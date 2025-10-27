#!/bin/bash
# Quick progress checker for Java-wide monitoring

echo "======================================"
echo "Java-Wide Monitoring Progress Tracker"
echo "======================================"
echo ""

# Find the most recent log file
LOGFILE=$(ls -t java_monitoring_run_*.log 2>/dev/null | head -1)

if [ -z "$LOGFILE" ]; then
    echo "❌ No monitoring log file found!"
    exit 1
fi

echo "📄 Log file: $LOGFILE"
echo ""

# Check if process is still running
if pgrep -f "run_weekly_java_monitor" > /dev/null; then
    echo "✅ Monitoring process: RUNNING"
else
    echo "⚠️  Monitoring process: STOPPED"
fi
echo ""

# Count regions analyzed
TOTAL_REGIONS=29
ANALYZED=$(grep -c "Successfully analyzed" "$LOGFILE" 2>/dev/null || echo "0")
CURRENT=$(grep "🔍 Analyzing" "$LOGFILE" 2>/dev/null | tail -1 | sed 's/.*region: //')

echo "📊 Progress: $ANALYZED/$TOTAL_REGIONS regions completed"
if [ ! -z "$CURRENT" ]; then
    echo "🔄 Currently analyzing: $CURRENT"
fi
echo ""

# Show recent activity
echo "📝 Recent activity (last 5 lines):"
echo "-----------------------------------"
tail -5 "$LOGFILE" | sed 's/^/   /'
echo ""

# Check for errors
ERROR_COUNT=$(grep -c "ERROR" "$LOGFILE" 2>/dev/null || echo "0")
WARNING_COUNT=$(grep -c "WARNING" "$LOGFILE" 2>/dev/null || echo "0")

echo "⚠️  Errors: $ERROR_COUNT | Warnings: $WARNING_COUNT"
echo ""

# Estimate time remaining
if [ "$ANALYZED" -gt 0 ]; then
    START_TIME=$(grep "START TIME" "$LOGFILE" | grep -oE "[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}")
    if [ ! -z "$START_TIME" ]; then
        START_EPOCH=$(date -j -f "%Y-%m-%d %H:%M:%S" "$START_TIME" "+%s" 2>/dev/null)
        NOW_EPOCH=$(date "+%s")
        ELAPSED=$((NOW_EPOCH - START_EPOCH))
        AVG_TIME=$((ELAPSED / ANALYZED))
        REMAINING=$((TOTAL_REGIONS - ANALYZED))
        ETA_SECONDS=$((REMAINING * AVG_TIME))
        ETA_MINUTES=$((ETA_SECONDS / 60))
        
        echo "⏱️  Elapsed: $((ELAPSED / 60)) minutes"
        echo "⏱️  Estimated remaining: ~$ETA_MINUTES minutes"
    fi
fi

echo ""
echo "======================================"
echo "To watch live: tail -f $LOGFILE"
echo "======================================"
