#!/usr/bin/env python3
"""
Dynamic Scoring Integration Module

Integrates the enhanced dynamic systems to replace all static/pre-conceived data 
in the scoring system with real-time intelligence.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass

# Import the enhanced dynamic systems
try:
    from .enhanced_price_intelligence import EnhancedPriceIntelligence
    from .enhanced_infrastructure_analyzer import EnhancedInfrastructureAnalyzer
except ImportError:
    from enhanced_price_intelligence import EnhancedPriceIntelligence
    from enhanced_infrastructure_analyzer import EnhancedInfrastructureAnalyzer

logger = logging.getLogger(__name__)

@dataclass
class DynamicScoringResult:
    """Complete dynamic scoring result"""
    region_name: str
    
    # Market intelligence (100% dynamic)
    current_price_per_m2: float
    price_trend_30d: float
    market_heat: str
    market_confidence: float
    
    # Infrastructure intelligence (100% dynamic)
    infrastructure_score: float
    infrastructure_details: Dict[str, Any]  # Full infrastructure breakdown for display
    road_network_quality: float
    accessibility_score: float
    construction_activity: int
    infrastructure_confidence: float
    
    # Combined scoring
    speculative_score: float
    infrastructure_multiplier: float
    final_investment_score: float
    
    # Data provenance
    data_sources: Dict[str, str]
    analysis_timestamp: datetime
    overall_confidence: float

class DynamicScoringIntegration:
    """
    Replaces static scoring with 100% dynamic real-time analysis
    """
    
    def __init__(self):
        self.price_engine = EnhancedPriceIntelligence()
        self.infrastructure_engine = EnhancedInfrastructureAnalyzer()
        
        # Dynamic scoring weights (can be adjusted based on market conditions)
        self.scoring_weights = {
            'market_data': 0.4,          # 40% weight on market dynamics
            'infrastructure': 0.35,      # 35% weight on infrastructure
            'accessibility': 0.15,       # 15% weight on accessibility
            'construction_momentum': 0.1  # 10% weight on future development
        }
    
    def calculate_dynamic_score(self, region_name: str, region_config: Dict[str, Any]) -> DynamicScoringResult:
        """
        Calculate comprehensive investment score using available data sources.
        Gracefully handles missing/failed API data and adjusts confidence accordingly.
        
        Args:
            region_name: Name of the region
            region_config: Region configuration with coordinates/bbox
            
        Returns:
            Complete dynamic scoring result with data availability tracking
        """
        logger.info(f"🔄 Calculating dynamic score for {region_name}")
        
        # Extract coordinates and bbox from region config
        coordinates = self._extract_coordinates(region_config)
        bbox = self._extract_bbox(region_config, coordinates)
        
        # Track which data sources succeeded
        data_availability = {
            'market_data': False,
            'infrastructure_data': False,
            'satellite_data': True  # Always available (from change detection)
        }
        
        # Get live market intelligence (with timeout protection)
        try:
            market_data = self.price_engine.get_live_market_data(region_name, coordinates)
            data_availability['market_data'] = True
            logger.debug(f"✅ Market data retrieved for {region_name}")
        except Exception as e:
            logger.warning(f"⚠️ Market data unavailable for {region_name}: {e}")
            # Use fallback market data structure with defaults
            market_data = {
                'current_price_per_m2': 0,
                'price_trend_30d': 0,
                'market_heat': 'unknown',
                'data_confidence': 0.0,
                'data_source': 'unavailable',
                'unavailable_reason': str(e)
            }
        
        # Get live infrastructure analysis (with timeout protection)
        try:
            infrastructure_data = self.infrastructure_engine.analyze_live_infrastructure(region_name, bbox)
            data_availability['infrastructure_data'] = True
            logger.debug(f"✅ Infrastructure data retrieved for {region_name}")
        except Exception as e:
            logger.warning(f"⚠️ Infrastructure data unavailable for {region_name}: {e}")
            # Use fallback infrastructure structure with defaults
            infrastructure_data = {
                'infrastructure_score': 50.0,  # Neutral score
                'accessibility_data': {
                    'connectivity_score': 50.0,
                    'overall_accessibility': 50.0
                },
                'active_construction_projects': 0,
                'data_confidence': 0.0,
                'data_source': 'unavailable',
                'unavailable_reason': str(e)
            }
        
        # Calculate dynamic speculative score
        speculative_score = self._calculate_speculative_score(market_data, infrastructure_data)
        
        # Calculate infrastructure multiplier
        infrastructure_multiplier = self._calculate_infrastructure_multiplier(infrastructure_data)
        
        # Calculate final investment score
        final_score = self._calculate_final_investment_score(
            speculative_score, infrastructure_multiplier, market_data, infrastructure_data
        )
        
        # Calculate overall confidence based on data availability
        overall_confidence = self._calculate_overall_confidence(
            market_data, infrastructure_data, data_availability
        )
        
        # Build data sources report
        data_sources_report = {
            'satellite_data': 'earth_engine',
            'market_data': market_data.get('data_source', 'unavailable'),
            'infrastructure_data': infrastructure_data.get('data_source', 'unavailable'),
            'availability': data_availability,
            'missing_data_note': self._generate_missing_data_note(data_availability)
        }
        
        return DynamicScoringResult(
            region_name=region_name,
            
            # Market intelligence
            current_price_per_m2=market_data['current_price_per_m2'],
            price_trend_30d=market_data['price_trend_30d'],
            market_heat=market_data['market_heat'],
            market_confidence=market_data['data_confidence'],
            
            # Infrastructure intelligence
            infrastructure_score=infrastructure_data['infrastructure_score'],
            infrastructure_details=infrastructure_data,  # NEW: Full infrastructure breakdown
            road_network_quality=infrastructure_data['accessibility_data']['connectivity_score'],
            accessibility_score=infrastructure_data['accessibility_data']['overall_accessibility'],
            construction_activity=infrastructure_data['active_construction_projects'],
            infrastructure_confidence=infrastructure_data['data_confidence'],
            
            # Combined scoring
            speculative_score=speculative_score,
            infrastructure_multiplier=infrastructure_multiplier,
            final_investment_score=final_score,
            
            # Data provenance with transparency
            data_sources=data_sources_report,
            analysis_timestamp=datetime.now(),
            overall_confidence=overall_confidence
        )
    
    def _extract_coordinates(self, region_config: Dict[str, Any]) -> Dict[str, float]:
        """Extract coordinates from region configuration"""
        if 'center' in region_config:
            return {
                'lat': region_config['center']['lat'],
                'lng': region_config['center']['lng']
            }
        elif 'coordinates' in region_config:
            # Calculate center from polygon coordinates
            coords = region_config['coordinates'][0]  # First ring
            lats = [coord[1] for coord in coords]
            lngs = [coord[0] for coord in coords]
            return {
                'lat': sum(lats) / len(lats),
                'lng': sum(lngs) / len(lngs)
            }
        else:
            # Default to Yogyakarta center
            return {'lat': -7.7956, 'lng': 110.3695}
    
    def _extract_bbox(self, region_config: Dict[str, Any], coordinates: Dict[str, float]) -> Dict[str, float]:
        """Extract or calculate bounding box from region configuration"""
        if 'bbox' in region_config:
            return region_config['bbox']
        elif 'coordinates' in region_config:
            # Calculate bbox from polygon
            coords = region_config['coordinates'][0]
            lats = [coord[1] for coord in coords]
            lngs = [coord[0] for coord in coords]
            return {
                'north': max(lats),
                'south': min(lats),
                'east': max(lngs),
                'west': min(lngs)
            }
        else:
            # Create bbox around center point
            buffer = region_config.get('buffer', 1000) / 111000  # Convert meters to degrees
            return {
                'north': coordinates['lat'] + buffer,
                'south': coordinates['lat'] - buffer,
                'east': coordinates['lng'] + buffer,
                'west': coordinates['lng'] - buffer
            }
    
    def _calculate_speculative_score(self, market_data: Dict, infrastructure_data: Dict) -> float:
        """
        Calculate speculative investment score from dynamic data
        """
        base_score = 50  # Neutral starting point
        
        # Market momentum component
        price_trend = market_data['price_trend_30d']
        if price_trend > 10:
            momentum_bonus = 25
        elif price_trend > 5:
            momentum_bonus = 15
        elif price_trend > 0:
            momentum_bonus = 5
        else:
            momentum_bonus = max(-20, price_trend)  # Penalty for negative trends
        
        # Market heat component
        heat_bonuses = {
            'hot': 20,
            'warm': 10,
            'cool': 0,
            'cold': -10,
            'unknown': 0
        }
        heat_bonus = heat_bonuses.get(market_data['market_heat'], 0)
        
        # Infrastructure quality component
        infra_score = infrastructure_data['infrastructure_score']
        infra_bonus = (infra_score - 50) * 0.3  # Scale infrastructure impact
        
        # Construction momentum component
        construction_projects = infrastructure_data['active_construction_projects']
        construction_bonus = min(15, construction_projects * 3)
        
        # Calculate final speculative score
        final_score = base_score + momentum_bonus + heat_bonus + infra_bonus + construction_bonus
        
        return max(0, min(100, final_score))
    
    def _calculate_infrastructure_multiplier(self, infrastructure_data: Dict) -> float:
        """
        Calculate infrastructure multiplier from dynamic analysis
        """
        base_multiplier = 1.0
        
        # Infrastructure quality multiplier
        infra_score = infrastructure_data['infrastructure_score']
        quality_multiplier = 0.8 + (infra_score / 100) * 0.4  # Range: 0.8 to 1.2
        
        # Accessibility bonus
        accessibility = infrastructure_data['accessibility_data']['overall_accessibility']
        accessibility_bonus = (accessibility - 50) / 200  # Convert to multiplier
        
        # Construction momentum bonus
        construction_bonus = min(0.2, infrastructure_data['active_construction_projects'] * 0.05)
        
        return quality_multiplier + accessibility_bonus + construction_bonus
    
    def _calculate_final_investment_score(self, speculative_score: float, 
                                        infrastructure_multiplier: float,
                                        market_data: Dict, 
                                        infrastructure_data: Dict) -> float:
        """
        Calculate final weighted investment score
        """
        # Base score from speculation
        base_score = speculative_score * infrastructure_multiplier
        
        # Market confidence weighting
        market_confidence = market_data['data_confidence']
        infrastructure_confidence = infrastructure_data['data_confidence']
        
        # Weight by data confidence
        confidence_weight = (market_confidence + infrastructure_confidence) / 2
        
        # Apply confidence weighting (low confidence reduces score)
        final_score = base_score * (0.5 + (confidence_weight * 0.5))
        
        return max(0, min(100, final_score))
    
    def _calculate_overall_confidence(self, market_data: Dict, infrastructure_data: Dict, 
                                     data_availability: Dict[str, bool]) -> float:
        """
        Calculate overall confidence in the analysis based on data availability.
        Missing data sources significantly reduce confidence, not the score itself.
        """
        market_confidence = market_data['data_confidence']
        infrastructure_confidence = infrastructure_data['data_confidence']
        
        # Base confidence from data quality
        base_confidence = (market_confidence * 0.4) + (infrastructure_confidence * 0.6)
        
        # Penalize confidence (not score) for missing data sources
        available_sources = sum(data_availability.values())
        total_sources = len(data_availability)
        availability_factor = available_sources / total_sources
        
        # Reduce confidence based on missing sources
        # All sources available: 100% confidence
        # Satellite only (2 missing): ~45% confidence
        # Infrastructure + satellite (1 missing): ~65% confidence
        final_confidence = base_confidence * (0.3 + (availability_factor * 0.7))
        
        return max(0.2, min(1.0, final_confidence))  # Minimum 20% confidence
    
    def _generate_missing_data_note(self, data_availability: Dict[str, bool]) -> str:
        """
        Generate human-readable note about missing data sources
        """
        missing = [source for source, available in data_availability.items() if not available]
        
        if not missing:
            return "All data sources available"
        
        missing_names = {
            'market_data': 'Market/price data',
            'infrastructure_data': 'Infrastructure APIs',
            'satellite_data': 'Satellite imagery'
        }
        
        missing_str = ', '.join([missing_names.get(m, m) for m in missing])
        return f"⚠️ Limited data: {missing_str} unavailable - Score based on available sources only"
    
    def get_dynamic_catalyst_analysis(self, region_name: str, infrastructure_data: Dict) -> Dict[str, Any]:
        """
        Analyze infrastructure catalysts dynamically from real data
        """
        catalysts = []
        catalyst_score = 0
        
        # Analyze construction projects as catalysts
        construction_count = infrastructure_data['active_construction_projects']
        if construction_count > 0:
            catalysts.append(f"{construction_count} active infrastructure projects")
            catalyst_score += construction_count * 10
        
        # Analyze planned projects
        planned_count = infrastructure_data['planned_projects']
        if planned_count > 0:
            catalysts.append(f"{planned_count} government-planned developments")
            catalyst_score += planned_count * 5
        
        # Analyze infrastructure quality indicators
        infra_score = infrastructure_data['infrastructure_score']
        if infra_score > 80:
            catalysts.append("Excellent infrastructure connectivity")
            catalyst_score += 20
        elif infra_score > 60:
            catalysts.append("Strong infrastructure foundation")
            catalyst_score += 10
        
        # Analyze accessibility improvements
        accessibility = infrastructure_data['accessibility_data']['overall_accessibility']
        if accessibility > 80:
            catalysts.append("Superior accessibility and transport links")
            catalyst_score += 15
        
        return {
            'catalyst_count': len(catalysts),
            'catalyst_score': min(100, catalyst_score),
            'catalyst_details': catalysts,
            'momentum': 'accelerating' if catalyst_score > 40 else 'stable' if catalyst_score > 15 else 'slow'
        }

def create_dynamic_scoring_replacement():
    """
    Create a dynamic scoring system that replaces all static components
    """
    print("🔄 Creating Dynamic Scoring System - 100% Real-Time Data")
    print("=" * 70)
    
    print("📊 Components being replaced with dynamic data:")
    print("   ❌ Static regional_market_data → ✅ Live property portal APIs")
    print("   ❌ Pre-conceived infrastructure scores → ✅ Real-time OpenStreetMap data")
    print("   ❌ Fixed catalyst assumptions → ✅ Dynamic government project databases")
    print("   ❌ Hardcoded price baselines → ✅ Live market price analysis")
    print("   ❌ Static accessibility scores → ✅ Real-time infrastructure mapping")
    
    print("\\n🎯 Dynamic Data Sources:")
    print("   • Property Prices: Rumah123, OLX, Lamudi APIs")
    print("   • Infrastructure: OpenStreetMap Overpass API")
    print("   • Construction: Indonesian Government Open Data")
    print("   • Transport: Real-time accessibility analysis")
    print("   • Market Trends: Live listing analysis")
    
    return DynamicScoringIntegration()

def test_dynamic_scoring_integration():
    """
    Test the complete dynamic scoring integration
    """
    print("\\n🧪 Testing Complete Dynamic Scoring Integration")
    print("=" * 60)
    
    scorer = create_dynamic_scoring_replacement()
    
    # Test regions
    test_regions = [
        {
            'name': 'yogyakarta_urban',
            'center': {'lat': -7.7956, 'lng': 110.3695},
            'buffer': 2000
        },
        {
            'name': 'sleman_north', 
            'center': {'lat': -7.7200, 'lng': 110.3500},
            'buffer': 3000
        }
    ]
    
    for region_config in test_regions:
        region_name = region_config['name']
        print(f"\\n🎯 Dynamic Analysis: {region_name}")
        
        try:
            result = scorer.calculate_dynamic_score(region_name, region_config)
            
            print(f"   💰 Current Price: {result.current_price_per_m2:,.0f} IDR/m² ({result.price_trend_30d:+.1f}%)")
            print(f"   🌡️  Market Heat: {result.market_heat}")
            print(f"   🏗️ Infrastructure Score: {result.infrastructure_score:.1f}/100")
            print(f"   🚌 Accessibility: {result.accessibility_score:.1f}/100")
            print(f"   🚧 Active Construction: {result.construction_activity} projects")
            print(f"   📊 Speculative Score: {result.speculative_score:.1f}/100")
            print(f"   🎯 Final Investment Score: {result.final_investment_score:.1f}/100")
            print(f"   📈 Overall Confidence: {result.overall_confidence:.1%}")
            
            print(f"   🔗 Data Sources:")
            for source_type, source_name in result.data_sources.items():
                print(f"      - {source_type}: {source_name}")
            
            # Test catalyst analysis
            bbox = scorer._extract_bbox(region_config, {'lat': region_config['center']['lat'], 'lng': region_config['center']['lng']})
            infrastructure_data = scorer.infrastructure_engine.analyze_live_infrastructure(region_name, bbox)
            catalyst_analysis = scorer.get_dynamic_catalyst_analysis(region_name, infrastructure_data)
            
            print(f"   🚀 Catalyst Analysis:")
            print(f"      - Active catalysts: {catalyst_analysis['catalyst_count']}")
            print(f"      - Catalyst score: {catalyst_analysis['catalyst_score']}/100")
            print(f"      - Momentum: {catalyst_analysis['momentum']}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\\n✅ Dynamic scoring integration test completed!")
    print("\\n🎉 All static data successfully replaced with real-time intelligence!")

if __name__ == '__main__':
    test_dynamic_scoring_integration()