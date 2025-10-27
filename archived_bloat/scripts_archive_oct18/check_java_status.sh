#!/bin/bash
# Quick status checker for Java-wide monitoring

echo "======================================"
echo "Java-Wide Monitoring Status"
echo "======================================"
echo ""

# Check if process is running
if pgrep -f "run_weekly_java_monitor.py" > /dev/null; then
    echo "✅ STATUS: RUNNING"
    
    # Show latest log file
    LATEST_LOG=$(ls -t logs/java_weekly_*.log 2>/dev/null | head -1)
    
    if [ -n "$LATEST_LOG" ]; then
        echo "📁 Log File: $LATEST_LOG"
        echo ""
        echo "📊 Recent Activity (last 10 lines):"
        echo "--------------------------------------"
        tail -10 "$LATEST_LOG"
        echo ""
        echo "--------------------------------------"
        echo ""
        echo "💡 To view live progress: tail -f $LATEST_LOG"
    fi
    
    # Count regions processed (heuristic)
    if [ -n "$LATEST_LOG" ]; then
        ANALYZED=$(grep -c "Successfully analyzed" "$LATEST_LOG" 2>/dev/null || echo "0")
        echo "📈 Regions Analyzed So Far: ~$ANALYZED/29"
    fi
    
else
    echo "⏸️  STATUS: NOT RUNNING"
    echo ""
    echo "Check logs/java_weekly_*.log for results"
    echo ""
    
    # Show most recent completion message
    LATEST_LOG=$(ls -t logs/java_weekly_*.log 2>/dev/null | head -1)
    if [ -n "$LATEST_LOG" ]; then
        if grep -q "COMPLETED" "$LATEST_LOG"; then
            echo "✅ Last run completed successfully!"
        elif grep -q "FAILED" "$LATEST_LOG"; then
            echo "❌ Last run encountered errors"
        fi
    fi
fi

echo ""
echo "======================================"
