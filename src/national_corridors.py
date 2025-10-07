"""
Indonesia National Expansion - Strategic Corridor Definitions
CloudClearingAPI Phase 3: Indonesia-Wide Coverage

This module defines the expanded monitoring regions for strategic
real estate investment across Indonesia's major growth corridors.
"""

from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
import logging

logger = logging.getLogger(__name__)

@dataclass
class StrategicCorridor:
    """Enhanced area definition for strategic investment corridors"""
    name: str
    bbox: Tuple[float, float, float, float]  # west, south, east, north
    priority: int = 1
    island: str = 'unknown'
    focus: str = 'general'
    investment_tier: str = 'tier2'  # tier1, tier2, tier3
    infrastructure_catalysts: Optional[List[str]] = None
    expected_roi_years: Tuple[int, int] = (3, 5)
    risk_level: str = 'medium'  # low, medium, high, high-reward
    market_maturity: str = 'emerging'  # emerging, developing, mature
    key_cities: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.infrastructure_catalysts is None:
            self.infrastructure_catalysts = []
        if self.key_cities is None:
            self.key_cities = []
    
    def area_km2(self) -> float:
        """Calculate approximate area in square kilometers"""
        west, south, east, north = self.bbox
        width_km = (east - west) * 111.32 * np.cos(np.radians((south + north) / 2))
        height_km = (north - south) * 110.54
        return abs(width_km * height_km)
    
    def investment_score(self) -> float:
        """Calculate strategic investment score (0-100)"""
        # Base scoring logic
        priority_score = (4 - self.priority) * 20  # Priority 1 = 60, Priority 3 = 20
        
        # Tier weighting
        tier_multipliers = {'tier1': 1.0, 'tier2': 0.8, 'tier3': 0.6}
        tier_weight = tier_multipliers.get(self.investment_tier, 0.5)
        
        # Risk adjustment (higher risk can mean higher reward)
        risk_adjustments = {
            'low': 0.9,
            'medium': 1.0, 
            'high': 1.1,
            'high-reward': 1.3
        }
        risk_weight = risk_adjustments.get(self.risk_level, 1.0)
        
        # Infrastructure catalyst bonus
        infra_bonus = min(20, len(self.infrastructure_catalysts or []) * 5)
        
        base_score = priority_score * tier_weight * risk_weight + infra_bonus
        return min(100, max(0, base_score))

class IndonesiaNationalManager:
    """Manages strategic corridors across Indonesia for Phase 3 expansion"""
    
    def __init__(self):
        self.corridors = self._initialize_national_corridors()
    
    def _initialize_national_corridors(self) -> List[StrategicCorridor]:
        """Initialize all strategic corridors across Indonesia"""
        return [
            # TIER 1 EXPANSION TARGETS
            
            # 1. North Sumatra: Medan-Binjai-Deli Serdang Corridor
            StrategicCorridor(
                name="Medan Metro Expansion",
                bbox=(98.45, 3.30, 98.95, 3.80),
                priority=1,
                island="sumatra",
                focus="industrial_port",
                investment_tier="tier1",
                infrastructure_catalysts=[
                    "Kualanamu Airport expansion",
                    "Belawan Port upgrades", 
                    "Trans-Sumatra toll road",
                    "Palm oil processing facilities"
                ],
                expected_roi_years=(3, 5),
                risk_level="medium",
                market_maturity="developing",
                key_cities=["Medan", "Binjai", "Deli Serdang"]
            ),
            
            # 2. West Java: Bandung-Cirebon-Patimban Corridor  
            StrategicCorridor(
                name="West Java Industrial Triangle",
                bbox=(107.50, -6.60, 108.20, -6.00),
                priority=1,
                island="java",
                focus="port_industrial",
                investment_tier="tier1",
                infrastructure_catalysts=[
                    "Patimban Port operational",
                    "Jakarta-Bandung HSR",
                    "Jakarta-Cikampek toll expansion",
                    "Industrial estate development"
                ],
                expected_roi_years=(2, 4),
                risk_level="low",
                market_maturity="developing",
                key_cities=["Subang", "Purwakarta", "Karawang", "Cirebon"]
            ),
            
            # 3. East Kalimantan: Nusantara Capital Region (IKN)
            StrategicCorridor(
                name="Nusantara Capital Corridor",
                bbox=(116.80, -1.50, 117.50, -0.80),
                priority=1,
                island="kalimantan",
                focus="new_capital",
                investment_tier="tier1",
                infrastructure_catalysts=[
                    "IKN Phase 1 construction",
                    "Sepinggan Airport expansion",
                    "New road networks",
                    "Government relocation"
                ],
                expected_roi_years=(5, 10),
                risk_level="high-reward",
                market_maturity="emerging",
                key_cities=["Penajam Paser Utara", "Balikpapan", "Samarinda"]
            ),
            
            # 4. South Sulawesi: Makassar Metro Expansion
            StrategicCorridor(
                name="Makassar Gateway Expansion",
                bbox=(119.25, -5.50, 119.75, -5.00),
                priority=1,
                island="sulawesi",
                focus="regional_gateway",
                investment_tier="tier1", 
                infrastructure_catalysts=[
                    "Sultan Hasanuddin Airport expansion",
                    "Makassar Port development",
                    "Trans-Sulawesi toll roads",
                    "Eastern Indonesia hub development"
                ],
                expected_roi_years=(4, 6),
                risk_level="medium",
                market_maturity="developing",
                key_cities=["Makassar", "Gowa", "Takalar", "Maros"]
            ),
            
            # 5. Lampung: Trans-Sumatra Corridor + Bakauheni
            StrategicCorridor(
                name="Lampung Logistics Triangle",
                bbox=(105.00, -5.70, 105.70, -5.00),
                priority=1,
                island="sumatra",
                focus="logistics_gateway",
                investment_tier="tier1",
                infrastructure_catalysts=[
                    "Trans-Sumatra toll completion",
                    "Bakauheni Port expansion", 
                    "Java-Sumatra bridge speculation",
                    "Radin Inten Airport development"
                ],
                expected_roi_years=(5, 8),
                risk_level="medium-high",
                market_maturity="emerging",
                key_cities=["Bandar Lampung", "Metro", "Bakauheni"]
            ),
            
            # TIER 2 EXPANSION TARGETS
            
            # 6. Central Kalimantan: Palangka Raya Growth Triangle
            StrategicCorridor(
                name="Central Kalimantan Administrative Hub",
                bbox=(113.70, -2.50, 114.20, -2.00),
                priority=2,
                island="kalimantan",
                focus="administrative_mining",
                investment_tier="tier2",
                infrastructure_catalysts=[
                    "Tjilik Riwut Airport upgrades",
                    "Mining logistics expansion",
                    "Administrative center growth",
                    "Kapuas River port development"
                ],
                expected_roi_years=(6, 8),
                risk_level="medium",
                market_maturity="emerging",
                key_cities=["Palangka Raya", "Kahayan"]
            ),
            
            # 7. South Sumatra: Palembang-Lampung Industrial Corridor
            StrategicCorridor(
                name="South Sumatra Energy Corridor",
                bbox=(104.40, -3.30, 105.00, -2.70),
                priority=2,
                island="sumatra",
                focus="energy_industrial",
                investment_tier="tier2",
                infrastructure_catalysts=[
                    "Jakabaring Airport expansion",
                    "Boom Baru Port development",
                    "Energy sector projects",
                    "Industrial zone expansion"
                ],
                expected_roi_years=(4, 7),
                risk_level="medium",
                market_maturity="developing",
                key_cities=["Palembang", "Ogan Komering Ilir"]
            ),
            
            # 8. East Java: Malang-Batu-Blitar Triangle
            StrategicCorridor(
                name="East Java Agro-Tourism Triangle",
                bbox=(112.40, -8.30, 112.90, -7.80),
                priority=2,
                island="java",
                focus="agro_tourism",
                investment_tier="tier2",
                infrastructure_catalysts=[
                    "Abdul Rachman Saleh Airport",
                    "Agro-industrial development",
                    "Tourism infrastructure",
                    "Surabaya spillover effects"
                ],
                expected_roi_years=(5, 7),
                risk_level="medium",
                market_maturity="developing",
                key_cities=["Malang", "Batu", "Blitar"]
            ),
            
            # 9. North Kalimantan: Nunukan Border Economic Zone
            StrategicCorridor(
                name="North Kalimantan Border Zone",
                bbox=(117.50, 4.00, 117.90, 4.40),
                priority=2,
                island="kalimantan",
                focus="border_trade",
                investment_tier="tier2",
                infrastructure_catalysts=[
                    "Malaysia border infrastructure",
                    "Nunukan Airport development",
                    "Cross-border trade facilities",
                    "Strategic location advantages"
                ],
                expected_roi_years=(6, 9),
                risk_level="high",
                market_maturity="emerging",
                key_cities=["Nunukan", "Sebatik"]
            ),
            
            # 10. West Sumatra: Padang-Bukittinggi Corridor
            StrategicCorridor(
                name="West Sumatra Cultural Gateway",
                bbox=(100.20, -0.70, 100.70, -0.20),
                priority=2,
                island="sumatra",
                focus="cultural_gateway",
                investment_tier="tier2",
                infrastructure_catalysts=[
                    "Minangkabau Airport expansion",
                    "West Sumatra toll roads",
                    "Cultural tourism development",
                    "Regional gateway functions"
                ],
                expected_roi_years=(5, 8),
                risk_level="medium",
                market_maturity="emerging", 
                key_cities=["Padang", "Bukittinggi", "Padang Pariaman"]
            ),
            
            # EXISTING HIGH-PERFORMING REGIONS (from current system)
            
            StrategicCorridor(
                name="Solo Expansion Zone",
                bbox=(110.75, -7.65, 110.95, -7.45),
                priority=1,
                island="java",
                focus="urban_expansion",
                investment_tier="tier1",
                infrastructure_catalysts=[
                    "Adi Somarmo Airport",
                    "Solo-Yogya toll road",
                    "Industrial development",
                    "Urban sprawl patterns"
                ],
                expected_roi_years=(2, 4),
                risk_level="low",
                market_maturity="mature",
                key_cities=["Surakarta", "Boyolali", "Karanganyar"]
            ),
            
            StrategicCorridor(
                name="Kulon Progo Infrastructure Zone",
                bbox=(110.05, -7.99, 110.25, -7.78),
                priority=1,
                island="java",
                focus="infrastructure",
                investment_tier="tier1",
                infrastructure_catalysts=[
                    "YIA International Airport",
                    "Airport city development",
                    "Toll road connections",
                    "New town projects"
                ],
                expected_roi_years=(2, 5),
                risk_level="low",
                market_maturity="developing",
                key_cities=["Wates", "Sentolo", "Temon"]
            )
        ]
    
    def get_tier1_corridors(self) -> List[StrategicCorridor]:
        """Get Tier 1 strategic corridors for immediate expansion"""
        return [c for c in self.corridors if c.investment_tier == 'tier1']
    
    def get_tier2_corridors(self) -> List[StrategicCorridor]:
        """Get Tier 2 corridors for secondary expansion"""
        return [c for c in self.corridors if c.investment_tier == 'tier2']
    
    def get_corridors_by_island(self, island: str) -> List[StrategicCorridor]:
        """Get corridors filtered by island"""
        return [c for c in self.corridors if c.island.lower() == island.lower()]
    
    def get_top_investment_opportunities(self, count: int = 10) -> List[StrategicCorridor]:
        """Get top corridors ranked by investment score"""
        sorted_corridors = sorted(self.corridors, 
                                key=lambda x: x.investment_score(), 
                                reverse=True)
        return sorted_corridors[:count]
    
    def generate_expansion_plan(self) -> Dict[str, Any]:
        """Generate comprehensive expansion plan"""
        tier1 = self.get_tier1_corridors()
        tier2 = self.get_tier2_corridors()
        
        total_area = sum(c.area_km2() for c in self.corridors)
        
        by_island = {}
        for corridor in self.corridors:
            if corridor.island not in by_island:
                by_island[corridor.island] = []
            by_island[corridor.island].append(corridor.name)
        
        return {
            'total_corridors': len(self.corridors),
            'tier1_count': len(tier1),
            'tier2_count': len(tier2),
            'total_coverage_km2': total_area,
            'coverage_by_island': by_island,
            'top_opportunities': [
                {
                    'name': c.name,
                    'score': c.investment_score(),
                    'tier': c.investment_tier,
                    'roi_years': f"{c.expected_roi_years[0]}-{c.expected_roi_years[1]}",
                    'risk': c.risk_level
                }
                for c in self.get_top_investment_opportunities(10)
            ],
            'investment_catalysts': [
                catalyst 
                for corridor in self.corridors 
                for catalyst in (corridor.infrastructure_catalysts or [])
            ]
        }

# Global instance
_national_manager = None

def get_national_manager() -> IndonesiaNationalManager:
    """Get the global national expansion manager"""
    global _national_manager
    if _national_manager is None:
        _national_manager = IndonesiaNationalManager()
    return _national_manager

def generate_expansion_report():
    """Generate comprehensive expansion report"""
    manager = get_national_manager()
    plan = manager.generate_expansion_plan()
    
    print("🇮🇩 INDONESIA NATIONAL EXPANSION PLAN")
    print("="*50)
    print(f"Total Strategic Corridors: {plan['total_corridors']}")
    print(f"Tier 1 (Immediate): {plan['tier1_count']}")
    print(f"Tier 2 (Secondary): {plan['tier2_count']}")
    print(f"Total Coverage: {plan['total_coverage_km2']:,.0f} km²")
    print()
    
    print("🏆 TOP 10 INVESTMENT OPPORTUNITIES:")
    for i, opp in enumerate(plan['top_opportunities'], 1):
        print(f"{i:2d}. {opp['name']:<35} | Score: {opp['score']:5.1f} | {opp['tier']} | {opp['roi_years']} years | {opp['risk']}")
    
    print()
    print("🗺️ COVERAGE BY ISLAND:")
    for island, corridors in plan['coverage_by_island'].items():
        print(f"{island.capitalize()}: {len(corridors)} corridors")
        for corridor in corridors:
            print(f"  - {corridor}")
    
    return plan

if __name__ == "__main__":
    generate_expansion_report()