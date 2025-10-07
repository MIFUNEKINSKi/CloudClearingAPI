"""
Infrastructure Intelligence Module

Integrates real infrastructure data (roads, utilities, planned developments) 
to enhance speculative scoring accuracy beyond heuristics.

Author: CloudClearingAPI Team  
Date: September 2025
"""

import requests
import json
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon, box
import numpy as np
from datetime import datetime, timedelta
import ee

logger = logging.getLogger(__name__)

@dataclass
class InfrastructureFeature:
    """Container for infrastructure data"""
    feature_type: str      # 'highway', 'railway', 'airport', 'port'
    name: str
    geometry: Any          # Shapely geometry
    importance: str        # 'primary', 'secondary', 'tertiary'
    status: str           # 'existing', 'under_construction', 'planned'
    distance_km: float    # Distance from analysis area
    impact_score: float   # 0-100

class InfrastructureAnalyzer:
    """
    Analyzes real infrastructure data to enhance investment scoring
    """
    
    def __init__(self):
        self.osm_base_url = "https://overpass-api.de/api/interpreter"
        self.infrastructure_weights = {
            # Road infrastructure
            'motorway': 100,
            'trunk': 90, 
            'primary': 80,
            'secondary': 60,
            'tertiary': 40,
            'motorway_construction': 95,
            'trunk_construction': 85,
            
            # Railways
            'rail': 75,
            'light_rail': 65,
            'subway': 70,
            'rail_construction': 80,
            
            # Aviation
            'aerodrome': 90,
            'airport': 95,
            'helipad': 30,
            
            # Ports and logistics
            'harbour': 85,
            'port': 90,
            'logistics': 70
        }
        
        # Distance decay factors (how importance decreases with distance)
        self.distance_decay = {
            'motorway': {'max_distance': 10, 'half_life': 3},      # Highway impact up to 10km
            'airport': {'max_distance': 25, 'half_life': 8},       # Airport impact up to 25km  
            'railway': {'max_distance': 5, 'half_life': 2},        # Rail impact up to 5km
            'port': {'max_distance': 15, 'half_life': 5}           # Port impact up to 15km
        }

    def analyze_infrastructure_context(self, 
                                     bbox: Dict[str, float],
                                     region_name: str) -> Dict[str, Any]:
        """
        Analyze infrastructure context around a region using real data
        
        Args:
            bbox: Bounding box coordinates
            region_name: Name of the region being analyzed
            
        Returns:
            Infrastructure analysis results
        """
        
        analysis = {
            'infrastructure_score': 50,  # Base score
            'major_features': [],
            'construction_projects': [],
            'planned_developments': [],
            'accessibility_score': 50,
            'logistics_score': 50,
            'reasoning': []
        }
        
        try:
            # Expand bbox for infrastructure search (look 20km beyond region)
            expanded_bbox = self._expand_bbox(bbox, expansion_km=20)
            
            # Query OpenStreetMap for infrastructure
            roads_data = self._query_osm_roads(expanded_bbox)
            airports_data = self._query_osm_airports(expanded_bbox)
            railways_data = self._query_osm_railways(expanded_bbox)
            
            # Analyze each infrastructure type
            road_analysis = self._analyze_road_infrastructure(roads_data, bbox)
            airport_analysis = self._analyze_airport_infrastructure(airports_data, bbox)
            railway_analysis = self._analyze_railway_infrastructure(railways_data, bbox)
            
            # Combine analyses
            analysis.update(self._combine_infrastructure_analysis(
                road_analysis, airport_analysis, railway_analysis, region_name
            ))
            
        except Exception as e:
            logger.warning(f"Infrastructure analysis failed for {region_name}: {e}")
            analysis['reasoning'].append("⚠️ Infrastructure data unavailable - using regional defaults")
            
            # Fallback to regional knowledge
            analysis.update(self._get_regional_infrastructure_fallback(region_name))
        
        return analysis

    def _expand_bbox(self, bbox: Dict[str, float], expansion_km: float) -> Dict[str, float]:
        """Expand bounding box by specified kilometers"""
        # Rough conversion: 1 degree ≈ 111km
        expansion_deg = expansion_km / 111.0
        
        return {
            'west': bbox['west'] - expansion_deg,
            'south': bbox['south'] - expansion_deg, 
            'east': bbox['east'] + expansion_deg,
            'north': bbox['north'] + expansion_deg
        }

    def _query_osm_roads(self, bbox: Dict[str, float]) -> List[Dict]:
        """Query OpenStreetMap for road infrastructure"""
        
        overpass_query = f"""
        [out:json][timeout:30];
        (
          way["highway"~"^(motorway|trunk|primary|secondary)$"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
          way["highway"~"^(motorway|trunk|primary)_construction$"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
        );
        out geom;
        """
        
        try:
            response = requests.post(self.osm_base_url, data=overpass_query, timeout=30)
            return response.json().get('elements', [])
        except Exception as e:
            logger.warning(f"OSM road query failed: {e}")
            return []

    def _query_osm_airports(self, bbox: Dict[str, float]) -> List[Dict]:
        """Query OpenStreetMap for airports"""
        
        overpass_query = f"""
        [out:json][timeout:30];
        (
          way["aeroway"="aerodrome"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
          node["aeroway"="aerodrome"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
          way["aeroway"="airport"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
        );
        out geom;
        """
        
        try:
            response = requests.post(self.osm_base_url, data=overpass_query, timeout=30)
            return response.json().get('elements', [])
        except Exception as e:
            logger.warning(f"OSM airport query failed: {e}")
            return []

    def _query_osm_railways(self, bbox: Dict[str, float]) -> List[Dict]:
        """Query OpenStreetMap for railway infrastructure"""
        
        overpass_query = f"""
        [out:json][timeout:30];
        (
          way["railway"="rail"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
          way["railway"="light_rail"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
          way["railway"="construction"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
        );
        out geom;
        """
        
        try:
            response = requests.post(self.osm_base_url, data=overpass_query, timeout=30)
            return response.json().get('elements', [])
        except Exception as e:
            logger.warning(f"OSM railway query failed: {e}")
            return []

    def _analyze_road_infrastructure(self, roads_data: List[Dict], target_bbox: Dict[str, float]) -> Dict[str, Any]:
        """Analyze road infrastructure impact"""
        
        analysis = {
            'score': 0,
            'major_roads': [],
            'construction_roads': [],
            'accessibility_multiplier': 1.0
        }
        
        target_center = Point(
            (target_bbox['west'] + target_bbox['east']) / 2,
            (target_bbox['south'] + target_bbox['north']) / 2
        )
        
        for road in roads_data:
            try:
                highway_type = road.get('tags', {}).get('highway', '')
                road_name = road.get('tags', {}).get('name', f'Unnamed {highway_type}')
                
                # Calculate distance to target region
                if road.get('geometry'):
                    coords = [(node['lon'], node['lat']) for node in road['geometry']]
                    if len(coords) >= 2:
                        road_line = LineString(coords)
                        distance_km = target_center.distance(road_line) * 111  # Rough km conversion
                        
                        # Apply distance decay
                        base_weight = self.infrastructure_weights.get(highway_type, 0)
                        if distance_km <= self.distance_decay.get('motorway', {}).get('max_distance', 10):
                            decay = np.exp(-distance_km / self.distance_decay.get('motorway', {}).get('half_life', 3))
                            weighted_score = base_weight * decay
                            
                            analysis['score'] += weighted_score
                            
                            feature_info = {
                                'name': road_name,
                                'type': highway_type,
                                'distance_km': round(distance_km, 1),
                                'impact_score': round(weighted_score, 1)
                            }
                            
                            if 'construction' in highway_type:
                                analysis['construction_roads'].append(feature_info)
                            else:
                                analysis['major_roads'].append(feature_info)
                
            except Exception as e:
                logger.debug(f"Error processing road: {e}")
                continue
        
        # Calculate accessibility multiplier
        if analysis['score'] > 200:
            analysis['accessibility_multiplier'] = 1.5  # Excellent access
        elif analysis['score'] > 100:
            analysis['accessibility_multiplier'] = 1.3  # Good access
        elif analysis['score'] > 50:
            analysis['accessibility_multiplier'] = 1.1  # Moderate access
        
        return analysis

    def _analyze_airport_infrastructure(self, airports_data: List[Dict], target_bbox: Dict[str, float]) -> Dict[str, Any]:
        """Analyze airport infrastructure impact"""
        
        analysis = {
            'score': 0,
            'airports': [],
            'aviation_multiplier': 1.0
        }
        
        target_center = Point(
            (target_bbox['west'] + target_bbox['east']) / 2,
            (target_bbox['south'] + target_bbox['north']) / 2
        )
        
        for airport in airports_data:
            try:
                airport_name = airport.get('tags', {}).get('name', 'Unnamed Airport')
                airport_type = airport.get('tags', {}).get('aeroway', 'aerodrome')
                
                # Get airport location
                if airport['type'] == 'node':
                    airport_point = Point(airport['lon'], airport['lat'])
                elif airport.get('geometry'):
                    # For ways, use centroid
                    coords = [(node['lon'], node['lat']) for node in airport['geometry']]
                    if coords:
                        airport_polygon = Polygon(coords) if len(coords) > 2 else Point(coords[0])
                        airport_point = airport_polygon.centroid
                    else:
                        continue
                else:
                    continue
                
                distance_km = target_center.distance(airport_point) * 111
                
                # Apply distance decay for airports
                if distance_km <= self.distance_decay.get('airport', {}).get('max_distance', 25):
                    base_weight = self.infrastructure_weights.get('airport', 95)
                    decay = np.exp(-distance_km / self.distance_decay.get('airport', {}).get('half_life', 8))
                    weighted_score = base_weight * decay
                    
                    analysis['score'] += weighted_score
                    analysis['airports'].append({
                        'name': airport_name,
                        'type': airport_type,
                        'distance_km': round(distance_km, 1),
                        'impact_score': round(weighted_score, 1)
                    })
                
            except Exception as e:
                logger.debug(f"Error processing airport: {e}")
                continue
        
        # Aviation multiplier for tourism/business development
        if analysis['score'] > 150:
            analysis['aviation_multiplier'] = 1.4
        elif analysis['score'] > 75:
            analysis['aviation_multiplier'] = 1.2
        
        return analysis

    def _analyze_railway_infrastructure(self, railways_data: List[Dict], target_bbox: Dict[str, float]) -> Dict[str, Any]:
        """Analyze railway infrastructure impact"""
        
        analysis = {
            'score': 0,
            'railways': [],
            'transit_multiplier': 1.0
        }
        
        target_center = Point(
            (target_bbox['west'] + target_bbox['east']) / 2,
            (target_bbox['south'] + target_bbox['north']) / 2
        )
        
        for railway in railways_data:
            try:
                railway_type = railway.get('tags', {}).get('railway', 'rail')
                railway_name = railway.get('tags', {}).get('name', f'Railway {railway_type}')
                
                if railway.get('geometry'):
                    coords = [(node['lon'], node['lat']) for node in railway['geometry']]
                    if len(coords) >= 2:
                        railway_line = LineString(coords)
                        distance_km = target_center.distance(railway_line) * 111
                        
                        if distance_km <= self.distance_decay.get('railway', {}).get('max_distance', 5):
                            base_weight = self.infrastructure_weights.get(railway_type, 75)
                            decay = np.exp(-distance_km / self.distance_decay.get('railway', {}).get('half_life', 2))
                            weighted_score = base_weight * decay
                            
                            analysis['score'] += weighted_score
                            analysis['railways'].append({
                                'name': railway_name,
                                'type': railway_type,
                                'distance_km': round(distance_km, 1),
                                'impact_score': round(weighted_score, 1)
                            })
                
            except Exception as e:
                logger.debug(f"Error processing railway: {e}")
                continue
        
        if analysis['score'] > 100:
            analysis['transit_multiplier'] = 1.3
        elif analysis['score'] > 50:
            analysis['transit_multiplier'] = 1.15
        
        return analysis

    def _combine_infrastructure_analysis(self, 
                                       road_analysis: Dict, 
                                       airport_analysis: Dict,
                                       railway_analysis: Dict,
                                       region_name: str) -> Dict[str, Any]:
        """Combine all infrastructure analyses into final score"""
        
        # Weighted combination
        total_score = (
            road_analysis['score'] * 0.4 +      # Roads most important
            airport_analysis['score'] * 0.35 +   # Airports very important
            railway_analysis['score'] * 0.25     # Railways moderately important
        )
        
        # Calculate multipliers
        accessibility_multiplier = max(
            road_analysis['accessibility_multiplier'],
            railway_analysis['transit_multiplier']
        )
        
        aviation_multiplier = airport_analysis['aviation_multiplier']
        
        final_score = min(100, total_score * accessibility_multiplier * aviation_multiplier)
        
        # Generate reasoning
        reasoning = []
        
        # Road infrastructure
        major_roads = road_analysis['major_roads']
        construction_roads = road_analysis['construction_roads']
        
        if major_roads:
            reasoning.append(f"🛣️ {len(major_roads)} major roads within range")
        if construction_roads:
            reasoning.append(f"🚧 {len(construction_roads)} roads under construction - major development signal")
        
        # Airport infrastructure  
        airports = airport_analysis['airports']
        if airports:
            closest_airport = min(airports, key=lambda x: x['distance_km'])
            reasoning.append(f"✈️ Airport access: {closest_airport['name']} ({closest_airport['distance_km']}km)")
        
        # Railway infrastructure
        railways = railway_analysis['railways']
        if railways:
            reasoning.append(f"🚄 Railway connectivity: {len(railways)} lines")
        
        # Overall assessment
        if final_score > 80:
            reasoning.append("🌟 EXCELLENT infrastructure connectivity")
        elif final_score > 60:
            reasoning.append("✅ Good infrastructure access")
        elif final_score > 40:
            reasoning.append("⚠️ Limited infrastructure - higher risk")
        
        return {
            'infrastructure_score': round(final_score, 1),
            'major_features': major_roads + airports + railways,
            'construction_projects': construction_roads,
            'accessibility_score': round(road_analysis['score'], 1),
            'logistics_score': round((road_analysis['score'] + railway_analysis['score']) / 2, 1),
            'reasoning': reasoning
        }

    def _get_regional_infrastructure_fallback(self, region_name: str) -> Dict[str, Any]:
        """Fallback infrastructure scoring based on regional knowledge"""
        
        # Regional infrastructure knowledge base
        regional_scores = {
            'solo_expansion': {
                'infrastructure_score': 85,
                'reasoning': ['✈️ Solo Airport expansion planned', '🛣️ Major highway access', '🚄 Railway connectivity']
            },
            'yogyakarta_periurban': {
                'infrastructure_score': 80,
                'reasoning': ['✈️ New International Airport corridor', '🛣️ Ring road development']
            },
            'gunungkidul_east': {
                'infrastructure_score': 70,
                'reasoning': ['🛣️ Coastal highway planned', '🌊 Tourism corridor development']
            },
            'kulonprogo_west': {
                'infrastructure_score': 82,
                'reasoning': ['✈️ New International Airport', '🛣️ Airport connector roads']
            },
            'semarang_industrial': {
                'infrastructure_score': 88,
                'reasoning': ['🚢 Major port access', '🛣️ Industrial highway', '🚄 Railway freight']
            },
            'surakarta_suburbs': {
                'infrastructure_score': 75,
                'reasoning': ['🛣️ Ring road planned', '🏭 Logistics hub development']
            }
        }
        
        return regional_scores.get(region_name, {
            'infrastructure_score': 50,
            'reasoning': ['📍 Regional infrastructure data unavailable']
        })