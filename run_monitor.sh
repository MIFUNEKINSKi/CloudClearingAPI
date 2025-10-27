#!/bin/bash
# Wrapper script to run weekly monitoring using virtual environment

# Change to script directory
cd "$(dirname "$0")"

# Activate virtual environment and run monitoring
source venv/bin/activate
python run_weekly_java_monitor.py

# Deactivate when done
deactivate
