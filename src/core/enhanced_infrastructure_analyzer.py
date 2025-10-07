#!/usr/bin/env python3
"""
Enhanced Dynamic Infrastructure Analyzer

Replaces static infrastructure assumptions with real-time data from:
- OpenStreetMap Overpass API for current infrastructure
- Indonesian Government APIs for planned projects  
- Construction permit databases
- Real-time traffic and accessibility analysis
"""

import requests
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import numpy as np
import time
import re

logger = logging.getLogger(__name__)

class EnhancedInfrastructureAnalyzer:
    """
    Dynamic infrastructure analysis using real-time data sources
    """
    
    def __init__(self):
        self.overpass_url = "https://overpass-api.de/api/interpreter"
        self.nominatim_url = "https://nominatim.openstreetmap.org/search"
        
        # Indonesian government data sources
        self.gov_data_sources = {
            'construction_permits': 'https://data.go.id/api/3/action/datastore_search',
            'infrastructure_budget': 'https://data.go.id/api/3/action/package_search',
            'transportation_projects': 'https://data.go.id/api/3/action/datastore_search'
        }
        
        # Infrastructure scoring weights
        self.infrastructure_weights = {
            'motorway': 100,
            'trunk': 90,
            'primary': 80,
            'secondary': 60,
            'tertiary': 40,
            'rail': 85,
            'subway': 90,
            'airport': 95,
            'port': 90,
            'construction': 120  # Future infrastructure gets bonus
        }
        
        # Cache for expensive API calls
        self.cache = {}
        self.cache_duration = 3600  # 1 hour
    
    def analyze_live_infrastructure(self, region_name: str, bbox: Dict[str, float]) -> Dict[str, Any]:
        """
        Analyze infrastructure using real-time data sources
        
        Args:
            region_name: Name of the region
            bbox: Bounding box {'north': float, 'south': float, 'east': float, 'west': float}
            
        Returns:
            Comprehensive infrastructure analysis
        """
        cache_key = f"{region_name}_{bbox['north']:.4f}_{bbox['south']:.4f}"
        
        # Check cache
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if (datetime.now() - timestamp).seconds < self.cache_duration:
                logger.info(f"Using cached infrastructure data for {region_name}")
                return cached_data
        
        logger.info(f"Fetching live infrastructure data for {region_name}")
        
        try:
            # Get current infrastructure from OpenStreetMap
            current_infrastructure = self._fetch_osm_infrastructure(bbox)
            
            # Get construction and planned projects
            construction_projects = self._fetch_construction_projects(region_name, bbox)
            
            # Get government infrastructure plans
            planned_projects = self._fetch_government_plans(region_name)
            
            # Analyze accessibility
            accessibility_data = self._analyze_accessibility(current_infrastructure, bbox)
            
            # Calculate comprehensive infrastructure score
            infrastructure_analysis = self._calculate_infrastructure_score(
                region_name, current_infrastructure, construction_projects, 
                planned_projects, accessibility_data
            )
            
            # Cache results
            self.cache[cache_key] = (infrastructure_analysis, datetime.now())
            
            return infrastructure_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing infrastructure for {region_name}: {e}")
            return self._generate_fallback_analysis(region_name)
    
    def _fetch_osm_infrastructure(self, bbox: Dict[str, float]) -> Dict[str, Any]:
        """
        Fetch current infrastructure from OpenStreetMap
        """
        # Overpass API query for comprehensive infrastructure
        query = f"""
        [out:json][timeout:25];
        (
          // Roads
          way["highway"~"^(motorway|trunk|primary|secondary|tertiary)$"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
          way["highway"]["construction"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
          
          // Railways
          way["railway"~"^(rail|subway|light_rail)$"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
          way["railway"]["construction"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
          
          // Aviation
          way["aeroway"~"^(runway|taxiway)$"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
          node["aeroway"="aerodrome"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
          
          // Ports and logistics
          way["harbour"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
          node["amenity"="port"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
          
          // Public transport
          node["amenity"="bus_station"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
          node["public_transport"="station"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
          
          // Utilities
          way["power"="line"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
          node["amenity"="fuel"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
        );
        out geom;
        """
        
        try:
            response = requests.post(
                self.overpass_url,
                data={'data': query},
                timeout=30,
                headers={'User-Agent': 'CloudClearingAPI/1.0'}
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._process_osm_data(data)
            else:
                logger.warning(f"Overpass API returned status {response.status_code}")
                
        except Exception as e:
            logger.error(f"Overpass API error: {e}")
        
        return {'elements': [], 'processed': {}}
    
    def _process_osm_data(self, osm_data: Dict) -> Dict[str, Any]:
        """
        Process and categorize OSM infrastructure data
        """
        processed = {
            'roads': {'motorway': [], 'trunk': [], 'primary': [], 'secondary': [], 'tertiary': []},
            'railways': {'rail': [], 'subway': [], 'light_rail': []},
            'aviation': {'airport': [], 'runway': []},
            'ports': {'harbour': [], 'port': []},
            'public_transport': {'bus_station': [], 'train_station': []},
            'construction': {'road': [], 'rail': [], 'other': []},
            'utilities': {'power_line': [], 'fuel_station': []},
            'total_elements': 0
        }
        
        elements = osm_data.get('elements', [])
        processed['total_elements'] = len(elements)
        
        for element in elements:
            tags = element.get('tags', {})
            
            # Categorize roads
            if 'highway' in tags:
                highway_type = tags['highway']
                if highway_type in processed['roads']:
                    processed['roads'][highway_type].append(element)
                elif 'construction' in tags:
                    processed['construction']['road'].append(element)
            
            # Categorize railways
            elif 'railway' in tags:
                railway_type = tags['railway']
                if railway_type in processed['railways']:
                    processed['railways'][railway_type].append(element)
                elif 'construction' in tags:
                    processed['construction']['rail'].append(element)
            
            # Categorize aviation
            elif 'aeroway' in tags:
                processed['aviation']['runway'].append(element)
            elif tags.get('aeroway') == 'aerodrome':
                processed['aviation']['airport'].append(element)
            
            # Categorize ports
            elif 'harbour' in tags:
                processed['ports']['harbour'].append(element)
            elif tags.get('amenity') == 'port':
                processed['ports']['port'].append(element)
            
            # Public transport
            elif tags.get('amenity') == 'bus_station':
                processed['public_transport']['bus_station'].append(element)
            elif tags.get('public_transport') == 'station':
                processed['public_transport']['train_station'].append(element)
            
            # Utilities
            elif tags.get('power') == 'line':
                processed['utilities']['power_line'].append(element)
            elif tags.get('amenity') == 'fuel':
                processed['utilities']['fuel_station'].append(element)
        
        return {
            'elements': elements,
            'processed': processed,
            'analysis_timestamp': datetime.now().isoformat()
        }
    
    def _fetch_construction_projects(self, region_name: str, bbox: Dict[str, float]) -> List[Dict]:
        """
        Fetch active construction projects from Indonesian government databases
        """
        projects = []
        
        try:
            # Indonesian construction permit database
            search_terms = self._get_indonesian_region_terms(region_name)
            
            for term in search_terms:
                # Search government construction database
                params = {
                    'resource_id': 'construction-permits-2024',  # Hypothetical resource ID
                    'q': term,
                    'limit': 50
                }
                
                response = requests.get(
                    self.gov_data_sources['construction_permits'],
                    params=params,
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    records = data.get('result', {}).get('records', [])
                    
                    for record in records:
                        if self._is_infrastructure_project(record):
                            projects.append({
                                'name': record.get('project_name', 'Unknown'),
                                'type': record.get('project_type', 'construction'),
                                'status': record.get('status', 'active'),
                                'budget': record.get('budget', 0),
                                'start_date': record.get('start_date'),
                                'completion_date': record.get('completion_date'),
                                'source': 'government_permits'
                            })
                
                time.sleep(0.5)  # Rate limiting
                
        except Exception as e:
            logger.warning(f"Error fetching construction projects: {e}")
        
        return projects
    
    def _fetch_government_plans(self, region_name: str) -> List[Dict]:
        """
        Fetch government infrastructure development plans
        """
        plans = []
        
        try:
            # Indonesian infrastructure planning database
            search_terms = self._get_indonesian_region_terms(region_name)
            
            for term in search_terms:
                params = {
                    'q': f'infrastructure {term}',
                    'rows': 20
                }
                
                response = requests.get(
                    self.gov_data_sources['infrastructure_budget'],
                    params=params,
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('result', {}).get('results', [])
                    
                    for result in results:
                        # Extract infrastructure plans from government packages
                        plan_data = self._extract_plan_data(result)
                        if plan_data:
                            plans.append(plan_data)
                
                time.sleep(0.5)
                
        except Exception as e:
            logger.warning(f"Error fetching government plans: {e}")
        
        return plans
    
    def _get_indonesian_region_terms(self, region_name: str) -> List[str]:
        """
        Convert region names to Indonesian administrative terms for government API searches
        """
        region_mapping = {
            'yogyakarta_urban': ['yogyakarta', 'kota yogyakarta', 'diy'],
            'yogyakarta_periurban': ['yogyakarta', 'diy', 'bantul', 'sleman'],
            'sleman_north': ['sleman', 'kabupaten sleman', 'diy'],
            'bantul_south': ['bantul', 'kabupaten bantul', 'diy'],
            'kulonprogo_west': ['kulon progo', 'kabupaten kulon progo', 'diy'],
            'gunungkidul_east': ['gunungkidul', 'kabupaten gunungkidul', 'diy'],
            'solo_expansion': ['surakarta', 'solo', 'jawa tengah'],
            'magelang_corridor': ['magelang', 'kabupaten magelang', 'jawa tengah'],
            'semarang_industrial': ['semarang', 'kota semarang', 'jawa tengah'],
            'surakarta_suburbs': ['surakarta', 'karesidenan surakarta', 'jawa tengah']
        }
        
        return region_mapping.get(region_name, [region_name.replace('_', ' ')])
    
    def _is_infrastructure_project(self, record: Dict) -> bool:
        """
        Determine if a government record represents infrastructure development
        """
        infrastructure_keywords = [
            'jalan', 'road', 'highway', 'toll', 'bridge', 'jembatan',
            'railway', 'kereta', 'airport', 'bandara', 'port', 'pelabuhan',
            'infrastructure', 'infrastruktur', 'transportation', 'transportasi',
            'utilities', 'listrik', 'power', 'water', 'air'
        ]
        
        text_to_check = ' '.join([
            str(record.get('project_name', '')),
            str(record.get('project_type', '')),
            str(record.get('description', ''))
        ]).lower()
        
        return any(keyword in text_to_check for keyword in infrastructure_keywords)
    
    def _extract_plan_data(self, result: Dict) -> Optional[Dict]:
        """
        Extract infrastructure plan data from government API results
        """
        try:
            title = result.get('title', '')
            notes = result.get('notes', '')
            
            # Check if this is an infrastructure-related plan
            if self._is_infrastructure_related(title + ' ' + notes):
                return {
                    'name': title,
                    'description': notes,
                    'type': 'planned_development',
                    'source': 'government_planning',
                    'url': result.get('url', ''),
                    'organization': result.get('organization', {}).get('title', ''),
                    'last_updated': result.get('metadata_modified', '')
                }
        except Exception:
            pass
        
        return None
    
    def _is_infrastructure_related(self, text: str) -> bool:
        """
        Check if text is related to infrastructure development
        """
        infrastructure_terms = [
            'pembangunan jalan', 'infrastruktur', 'transportasi', 'jembatan',
            'bandara', 'pelabuhan', 'kereta api', 'terminal', 'road development',
            'infrastructure development', 'transportation', 'utilities'
        ]
        
        text_lower = text.lower()
        return any(term in text_lower for term in infrastructure_terms)
    
    def _analyze_accessibility(self, infrastructure_data: Dict, bbox: Dict[str, float]) -> Dict[str, Any]:
        """
        Analyze accessibility based on infrastructure density and connectivity
        """
        processed = infrastructure_data.get('processed', {})
        
        # Calculate road network density
        total_roads = sum(len(roads) for roads in processed['roads'].values())
        road_density = total_roads / self._calculate_bbox_area(bbox)
        
        # Calculate public transport accessibility
        bus_stations = len(processed['public_transport']['bus_station'])
        train_stations = len(processed['public_transport']['train_station'])
        transport_score = (bus_stations * 10) + (train_stations * 20)
        
        # Calculate connectivity score
        major_roads = len(processed['roads']['motorway']) + len(processed['roads']['trunk'])
        connectivity_score = min(100, major_roads * 15)
        
        # Calculate utility access
        power_lines = len(processed['utilities']['power_line'])
        fuel_stations = len(processed['utilities']['fuel_station'])
        utility_score = min(100, (power_lines * 5) + (fuel_stations * 10))
        
        return {
            'road_density': road_density,
            'public_transport_score': min(100, transport_score),
            'connectivity_score': connectivity_score,
            'utility_access_score': utility_score,
            'overall_accessibility': (connectivity_score + transport_score + utility_score) / 3
        }
    
    def _calculate_bbox_area(self, bbox: Dict[str, float]) -> float:
        """
        Calculate approximate area of bounding box in km²
        """
        lat_diff = bbox['north'] - bbox['south']
        lng_diff = bbox['east'] - bbox['west']
        
        # Rough conversion to km² (simplified)
        return abs(lat_diff * lng_diff) * 111 * 111
    
    def _calculate_infrastructure_score(self, region_name: str, 
                                      current_infrastructure: Dict,
                                      construction_projects: List[Dict],
                                      planned_projects: List[Dict],
                                      accessibility_data: Dict) -> Dict[str, Any]:
        """
        Calculate comprehensive infrastructure score from all data sources
        """
        processed = current_infrastructure.get('processed', {})
        
        # Base infrastructure score from existing infrastructure
        base_score = 0
        infrastructure_details = {}
        
        # Score existing roads
        for road_type, roads in processed['roads'].items():
            weight = self.infrastructure_weights.get(road_type, 30)
            count = len(roads)
            contribution = min(40, count * (weight / 10))  # Cap contribution per type
            base_score += contribution
            infrastructure_details[f'{road_type}_roads'] = count
        
        # Score railways
        for rail_type, rails in processed['railways'].items():
            weight = self.infrastructure_weights.get(rail_type, 70)
            count = len(rails)
            contribution = min(30, count * (weight / 10))
            base_score += contribution
            infrastructure_details[f'{rail_type}_lines'] = count
        
        # Score aviation infrastructure
        airports = len(processed['aviation']['airport'])
        runways = len(processed['aviation']['runway'])
        aviation_score = min(25, (airports * 20) + (runways * 5))
        base_score += aviation_score
        infrastructure_details['airports'] = airports
        
        # Score ports and logistics
        ports = len(processed['ports']['port']) + len(processed['ports']['harbour'])
        port_score = min(20, ports * 15)
        base_score += port_score
        infrastructure_details['ports'] = ports
        
        # Bonus for construction projects (future infrastructure)
        construction_bonus = min(25, len(construction_projects) * 5)
        base_score += construction_bonus
        
        # Bonus for planned projects (government commitment)
        planning_bonus = min(20, len(planned_projects) * 3)
        base_score += planning_bonus
        
        # Accessibility multiplier
        accessibility_multiplier = 1 + (accessibility_data['overall_accessibility'] / 200)
        final_score = min(100, base_score * accessibility_multiplier)
        
        return {
            'region_name': region_name,
            'infrastructure_score': final_score,
            'base_score': base_score,
            'construction_bonus': construction_bonus,
            'planning_bonus': planning_bonus,
            'accessibility_multiplier': accessibility_multiplier,
            'infrastructure_details': infrastructure_details,
            'active_construction_projects': len(construction_projects),
            'planned_projects': len(planned_projects),
            'accessibility_data': accessibility_data,
            'data_sources': {
                'osm_elements': current_infrastructure.get('processed', {}).get('total_elements', 0),
                'construction_projects': len(construction_projects),
                'government_plans': len(planned_projects)
            },
            'analysis_timestamp': datetime.now().isoformat(),
            'data_confidence': self._calculate_data_confidence(current_infrastructure, construction_projects, planned_projects)
        }
    
    def _calculate_data_confidence(self, infrastructure: Dict, construction: List, plans: List) -> float:
        """
        Calculate confidence score based on data availability
        """
        osm_elements = infrastructure.get('processed', {}).get('total_elements', 0)
        
        # Base confidence from OSM data availability
        osm_confidence = min(1.0, osm_elements / 50)
        
        # Additional confidence from government data
        gov_confidence = min(0.5, (len(construction) + len(plans)) / 20)
        
        return osm_confidence + gov_confidence
    
    def _generate_fallback_analysis(self, region_name: str) -> Dict[str, Any]:
        """
        Generate fallback analysis when API calls fail
        """
        logger.info(f"Using fallback infrastructure analysis for {region_name}")
        
        return {
            'region_name': region_name,
            'infrastructure_score': 50.0,  # Neutral score
            'base_score': 45.0,
            'construction_bonus': 5.0,
            'planning_bonus': 0.0,
            'accessibility_multiplier': 1.0,
            'infrastructure_details': {},
            'active_construction_projects': 0,
            'planned_projects': 0,
            'accessibility_data': {
                'road_density': 0.5,
                'public_transport_score': 30,
                'connectivity_score': 40,
                'utility_access_score': 50,
                'overall_accessibility': 40
            },
            'data_sources': {
                'osm_elements': 0,
                'construction_projects': 0,
                'government_plans': 0
            },
            'analysis_timestamp': datetime.now().isoformat(),
            'data_confidence': 0.2,
            'status': 'fallback_analysis'
        }

def test_enhanced_infrastructure_analyzer():
    """
    Test the enhanced infrastructure analyzer
    """
    print("🧪 Testing Enhanced Dynamic Infrastructure Analyzer")
    print("=" * 60)
    
    analyzer = EnhancedInfrastructureAnalyzer()
    
    # Test regions with different characteristics
    test_regions = [
        ('yogyakarta_urban', {
            'north': -7.7500, 'south': -7.8500,
            'east': 110.4200, 'west': 110.3200
        }),
        ('sleman_north', {
            'north': -7.6800, 'south': -7.7800,
            'east': 110.4000, 'west': 110.3000
        })
    ]
    
    for region_name, bbox in test_regions:
        print(f"\\n🏗️ Analyzing {region_name}...")
        
        try:
            analysis = analyzer.analyze_live_infrastructure(region_name, bbox)
            
            print(f"   📊 Infrastructure score: {analysis['infrastructure_score']:.1f}/100")
            print(f"   🚧 Active construction: {analysis['active_construction_projects']} projects")
            print(f"   📋 Planned projects: {analysis['planned_projects']} projects")
            print(f"   🚌 Accessibility score: {analysis['accessibility_data']['overall_accessibility']:.1f}/100")
            print(f"   📈 Data confidence: {analysis['data_confidence']:.1%}")
            
            # Show infrastructure breakdown
            if analysis['infrastructure_details']:
                print("   🛣️ Infrastructure details:")
                for infra_type, count in analysis['infrastructure_details'].items():
                    if count > 0:
                        print(f"      - {infra_type}: {count}")
            
            # Show data sources
            sources = analysis['data_sources']
            print(f"   📡 Data sources: OSM({sources['osm_elements']}) + Gov({sources['construction_projects'] + sources['government_plans']})")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\\n✅ Enhanced infrastructure analyzer test completed!")

if __name__ == '__main__':
    test_enhanced_infrastructure_analyzer()