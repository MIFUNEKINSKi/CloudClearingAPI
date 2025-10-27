#!/bin/bash
# Quick monitoring status checker

echo "=================================="
echo "📊 MONITORING STATUS CHECK"
echo "=================================="
echo ""

# Check if process is running
RUNNING=$(ps aux | grep "run_weekly_java_monitor" | grep -v grep | wc -l)
if [ $RUNNING -gt 0 ]; then
    echo "✅ Monitoring is RUNNING"
    echo "   Process IDs: $(ps aux | grep 'run_weekly_java_monitor' | grep -v grep | awk '{print $2}' | tr '\n' ', ' | sed 's/,$//')"
else
    echo "❌ Monitoring is NOT running"
fi

echo ""
echo "⏰ Timeline:"
START_TIME="21:36"
CURRENT=$(date +"%H:%M")
END_TIME="23:03"
echo "   Started:    $START_TIME (9:36 PM)"
echo "   Current:    $CURRENT"
echo "   Expected:   $END_TIME (11:03 PM)"

# Calculate minutes elapsed
START_MIN=$((21*60 + 36))
CURRENT_MIN=$(date +"%H*60 + %M" | bc)
ELAPSED=$((CURRENT_MIN - START_MIN))
REMAINING=$((87 - ELAPSED))

if [ $ELAPSED -lt 0 ]; then
    echo "   Status: Waiting to start or clock adjustment"
elif [ $ELAPSED -lt 87 ]; then
    PERCENT=$((ELAPSED * 100 / 87))
    echo "   Progress:   ~$ELAPSED minutes / 87 minutes ($PERCENT%)"
    echo "   Remaining:  ~$REMAINING minutes"
else
    echo "   Status: Should be complete! Checking outputs..."
fi

echo ""
echo "📁 Latest Output Files:"
LATEST_JSON=$(ls -t output/monitoring/weekly_monitoring_*.json 2>/dev/null | head -1)
LATEST_PDF=$(ls -t output/reports/executive_summary_*.pdf 2>/dev/null | head -1)

if [ -n "$LATEST_JSON" ]; then
    JSON_TIME=$(stat -f "%Sm" -t "%H:%M" "$LATEST_JSON")
    JSON_NAME=$(basename "$LATEST_JSON")
    echo "   Latest JSON: $JSON_NAME ($JSON_TIME)"
else
    echo "   Latest JSON: None found"
fi

if [ -n "$LATEST_PDF" ]; then
    PDF_TIME=$(stat -f "%Sm" -t "%H:%M" "$LATEST_PDF")
    PDF_NAME=$(basename "$LATEST_PDF")
    echo "   Latest PDF:  $PDF_NAME ($PDF_TIME)"
else
    echo "   Latest PDF:  None found"
fi

echo ""
echo "=================================="
echo "Run this script again to check progress:"
echo "  ./check_monitoring_status.sh"
echo "=================================="
