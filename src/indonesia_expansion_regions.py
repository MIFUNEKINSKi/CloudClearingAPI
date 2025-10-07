"""
Indonesia-Wide Expansion Regions
Comprehensive coverage for identifying emerging investment opportunities across Indonesia

This module defines strategic monitoring regions across:
- Java (complete coverage)
- Sumatra (key growth corridors)
- Bali & Nusa Tenggara (tourism & development zones)
- Kalimantan (resource & infrastructure corridors)
- Sulawesi (emerging growth areas)
"""

from dataclasses import dataclass
from typing import List, Tuple, Dict
import logging

logger = logging.getLogger(__name__)

@dataclass
class IndonesiaRegion:
    """Represents a strategic monitoring region in Indonesia"""
    name: str
    bbox: Tuple[float, float, float, float]  # west, south, east, north
    island: str
    province: str
    focus: str  # infrastructure, industrial, tourism, agricultural, urban, coastal
    priority: int  # 1=high, 2=medium, 3=low
    description: str = ""
    
    def area_km2(self) -> float:
        """Calculate approximate area in square kilometers"""
        import numpy as np
        west, south, east, north = self.bbox
        width_km = (east - west) * 111.32 * np.cos(np.radians((south + north) / 2))
        height_km = (north - south) * 110.54
        return abs(width_km * height_km)


class IndonesiaExpansionManager:
    """Manages comprehensive Indonesia-wide monitoring regions"""
    
    def __init__(self):
        self.java_regions = self._initialize_java_regions()
        self.sumatra_regions = self._initialize_sumatra_regions()
        self.bali_nusa_tenggara_regions = self._initialize_bali_nusa_tenggara_regions()
        self.kalimantan_regions = self._initialize_kalimantan_regions()
        self.sulawesi_regions = self._initialize_sulawesi_regions()
        self.papua_maluku_regions = self._initialize_papua_maluku_regions()
        
        # Combined list
        self.all_regions = (
            self.java_regions + 
            self.sumatra_regions + 
            self.bali_nusa_tenggara_regions +
            self.kalimantan_regions +
            self.sulawesi_regions +
            self.papua_maluku_regions
        )
    
    def _initialize_java_regions(self) -> List[IndonesiaRegion]:
        """Initialize comprehensive Java monitoring regions"""
        return [
            # === JAKARTA & SURROUNDINGS ===
            IndonesiaRegion(
                name="jakarta_north_sprawl",
                bbox=(106.70, -6.15, 106.90, -5.95),
                island="java",
                province="dki_jakarta",
                focus="urban",
                priority=1,
                description="North Jakarta urban expansion toward Bekasi"
            ),
            IndonesiaRegion(
                name="jakarta_south_suburbs",
                bbox=(106.75, -6.45, 106.95, -6.25),
                island="java",
                province="dki_jakarta",
                focus="urban",
                priority=1,
                description="South Jakarta suburban growth toward Depok"
            ),
            IndonesiaRegion(
                name="tangerang_bsd_corridor",
                bbox=(106.60, -6.35, 106.80, -6.15),
                island="java",
                province="banten",
                focus="urban",
                priority=1,
                description="Tangerang-BSD City development corridor"
            ),
            IndonesiaRegion(
                name="bekasi_industrial_belt",
                bbox=(106.95, -6.35, 107.15, -6.15),
                island="java",
                province="west_java",
                focus="industrial",
                priority=1,
                description="Bekasi industrial and logistics hub"
            ),
            IndonesiaRegion(
                name="cikarang_mega_industrial",
                bbox=(107.10, -6.35, 107.30, -6.15),
                island="java",
                province="west_java",
                focus="industrial",
                priority=1,
                description="Cikarang mega-industrial park"
            ),
            
            # === WEST JAVA ===
            IndonesiaRegion(
                name="bandung_north_expansion",
                bbox=(107.55, -6.85, 107.75, -6.65),
                island="java",
                province="west_java",
                focus="urban",
                priority=1,
                description="North Bandung urban expansion"
            ),
            IndonesiaRegion(
                name="bandung_east_tech_corridor",
                bbox=(107.65, -6.95, 107.85, -6.75),
                island="java",
                province="west_java",
                focus="technology",
                priority=1,
                description="East Bandung technology and education corridor"
            ),
            IndonesiaRegion(
                name="cirebon_port_industrial",
                bbox=(108.50, -6.80, 108.70, -6.60),
                island="java",
                province="west_java",
                focus="industrial",
                priority=2,
                description="Cirebon port and industrial development"
            ),
            IndonesiaRegion(
                name="subang_patimban_megaport",
                bbox=(107.70, -6.50, 108.00, -6.20),
                island="java",
                province="west_java",
                focus="infrastructure",
                priority=1,
                description="Patimban mega-port development zone"
            ),
            IndonesiaRegion(
                name="bogor_puncak_highland",
                bbox=(106.75, -6.70, 106.95, -6.50),
                island="java",
                province="west_java",
                focus="tourism",
                priority=2,
                description="Bogor-Puncak highland tourism and residential"
            ),
            
            # === CENTRAL JAVA ===
            IndonesiaRegion(
                name="semarang_port_expansion",
                bbox=(110.35, -7.05, 110.55, -6.85),
                island="java",
                province="central_java",
                focus="industrial",
                priority=1,
                description="Semarang port and industrial expansion"
            ),
            IndonesiaRegion(
                name="semarang_south_urban",
                bbox=(110.30, -7.15, 110.50, -6.95),
                island="java",
                province="central_java",
                focus="urban",
                priority=2,
                description="South Semarang urban growth"
            ),
            IndonesiaRegion(
                name="solo_raya_expansion",
                bbox=(110.75, -7.65, 110.95, -7.45),
                island="java",
                province="central_java",
                focus="urban",
                priority=2,
                description="Solo Raya metropolitan expansion"
            ),
            IndonesiaRegion(
                name="yogyakarta_urban_core",
                bbox=(110.32, -7.85, 110.42, -7.75),
                island="java",
                province="diy_yogyakarta",
                focus="urban",
                priority=2,
                description="Yogyakarta city core development"
            ),
            IndonesiaRegion(
                name="yogyakarta_kulon_progo_airport",
                bbox=(110.05, -7.99, 110.25, -7.78),
                island="java",
                province="diy_yogyakarta",
                focus="infrastructure",
                priority=1,
                description="Kulon Progo International Airport zone"
            ),
            IndonesiaRegion(
                name="magelang_borobudur_corridor",
                bbox=(110.15, -7.65, 110.35, -7.45),
                island="java",
                province="central_java",
                focus="tourism",
                priority=2,
                description="Magelang-Borobudur tourism corridor"
            ),
            IndonesiaRegion(
                name="purwokerto_south_expansion",
                bbox=(109.20, -7.50, 109.40, -7.30),
                island="java",
                province="central_java",
                focus="urban",
                priority=3,
                description="Purwokerto southern development"
            ),
            IndonesiaRegion(
                name="tegal_brebes_coastal",
                bbox=(108.95, -7.05, 109.15, -6.85),
                island="java",
                province="central_java",
                focus="coastal",
                priority=3,
                description="Tegal-Brebes coastal development"
            ),
            
            # === EAST JAVA ===
            IndonesiaRegion(
                name="surabaya_west_expansion",
                bbox=(112.60, -7.35, 112.80, -7.15),
                island="java",
                province="east_java",
                focus="urban",
                priority=1,
                description="West Surabaya urban expansion"
            ),
            IndonesiaRegion(
                name="surabaya_east_industrial",
                bbox=(112.75, -7.35, 112.95, -7.15),
                island="java",
                province="east_java",
                focus="industrial",
                priority=1,
                description="East Surabaya industrial zone"
            ),
            IndonesiaRegion(
                name="gresik_port_industrial",
                bbox=(112.60, -7.20, 112.80, -7.00),
                island="java",
                province="east_java",
                focus="industrial",
                priority=1,
                description="Gresik port and industrial complex"
            ),
            IndonesiaRegion(
                name="sidoarjo_delta_development",
                bbox=(112.65, -7.55, 112.85, -7.35),
                island="java",
                province="east_java",
                focus="urban",
                priority=2,
                description="Sidoarjo delta urban development"
            ),
            IndonesiaRegion(
                name="malang_south_highland",
                bbox=(112.55, -8.05, 112.75, -7.85),
                island="java",
                province="east_java",
                focus="tourism",
                priority=2,
                description="South Malang highland tourism zone"
            ),
            IndonesiaRegion(
                name="banyuwangi_ferry_corridor",
                bbox=(114.30, -8.35, 114.50, -8.15),
                island="java",
                province="east_java",
                focus="coastal",
                priority=2,
                description="Banyuwangi ferry terminal corridor"
            ),
            IndonesiaRegion(
                name="probolinggo_bromo_gateway",
                bbox=(113.15, -7.85, 113.35, -7.65),
                island="java",
                province="east_java",
                focus="tourism",
                priority=3,
                description="Probolinggo-Bromo gateway development"
            ),
            IndonesiaRegion(
                name="jember_southern_coast",
                bbox=(113.65, -8.35, 113.85, -8.15),
                island="java",
                province="east_java",
                focus="coastal",
                priority=3,
                description="Jember southern coastal development"
            ),
            
            # === BANTEN ===
            IndonesiaRegion(
                name="serang_cilegon_industrial",
                bbox=(106.00, -6.10, 106.20, -5.90),
                island="java",
                province="banten",
                focus="industrial",
                priority=1,
                description="Serang-Cilegon industrial mega-complex"
            ),
            IndonesiaRegion(
                name="merak_port_corridor",
                bbox=(105.95, -5.95, 106.15, -5.75),
                island="java",
                province="banten",
                focus="infrastructure",
                priority=2,
                description="Merak port and logistics corridor"
            ),
            IndonesiaRegion(
                name="anyer_carita_coastal",
                bbox=(105.85, -6.20, 106.05, -6.00),
                island="java",
                province="banten",
                focus="tourism",
                priority=3,
                description="Anyer-Carita coastal resort development"
            ),
        ]
    
    def _initialize_sumatra_regions(self) -> List[IndonesiaRegion]:
        """Initialize key Sumatra monitoring regions"""
        return [
            # === NORTH SUMATRA ===
            IndonesiaRegion(
                name="medan_kuala_namu_corridor",
                bbox=(98.60, 3.50, 98.80, 3.70),
                island="sumatra",
                province="north_sumatra",
                focus="infrastructure",
                priority=1,
                description="Medan-Kuala Namu Airport corridor"
            ),
            IndonesiaRegion(
                name="medan_belawan_port",
                bbox=(98.65, 3.70, 98.85, 3.90),
                island="sumatra",
                province="north_sumatra",
                focus="industrial",
                priority=1,
                description="Belawan Port industrial zone"
            ),
            IndonesiaRegion(
                name="lake_toba_tourism_zone",
                bbox=(98.75, 2.50, 99.05, 2.80),
                island="sumatra",
                province="north_sumatra",
                focus="tourism",
                priority=2,
                description="Lake Toba tourism development zone"
            ),
            
            # === SOUTH SUMATRA ===
            IndonesiaRegion(
                name="palembang_boom_baru_port",
                bbox=(104.70, -3.05, 104.90, -2.85),
                island="sumatra",
                province="south_sumatra",
                focus="industrial",
                priority=1,
                description="Palembang Boom Baru port expansion"
            ),
            IndonesiaRegion(
                name="palembang_jakabaring_expansion",
                bbox=(104.75, -3.05, 104.95, -2.85),
                island="sumatra",
                province="south_sumatra",
                focus="urban",
                priority=2,
                description="Jakabaring sports city expansion"
            ),
            
            # === LAMPUNG ===
            IndonesiaRegion(
                name="bandar_lampung_south_expansion",
                bbox=(105.20, -5.50, 105.40, -5.30),
                island="sumatra",
                province="lampung",
                focus="urban",
                priority=2,
                description="South Bandar Lampung expansion"
            ),
            IndonesiaRegion(
                name="bakauheni_ferry_corridor",
                bbox=(105.70, -5.95, 105.90, -5.75),
                island="sumatra",
                province="lampung",
                focus="infrastructure",
                priority=2,
                description="Bakauheni ferry terminal corridor"
            ),
            
            # === RIAU & BATAM ===
            IndonesiaRegion(
                name="batam_industrial_expansion",
                bbox=(104.00, 1.00, 104.20, 1.20),
                island="sumatra",
                province="riau_islands",
                focus="industrial",
                priority=1,
                description="Batam industrial zone expansion"
            ),
            IndonesiaRegion(
                name="pekanbaru_urban_growth",
                bbox=(101.40, 0.45, 101.60, 0.65),
                island="sumatra",
                province="riau",
                focus="urban",
                priority=2,
                description="Pekanbaru urban development"
            ),
        ]
    
    def _initialize_bali_nusa_tenggara_regions(self) -> List[IndonesiaRegion]:
        """Initialize Bali & Nusa Tenggara regions"""
        return [
            # === BALI ===
            IndonesiaRegion(
                name="denpasar_north_expansion",
                bbox=(115.15, -8.60, 115.35, -8.40),
                island="bali",
                province="bali",
                focus="urban",
                priority=1,
                description="North Denpasar urban expansion"
            ),
            IndonesiaRegion(
                name="sanur_beach_resort",
                bbox=(115.25, -8.75, 115.35, -8.65),
                island="bali",
                province="bali",
                focus="tourism",
                priority=2,
                description="Sanur beach resort development"
            ),
            IndonesiaRegion(
                name="canggu_seminyak_corridor",
                bbox=(115.10, -8.70, 115.20, -8.60),
                island="bali",
                province="bali",
                focus="tourism",
                priority=1,
                description="Canggu-Seminyak tourism corridor"
            ),
            IndonesiaRegion(
                name="ubud_north_highland",
                bbox=(115.20, -8.55, 115.40, -8.35),
                island="bali",
                province="bali",
                focus="tourism",
                priority=2,
                description="North Ubud highland tourism"
            ),
            IndonesiaRegion(
                name="tabanan_west_coast",
                bbox=(115.05, -8.65, 115.25, -8.45),
                island="bali",
                province="bali",
                focus="tourism",
                priority=2,
                description="West Tabanan coastal development"
            ),
            
            # === LOMBOK ===
            IndonesiaRegion(
                name="mataram_urban_expansion",
                bbox=(116.05, -8.65, 116.25, -8.45),
                island="lombok",
                province="west_nusa_tenggara",
                focus="urban",
                priority=2,
                description="Mataram urban expansion"
            ),
            IndonesiaRegion(
                name="lombok_mandalika_resort",
                bbox=(116.25, -8.95, 116.45, -8.75),
                island="lombok",
                province="west_nusa_tenggara",
                focus="tourism",
                priority=1,
                description="Mandalika mega-resort development"
            ),
        ]
    
    def _initialize_kalimantan_regions(self) -> List[IndonesiaRegion]:
        """Initialize Kalimantan (Borneo) regions"""
        return [
            # === EAST KALIMANTAN / NEW CAPITAL ===
            IndonesiaRegion(
                name="nusantara_capital_core",
                bbox=(116.95, -1.00, 117.15, -0.80),
                island="kalimantan",
                province="east_kalimantan",
                focus="infrastructure",
                priority=1,
                description="IKN Nusantara capital city core"
            ),
            IndonesiaRegion(
                name="nusantara_balikpapan_corridor",
                bbox=(116.80, -1.35, 117.00, -1.15),
                island="kalimantan",
                province="east_kalimantan",
                focus="infrastructure",
                priority=1,
                description="IKN-Balikpapan development corridor"
            ),
            IndonesiaRegion(
                name="balikpapan_port_industrial",
                bbox=(116.80, -1.35, 117.00, -1.15),
                island="kalimantan",
                province="east_kalimantan",
                focus="industrial",
                priority=2,
                description="Balikpapan port and industrial zone"
            ),
            IndonesiaRegion(
                name="samarinda_urban_expansion",
                bbox=(117.10, -0.60, 117.30, -0.40),
                island="kalimantan",
                province="east_kalimantan",
                focus="urban",
                priority=2,
                description="Samarinda urban expansion"
            ),
            
            # === SOUTH KALIMANTAN ===
            IndonesiaRegion(
                name="banjarmasin_port_development",
                bbox=(114.55, -3.40, 114.75, -3.20),
                island="kalimantan",
                province="south_kalimantan",
                focus="industrial",
                priority=2,
                description="Banjarmasin port development"
            ),
            
            # === WEST KALIMANTAN ===
            IndonesiaRegion(
                name="pontianak_urban_growth",
                bbox=(109.30, -0.10, 109.50, 0.10),
                island="kalimantan",
                province="west_kalimantan",
                focus="urban",
                priority=3,
                description="Pontianak urban development"
            ),
        ]
    
    def _initialize_sulawesi_regions(self) -> List[IndonesiaRegion]:
        """Initialize Sulawesi regions"""
        return [
            # === SOUTH SULAWESI ===
            IndonesiaRegion(
                name="makassar_urban_expansion",
                bbox=(119.40, -5.25, 119.60, -5.05),
                island="sulawesi",
                province="south_sulawesi",
                focus="urban",
                priority=1,
                description="Makassar urban expansion"
            ),
            IndonesiaRegion(
                name="makassar_port_corridor",
                bbox=(119.35, -5.15, 119.55, -4.95),
                island="sulawesi",
                province="south_sulawesi",
                focus="industrial",
                priority=2,
                description="Makassar port and logistics corridor"
            ),
            
            # === NORTH SULAWESI ===
            IndonesiaRegion(
                name="manado_tourism_expansion",
                bbox=(124.80, 1.40, 125.00, 1.60),
                island="sulawesi",
                province="north_sulawesi",
                focus="tourism",
                priority=2,
                description="Manado tourism expansion"
            ),
            IndonesiaRegion(
                name="bitung_port_industrial",
                bbox=(125.15, 1.40, 125.35, 1.60),
                island="sulawesi",
                province="north_sulawesi",
                focus="industrial",
                priority=2,
                description="Bitung port industrial zone"
            ),
        ]
    
    def _initialize_papua_maluku_regions(self) -> List[IndonesiaRegion]:
        """Initialize Papua & Maluku regions"""
        return [
            # === PAPUA ===
            IndonesiaRegion(
                name="jayapura_urban_development",
                bbox=(140.65, -2.65, 140.85, -2.45),
                island="papua",
                province="papua",
                focus="urban",
                priority=3,
                description="Jayapura urban development"
            ),
            
            # === MALUKU ===
            IndonesiaRegion(
                name="ambon_tourism_expansion",
                bbox=(128.15, -3.75, 128.35, -3.55),
                island="maluku",
                province="maluku",
                focus="tourism",
                priority=3,
                description="Ambon tourism expansion"
            ),
        ]
    
    # === FILTERING AND QUERY METHODS ===
    
    def get_all_regions(self) -> List[IndonesiaRegion]:
        """Get all monitoring regions"""
        return self.all_regions
    
    def get_java_regions(self) -> List[IndonesiaRegion]:
        """Get all Java regions"""
        return self.java_regions
    
    def get_regions_by_island(self, island: str) -> List[IndonesiaRegion]:
        """Get regions filtered by island"""
        return [r for r in self.all_regions if r.island.lower() == island.lower()]
    
    def get_regions_by_priority(self, priority: int) -> List[IndonesiaRegion]:
        """Get regions filtered by priority"""
        return [r for r in self.all_regions if r.priority == priority]
    
    def get_regions_by_focus(self, focus: str) -> List[IndonesiaRegion]:
        """Get regions filtered by focus area"""
        return [r for r in self.all_regions if r.focus.lower() == focus.lower()]
    
    def get_priority1_java_regions(self) -> List[IndonesiaRegion]:
        """Get Priority 1 Java regions (highest investment potential)"""
        return [r for r in self.java_regions if r.priority == 1]
    
    def get_region_by_name(self, name: str):
        """Get a specific region by name"""
        for region in self.all_regions:
            if region.name.lower() == name.lower():
                return region
        return None
    
    def get_region_bbox_dict(self, name: str):
        """Get region bbox as dictionary (compatible with automated_monitor)"""
        region = self.get_region_by_name(name)
        if region:
            west, south, east, north = region.bbox
            return {
                'west': west,
                'south': south,
                'east': east,
                'north': north
            }
        return None
    
    def get_summary_stats(self) -> Dict:
        """Get summary statistics"""
        return {
            'total_regions': len(self.all_regions),
            'java_regions': len(self.java_regions),
            'sumatra_regions': len(self.sumatra_regions),
            'bali_nusa_tenggara_regions': len(self.bali_nusa_tenggara_regions),
            'kalimantan_regions': len(self.kalimantan_regions),
            'sulawesi_regions': len(self.sulawesi_regions),
            'papua_maluku_regions': len(self.papua_maluku_regions),
            'priority_1_count': len([r for r in self.all_regions if r.priority == 1]),
            'priority_2_count': len([r for r in self.all_regions if r.priority == 2]),
            'priority_3_count': len([r for r in self.all_regions if r.priority == 3]),
            'total_coverage_km2': sum(r.area_km2() for r in self.all_regions)
        }


# Global instance
_expansion_manager = None

def get_expansion_manager() -> IndonesiaExpansionManager:
    """Get the global expansion manager instance"""
    global _expansion_manager
    if _expansion_manager is None:
        _expansion_manager = IndonesiaExpansionManager()
    return _expansion_manager


# Convenience function for automated_monitor integration
def get_all_java_region_names() -> List[str]:
    """Get list of all Java region names for automated monitoring"""
    manager = get_expansion_manager()
    return [region.name for region in manager.get_java_regions()]


def get_priority1_java_region_names() -> List[str]:
    """Get list of Priority 1 Java regions for initial rollout"""
    manager = get_expansion_manager()
    return [region.name for region in manager.get_priority1_java_regions()]


def get_all_indonesia_region_names() -> List[str]:
    """Get list of all Indonesia regions for full nationwide monitoring"""
    manager = get_expansion_manager()
    return [region.name for region in manager.get_all_regions()]
