"""
Multi-region management for CloudClearingAPI

This module provides functionality for managing multiple areas of interest
across Indonesia and implementing automated discovery of overlooked development areas.
"""

from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
import logging

logger = logging.getLogger(__name__)

@dataclass
class AreaOfInterest:
    """Represents an area of interest for monitoring"""
    name: str
    bbox: Tuple[float, float, float, float]  # west, south, east, north
    priority: int = 1
    island: str = 'unknown'
    focus: str = 'general'
    
    def area_km2(self) -> float:
        """Calculate approximate area in square kilometers"""
        west, south, east, north = self.bbox
        # Rough calculation using average latitude
        width_km = (east - west) * 111.32 * np.cos(np.radians((south + north) / 2))
        height_km = (north - south) * 110.54
        return abs(width_km * height_km)
    
    def to_ee_geometry(self):
        """Convert bbox to Earth Engine geometry"""
        try:
            import ee
            west, south, east, north = self.bbox
            return ee.Geometry.Rectangle([west, south, east, north])
        except ImportError:
            logger.warning("Earth Engine not available for geometry conversion")
            return None

class RegionManager:
    """Manages multiple areas of interest across Indonesia"""
    
    def __init__(self):
        self.areas = self._initialize_priority_areas()
    
    def _initialize_priority_areas(self) -> List[AreaOfInterest]:
        """Initialize the priority monitoring areas across Indonesia"""
        return [
            # Java Priority Areas
            AreaOfInterest(
                name="Kulon Progo Airport Zone",
                bbox=(110.05, -7.99, 110.25, -7.78),
                priority=1,
                island="java", 
                focus="infrastructure"
            ),
            AreaOfInterest(
                name="Subang-Patimban Port Corridor",
                bbox=(107.70, -6.50, 108.00, -6.20),
                priority=1,
                island="java",
                focus="industrial"
            ),
            AreaOfInterest(
                name="Greater Bandung Transportation Hub",
                bbox=(107.45, -7.05, 107.75, -6.75), 
                priority=1,
                island="java",
                focus="transportation"
            ),
            
            # Sumatra Priority Areas
            AreaOfInterest(
                name="Medan Suburban Belt",
                bbox=(98.55, 3.40, 98.85, 3.70),
                priority=1,
                island="sumatra",
                focus="urban"
            ),
            
            # Bali Priority Areas
            AreaOfInterest(
                name="West Bali Resort Belt", 
                bbox=(115.05, -8.65, 115.25, -8.40),
                priority=1,
                island="bali",
                focus="tourism"
            ),
            
            # Additional monitoring areas
            AreaOfInterest(
                name="Central Java Industrial Zone",
                bbox=(110.20, -7.10, 110.50, -6.80),
                priority=2,
                island="java",
                focus="industrial"
            ),
            AreaOfInterest(
                name="East Java Coastal Development",
                bbox=(112.50, -7.80, 112.80, -7.50),
                priority=2, 
                island="java",
                focus="coastal"
            ),
            AreaOfInterest(
                name="Palembang Expansion Zone",
                bbox=(104.60, -3.10, 104.90, -2.80),
                priority=2,
                island="sumatra", 
                focus="urban"
            ),
            AreaOfInterest(
                name="Denpasar Urban Sprawl",
                bbox=(115.15, -8.75, 115.45, -8.45),
                priority=2,
                island="bali",
                focus="urban"
            ),
            AreaOfInterest(
                name="North Sumatra Agricultural Belt",
                bbox=(98.80, 3.10, 99.10, 3.40), 
                priority=3,
                island="sumatra",
                focus="agriculture"
            )
        ]
    
    def get_all_regions(self) -> List[AreaOfInterest]:
        """Get all registered areas of interest"""
        return self.areas
    
    def get_regions_by_priority(self, priority: int) -> List[AreaOfInterest]:
        """Get areas filtered by priority level"""
        return [area for area in self.areas if area.priority == priority]
    
    def get_regions_by_island(self, island: str) -> List[AreaOfInterest]:
        """Get areas filtered by island"""
        return [area for area in self.areas if area.island.lower() == island.lower()]
    
    def get_total_coverage(self) -> float:
        """Get total area coverage in km²"""
        return sum(area.area_km2() for area in self.areas)
    
    def get_region_by_name(self, name: str) -> Optional[AreaOfInterest]:
        """Get a region by its name"""
        for area in self.areas:
            if area.name.lower() == name.lower():
                return area
        return None
    
    def get_region_bbox(self, name: str) -> Optional[Dict[str, float]]:
        """Get a region's bounding box by name as a dictionary"""
        # First check if it's in the defined areas
        area = self.get_region_by_name(name)
        if area:
            west, south, east, north = area.bbox
            return {
                'west': west,
                'south': south,
                'east': east,
                'north': north
            }
        
        # Default regions for the automated monitor (Yogyakarta area focus)
        default_regions = {
            'yogyakarta_urban': {
                'west': 110.32, 'south': -7.85, 'east': 110.42, 'north': -7.75
            },
            'yogyakarta_periurban': {
                'west': 110.25, 'south': -7.95, 'east': 110.55, 'north': -7.65
            },
            'sleman_north': {
                'west': 110.30, 'south': -7.75, 'east': 110.50, 'north': -7.55
            },
            'bantul_south': {
                'west': 110.30, 'south': -8.05, 'east': 110.50, 'north': -7.85
            },
            'kulonprogo_west': {
                'west': 110.05, 'south': -7.95, 'east': 110.35, 'north': -7.75
            },
            'gunungkidul_east': {
                'west': 110.50, 'south': -8.15, 'east': 110.80, 'north': -7.95
            },
            'magelang_corridor': {
                'west': 110.15, 'south': -7.65, 'east': 110.35, 'north': -7.45
            },
            'solo_expansion': {
                'west': 110.75, 'south': -7.65, 'east': 110.95, 'north': -7.45
            },
            'semarang_industrial': {
                'west': 110.35, 'south': -7.05, 'east': 110.55, 'north': -6.85
            },
            'surakarta_suburbs': {
                'west': 110.80, 'south': -7.65, 'east': 111.00, 'north': -7.45
            }
        }
        
        return default_regions.get(name.lower())

    def get_coverage_by_island(self) -> Dict[str, Dict[str, Any]]:
        """Get coverage statistics by island"""
        islands = {}
        for area in self.areas:
            if area.island not in islands:
                islands[area.island] = {
                    'count': 0,
                    'total_area_km2': 0.0,
                    'areas': []
                }
            islands[area.island]['count'] += 1
            islands[area.island]['total_area_km2'] += area.area_km2()
            islands[area.island]['areas'].append(area.name)
        
        return islands

class OverlookedAreaDetector:
    """Detects potentially overlooked areas for development monitoring"""
    
    def __init__(self):
        self.weights = {
            'nightlights': 0.30,    # Low nightlights = undeveloped
            'population': 0.25,     # Low population = room for growth  
            'roads': 0.25,         # Low road density = underdeveloped
            'proximity': 0.20      # High proximity = development pressure
        }
    
    def calculate_overlooked_score(self, 
                                 nightlights: float,
                                 population_density: float, 
                                 road_density: float,
                                 distance_to_city: float) -> float:
        """
        Calculate overlooked area score (0-100, higher = more overlooked)
        
        Args:
            nightlights: VIIRS nighttime lights (0-100)
            population_density: People per km² 
            road_density: Road km per km²
            distance_to_city: Distance to nearest major city (km)
        """
        
        # Normalize inputs (higher score = more "overlooked")
        nightlights_score = max(0, 100 - nightlights)  # Lower lights = higher score
        
        # Population density score (optimal around 10-100 people/km²)
        if population_density < 10:
            pop_score = 50  # Too sparse
        elif population_density < 100: 
            pop_score = 100  # Good potential
        else:
            pop_score = max(0, 100 - (population_density - 100) / 10)  # Too dense
        
        # Road density score (lower density = higher potential)
        road_score = max(0, 100 - road_density * 10)
        
        # Proximity score (closer to cities = higher development pressure)
        if distance_to_city > 50:
            proximity_score = 0  # Too far
        else:
            proximity_score = 100 - (distance_to_city * 2)  # Closer = higher score
        
        # Weighted combination
        total_score = (
            self.weights['nightlights'] * nightlights_score +
            self.weights['population'] * pop_score + 
            self.weights['roads'] * road_score +
            self.weights['proximity'] * proximity_score
        )
        
        return min(100, max(0, total_score))
    
    def generate_candidate_grid(self, bbox: Tuple[float, float, float, float], 
                              grid_size_km: float = 2.0) -> List[Tuple[float, float, float, float]]:
        """Generate a grid of candidate areas within the bounding box"""
        west, south, east, north = bbox
        
        # Convert km to degrees (approximate)
        lat_step = grid_size_km / 110.54
        lon_step = grid_size_km / (111.32 * np.cos(np.radians((south + north) / 2)))
        
        candidates = []
        lat = south
        while lat < north:
            lon = west
            while lon < east:
                candidate_bbox = (
                    lon, 
                    lat,
                    min(lon + lon_step, east),
                    min(lat + lat_step, north)
                )
                candidates.append(candidate_bbox)
                lon += lon_step
            lat += lat_step
        
        return candidates

# Global instance
_region_manager = None

def get_region_manager() -> RegionManager:
    """Get the global region manager instance"""
    global _region_manager
    if _region_manager is None:
        _region_manager = RegionManager()
    return _region_manager