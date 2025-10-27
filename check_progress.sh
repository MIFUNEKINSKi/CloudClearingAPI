#!/bin/bash#!/bin/bash

# Quick monitoring progress checker# Monitor the progress of the weekly monitoring run



echo "📊 CloudClearing Monitoring Progress"echo "🔍 CloudClearingAPI - Weekly Monitoring Progress"

echo "======================================"echo "================================================"

echo ""echo ""



# Check if process is running# Check if process is running

if ps aux | grep -E "python.*run_.*monitor" | grep -v grep > /dev/null; thenif ps aux | grep -v grep | grep "run_weekly_monitor.py" > /dev/null; then

    echo "✅ Status: RUNNING"    echo "✅ Process is RUNNING"

else    echo ""

    echo "❌ Status: NOT RUNNING"else

fi    echo "❌ Process is NOT running"

    echo ""

echo ""fi

echo "📈 Latest Progress (last 10 lines):"

tail -10 monitoring_output.log 2>/dev/null || echo "No log file yet"# Count completed regions

completed=$(grep -c "Successfully analyzed using" full_corrected_run_java.log 2>/dev/null || echo "0")

echo ""echo "📊 Regions Completed: $completed"

echo "🕐 To watch live: tail -f monitoring_output.log"

echo "📁 To check for output: ls -lt output/monitoring/*.json | head -1"# Show last few log lines

echo ""
echo "📋 Recent Activity:"
echo "-------------------"
tail -15 full_corrected_run_java.log 2>/dev/null || echo "Log file not found"

echo ""
echo "To watch live: tail -f full_corrected_run_java.log"
