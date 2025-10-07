#!/usr/bin/env python3
"""
Automated Weekly Monitoring Scheduler
CloudClearingAPI: Scheduled Strategic Corridor Investment Intelligence

This script sets up automated weekly monitoring that can be run via cron job
or scheduled task to generate regular investment intelligence reports.
"""

import asyncio
import logging
from datetime import datetime, timedelta
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from weekly_strategic_monitor import run_weekly_strategic_monitoring

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./logs/weekly_monitoring.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class WeeklyMonitoringScheduler:
    """Handles automated weekly monitoring execution"""
    
    def __init__(self):
        self.execution_log = Path('./logs/execution_log.json')
        self.lock_file = Path('./logs/weekly_monitor.lock')
    
    async def run_scheduled_monitoring(self):
        """Run the scheduled weekly monitoring with proper error handling"""
        
        # Check if another instance is running
        if self.lock_file.exists():
            logger.warning("Another monitoring instance is running. Exiting.")
            return
        
        # Create lock file
        self.lock_file.write_text(str(os.getpid()))
        
        try:
            logger.info("🚀 Starting scheduled weekly strategic monitoring")
            
            # Run the monitoring
            results = await run_weekly_strategic_monitoring()
            
            # Log execution results
            self._log_execution(results, success=True)
            
            # Generate summary for logs
            exec_summary = results.get('executive_summary', {})
            logger.info(f"✅ Weekly monitoring completed successfully")
            logger.info(f"   Market Status: {exec_summary.get('market_status', 'Unknown')}")
            logger.info(f"   High-Conviction Opportunities: {exec_summary.get('key_metrics', {}).get('high_conviction_opportunities', 0)}")
            logger.info(f"   Total Changes: {exec_summary.get('key_metrics', {}).get('total_weekly_changes', 0)}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Weekly monitoring failed: {str(e)}")
            self._log_execution({'error': str(e)}, success=False)
            raise
            
        finally:
            # Remove lock file
            if self.lock_file.exists():
                self.lock_file.unlink()
    
    def _log_execution(self, results: dict, success: bool):
        """Log execution results for tracking"""
        import json
        
        execution_record = {
            'timestamp': datetime.now().isoformat(),
            'success': success,
            'results_summary': {
                'market_status': results.get('executive_summary', {}).get('market_status', 'Unknown'),
                'high_conviction_opportunities': results.get('executive_summary', {}).get('key_metrics', {}).get('high_conviction_opportunities', 0),
                'total_changes': results.get('executive_summary', {}).get('key_metrics', {}).get('total_weekly_changes', 0),
                'critical_alerts': results.get('executive_summary', {}).get('key_metrics', {}).get('critical_alerts', 0)
            } if success else {'error': results.get('error', 'Unknown error')}
        }
        
        # Append to execution log
        log_entries = []
        if self.execution_log.exists():
            try:
                with open(self.execution_log, 'r') as f:
                    log_entries = json.load(f)
            except:
                log_entries = []
        
        log_entries.append(execution_record)
        
        # Keep only last 50 executions
        log_entries = log_entries[-50:]
        
        with open(self.execution_log, 'w') as f:
            json.dump(log_entries, f, indent=2)
    
    def get_execution_history(self) -> list:
        """Get recent execution history"""
        import json
        
        if not self.execution_log.exists():
            return []
        
        try:
            with open(self.execution_log, 'r') as f:
                return json.load(f)
        except:
            return []

def setup_cron_job():
    """Generate cron job command for weekly execution"""
    script_path = Path(__file__).absolute()
    python_path = sys.executable
    
    # Run every Monday at 6 AM
    cron_command = f"0 6 * * 1 cd {project_root} && {python_path} {script_path} > /dev/null 2>&1"
    
    print("📅 To set up automated weekly monitoring, add this to your crontab:")
    print(f"   {cron_command}")
    print()
    print("Commands to set up:")
    print(f"   crontab -e")
    print(f"   # Add the line above")
    print(f"   # Save and exit")
    print()
    print("Or run manually with:")
    print(f"   {python_path} {script_path}")

async def main():
    """Main execution function"""
    scheduler = WeeklyMonitoringScheduler()
    
    # Create logs directory
    Path('./logs').mkdir(exist_ok=True)
    
    if len(sys.argv) > 1 and sys.argv[1] == '--setup-cron':
        setup_cron_job()
        return
    
    if len(sys.argv) > 1 and sys.argv[1] == '--history':
        history = scheduler.get_execution_history()
        print("📊 EXECUTION HISTORY:")
        print("=" * 40)
        for entry in history[-10:]:  # Last 10 executions
            status = "✅" if entry['success'] else "❌"
            timestamp = entry['timestamp'][:19].replace('T', ' ')
            print(f"{status} {timestamp}")
            if entry['success']:
                summary = entry['results_summary']
                print(f"   Market: {summary.get('market_status', 'Unknown')}")
                print(f"   Opportunities: {summary.get('high_conviction_opportunities', 0)}")
                print(f"   Changes: {summary.get('total_changes', 0)}")
            else:
                print(f"   Error: {entry['results_summary'].get('error', 'Unknown')}")
            print()
        return
    
    # Run the monitoring
    await scheduler.run_scheduled_monitoring()

if __name__ == "__main__":
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--help':
            print("🇮🇩 CloudClearingAPI Weekly Strategic Monitoring Scheduler")
            print("=" * 60)
            print("Usage:")
            print("  python weekly_scheduler.py              # Run monitoring now")
            print("  python weekly_scheduler.py --setup-cron # Show cron setup commands")
            print("  python weekly_scheduler.py --history    # Show execution history")
            print("  python weekly_scheduler.py --help       # Show this help")
            sys.exit(0)
    
    # Run the scheduler
    asyncio.run(main())