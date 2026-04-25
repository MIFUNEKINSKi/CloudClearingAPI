#!/usr/bin/env python3
"""
CloudClearingAPI Weekly Cron Runner with Email Reporting.

Runs the full Java monitoring analysis and emails the PDF report.
Designed to be run via macOS launchd or cron.

Usage:
    python run_weekly_cron.py              # Full run + email
    python run_weekly_cron.py --test-email  # Send test email only
    python run_weekly_cron.py --no-email    # Run without email

Email Configuration (in .env file):
    GMAIL_ADDRESS=moorecash@gmail.com
    GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
    REPORT_RECIPIENT=moorecash@gmail.com
"""
import sys
import os
import argparse
import smtplib
import json
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.resolve()
os.chdir(PROJECT_ROOT)

# Logging
LOG_FILE = PROJECT_ROOT / "logs" / f"cron_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
LOG_FILE.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('weekly_cron')


def load_env():
    """Load environment variables from .env file."""
    env_file = PROJECT_ROOT / '.env'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())


def find_latest_output():
    """Find the most recent monitoring JSON and PDF report."""
    monitoring_dir = PROJECT_ROOT / 'output' / 'monitoring'
    reports_dir = PROJECT_ROOT / 'output' / 'reports'
    
    json_files = sorted(monitoring_dir.glob('weekly_monitoring_*.json'), reverse=True)
    pdf_files = sorted(reports_dir.glob('executive_summary_*.pdf'), reverse=True)
    
    latest_json = json_files[0] if json_files else None
    latest_pdf = pdf_files[0] if pdf_files else None
    
    return latest_json, latest_pdf


def extract_summary(json_path):
    """Extract key stats from the monitoring JSON for the email body."""
    try:
        with open(json_path) as f:
            data = json.load(f)
        
        summary = data.get('summary', {})
        analysis = data.get('yogyakarta_analysis', data.get('investment_analysis', {}).get('yogyakarta_analysis', {}))
        
        regions_analyzed = summary.get('regions_monitored', len(data.get('regions_analyzed', [])))
        total_changes = summary.get('total_changes', 0)
        total_area = summary.get('total_area_hectares', 0)
        
        buy_recs = analysis.get('buy_recommendations', [])
        watch_list = analysis.get('watch_list', [])
        pass_list = analysis.get('pass_list', [])
        
        alerts = summary.get('alert_summary', {})
        
        # Build summary text
        lines = [
            f"📊 CloudClearingAPI Weekly Report — {datetime.now().strftime('%B %d, %Y')}",
            f"",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"",
            f"OVERVIEW",
            f"  Regions Analyzed: {regions_analyzed}",
            f"  Total Changes Detected: {total_changes:,}",
            f"  Total Area Changed: {total_area:,.1f} hectares",
            f"  Critical Alerts: {alerts.get('critical', 0)}",
            f"",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"",
            f"RECOMMENDATIONS",
            f"  ✅ BUY:   {len(buy_recs)} regions",
            f"  ⚠️  WATCH: {len(watch_list)} regions",
            f"  🔴 PASS:  {len(pass_list)} regions",
            f"",
        ]
        
        if buy_recs:
            lines.append("TOP BUY RECOMMENDATIONS:")
            for rec in buy_recs[:5]:
                name = rec.get('region', 'Unknown')
                score = rec.get('investment_score', 0)
                changes = rec.get('satellite_changes', 0)
                rationale = rec.get('rationale', '')
                lines.append(f"  • {name}: {score:.1f}/100 ({changes:,} changes)")
                if rationale:
                    lines.append(f"    {rationale}")
            lines.append("")
        
        lines.extend([
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            "Full PDF report attached.",
            "",
            "— CloudClearingAPI Automated Report",
        ])
        
        return '\n'.join(lines)
        
    except Exception as e:
        logger.warning(f"Could not extract summary: {e}")
        return f"CloudClearingAPI weekly monitoring completed on {datetime.now().strftime('%B %d, %Y')}.\n\nSee attached PDF report for details."


def send_email(subject, body, pdf_path=None, test=False):
    """Send email via Gmail SMTP with optional PDF attachment."""
    gmail_address = os.environ.get('GMAIL_ADDRESS', 'moorecash@gmail.com')
    gmail_password = os.environ.get('GMAIL_APP_PASSWORD', '')
    recipient = os.environ.get('REPORT_RECIPIENT', 'moorecash@gmail.com')
    
    if not gmail_password:
        logger.error("❌ GMAIL_APP_PASSWORD not set in .env file!")
        logger.error("   Generate one at: https://myaccount.google.com/apppasswords")
        logger.error("   Add to .env: GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx")
        return False
    
    msg = MIMEMultipart()
    msg['From'] = gmail_address
    msg['To'] = recipient
    msg['Subject'] = subject
    
    msg.attach(MIMEText(body, 'plain'))
    
    # Attach PDF if available
    if pdf_path and Path(pdf_path).exists():
        with open(pdf_path, 'rb') as f:
            pdf_attachment = MIMEApplication(f.read(), _subtype='pdf')
            pdf_attachment.add_header(
                'Content-Disposition', 'attachment',
                filename=Path(pdf_path).name
            )
            msg.attach(pdf_attachment)
        logger.info(f"📎 Attached PDF: {Path(pdf_path).name}")
    
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(gmail_address, gmail_password)
            server.send_message(msg)
        logger.info(f"✅ Email sent to {recipient}")
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("❌ Gmail authentication failed!")
        logger.error("   Make sure you're using an App Password, not your regular password.")
        logger.error("   Generate one at: https://myaccount.google.com/apppasswords")
        return False
    except Exception as e:
        logger.error(f"❌ Email failed: {e}")
        return False


def run_monitoring():
    """Run the full monitoring analysis."""
    logger.info("🚀 Starting CloudClearingAPI weekly monitoring run...")
    
    # Monkey-patch input() to auto-confirm
    import builtins
    builtins.input = lambda *args, **kwargs: 'yes'
    
    sys.path.insert(0, str(PROJECT_ROOT))
    
    try:
        from run_weekly_java_monitor import main
        import asyncio
        # Pass all_regions=True so we monitor the full 65-region set
        # (Java + Sumatra + Bali/Lombok/NTT + Eastern), matching the old
        # crontab invocation `run_weekly_java_monitor.py --all --yes`.
        # Without this, main() defaults to all_regions=False → only 31 regions.
        asyncio.run(main(all_regions=True, auto_confirm=True))
        logger.info("✅ Monitoring run completed successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Monitoring run failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    parser = argparse.ArgumentParser(description='CloudClearingAPI Weekly Cron Runner')
    parser.add_argument('--test-email', action='store_true', help='Send test email only')
    parser.add_argument('--no-email', action='store_true', help='Run monitoring without sending email')
    args = parser.parse_args()
    
    load_env()
    
    if args.test_email:
        logger.info("📧 Sending test email...")
        success = send_email(
            subject=f"CloudClearingAPI Test Email — {datetime.now().strftime('%B %d, %Y')}",
            body="This is a test email from CloudClearingAPI.\n\nIf you received this, your email configuration is working correctly! ✅",
            test=True
        )
        sys.exit(0 if success else 1)
    
    # Run the monitoring
    run_success = run_monitoring()
    
    if not args.no_email:
        # Find output files
        latest_json, latest_pdf = find_latest_output()
        
        if latest_json:
            body = extract_summary(latest_json)
        else:
            body = f"Monitoring run {'completed' if run_success else 'FAILED'} on {datetime.now().strftime('%B %d, %Y')}."
        
        if not run_success:
            body = f"⚠️ MONITORING RUN ENCOUNTERED ERRORS\n\nCheck log: {LOG_FILE}\n\n{body}"
        
        send_email(
            subject=f"CloudClearingAPI Weekly Report — {datetime.now().strftime('%B %d, %Y')}",
            body=body,
            pdf_path=latest_pdf
        )
    
    sys.exit(0 if run_success else 1)


if __name__ == '__main__':
    main()
