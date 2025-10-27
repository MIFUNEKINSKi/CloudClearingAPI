#!/bin/bash
# Monitor the progress of the weekly monitoring run

echo "🔍 CloudClearingAPI - Weekly Monitoring Progress"
echo "================================================"
echo ""

# Check if process is running
if ps aux | grep -v grep | grep "run_weekly_monitor.py" > /dev/null; then
    echo "✅ Process is RUNNING"
    echo ""
else
    echo "❌ Process is NOT running"
    echo ""
fi

# Count completed regions
completed=$(grep -c "Successfully analyzed using" full_corrected_run_java.log 2>/dev/null || echo "0")
echo "📊 Regions Completed: $completed"

# Show last few log lines
echo ""
echo "📋 Recent Activity:"
echo "-------------------"
tail -15 full_corrected_run_java.log 2>/dev/null || echo "Log file not found"

echo ""
echo "To watch live: tail -f full_corrected_run_java.log"
