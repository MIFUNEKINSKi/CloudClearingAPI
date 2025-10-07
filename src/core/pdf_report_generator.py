"""
PDF Report Generator for CloudClearingAPI Weekly Monitoring

This module generates professional executive summary PDFs from monitoring results.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from io import BytesIO
import base64
from reportlab.platypus import Image as ReportLabImage

logger = logging.getLogger(__name__)

class PDFReportGenerator:
    """
    Generates professional PDF executive summaries from monitoring results
    """
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Setup custom paragraph styles for the report"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#2E86AB')
        ))
        
        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=15,
            spaceBefore=20,
            textColor=colors.HexColor('#A23B72')
        ))
        
        # Subsection header style
        self.styles.add(ParagraphStyle(
            name='SubsectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=10,
            spaceBefore=15,
            textColor=colors.HexColor('#F18F01')
        ))
        
        # Alert style
        self.styles.add(ParagraphStyle(
            name='AlertCritical',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.red,
            leftIndent=20
        ))
        
        # Alert style
        self.styles.add(ParagraphStyle(
            name='AlertMajor',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.orange,
            leftIndent=20
        ))
        
        # Investment opportunity style
        self.styles.add(ParagraphStyle(
            name='InvestmentOpportunity',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#2E86AB'),
            leftIndent=15,
            spaceAfter=5
        ))
        
        # Footer style
        self.styles.add(ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            alignment=TA_CENTER,
            textColor=colors.grey
        ))

    def generate_executive_summary(self, json_file_path: str, output_dir: Optional[str] = None) -> str:
        """
        Generate PDF executive summary from monitoring JSON results
        
        Args:
            json_file_path: Path to the monitoring JSON file
            output_dir: Directory to save the PDF (defaults to output/reports)
            
        Returns:
            Path to the generated PDF file
        """
        # Load monitoring data
        with open(json_file_path, 'r') as f:
            data = json.load(f)
        
        # Setup output directory
        if output_dir is None:
            output_path = Path('./output/reports')
        else:
            output_path = Path(output_dir)
        
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate PDF filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_filename = output_path / f"executive_summary_{timestamp}.pdf"
        
        # Create PDF document
        doc = SimpleDocTemplate(
            str(pdf_filename),
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Build content
        story = []
        
        # Add title and header
        story.extend(self._build_header(data))
        
        # Add executive summary
        story.extend(self._build_executive_summary(data))
        
        # Add monitoring results
        story.extend(self._build_monitoring_results(data))
        
        # Add alerts section
        story.extend(self._build_alerts_section(data))
        
        # Add investment analysis
        story.extend(self._build_investment_analysis(data))
        
        # Add satellite imagery summary
        story.extend(self._build_satellite_imagery_summary(data))
        
        # Add regional breakdown
        story.extend(self._build_regional_breakdown(data))
        
        # Add footer
        story.extend(self._build_footer(data))
        
        # Generate PDF
        doc.build(story)
        
        logger.info(f"📄 Executive summary PDF generated: {pdf_filename}")
        return str(pdf_filename)

    def _build_header(self, data: Dict[str, Any]) -> List:
        """Build the document header"""
        story = []
        
        # Title
        story.append(Paragraph("🛰️ CloudClearing Weekly Monitoring Report", self.styles['CustomTitle']))
        story.append(Spacer(1, 12))
        
        # Report metadata
        analysis_date = datetime.fromisoformat(data['timestamp']).strftime('%B %d, %Y')
        period = data['period']
        
        metadata_data = [
            ['Report Date:', analysis_date],
            ['Analysis Period:', period],
            ['Regions Monitored:', str(data['summary'].get('regions_monitored', 0))],
            ['Analysis Confidence:', data.get('investment_analysis', {}).get('executive_summary', {}).get('analysis_confidence', 'UNKNOWN')]
        ]
        
        metadata_table = Table(metadata_data, colWidths=[2*inch, 3*inch])
        metadata_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F4FD')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2E86AB')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#F8FBFD')]),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#DDDDDD'))
        ]))
        story.append(metadata_table)
        story.append(Spacer(1, 20))
        
        return story

    def _build_executive_summary(self, data: Dict[str, Any]) -> List:
        """Build the executive summary section"""
        story = []
        
        story.append(Paragraph("📊 EXECUTIVE SUMMARY", self.styles['SectionHeader']))
        
        summary = data.get('summary', {})
        investment_summary = data.get('investment_analysis', {}).get('executive_summary', {})
        
        # Market status
        market_status = investment_summary.get('market_status', 'Unknown')
        story.append(Paragraph(f"<b>Market Status:</b> {market_status}", self.styles['Normal']))
        story.append(Spacer(1, 10))
        
        # Key metrics
        key_metrics = [
            ['Total Changes Detected:', f"{summary.get('total_changes', 0):,}"],
            ['Total Area Changed:', f"{summary.get('total_area_hectares', 0):,.1f} hectares"],
            ['Critical Alerts:', str(summary.get('alert_summary', {}).get('critical', 0))],
            ['Investment Opportunities:', str(investment_summary.get('opportunity_breakdown', {}).get('total_opportunities', 0))]
        ]
        
        metrics_table = Table(key_metrics, colWidths=[2.5*inch, 2*inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F4FD')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2E86AB')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.HexColor('#F0F8FF'), colors.white]),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#CCCCCC'))
        ]))
        story.append(metrics_table)
        story.append(Spacer(1, 15))
        
        return story

    def _build_monitoring_results(self, data: Dict[str, Any]) -> List:
        """Build the monitoring results section"""
        story = []
        
        story.append(Paragraph("🔍 MONITORING RESULTS", self.styles['SectionHeader']))
        
        regions_analyzed = data.get('regions_analyzed', [])
        
        # Top 5 most active regions
        yogyakarta_regions = [r for r in regions_analyzed if r.get('analysis_type') == 'yogyakarta_region']
        strategic_regions = [r for r in regions_analyzed if r.get('analysis_type') == 'strategic_corridor']
        
        if yogyakarta_regions:
            story.append(Paragraph("Most Active Regions:", self.styles['SubsectionHeader']))
            
            # Sort by change count
            top_regions = sorted(yogyakarta_regions, key=lambda x: x['change_count'], reverse=True)[:5]
            
            region_data = [['Region', 'Changes', 'Area (hectares)']]
            for region in top_regions:
                region_data.append([
                    region['region_name'].replace('_', ' ').title(),
                    f"{region['change_count']:,}",
                    f"{region['total_area_m2']/10000:.1f}"
                ])
            
            region_table = Table(region_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
            region_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E86AB')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#F8FBFD'), colors.white]),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#CCCCCC'))
            ]))
            story.append(region_table)
            story.append(Spacer(1, 15))
        
        if strategic_regions:
            story.append(Paragraph("Strategic Corridor Activity:", self.styles['SubsectionHeader']))
            
            strategic_data = [['Corridor', 'Changes', 'Investment Tier']]
            for region in strategic_regions[:5]:
                corridor_info = region.get('corridor_info', {})
                strategic_data.append([
                    region['region_name'].replace('_', ' ').title(),
                    f"{region['change_count']:,}",
                    corridor_info.get('investment_tier', 'Unknown').upper()
                ])
            
            strategic_table = Table(strategic_data, colWidths=[2.5*inch, 1*inch, 1*inch])
            strategic_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#A23B72')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#FDF0F5'), colors.white]),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#CCCCCC'))
            ]))
            story.append(strategic_table)
            story.append(Spacer(1, 15))
        
        # Add activity chart if we have enough regions
        all_regions = yogyakarta_regions + strategic_regions
        if len(all_regions) >= 3:
            try:
                chart_buffer = self._create_region_activity_chart(all_regions)
                chart_image = ReportLabImage(chart_buffer, width=6*inch, height=3.6*inch)
                story.append(Paragraph("Regional Activity Overview:", self.styles['SubsectionHeader']))
                story.append(chart_image)
                story.append(Spacer(1, 15))
            except Exception as e:
                logger.warning(f"Failed to generate activity chart: {e}")
        
        return story

    def _build_alerts_section(self, data: Dict[str, Any]) -> List:
        """Build the alerts section"""
        story = []
        
        alerts = data.get('alerts', [])
        if not alerts:
            return story
        
        story.append(Paragraph("🚨 CRITICAL ALERTS", self.styles['SectionHeader']))
        
        critical_alerts = [a for a in alerts if a['level'] == 'CRITICAL']
        major_alerts = [a for a in alerts if a['level'] == 'MAJOR']
        
        if critical_alerts:
            story.append(Paragraph(f"Critical Alerts ({len(critical_alerts)}):", self.styles['SubsectionHeader']))
            for alert in critical_alerts[:10]:  # Limit to top 10
                story.append(Paragraph(f"• {alert['message']}", self.styles['AlertCritical']))
            story.append(Spacer(1, 10))
        
        if major_alerts:
            story.append(Paragraph(f"Major Alerts ({len(major_alerts)}):", self.styles['SubsectionHeader']))
            for alert in major_alerts[:5]:  # Limit to top 5
                story.append(Paragraph(f"• {alert['message']}", self.styles['AlertMajor']))
            story.append(Spacer(1, 15))
        
        return story

    def _build_investment_analysis(self, data: Dict[str, Any]) -> List:
        """Build the investment analysis section"""
        story = []
        
        investment_analysis = data.get('investment_analysis', {})
        if not investment_analysis or investment_analysis.get('status') == 'no_data':
            return story
        
        story.append(Paragraph("💰 INVESTMENT OPPORTUNITIES", self.styles['SectionHeader']))
        
        # Executive summary
        exec_summary = investment_analysis.get('executive_summary', {})
        top_opportunity = exec_summary.get('top_opportunity', {})
        
        if top_opportunity and top_opportunity.get('region'):
            score = top_opportunity.get('score', top_opportunity.get('investment_score', 0))
            story.append(Paragraph(
                f"<b>🏆 TOP OPPORTUNITY:</b> {top_opportunity['region'].upper()} "
                f"({score:.1f}/100, {top_opportunity['type']})",
                self.styles['InvestmentOpportunity']
            ))
            story.append(Spacer(1, 10))
        
        # Yogyakarta opportunities
        yogyakarta_analysis = investment_analysis.get('yogyakarta_analysis', {})
        buy_recommendations = yogyakarta_analysis.get('buy_recommendations', [])
        
        if buy_recommendations:
            story.append(Paragraph("🏠 Top Investment Opportunities:", self.styles['SubsectionHeader']))
            
            # Create a compact detail style for table cells
            detail_style = ParagraphStyle(
                'DetailStyle',
                parent=self.styles['Normal'],
                fontSize=8,
                leading=10,
                leftIndent=0,
                rightIndent=0
            )
            
            opp_data = [['Region', 'Score', 'Confidence', 'Investment Intelligence']]
            for rec in buy_recommendations[:5]:  # Top 5
                # Generate meaningful investment rationale based on data
                score = rec.get('score', rec.get('investment_score', rec.get('dynamic_score', 0)))
                region_name = rec.get('region', 'Unknown')
                
                # Generate detailed investment explanation based on actual data
                investment_score = rec.get('investment_score', score)
                price_trend = rec.get('price_trend_30d', 0)
                current_price = rec.get('current_price_per_m2', 0)
                satellite_changes = rec.get('satellite_changes', 0)
                infrastructure_score = rec.get('infrastructure_score', 0)
                market_heat = rec.get('market_heat', 'unknown')
                data_sources = rec.get('data_sources', {})
                confidence = rec.get('confidence', rec.get('confidence_level', 0.5))
                
                # Build comprehensive data-driven explanation
                key_factors = []
                
                # Price momentum analysis with detail
                if price_trend > 10:
                    key_factors.append(f"<b>Strong price momentum</b> (+{price_trend:.1f}%)")
                elif price_trend > 5:
                    key_factors.append(f"<b>Positive price trend</b> (+{price_trend:.1f}%)")
                elif price_trend > 0:
                    key_factors.append(f"<b>Stable market</b> (+{price_trend:.1f}%)")
                else:
                    key_factors.append(f"<b>Price correction</b> ({price_trend:.1f}%)")
                
                # Add price context if available
                if current_price > 0:
                    key_factors.append(f"Current: Rp {current_price:,.0f}/m²")
                
                # Development activity with detail
                if satellite_changes > 30000:
                    key_factors.append(f"<b>Massive development</b>: {satellite_changes:,} changes detected")
                elif satellite_changes > 10000:
                    key_factors.append(f"<b>High development</b>: {satellite_changes:,} changes detected")
                elif satellite_changes > 1000:
                    key_factors.append(f"<b>Moderate activity</b>: {satellite_changes:,} changes detected")
                elif satellite_changes > 0:
                    key_factors.append(f"<b>Low activity</b>: {satellite_changes:,} changes detected")
                
                # Infrastructure quality with specifics
                if infrastructure_score >= 100:
                    key_factors.append(f"<b>Excellent infrastructure</b> (Score: {infrastructure_score:.0f})")
                elif infrastructure_score >= 80:
                    key_factors.append(f"<b>Good connectivity</b> (Score: {infrastructure_score:.0f})")
                elif infrastructure_score > 0:
                    key_factors.append(f"<b>Developing infrastructure</b> (Score: {infrastructure_score:.0f})")
                
                # Market conditions
                if market_heat == 'hot':
                    key_factors.append("<b>Hot market</b> - High demand")
                elif market_heat == 'warm':
                    key_factors.append("<b>Warming market</b> - Growing interest")
                elif market_heat == 'cold':
                    key_factors.append("<b>Buyer's market</b> - Good entry point")
                
                # Data source transparency and missing data warnings
                sources_used = []
                missing_sources = []
                
                # Check data availability
                if isinstance(data_sources, dict):
                    availability = data_sources.get('availability', {})
                    
                    # Track available sources
                    if data_sources.get('market_data') and data_sources.get('market_data') != 'unavailable':
                        sources_used.append("Market data")
                    elif not availability.get('market_data', True):  # If explicitly marked unavailable
                        missing_sources.append("Market data")
                    
                    if data_sources.get('satellite_data'):
                        sources_used.append("Satellite imagery")
                    
                    if data_sources.get('infrastructure_data') and data_sources.get('infrastructure_data') != 'unavailable':
                        sources_used.append("Infrastructure API")
                    elif not availability.get('infrastructure_data', True):
                        missing_sources.append("Infrastructure API")
                
                # Show available sources
                if sources_used:
                    key_factors.append(f"<i>Data: {', '.join(sources_used)}</i>")
                
                # IMPORTANT: Warn about missing data
                if missing_sources:
                    key_factors.append(f"<i>⚠️ Limited: {', '.join(missing_sources)} unavailable</i>")
                
                # Show missing data note if present
                if isinstance(data_sources, dict) and 'missing_data_note' in data_sources:
                    note = data_sources['missing_data_note']
                    if 'unavailable' in note.lower():
                        key_factors.append(f"<i>{note}</i>")
                
                # Combine ALL factors into comprehensive explanation (no truncation)
                if key_factors:
                    key_reason = "<br/>• ".join(key_factors)
                else:
                    # Fallback to actual rationale if available
                    key_reason = rec.get('rationale', f"Investment score: {investment_score:.1f}/100 (Confidence: {confidence:.0%})")
                
                # Use Paragraph for text wrapping instead of plain string
                key_benefit_para = Paragraph(key_reason, detail_style)
                
                opp_data.append([
                    Paragraph(rec['region'].replace('_', ' ').title(), detail_style),
                    Paragraph(f"<b>{score:.1f}</b>/100", detail_style),
                    Paragraph(f"{confidence:.0%}", detail_style),
                    key_benefit_para
                ])
            
            # Wider table with better proportions - Key Benefit gets most space
            opp_table = Table(opp_data, colWidths=[1.2*inch, 0.7*inch, 0.7*inch, 4*inch])
            opp_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F18F01')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (2, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#FEF8F1'), colors.white]),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#CCCCCC')),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(opp_table)
            story.append(Spacer(1, 15))
        
        return story

    def _build_satellite_imagery_summary(self, data: Dict[str, Any]) -> List:
        """Build satellite imagery summary section with embedded before/after images"""
        story = []
        
        regions_analyzed = data.get('regions_analyzed', [])
        # Look for regions with saved images (our new implementation)
        regions_with_saved_images = [r for r in regions_analyzed if r.get('saved_images', {})]
        regions_with_imagery = [r for r in regions_analyzed if r.get('satellite_images', {}).get('week_a_true_color')]
        
        # Use saved images if available, otherwise fall back to URL-based imagery
        regions_to_show = regions_with_saved_images if regions_with_saved_images else regions_with_imagery
        
        if not regions_to_show:
            return story
        
        story.append(Paragraph("🛰️ SATELLITE IMAGERY ANALYSIS", self.styles['SectionHeader']))
        
        # Add before/after imagery for top investment opportunities
        investment_analysis = data.get('investment_analysis', {})
        yogyakarta_analysis = investment_analysis.get('yogyakarta_analysis', {})
        buy_recommendations = yogyakarta_analysis.get('buy_recommendations', [])
        
        # Show images for top 3 buy recommendations
        regions_shown = 0
        for rec in buy_recommendations[:3]:
            region_name = rec.get('region', '')
            region_data = next((r for r in regions_to_show if r.get('region_name') == region_name), None)
            
            if region_data and regions_shown < 3:
                story.extend(self._add_region_imagery(region_data, rec))
                regions_shown += 1
        
        # If we have fewer than 3 regions from buy recommendations, add more high-change regions
        if regions_shown < 3:
            high_change_regions = sorted(
                [r for r in regions_to_show if r.get('region_name') not in [rec.get('region') for rec in buy_recommendations]], 
                key=lambda x: x.get('change_count', 0), 
                reverse=True
            )
            
            for region_data in high_change_regions[:3-regions_shown]:
                story.extend(self._add_region_imagery(region_data))
                regions_shown += 1
        
        # Summary table for all regions with imagery - including scores and explanations
        # EXCLUDE regions already shown in Investment Opportunities section
        story.append(Paragraph("📊 Complete Regional Analysis", self.styles['SubsectionHeader']))
        
        # Add methodology explanation ONCE at the beginning
        story.append(Paragraph(
            "<b>Investment Methodology:</b> Our analysis combines satellite-detected land use changes with "
            "market intelligence and infrastructure data. Each region receives an investment score (0-100) based on: "
            "<b>(1) Development Activity</b> - volume and pace of land use changes, "
            "<b>(2) Infrastructure Quality</b> - proximity to roads, ports, airports, "
            "<b>(3) Market Dynamics</b> - property price trends and market heat. "
            "Confidence levels (20-90%) reflect data availability across these sources. "
            "Satellite imagery shows before/after comparisons where available; NDVI (vegetation index) "
            "maps highlight vegetation loss (red = clearing for development) and gain (green = revegetation).",
            self.styles['Normal']
        ))
        story.append(Spacer(1, 15))
        
        # Create compact style for table cells with wrapping
        compact_style = ParagraphStyle(
            'CompactStyle',
            parent=self.styles['Normal'],
            fontSize=8,
            leading=9,
        )
        
        imagery_data = [['Region', 'Changes', 'Area (ha)', 'Score', 'Investment Notes', 'Period']]
        
        # Get investment analysis for scoring context
        investment_analysis = data.get('investment_analysis', {})
        yogyakarta_analysis = investment_analysis.get('yogyakarta_analysis', {})
        all_recommendations = yogyakarta_analysis.get('buy_recommendations', []) + \
                            yogyakarta_analysis.get('hold_recommendations', []) + \
                            yogyakarta_analysis.get('sell_recommendations', [])
        
        # Get list of regions already featured in Investment Opportunities
        featured_region_names = [rec.get('region') for rec in buy_recommendations[:5]]
        
        # Only show regions NOT already in the Investment Opportunities table
        remaining_regions = [r for r in regions_analyzed if r.get('region_name') not in featured_region_names]
        
        for region in remaining_regions:
            region_name = region['region_name'].replace('_', ' ').title()
            changes = region.get('change_count', 0)
            area = region.get('total_area_m2', 0) / 10000  # Convert m2 to hectares
            period = region.get('analysis_period', 'June 23-30, 2025')
            
            # Find investment score and explanation
            rec = next((r for r in all_recommendations if r.get('region') == region['region_name']), None)
            
            if rec:
                score = rec.get('score', rec.get('investment_score', rec.get('dynamic_score', 0)))
                confidence = rec.get('confidence', rec.get('confidence_level', 0.5))
                
                # Generate explanation based on score
                if score >= 80:
                    explanation = f"<b>Strong Buy</b> ({confidence:.0%} confidence)"
                elif score >= 60:
                    explanation = f"<b>Hold/Monitor</b> ({confidence:.0%} confidence)"
                else:
                    explanation = f"<b>Weak</b> ({confidence:.0%} confidence)"
                
                # Add reason for low scores
                if score < 60:
                    reasons = []
                    if changes < 100:
                        reasons.append("Very low activity")
                    elif changes < 1000:
                        reasons.append("Low development")
                    if area < 10:
                        reasons.append("Small area")
                    price_trend = rec.get('price_trend_30d', 0)
                    if price_trend < 0:
                        reasons.append(f"Price declining ({price_trend:.1f}%)")
                    elif price_trend < 2:
                        reasons.append("Stagnant prices")
                    infrastructure_score = rec.get('infrastructure_score', 0)
                    if infrastructure_score < 50:
                        reasons.append("Poor infrastructure")
                    
                    if reasons:
                        explanation += f": {', '.join(reasons[:2])}"
                elif score >= 80:
                    # Highlight positives for high scores
                    reasons = []
                    price_trend = rec.get('price_trend_30d', 0)
                    if price_trend > 10:
                        reasons.append(f"+{price_trend:.1f}% price growth")
                    if changes > 10000:
                        reasons.append(f"{changes:,} changes")
                    if reasons:
                        explanation += f": {', '.join(reasons[:2])}"
                
                # Check for missing data and add note
                data_sources = rec.get('data_sources', {})
                if isinstance(data_sources, dict):
                    availability = data_sources.get('availability', {})
                    missing = []
                    if not availability.get('market_data', True):
                        missing.append("Market")
                    if not availability.get('infrastructure_data', True):
                        missing.append("Infra")
                    if missing:
                        explanation += f" <i>(Limited: {'/'.join(missing)} API unavailable)</i>"
                
                score_str = f"{score:.1f}/100"
            else:
                score_str = "N/A"
                explanation = "Not scored"
            
            imagery_data.append([
                Paragraph(region_name, compact_style),
                Paragraph(f"{changes:,}", compact_style),
                Paragraph(f"{area:.1f}", compact_style),
                Paragraph(score_str, compact_style),
                Paragraph(explanation, compact_style),
                Paragraph(period, compact_style)
            ])
        
        if len(imagery_data) > 1:  # Only show table if there are regions to display
            imagery_table = Table(imagery_data, colWidths=[1.2*inch, 0.8*inch, 0.7*inch, 0.7*inch, 2.1*inch, 1.1*inch])
            imagery_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4A90E2')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (3, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#F0F8FF'), colors.white]),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#CCCCCC')),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(imagery_table)
            story.append(Spacer(1, 15))
        
        return story

    def _add_region_imagery(self, region_data: Dict[str, Any], investment_rec: Optional[Dict[str, Any]] = None) -> List:
        """Add before/after satellite imagery for a specific region"""
        story = []
        
        region_name = region_data.get('region_name', 'Unknown Region').replace('_', ' ').title()
        changes = region_data.get('change_count', 0)
        area_ha = region_data.get('total_area_m2', 0) / 10000
        
        # Add region header with investment info if available
        if investment_rec:
            score = investment_rec.get('score', investment_rec.get('investment_score', 0))
            confidence = investment_rec.get('confidence_level', investment_rec.get('confidence', 0.5))
            story.append(Paragraph(
                f"<b>🏆 {region_name}</b> - Investment Score: {score:.1f}/100 ({confidence:.0%} confidence)",
                self.styles['SubsectionHeader']
            ))
            
            # Add detailed investment factors
            story.append(Paragraph(
                f"<b>Development Activity:</b> {changes:,} land use changes detected across {area_ha:.1f} hectares",
                self.styles['Normal']
            ))
            
            # Extract and display key investment factors
            factors = []
            
            # Satellite-derived factors
            change_types = region_data.get('change_types', {})
            if change_types:
                total_changes = sum(change_types.values())
                # Highlight significant change types (Type 3 = built-up expansion, Type 4 = vegetation loss)
                if change_types.get(3, 0) > total_changes * 0.3:
                    factors.append(f"Heavy urban/built-up expansion ({change_types[3]:,} sites)")
                if change_types.get(4, 0) > total_changes * 0.2:
                    factors.append(f"Significant vegetation clearing ({change_types[4]:,} sites)")
            
            # Market factors from investment recommendation
            price_trend = investment_rec.get('price_trend_percent')
            if price_trend and price_trend > 5:
                factors.append(f"Strong property price growth (+{price_trend:.1f}%)")
            elif price_trend and price_trend > 0:
                factors.append(f"Moderate price appreciation (+{price_trend:.1f}%)")
            
            market_heat = investment_rec.get('market_heat', '').lower()
            if 'hot' in market_heat or 'very hot' in market_heat:
                factors.append("Hot real estate market")
            elif 'warm' in market_heat:
                factors.append("Active real estate market")
            
            infra_score = investment_rec.get('infrastructure_score', 0)
            infra_details = investment_rec.get('infrastructure_details', {})
            
            # Show infrastructure score
            if infra_score > 70:
                factors.append(f"Excellent infrastructure access ({infra_score:.0f}/100)")
            elif infra_score > 50:
                factors.append(f"Good infrastructure ({infra_score:.0f}/100)")
            
            # Show detailed infrastructure breakdown if available
            if infra_details and isinstance(infra_details, dict):
                infra_factors = []
                
                # Roads
                major_features = infra_details.get('major_features', [])
                roads = [f for f in major_features if f.get('type') == 'road']
                if roads:
                    infra_factors.append(f"{len(roads)} major roads nearby")
                
                # Airports
                airports = [f for f in major_features if f.get('type') == 'airport']
                if airports:
                    closest = min(airports, key=lambda x: x.get('distance_km', 999))
                    infra_factors.append(f"Airport: {closest.get('name', 'N/A')} ({closest.get('distance_km', 0):.1f}km)")
                
                # Railways
                railways = [f for f in major_features if f.get('type') == 'railway']
                if railways:
                    infra_factors.append(f"{len(railways)} railway lines")
                
                # Construction projects
                construction = infra_details.get('construction_projects', [])
                if construction:
                    infra_factors.append(f"{len(construction)} active construction projects")
                
                # Add reasoning if available
                reasoning = infra_details.get('reasoning', [])
                if reasoning:
                    for reason in reasoning[:2]:  # Show top 2 reasoning points
                        if reason not in infra_factors:  # Avoid duplication
                            infra_factors.append(reason)
                
                # Add infrastructure factors to main factors list
                if infra_factors:
                    factors.extend(infra_factors)
            
            # Development velocity
            dev_velocity = region_data.get('development_velocity')
            if dev_velocity and dev_velocity > 1.5:
                factors.append(f"Accelerating development pace ({dev_velocity:.1f}x baseline)")
            elif dev_velocity and dev_velocity > 1.0:
                factors.append(f"Sustained development activity")
            
            # Display factors
            if factors:
                story.append(Paragraph(
                    f"<b>Key Investment Factors:</b>",
                    self.styles['Normal']
                ))
                for factor in factors:
                    story.append(Paragraph(f"   • {factor}", self.styles['Normal']))
            
            # Show scoring methodology breakdown
            story.append(Paragraph(
                f"<b>Score Composition:</b>",
                self.styles['Normal']
            ))
            
            score_components = []
            if investment_rec.get('price_trend_30d') is not None:
                score_components.append(f"Market momentum: {investment_rec.get('price_trend_30d', 0):.1f}% price trend")
            if investment_rec.get('infrastructure_score'):
                score_components.append(f"Infrastructure: {investment_rec.get('infrastructure_score', 0):.0f}/100 quality rating")
            if changes > 0:
                score_components.append(f"Development activity: {changes:,} satellite-detected changes")
            
            for component in score_components:
                story.append(Paragraph(f"   • {component}", self.styles['Normal']))
            
            # Data availability warning if confidence is low
            data_sources = investment_rec.get('data_sources', {})
            if isinstance(data_sources, dict):
                availability = data_sources.get('availability', {})
                missing_sources = []
                if not availability.get('market_data', True):
                    missing_sources.append('market pricing')
                if not availability.get('infrastructure_data', True):
                    missing_sources.append('infrastructure APIs')
                
                if missing_sources and confidence < 0.6:
                    story.append(Paragraph(
                        f"<i>⚠️ Limited data: {', '.join(missing_sources)} unavailable. Score based primarily on satellite activity.</i>",
                        self.styles['Normal']
                    ))
        else:
            story.append(Paragraph(f"<b>📍 {region_name}</b>", self.styles['SubsectionHeader']))
            story.append(Paragraph(
                f"<b>Changes Detected:</b> {changes:,} | <b>Area Affected:</b> {area_ha:.1f} hectares",
                self.styles['Normal']
            ))
        
        story.append(Spacer(1, 10))
        
        # Try to add saved images if available
        saved_images = region_data.get('saved_images', {})
        if saved_images:
            import os
            
            # Check file sizes to determine if images have meaningful data
            before_true_path = saved_images.get('week_a_true_color')
            after_true_path = saved_images.get('week_b_true_color')
            before_false_path = saved_images.get('week_a_false_color')
            after_false_path = saved_images.get('week_b_false_color')
            
            # Use true color if files are large enough, otherwise try false color
            before_image_path = before_true_path
            after_image_path = after_true_path
            image_type_label = "True Color Satellite Imagery"
            
            # Check if true color images are too small (likely empty)
            if (before_true_path and os.path.exists(before_true_path) and 
                after_true_path and os.path.exists(after_true_path)):
                before_size = os.path.getsize(before_true_path)
                after_size = os.path.getsize(after_true_path)
                
                # If true color images are very small (< 5KB), try false color
                if before_size < 5000 or after_size < 5000:
                    if (before_false_path and os.path.exists(before_false_path) and
                        after_false_path and os.path.exists(after_false_path)):
                        before_false_size = os.path.getsize(before_false_path)
                        after_false_size = os.path.getsize(after_false_path)
                        
                        if before_false_size > before_size or after_false_size > after_size:
                            before_image_path = before_false_path
                            after_image_path = after_false_path
                            image_type_label = "False Color Satellite Imagery (NIR-Red-Green)"
            
            # Display meaningful change analysis instead of potentially empty images
            # Check if images are large enough to be meaningful
            meaningful_images = False
            images_displayed = False
            if before_image_path and after_image_path:
                if (os.path.exists(before_image_path) and os.path.exists(after_image_path) and
                    os.path.getsize(before_image_path) > 10000 and os.path.getsize(after_image_path) > 10000):  # At least 10KB each
                    meaningful_images = True
            
            if meaningful_images:
                try:
                    story.append(Paragraph(f"<b>{image_type_label}:</b>", self.styles['Normal']))
                    
                    # Create before/after comparison
                    before_img = ReportLabImage(before_image_path, width=2.5*inch, height=2*inch)
                    after_img = ReportLabImage(after_image_path, width=2.5*inch, height=2*inch)
                    
                    # Create a table for side-by-side images
                    img_table = Table([
                        ['BEFORE', 'AFTER'],
                        [before_img, after_img]
                    ], colWidths=[2.7*inch, 2.7*inch])
                    
                    img_table.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E8F4FD')),
                        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#CCCCCC'))
                    ]))
                    story.append(img_table)
                    story.append(Spacer(1, 10))
                    images_displayed = True
                        
                except Exception as e:
                    # If image loading fails, show explanatory text
                    story.append(Paragraph(
                        f"<b>Satellite Imagery Issue:</b> Before/after images could not be displayed. "
                        f"Error: {str(e)}",
                        self.styles['Normal']
                    ))
                    story.append(Spacer(1, 10))
                    images_displayed = False
            
            # If before/after images weren't displayed, show change statistics
            if not images_displayed:
                story.append(Paragraph(
                    f"<i>Note: Satellite imagery unavailable for this period. Analysis based on statistical change detection.</i>",
                    self.styles['Normal']
                ))
                story.append(Spacer(1, 5))
            
            # Add NDVI change image if available
            ndvi_image_path = saved_images.get('ndvi_change')
            if ndvi_image_path and os.path.exists(ndvi_image_path):
                try:
                    story.append(Paragraph(
                        "<b>Vegetation Change Analysis (NDVI):</b> "
                        "Red = vegetation loss/land clearing (potential construction sites), "
                        "Green = vegetation gain/revegetation",
                        self.styles['Normal']
                    ))
                    ndvi_img = ReportLabImage(ndvi_image_path, width=4*inch, height=3*inch)
                    story.append(ndvi_img)
                except Exception as e:
                    story.append(Paragraph(
                        f"<i>NDVI image could not be loaded: {str(e)}</i>",
                        self.styles['Normal']
                    ))
        else:
            # Fall back to URL-based imagery note if no saved images
            story.append(Paragraph(
                "<i>Satellite imagery available through CloudClearing dashboard</i>",
                self.styles['Normal']
            ))
        
        story.append(Spacer(1, 20))
        return story

    def _build_regional_breakdown(self, data: Dict[str, Any]) -> List:
        """Build detailed regional breakdown"""
        story = []
        
        story.append(PageBreak())
        story.append(Paragraph("📍 REGIONAL BREAKDOWN", self.styles['SectionHeader']))
        
        regions_analyzed = data.get('regions_analyzed', [])
        
        # Group by analysis type
        yogyakarta_regions = [r for r in regions_analyzed if r.get('analysis_type') == 'yogyakarta_region']
        
        if yogyakarta_regions:
            story.append(Paragraph("Yogyakarta Region Details:", self.styles['SubsectionHeader']))
            
            for region in sorted(yogyakarta_regions, key=lambda x: x['change_count'], reverse=True)[:8]:
                region_name = region['region_name'].replace('_', ' ').title()
                changes = region['change_count']
                area_ha = region['total_area_m2'] / 10000
                
                story.append(Paragraph(f"<b>{region_name}</b>", self.styles['Normal']))
                story.append(Paragraph(
                    f"Changes: {changes:,} | Area: {area_ha:.1f} ha | "
                    f"Density: {changes/area_ha:.1f} changes/ha",
                    self.styles['Normal']
                ))
                
                # Add satellite imagery information if available
                sat_images = region.get('satellite_images', {})
                if sat_images.get('week_a_true_color'):
                    week_a_date = sat_images.get('week_a_date', 'Unknown')
                    week_b_date = sat_images.get('week_b_date', 'Unknown')
                    story.append(Paragraph(
                        f"📡 <b>Satellite Imagery Available:</b> Before ({week_a_date}) | After ({week_b_date})",
                        self.styles['Normal']
                    ))
                    story.append(Paragraph(
                        f"<i>Note: Imagery URLs are authentication-protected and available through the system dashboard.</i>",
                        self.styles['Footer']
                    ))
                
                story.append(Spacer(1, 10))
        
        return story

    def _create_region_activity_chart(self, regions_data: List[Dict[str, Any]]) -> BytesIO:
        """Create a bar chart of regional activity"""
        # Sort regions by change count and take top 8
        top_regions = sorted(regions_data, key=lambda x: x['change_count'], reverse=True)[:8]
        
        region_names = [r['region_name'].replace('_', ' ').title() for r in top_regions]
        change_counts = [r['change_count'] for r in top_regions]
        
        # Create the chart
        plt.figure(figsize=(10, 6))
        bars = plt.bar(range(len(region_names)), change_counts, color='#2E86AB', alpha=0.8)
        
        # Customize the chart
        plt.title('Top Regions by Change Activity', fontsize=16, pad=20)
        plt.xlabel('Region', fontsize=12)
        plt.ylabel('Number of Changes', fontsize=12)
        plt.xticks(range(len(region_names)), region_names, rotation=45, ha='right')
        
        # Add value labels on bars
        for bar, count in zip(bars, change_counts):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(change_counts)*0.01,
                    f'{count:,}', ha='center', va='bottom', fontsize=10)
        
        plt.tight_layout()
        plt.grid(axis='y', alpha=0.3)
        
        # Save to BytesIO
        img_buffer = BytesIO()
        plt.savefig(img_buffer, format='PNG', dpi=150, bbox_inches='tight')
        plt.close()
        img_buffer.seek(0)
        
        return img_buffer

    def _build_footer(self, data: Dict[str, Any]) -> List:
        """Build document footer"""
        story = []
        
        story.append(Spacer(1, 30))
        story.append(Paragraph("_" * 80, self.styles['Footer']))
        story.append(Paragraph(
            f"Generated by CloudClearing Automated Monitor | "
            f"Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
            f"© 2025 CloudClearing Intelligence",
            self.styles['Footer']
        ))
        
        return story

def generate_pdf_from_json(json_file_path: str, output_dir: Optional[str] = None) -> str:
    """
    Convenience function to generate PDF report from JSON file
    
    Args:
        json_file_path: Path to monitoring JSON file
        output_dir: Directory to save PDF report
        
    Returns:
        Path to generated PDF file
    """
    generator = PDFReportGenerator()
    return generator.generate_executive_summary(json_file_path, output_dir)

if __name__ == "__main__":
    # Example usage
    import sys
    if len(sys.argv) > 1:
        pdf_path = generate_pdf_from_json(sys.argv[1])
        print(f"PDF report generated: {pdf_path}")
    else:
        print("Usage: python pdf_report_generator.py <json_file_path>")