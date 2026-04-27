#!/usr/bin/env python3
"""
Weekly Java-Wide Monitor - Async Parallel Processing
Monitors all 29 regions across Java island for development changes

Features:
- Async parallel processing (5 regions at a time to respect GEE rate limits)
- GEE + OSM caching for performance
- Progress tracking with real-time updates
- Graceful error handling per region

Expected Runtime: ~30-35 minutes for all 29 regions (with warm cache)
"""

import sys
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Setup comprehensive logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/java_weekly_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


async def process_region_batch(
    monitor,
    regions: List[str],
    week_a_start: str,
    week_b_start: str,
    batch_num: int,
    total_batches: int
) -> List[Dict[str, Any]]:
    """
    Process a batch of regions in parallel.
    
    Args:
        monitor: AutomatedMonitor instance
        regions: List of region names to process
        week_a_start: Start date for week A
        week_b_start: Start date for week B
        batch_num: Current batch number (1-indexed)
        total_batches: Total number of batches
    
    Returns:
        List of analysis results (successful regions only)
    """
    print(f"\n📦 Batch {batch_num}/{total_batches}: Processing {len(regions)} regions in parallel...")
    
    # Create async tasks for each region
    tasks = []
    for region_name in regions:
        task = monitor._analyze_region(region_name, week_a_start, week_b_start)
        tasks.append(task)
    
    # Execute all tasks in parallel and gather results
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results and handle errors
    successful_results = []
    for region_name, result in zip(regions, results):
        if isinstance(result, Exception):
            logger.error(f"   ❌ {region_name}: {str(result)}")
        elif result is None:
            logger.warning(f"   ⚠️  {region_name}: No data available")
        else:
            # Result is a dict - check if cached
            cache_status = "🔵 CACHED" if result.get('_cached') else "🟢 FRESH"  # type: ignore
            logger.info(f"   ✅ {region_name}: {result['change_count']:,} changes ({cache_status})")  # type: ignore
            result['analysis_type'] = 'yogyakarta_region'  # type: ignore
            successful_results.append(result)
    
    return successful_results


async def run_parallel_monitoring(
    monitor,
    regions: List[str],
    week_a_start: str,
    week_b_start: str,
    batch_size: int = 5
) -> List[Dict[str, Any]]:
    """
    Process all regions in parallel batches.
    
    Args:
        monitor: AutomatedMonitor instance
        regions: List of all region names
        week_a_start: Start date for week A
        week_b_start: Start date for week B
        batch_size: Number of regions to process in parallel (default 5 for GEE rate limits)
    
    Returns:
        List of all successful analysis results
    """
    all_results = []
    total_regions = len(regions)
    
    # Split regions into batches
    batches = [regions[i:i + batch_size] for i in range(0, total_regions, batch_size)]
    total_batches = len(batches)
    
    logger.info(f"🚀 Parallel processing: {total_regions} regions in {total_batches} batches of {batch_size}")
    
    # Process each batch
    batch_start_time = datetime.now()
    for batch_num, batch in enumerate(batches, 1):
        batch_results = await process_region_batch(
            monitor, batch, week_a_start, week_b_start, batch_num, total_batches
        )
        all_results.extend(batch_results)
        
        # Show progress
        completed = len(all_results)
        progress_pct = (completed / total_regions) * 100
        elapsed = (datetime.now() - batch_start_time).total_seconds() / 60
        
        # Estimate remaining time
        if completed > 0:
            avg_time_per_region = elapsed / completed
            remaining_regions = total_regions - completed
            eta_minutes = avg_time_per_region * remaining_regions
            
            print(f"\n📊 Progress: {completed}/{total_regions} regions ({progress_pct:.1f}%)")
            print(f"   ⏱️  Elapsed: {elapsed:.1f} min | ETA: {eta_minutes:.1f} min remaining")
        
        # Small delay between batches to be respectful to APIs
        if batch_num < total_batches:
            await asyncio.sleep(2)
    
    return all_results


def _load_env_from_file() -> None:
    """Load .env into os.environ. Uses assignment (not setdefault) so a stale
    value in the parent shell can't shadow a freshly-rotated credential."""
    import os
    env_file = Path('.env')
    if not env_file.exists():
        return
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()


def _smtp_preflight() -> tuple[bool, str]:
    """Try an SMTP login without sending anything. Returns (ok, reason).

    Run at the start of the weekly pipeline so an auth failure surfaces in
    the first few seconds of the log instead of after a 30-minute pipeline.
    """
    import os
    import smtplib
    _load_env_from_file()
    address = os.environ.get('GMAIL_ADDRESS', '')
    password = os.environ.get('GMAIL_APP_PASSWORD', '')
    if not address or not password:
        return False, 'GMAIL_ADDRESS or GMAIL_APP_PASSWORD missing in .env'
    pwd_compact = password.replace(' ', '')
    if not (len(pwd_compact) == 16 and pwd_compact.isalpha() and pwd_compact.islower()):
        return False, (
            f'GMAIL_APP_PASSWORD does not look like a Google App Password '
            f'({len(pwd_compact)} chars; expected 16 lowercase letters). '
            'Generate one at https://myaccount.google.com/apppasswords'
        )
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=15) as server:
            server.login(address, password)
        return True, 'ok'
    except smtplib.SMTPAuthenticationError as e:
        return False, f'SMTP auth rejected: {e.smtp_code} {e.smtp_error!r}'
    except Exception as e:
        return False, f'SMTP error: {type(e).__name__}: {e}'


def _send_webhook_alert(subject: str, body: str, json_path: str = None) -> bool:
    """Post the briefing to WEBHOOK_URL (Slack-compatible) when email fails.

    Without this fallback a broken email silently hides every BUY signal —
    defeats the whole purpose of running the pipeline.
    """
    import os
    import json as _json
    import urllib.request
    _load_env_from_file()
    webhook_url = os.environ.get('WEBHOOK_URL', '')
    if not webhook_url or 'YOUR/SLACK/WEBHOOK' in webhook_url:
        logger.warning('WEBHOOK_URL not configured — cannot fall back from email')
        return False
    # Slack messages cap around 40k chars; trim aggressively
    trimmed_body = body if len(body) < 35000 else body[:35000] + '\n\n…(truncated)'
    payload = {
        'text': f'*{subject}*\n```\n{trimmed_body}\n```',
        'attachments': [{
            'color': '#ff8800',
            'text': f'Email delivery failed — JSON output: `{json_path}`' if json_path else 'Email delivery failed',
        }],
    }
    try:
        req = urllib.request.Request(
            webhook_url,
            data=_json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            ok = 200 <= resp.status < 300
            if ok:
                logger.info(f'Webhook fallback delivered ({resp.status})')
            else:
                logger.error(f'Webhook returned HTTP {resp.status}')
            return ok
    except Exception as e:
        logger.error(f'Webhook delivery failed: {type(e).__name__}: {e}')
        return False


def _send_report_email(json_path: str, pdf_path: str = None) -> bool:
    """Send email report after a successful monitoring run.

    Requires GMAIL_APP_PASSWORD in .env file.
    Returns True if email was sent, False otherwise.

    On failure, automatically posts a webhook fallback (Slack-compatible)
    so the briefing isn't lost. Subject is tagged [LOW-CONF] when more than
    20 % of regions ended up on benchmark/fallback data.
    """
    import os
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.application import MIMEApplication

    _load_env_from_file()

    gmail_address = os.environ.get('GMAIL_ADDRESS', 'moorecash@gmail.com')
    gmail_password = os.environ.get('GMAIL_APP_PASSWORD', '')
    recipient = os.environ.get('REPORT_RECIPIENT', 'moorecash@gmail.com')

    if not gmail_password:
        logger.warning("GMAIL_APP_PASSWORD not set — skipping email")
        return False

    # Build actionable investment briefing from JSON
    body_lines = [
        f"CLOUDCLEARINGAPI — WEEKLY INVESTMENT BRIEFING",
        f"Report Date: {datetime.now().strftime('%B %d, %Y')}",
        "=" * 55,
        "",
    ]
    # Default values for the low-confidence subject tag (computed below if data loads)
    market_fallback_pct = 0.0
    sar_only_pct = 0.0
    try:
        import json as _json
        with open(json_path) as f:
            data = _json.load(f)

        yog = data.get('investment_analysis', {}).get('yogyakarta_analysis', {})
        strong_buy = yog.get('strong_buy_recommendations', [])
        buy = yog.get('buy_recommendations', [])
        watch = yog.get('watch_list', [])
        passes = yog.get('pass_list', [])
        all_recs = strong_buy + buy + watch + passes

        # --- Data quality (computed first so we can tag the subject) ---
        n = max(1, len(all_recs))
        market_fallback = sum(
            1 for r in all_recs
            if r.get('data_sources', {}).get('market') in ('fallback', 'regional_benchmark', 'static_benchmark', None)
        )
        live_market = len(all_recs) - market_fallback
        # Both osm_live (fresh query) and osm_cached (within 7-day cache TTL) are
        # genuine OSM data. Only 'fallback' / 'unavailable' are non-OSM.
        live_infra = sum(
            1 for r in all_recs
            if 'osm' in str(r.get('data_sources', {}).get('infrastructure', '')).lower()
        )
        sar_only_count = sum(1 for r in all_recs if r.get('data_sources', {}).get('satellite') == 'sar_only')
        market_fallback_pct = market_fallback / n
        sar_only_pct = sar_only_count / n

        # --- Portfolio Overview ---
        body_lines.append(f"PORTFOLIO OVERVIEW")
        body_lines.append(f"  Regions Scored: {len(all_recs)}")
        body_lines.append(f"  STRONG BUY: {len(strong_buy)} | BUY: {len(buy)} | WATCH: {len(watch)} | PASS: {len(passes)}")
        body_lines.append(f"  Data Quality: {live_market}/{len(all_recs)} live market, {live_infra}/{len(all_recs)} live infrastructure")
        if sar_only_count:
            body_lines.append(
                f"  ⚠ {sar_only_count}/{len(all_recs)} regions on SAR-only satellite "
                f"(no optical verification — confidence reduced)"
            )
        if market_fallback_pct >= 0.20:
            body_lines.append(
                f"  ⚠ LOW-CONFIDENCE RUN: {market_fallback}/{len(all_recs)} regions "
                f"({market_fallback_pct:.0%}) ended up on static benchmark pricing — "
                "verify any BUY independently before acting"
            )
        body_lines.append("")

        # --- Tier transitions vs prior run (the "early signal" section) ---
        transitions = data.get('tier_transitions', {})
        upgrades = transitions.get('upgrades', [])
        downgrades = transitions.get('downgrades', [])
        if upgrades or downgrades:
            body_lines.append("📈 TIER CHANGES SINCE LAST RUN")
            body_lines.append("-" * 55)
            if upgrades:
                body_lines.append(f"  ⬆ UPGRADES ({len(upgrades)}):")
                for u in upgrades[:8]:
                    region = u['region'].replace('_', ' ').title()
                    arrow_emoji = '🔥' if u['to_tier'] == 'STRONG_BUY' else '✅' if u['to_tier'] == 'BUY' else '👀'
                    body_lines.append(
                        f"     {arrow_emoji} {region}: {u['from_tier']} ({u['from_score']:.1f}) "
                        f"→ {u['to_tier']} ({u['to_score']:.1f}, {u['score_delta']:+.1f}pts)"
                    )
            if downgrades:
                body_lines.append(f"  ⬇ DOWNGRADES ({len(downgrades)}):")
                for d in downgrades[:5]:
                    region = d['region'].replace('_', ' ').title()
                    body_lines.append(
                        f"     ⚠ {region}: {d['from_tier']} ({d['from_score']:.1f}) "
                        f"→ {d['to_tier']} ({d['to_score']:.1f}, {d['score_delta']:+.1f}pts)"
                    )
            body_lines.append("")

        # --- Top BUY Opportunities (STRONG_BUY first, then BUY) ---
        priority_recs = strong_buy + buy
        if priority_recs:
            body_lines.append("PRIORITY OPPORTUNITIES — 🔥 STRONG BUY first, then BUY")
            body_lines.append("-" * 55)
            for i, r in enumerate(sorted(priority_recs, key=lambda x: x.get('investment_score', 0), reverse=True)[:10], 1):
                tier = '🔥 STRONG BUY' if r.get('recommendation') == 'STRONG_BUY' else 'BUY'
                name = r.get('region', '?').replace('_', ' ').title()
                score = r.get('investment_score', 0)
                conf = r.get('confidence', r.get('confidence_level', 0))
                price = r.get('current_price_per_m2', 0)
                rvi_val = r.get('rvi_data', {}).get('rvi', 0) if isinstance(r.get('rvi_data'), dict) else 0
                rvi_interp = r.get('rvi_data', {}).get('interpretation', '') if isinstance(r.get('rvi_data'), dict) else ''
                mom = r.get('momentum', {}).get('trend', 'n/a') if isinstance(r.get('momentum'), dict) else 'n/a'
                heat = r.get('market_heat', 'unknown')
                fp = r.get('financial_projection', {})
                # Use land-only ROI for BOTH horizons so comparison is apples-to-apples.
                # (Was mixing land_only_roi_3yr with projected_roi_5yr — produced
                # the bizarre "5Y ROI < 3Y ROI" anomaly in 30/65 regions.)
                if hasattr(fp, 'projected_roi_3yr'):
                    land_roi_3y = getattr(fp, 'land_only_roi_3yr', fp.projected_roi_3yr) or 0
                    land_roi_5y = getattr(fp, 'land_only_roi_5yr', getattr(fp, 'projected_roi_5yr', 0)) or 0
                    entry_cost = getattr(fp, 'total_acquisition_cost', 0)
                    future_val = getattr(fp, 'estimated_future_value_per_m2', 0)
                elif isinstance(fp, dict):
                    land_roi_3y = fp.get('land_only_roi_3yr', fp.get('projected_roi_3yr', 0)) or 0
                    land_roi_5y = fp.get('land_only_roi_5yr', fp.get('projected_roi_5yr', 0)) or 0
                    entry_cost = fp.get('total_acquisition_cost', 0)
                    future_val = fp.get('estimated_future_value_per_m2', 0)
                else:
                    land_roi_3y = land_roi_5y = entry_cost = future_val = 0

                # News WoW
                nwow = r.get('news_wow', {})
                wow_str = ''
                if isinstance(nwow, dict) and nwow.get('trend'):
                    wow_str = f" | News: {nwow.get('previous_articles', 0)}→{nwow.get('current_articles', 0)} ({nwow['trend']})"

                body_lines.append(f"  {i}. [{tier}] {name}")
                body_lines.append(f"     Score: {score:.1f}/100 | Confidence: {conf*100:.0f}% | Market: {heat}")
                body_lines.append(f"     Entry Price: Rp {price:,.0f}/m² → Rp {future_val:,.0f}/m² (projected)")
                body_lines.append(f"     ROI: 3Y {land_roi_3y*100:.1f}% | 5Y {land_roi_5y*100:.1f}%")
                if entry_cost:
                    body_lines.append(f"     Est. Acquisition (500m²): Rp {entry_cost:,.0f}")
                body_lines.append(f"     RVI: {rvi_val:.2f} ({rvi_interp}) | Momentum: {mom}{wow_str}")

                # Data source warning
                data_src = r.get('data_sources', {})
                warnings = []
                if data_src.get('market') in ('fallback', 'regional_benchmark'):
                    warnings.append('market=fallback')
                if 'fallback' in str(data_src.get('infrastructure', '')):
                    warnings.append('infra=fallback')
                if warnings:
                    body_lines.append(f"     ⚠ Data: {', '.join(warnings)} — verify pricing independently")
                body_lines.append("")

        # --- WATCH List ---
        if watch:
            body_lines.append("WATCH LIST (approaching BUY threshold)")
            body_lines.append("-" * 55)
            for r in sorted(watch, key=lambda x: x.get('investment_score', 0), reverse=True)[:5]:
                name = r.get('region', '?').replace('_', ' ').title()
                score = r.get('investment_score', 0)
                price = r.get('current_price_per_m2', 0)
                heat = r.get('market_heat', 'unknown')
                headroom = r.get('score_headroom', 0) or 0
                body_lines.append(f"  {name} — {score:.1f}/100 | Rp {price:,.0f}/m² | {heat} | headroom: {headroom:.1f}pts to BUY")
            body_lines.append("")

        # --- PASS Summary ---
        if passes:
            body_lines.append(f"PASS: {len(passes)} regions below threshold (see PDF for details)")
            body_lines.append("")

        # --- Actionable Next Steps ---
        body_lines.append("RECOMMENDED ACTIONS")
        body_lines.append("-" * 55)
        if priority_recs:
            top = sorted(priority_recs, key=lambda x: x.get('investment_score', 0), reverse=True)[0]
            top_name = top.get('region', '?').replace('_', ' ').title()
            top_tier = '🔥 STRONG BUY' if top.get('recommendation') == 'STRONG_BUY' else 'BUY'
            body_lines.append(f"  1. Priority due diligence: {top_name} [{top_tier}]")
            if strong_buy:
                body_lines.append(f"  2. Focus on the {len(strong_buy)} STRONG BUY region(s) first — these are top-decile signals")
            body_lines.append(f"  3. Verify land titles and zoning before deploying capital")
            body_lines.append(f"  4. Check local notary/PPAT availability for target plot")
            low_rvi = [r for r in priority_recs if isinstance(r.get('rvi_data'), dict) and r['rvi_data'].get('rvi', 999) < 0.85]
            if low_rvi:
                names = [r.get('region', '?').replace('_', ' ').title() for r in low_rvi[:3]]
                body_lines.append(f"  5. Undervalued (RVI < 0.85): {', '.join(names)} — potential deep value")
        body_lines.append("")
        body_lines.append("Full PDF report with Decision Matrix, financial projections, and")
        body_lines.append("risk analysis attached.")
    except Exception as e:
        body_lines.append(f"(Could not parse summary: {e})")
        body_lines.append("See attached PDF for details.")

    body_lines.append("")
    body_lines.append("— CloudClearingAPI Automated Report")

    # Subject prefix: tag low-confidence runs so the recipient can spot them
    # before opening the PDF. >=20% benchmark fallback OR any SAR-only is a flag.
    subject_prefix = ''
    if market_fallback_pct >= 0.20 or sar_only_pct >= 0.10:
        subject_prefix = '[LOW-CONF] '
    msg = MIMEMultipart()
    msg['From'] = gmail_address
    msg['To'] = recipient
    msg['Subject'] = (
        f"{subject_prefix}CloudClearingAPI Report — "
        f"{datetime.now().strftime('%B %d, %Y %H:%M')}"
    )
    msg.attach(MIMEText('\n'.join(body_lines), 'plain'))

    if pdf_path and Path(pdf_path).exists():
        with open(pdf_path, 'rb') as f:
            att = MIMEApplication(f.read(), _subtype='pdf')
            att.add_header('Content-Disposition', 'attachment', filename=Path(pdf_path).name)
            msg.attach(att)
        logger.info(f"Attached PDF: {Path(pdf_path).name}")

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(gmail_address, gmail_password)
            server.send_message(msg)
        logger.info(f"Email sent to {recipient}")
        return True
    except Exception as e:
        logger.error(f"Email failed: {e}")
        # Fallback: post the briefing to the webhook so the BUY signal isn't lost.
        # Without this, an SMTP outage silently hides every recommendation.
        webhook_ok = _send_webhook_alert(
            subject=msg['Subject'],
            body='\n'.join(body_lines),
            json_path=json_path,
        )
        if webhook_ok:
            logger.info('Webhook fallback delivered the briefing')
        return False


async def main(all_regions: bool = False, auto_confirm: bool = False):
    """Run weekly monitoring for Java or all Indonesia regions with parallel processing"""

    # SMTP preflight — surface email auth failures in the first 5 seconds of
    # the run instead of after a 30-min pipeline. Don't gate the pipeline:
    # we still want JSON/PDF generated even if email is broken (webhook
    # fallback will kick in at delivery time).
    smtp_ok, smtp_reason = _smtp_preflight()
    if smtp_ok:
        logger.info('✅ SMTP preflight passed — email delivery should work')
    else:
        logger.error(f'❌ SMTP preflight FAILED: {smtp_reason}')
        logger.error('   Email at end of run will fail; webhook fallback will be attempted.')
        logger.error('   Fix: generate App Password at https://myaccount.google.com/apppasswords')

    # Import expansion manager
    from src.indonesia_expansion_regions import get_expansion_manager
    expansion_manager = get_expansion_manager()

    # Get regions based on scope
    if all_regions:
        monitoring_regions = expansion_manager.get_all_regions()
        scope_label = "INDONESIA-WIDE"
    else:
        monitoring_regions = expansion_manager.get_java_regions()
        scope_label = "JAVA-WIDE"

    print("\n" + "="*100)
    print(f"🇮🇩 {scope_label} WEEKLY MONITORING")
    print("="*100)
    print()

    # Group by island and priority for reporting
    islands = {}
    for r in monitoring_regions:
        islands.setdefault(r.island, []).append(r)

    priority_1 = [r for r in monitoring_regions if r.priority == 1]
    priority_2 = [r for r in monitoring_regions if r.priority == 2]
    priority_3 = [r for r in monitoring_regions if r.priority == 3]

    print(f"📊 **MONITORING SCOPE**: {len(monitoring_regions)} Regions")
    print()
    print(f"   • Priority 1 (High Investment): {len(priority_1)} regions")
    print(f"   • Priority 2 (Medium Investment): {len(priority_2)} regions")
    print(f"   • Priority 3 (Emerging Markets): {len(priority_3)} regions")
    print()

    print("**Coverage Map:**")
    for island, regions in sorted(islands.items()):
        print(f"   • {island}: {len(regions)} regions")
    print()
    
    # Estimate processing time with parallel processing
    # With 5 parallel regions per batch: ~6 batches for 29 regions
    # Each batch: ~3-4 minutes (with GEE cache, faster after first run)
    avg_time_per_batch = 3.5  # minutes
    num_batches = (len(monitoring_regions) + 4) // 5  # Ceiling division
    estimated_minutes = num_batches * avg_time_per_batch
    estimated_hours = estimated_minutes / 60
    
    print(f"⏱️  **ESTIMATED TIME**: {estimated_minutes:.0f} minutes (~{estimated_hours:.1f} hours)")
    print(f"    With parallel processing: {len(monitoring_regions)} regions in {num_batches} batches of 5")
    print(f"    (First run: ~30-35 min | Cached runs: ~15-20 min)")
    print(f"📅 **START TIME**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("=" * 100)
    print()
    
    # Confirm before proceeding
    print("⚠️  This is a comprehensive monitoring run that will:")
    print(f"   1. Analyze satellite imagery for {len(monitoring_regions)} regions")
    print("   2. Calculate investment scores with resilient API handling")
    print("   3. Generate PDF report with all findings")
    print("   4. Save satellite images for top opportunities")
    print()

    if not auto_confirm:
        response = input("Continue with monitoring? (yes/no): ").strip().lower()
        if response != 'yes':
            print("\n❌ Monitoring cancelled by user")
            return

    print(f"\n🚀 Starting {scope_label.lower()} monitoring...")
    print("=" * 100)
    print()
    
    # Import and configure the automated monitor
    from src.core.automated_monitor import AutomatedMonitor
    from src.core.config import get_config
    
    # Initialize monitor
    logger.info(f"Initializing Automated Monitor for {scope_label.lower()} coverage...")
    monitor = AutomatedMonitor()

    # Set monitoring regions
    monitor.yogyakarta_regions = [region.name for region in monitoring_regions]
    logger.info(f"✅ Configured with {len(monitor.yogyakarta_regions)} regions")
    
    # Update region manager to handle expansion regions
    original_get_bbox = monitor.region_manager.get_region_bbox
    
    def enhanced_get_bbox(name: str):
        """Enhanced bbox getter that checks expansion regions first"""
        # Try expansion manager first
        bbox = expansion_manager.get_region_bbox_dict(name)
        if bbox:
            return bbox
        # Fall back to original regions
        return original_get_bbox(name)
    
    # Monkey-patch the region manager
    monitor.region_manager.get_region_bbox = enhanced_get_bbox
    logger.info("✅ Enhanced region manager with Indonesia expansion support")
    
    # Run the monitoring with parallel processing
    start_time = datetime.now()
    
    try:
        print(f"\n📡 Processing {len(monitoring_regions)} regions in parallel batches...")
        print("   (Progress updates will appear as each batch completes)")
        print()
        
        # Calculate date ranges using monitor's method
        end_date, start_date = monitor._get_optimal_date_range(0)
        
        week_a_start = start_date.strftime('%Y-%m-%d')
        week_b_start = end_date.strftime('%Y-%m-%d')
        
        logger.info(f"📅 Week A: {week_a_start}")
        logger.info(f"📅 Week B: {week_b_start}")
        
        # Run parallel batch processing
        results_list = await run_parallel_monitoring(
            monitor=monitor,
            regions=[region.name for region in monitoring_regions],
            week_a_start=week_a_start,
            week_b_start=week_b_start,
            batch_size=5  # Process 5 regions at a time
        )
        
        # Aggregate results (same format as run_weekly_monitoring)
        total_changes = sum(r.get('change_count', 0) for r in results_list)
        total_area_m2 = sum(r.get('total_area_m2', 0) for r in results_list)
        
        # Collect alerts
        all_alerts = []
        for result in results_list:
            if result.get('alerts'):
                all_alerts.extend(result['alerts'])
        
        # Assemble monitoring results object for investment analysis
        monitoring_results = {
            'timestamp': end_date.isoformat(),
            'regions_analyzed': results_list,
            'total_changes': total_changes,
            'total_area_m2': total_area_m2,
            'alerts': all_alerts,
            'period': f"{week_a_start} to {week_b_start}"
        }
        
        # Generate summary statistics for PDF compatibility
        alert_summary = {
            'critical': len([a for a in all_alerts if a.get('severity') == 'CRITICAL']),
            'major': len([a for a in all_alerts if a.get('severity') == 'MAJOR']),
            'total': len(all_alerts)
        }
        
        # Get top 3 most active regions
        sorted_regions = sorted(results_list, key=lambda x: x.get('change_count', 0), reverse=True)
        most_active = [
            {
                'name': r['region_name'],
                'changes': r.get('change_count', 0),
                'area_hectares': r.get('total_area_m2', 0) / 10000
            }
            for r in sorted_regions[:3]
        ]
        
        monitoring_results['summary'] = {
            'status': 'completed',
            'regions_monitored': len(results_list),
            'total_changes': total_changes,
            'total_area_hectares': total_area_m2 / 10000,
            'average_changes_per_region': total_changes / len(results_list) if results_list else 0,
            'alert_summary': alert_summary,
            'most_active_regions': most_active
        }
        
        # Generate investment analysis
        print()
        print("💰 Generating investment analysis...")
        print(
            "   ℹ️  Batch progress / ETA above applies to satellite processing only — not this phase."
        )
        print(
            "   Dynamic scoring hits Overpass per region; watch logs for "
            "'Overpass 1/2/3' and 'Scoring [n/N]' lines."
        )
        investment_analysis = monitor._generate_investment_analysis(monitoring_results)

        # Add investment analysis to final results
        results = monitoring_results
        results['investment_analysis'] = investment_analysis

        # Tier transitions vs prior run — directly serves "see opportunities
        # early": a region moving from PASS→WATCH or WATCH→BUY this week is
        # a high-signal event that the briefing should highlight first.
        try:
            prev_state = monitor._load_previous_region_state()
            yog = investment_analysis.get('yogyakarta_analysis', {})
            current_recs = (yog.get('strong_buy_recommendations', []) +
                            yog.get('buy_recommendations', []) +
                            yog.get('watch_list', []) +
                            yog.get('pass_list', []))
            tier_rank = {'PASS': 0, 'WATCH': 1, 'BUY': 2, 'STRONG_BUY': 3}
            upgrades, downgrades, new_regions = [], [], []
            for r in current_recs:
                name = r.get('region') or r.get('region_name')
                if not name:
                    continue
                curr_tier = r.get('recommendation', 'PASS')
                curr_score = r.get('investment_score', 0)
                prev = prev_state.get(name)
                if prev is None:
                    new_regions.append({'region': name, 'tier': curr_tier, 'score': curr_score})
                    continue
                prev_tier = prev.get('recommendation', 'PASS')
                prev_score = prev.get('investment_score', 0)
                if tier_rank.get(curr_tier, 0) > tier_rank.get(prev_tier, 0):
                    upgrades.append({
                        'region': name, 'from_tier': prev_tier, 'to_tier': curr_tier,
                        'from_score': prev_score, 'to_score': curr_score,
                        'score_delta': round(curr_score - prev_score, 1),
                    })
                elif tier_rank.get(curr_tier, 0) < tier_rank.get(prev_tier, 0):
                    downgrades.append({
                        'region': name, 'from_tier': prev_tier, 'to_tier': curr_tier,
                        'from_score': prev_score, 'to_score': curr_score,
                        'score_delta': round(curr_score - prev_score, 1),
                    })
            # Sort upgrades by destination tier (most promoted first), then by score delta
            upgrades.sort(key=lambda x: (-tier_rank.get(x['to_tier'], 0), -x['score_delta']))
            downgrades.sort(key=lambda x: (-tier_rank.get(x['from_tier'], 0), x['score_delta']))
            results['tier_transitions'] = {
                'upgrades': upgrades,
                'downgrades': downgrades,
                'new_regions': new_regions,
                'compared_against': next((p['snapshot_path'] for p in prev_state.values()), None),
            }
            if upgrades or downgrades:
                logger.info(f"   📈 Tier transitions: {len(upgrades)} upgrade(s), {len(downgrades)} downgrade(s)")
        except Exception as e:
            logger.warning(f"   ⚠️ Failed to compute tier transitions: {e}")
        
        # ✅ CCAPI-27.2: Track benchmark drift after monitoring completes
        print()
        print("📊 Tracking benchmark drift...")
        try:
            from src.core.benchmark_drift_monitor import BenchmarkDriftMonitor
            
            drift_monitor = BenchmarkDriftMonitor(
                history_dir="./data/benchmark_drift",
                retention_days=180,  # 6 months
                enable_alerts=True
            )
            
            # Extract scored regions from investment analysis (these have financial_projection)
            yog = investment_analysis.get('yogyakarta_analysis', {})
            scored_regions = (
                yog.get('strong_buy_recommendations', []) +
                yog.get('buy_recommendations', []) +
                yog.get('watch_list', []) +
                yog.get('pass_list', [])
            )
            # Normalise key: investment analysis uses 'region' not 'region_name'
            drift_input = []
            for r in scored_regions:
                if not isinstance(r, dict):
                    continue
                entry = dict(r)
                if 'region' in entry and 'region_name' not in entry:
                    entry['region_name'] = entry['region']
                drift_input.append(entry)
            
            drift_summary = drift_monitor.track_drift(drift_input)
            
            # Add drift summary to results
            results['drift_monitoring'] = drift_summary
            
            # Log drift alerts
            drift_alerts = drift_summary.get('alerts', {})
            if drift_alerts.get('total', 0) > 0:
                print(f"   ⚠️  Drift Alerts: {drift_alerts['critical']} CRITICAL, {drift_alerts['warning']} WARNING")
                
                # Show critical alerts
                for alert in drift_alerts.get('details', []):
                    if alert['alert_level'] == 'CRITICAL':
                        print(f"      🔴 {alert['region_name']}: {alert['current_drift_pct']:+.1f}% drift "
                              f"({alert['consecutive_weeks']} weeks)")
            else:
                print("   ✅ No drift alerts - benchmarks are healthy")
                
        except Exception as drift_error:
            logger.warning(f"Drift monitoring failed (non-critical): {drift_error}")
            results['drift_monitoring'] = {'status': 'failed', 'error': str(drift_error)}
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() / 60
        
        # 💾 Save monitoring results to JSON
        print()
        print("💾 Saving monitoring results...")
        from pathlib import Path
        import json
        
        output_dir = Path("output/monitoring")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_filename = output_dir / f"weekly_monitoring_{timestamp}.json"
        
        # Custom JSON encoder for dataclasses
        def dataclass_serializer(obj):
            """Custom JSON serializer for dataclasses"""
            from dataclasses import is_dataclass, asdict
            if is_dataclass(obj):
                return asdict(obj)
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        with open(json_filename, 'w') as f:
            json.dump(results, f, indent=2, default=dataclass_serializer)
        
        logger.info(f"📁 Monitoring results saved to: {json_filename}")
        print(f"   ✅ JSON saved: {json_filename}")
        
        # 📄 Generate PDF executive summary
        print()
        print("📄 Generating PDF executive summary...")
        try:
            from src.core.pdf_report_generator import generate_pdf_from_json
            pdf_path = generate_pdf_from_json(str(json_filename))
            logger.info(f"📄 Executive summary PDF generated: {pdf_path}")
            print(f"   ✅ PDF generated: {pdf_path}")
        except Exception as e:
            logger.warning(f"Failed to generate PDF report: {e}")
            print(f"   ⚠️  PDF generation failed: {e}")
            pdf_path = None

        # 📧 Send email report after every successful run
        print()
        print("📧 Sending email report...")
        try:
            email_sent = _send_report_email(str(json_filename), pdf_path)
            if email_sent:
                print("   ✅ Email sent successfully")
            else:
                print("   ⚠️  Email not sent (check GMAIL_APP_PASSWORD in .env)")
        except Exception as e:
            logger.warning(f"Email sending failed: {e}")
            print(f"   ⚠️  Email failed: {e}")

        print()
        print("=" * 100)
        print("✅ JAVA-WIDE MONITORING COMPLETED!")
        print("=" * 100)
        print()
        
        # Comprehensive results summary
        regions_analyzed = results.get('regions_analyzed', [])
        total_changes = results.get('total_changes', 0)
        total_area = results.get('total_area_m2', 0) / 10000  # Convert to hectares
        alerts = results.get('alerts', [])
        
        print("📊 **SATELLITE ANALYSIS RESULTS:**")
        print(f"   • Regions Successfully Analyzed: {len(regions_analyzed)}/{len(monitoring_regions)}")
        print(f"   • Success Rate: {len(regions_analyzed)/len(monitoring_regions)*100:.1f}%")
        print(f"   • Total Changes Detected: {total_changes:,}")
        print(f"   • Total Area Changed: {total_area:,.1f} hectares")
        print(f"   • Critical Alerts: {len([a for a in alerts if a.get('level') == 'CRITICAL'])}")
        print(f"   • Major Alerts: {len([a for a in alerts if a.get('level') == 'MAJOR'])}")
        print()
        
        # Performance metrics
        print(f"⚡ **PERFORMANCE:**")
        print(f"   • Total Processing Time: {duration:.1f} minutes ({duration/60:.2f} hours)")
        print(f"   • Average Time per Region: {duration/len(monitoring_regions):.1f} minutes")
        print(f"   • Regions per Hour: {len(regions_analyzed)/(duration/60):.1f}")
        print()
        
        # Drift monitoring results (CCAPI-27.2)
        drift_data = results.get('drift_monitoring', {})
        if drift_data.get('status') == 'complete':
            drift_stats = drift_data.get('overall_stats', {})
            drift_alerts = drift_data.get('alerts', {})
            
            print("📈 **BENCHMARK DRIFT MONITORING (v2.9.0):**")
            print(f"   • Regions Tracked: {drift_data.get('regions_tracked', 0)}")
            print(f"   • Average Drift: {drift_stats.get('avg_drift_pct', 0):+.1f}%")
            print(f"   • Regions >10% Drift: {drift_stats.get('regions_above_10pct', 0)}")
            print(f"   • Regions >20% Drift: {drift_stats.get('regions_above_20pct', 0)}")
            print(f"   • Active Alerts: {drift_alerts.get('total', 0)} "
                  f"({drift_alerts.get('critical', 0)} CRITICAL, {drift_alerts.get('warning', 0)} WARNING)")
            
            if drift_alerts.get('total', 0) > 0:
                print()
                print("   ⚠️  **DRIFT ALERTS REQUIRING ATTENTION:**")
                for alert_detail in drift_alerts.get('details', [])[:5]:  # Show top 5
                    region = alert_detail['region_name']
                    drift = alert_detail['current_drift_pct']
                    weeks = alert_detail['consecutive_weeks']
                    level = alert_detail['alert_level']
                    icon = "🔴" if level == "CRITICAL" else "🟡"
                    print(f"      {icon} {region}: {drift:+.1f}% drift ({weeks} consecutive weeks)")
            
            print()
        
        # Investment analysis
        investment = results.get('investment_analysis', {})
        yogyakarta_analysis = investment.get('yogyakarta_analysis', {})  # Name is legacy but works for all regions
        strong_buy_recs = yogyakarta_analysis.get('strong_buy_recommendations', [])
        buy_recs = yogyakarta_analysis.get('buy_recommendations', [])
        watch_list = yogyakarta_analysis.get('watch_list', [])
        priority_recs = strong_buy_recs + buy_recs

        print("💰 **INVESTMENT INTELLIGENCE:**")
        print(f"   • 🔥 STRONG BUY: {len(strong_buy_recs)}")
        print(f"   • BUY: {len(buy_recs)}")
        print(f"   • WATCH: {len(watch_list)}")
        print()

        if priority_recs:
            print("   🏆 **TOP 10 PRIORITY OPPORTUNITIES (STRONG BUY first):**")
            for i, opp in enumerate(priority_recs[:10], 1):
                region_name = opp.get('region', 'Unknown')
                score = opp.get('investment_score', 0)
                confidence = opp.get('confidence_level', 0)
                changes = opp.get('satellite_changes', 0)
                
                # Get region details
                region_obj = next((r for r in monitoring_regions if r.name == region_name), None)
                province = region_obj.province if region_obj else 'Java'

                tier_badge = '🔥 STRONG BUY' if opp.get('recommendation') == 'STRONG_BUY' else 'BUY'
                print(f"      {i:2d}. [{tier_badge}] {region_name:40s} ({province})")
                print(f"          Score: {score:.1f}/100 | Confidence: {confidence:.0%} | Changes: {changes:,}")
                
                # Show data availability if present
                data_sources = opp.get('data_sources', {})
                if isinstance(data_sources, dict) and 'missing_data_note' in data_sources:
                    note = data_sources['missing_data_note']
                    if 'unavailable' in note.lower():
                        print(f"          ⚠️ {note}")
        
        print()
        print("=" * 100)
        print("📁 **OUTPUT FILES:**")
        print(f"   • Monitoring Data: output/monitoring/weekly_monitoring_*.json")
        print(f"   • PDF Report: output/reports/executive_summary_*.pdf")
        print(f"   • Satellite Images: output/satellite_images/weekly/")
        print(f"   • Drift History: data/benchmark_drift/*_drift_history.json")
        print(f"   • Detailed Logs: logs/java_weekly_*.log")
        print()
        
        print("=" * 100)
        print("🎯 **NEXT STEPS:**")
        print("   1. ✅ Review the PDF executive summary for investment insights")
        print("   2. ✅ Analyze satellite imagery for top opportunities")
        print("   3. ✅ Compare results across different Java regions")
        print("   4. ✅ Track confidence levels - follow up on low-confidence scores")
        print("   5. ✅ If successful, consider expanding to Sumatra/Bali")
        print("=" * 100)
        print()
        
        return results
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Monitoring interrupted by user")
        logger.warning("User interrupted monitoring")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"Monitoring failed: {e}", exc_info=True)
        print()
        print("=" * 100)
        print("❌ MONITORING FAILED!")
        print("=" * 100)
        print(f"Error: {str(e)}")
        print()
        print("Check logs/java_weekly_*.log for detailed error information")
        raise

if __name__ == "__main__":
    import asyncio
    import argparse

    parser = argparse.ArgumentParser(description='CloudClearing Weekly Monitoring')
    parser.add_argument('--all', action='store_true', help='Monitor all 65 regions (Java + Sumatra + Bali/Lombok/NTT + Eastern)')
    parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation prompt')
    args = parser.parse_args()

    scope = "Indonesia-Wide (65 regions)" if args.all else "Java-Wide (31 regions)"
    print()
    print(f"🚀 CloudClearing - {scope} Weekly Monitoring")
    print("   Comprehensive satellite analysis across Indonesia")
    print()

    try:
        asyncio.run(main(all_regions=args.all, auto_confirm=args.yes))
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
