#!/usr/bin/env python3
"""
View latest CloudClearing monitoring results
"""

import os
import glob
from pathlib import Path

def show_latest_results():
    """Show the latest monitoring results and available outputs"""
    print("🤖 CloudClearing Monitoring Results")
    print("=" * 50)
    
    # Find latest monitoring files
    monitoring_files = glob.glob("output/monitoring/weekly_monitoring_*.json")
    pdf_files = glob.glob("output/reports/executive_summary_*.pdf")
    html_files = glob.glob("output/imagery_viewer/imagery_viewer_*.html")
    
    if monitoring_files:
        latest_json = max(monitoring_files, key=os.path.getctime)
        print(f"📁 Latest JSON Data: {latest_json}")
    else:
        print("📁 No monitoring data found")
        return
    
    if pdf_files:
        latest_pdf = max(pdf_files, key=os.path.getctime)
        print(f"📄 Latest PDF Report: {latest_pdf}")
    else:
        print("📄 No PDF reports found")
    
    if html_files:
        latest_html = max(html_files, key=os.path.getctime)
        print(f"🌐 Latest Imagery Viewer: {latest_html}")
    else:
        print("🌐 No imagery viewers found")
    
    print("\n🚀 Quick Actions:")
    if pdf_files:
        print(f"   Open PDF Report: open '{max(pdf_files, key=os.path.getctime)}'")
    if html_files:
        print(f"   Open Imagery Viewer: open '{max(html_files, key=os.path.getctime)}'")
    
    print("\n📊 Generate Reports from Latest Data:")
    print(f"   PDF Report: python generate_pdf_report.py {latest_json}")
    print(f"   HTML Imagery Viewer: python generate_imagery_viewer.py {latest_json}")
    print(f"   🛰️ Cached Imagery Viewer: python generate_cached_imagery.py {latest_json}")
    
    print("\n🔄 Run New Analysis:")
    print("   Weekly Monitor: python run_weekly_monitor.py")
    
    print("\n💡 Tips:")
    print("   • Use cached imagery viewer for authentic satellite images")
    print("   • HTML viewer shows authentication-protected URLs")
    print("   • PDF report is best for executive summaries")

if __name__ == "__main__":
    show_latest_results()