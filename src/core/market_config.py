"""
Regional Market Configuration for CloudClearingAPI v2.6

This module defines regional tier classifications and market benchmarks for
Indonesia's land investment analysis. Regions are classified into 4 tiers based
on economic development, infrastructure quality, and market maturity.

Tier Classification Methodology:
- Tier 1 (Metros): Major metropolitan areas with established markets, high infrastructure
- Tier 2 (Secondary): Provincial capitals and secondary cities with good infrastructure
- Tier 3 (Emerging): Development corridors, periurban zones, emerging industrial/tourism areas
- Tier 4 (Frontier): Remote regions, emerging coastal areas, early-stage development

Author: CloudClearingAPI Team
Date: October 25, 2025
Version: 2.6-alpha
"""

from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# REGIONAL HIERARCHY - 4-Tier Classification System
# ============================================================================

REGIONAL_HIERARCHY = {
    # ========================================================================
    # TIER 1: METROPOLITAN HUBS
    # ========================================================================
    # Characteristics: Established urban centers, highest infrastructure scores,
    # proven land markets, high liquidity, GDP >$10B metropolitan area
    'tier_1_metros': {
        'description': 'Major metropolitan areas - Jakarta & Surabaya metros',
        'regions': [
            # Jakarta Metropolitan Area (Jabodetabek)
            'jakarta_north_sprawl',
            'jakarta_south_suburbs',
            'tangerang_bsd_corridor',
            'bekasi_industrial_belt',
            'cikarang_mega_industrial',
            
            # Surabaya Metropolitan Area (Gerbangkertosusila)
            'surabaya_west_expansion',
            'surabaya_east_industrial',
            'gresik_port_industrial',
            'sidoarjo_delta_development',
        ],
        'benchmarks': {
            'avg_price_m2': 8_000_000,  # IDR per m² (±Rp 5-12M range)
            'expected_growth': 0.12,     # 12% annual appreciation
            'liquidity': 'very_high',    # >100 transactions/month typical
            'market_depth': 'deep',      # Multiple buyer segments
            'infrastructure_baseline': 75  # Expected infrastructure score (0-100)
        },
        'characteristics': {
            'population_metro': '>5M',
            'gdp_metro': '>$10B',
            'airport': 'International hub',
            'port': 'Major commercial',
            'highways': 'Toll road network',
            'railways': 'Commuter rail',
            'typical_focus': 'Urban expansion, industrial, logistics'
        }
    },
    
    # ========================================================================
    # TIER 2: SECONDARY CITIES
    # ========================================================================
    # Characteristics: Provincial capitals, established infrastructure,
    # active real estate markets, regional economic centers
    'tier_2_secondary': {
        'description': 'Secondary cities and provincial capitals',
        'regions': [
            # West Java Provincial Centers
            'bandung_north_expansion',
            'subang_patimban_megaport',  # New mega-port elevates to Tier 2
            
            # Central Java Provincial Centers
            'semarang_port_expansion',
            'semarang_south_urban',
            'solo_raya_expansion',
            
            # DIY Yogyakarta (Special Region Capital)
            'yogyakarta_urban_core',
            
            # Banten Industrial Centers
            'serang_cilegon_industrial',  # Major industrial complex
        ],
        'benchmarks': {
            'avg_price_m2': 5_000_000,   # IDR per m² (±Rp 3-7M range)
            'expected_growth': 0.10,      # 10% annual appreciation
            'liquidity': 'high',          # 30-100 transactions/month
            'market_depth': 'moderate',   # Some buyer diversity
            'infrastructure_baseline': 60  # Expected infrastructure score
        },
        'characteristics': {
            'population_metro': '1-5M',
            'gdp_metro': '$3-10B',
            'airport': 'Domestic hub or regional',
            'port': 'Regional commercial (some)',
            'highways': 'Provincial highway network',
            'railways': 'Regional connections',
            'typical_focus': 'Urban growth, industrial zones, education hubs'
        }
    },
    
    # ========================================================================
    # TIER 3: EMERGING CORRIDORS
    # ========================================================================
    # Characteristics: Development corridors, periurban expansion zones,
    # emerging industrial/tourism areas, improving infrastructure
    'tier_3_emerging': {
        'description': 'Emerging development corridors and growth zones',
        'regions': [
            # Technology & Periurban Corridors
            'bandung_east_tech_corridor',
            
            # Industrial Corridors
            'cirebon_port_industrial',
            
            # Tourism & Highland Zones
            'bogor_puncak_highland',
            'yogyakarta_kulon_progo_airport',  # New airport catalyst
            'magelang_borobudur_corridor',
            'malang_south_highland',
            
            # Coastal Development Zones
            'banyuwangi_ferry_corridor',
            'merak_port_corridor',
            
            # Emerging Urban Zones
            'purwokerto_south_expansion',
            'probolinggo_bromo_gateway',
        ],
        'benchmarks': {
            'avg_price_m2': 3_000_000,   # IDR per m² (±Rp 1.5-4.5M range)
            'expected_growth': 0.08,      # 8% annual appreciation
            'liquidity': 'moderate',      # 10-30 transactions/month
            'market_depth': 'limited',    # Mostly local buyers
            'infrastructure_baseline': 45  # Expected infrastructure score
        },
        'characteristics': {
            'population_metro': '200K-1M',
            'gdp_metro': '$500M-$3B',
            'airport': 'Regional or under construction',
            'port': 'Local (some coastal regions)',
            'highways': 'National road connections',
            'railways': 'Limited or planned',
            'typical_focus': 'Periurban residential, tourism gateways, industrial corridors'
        }
    },
    
    # ========================================================================
    # TIER 4: FRONTIER REGIONS
    # ========================================================================
    # Characteristics: Remote areas, early-stage development, limited
    # infrastructure, speculative markets, high potential but high risk
    'tier_4_frontier': {
        'description': 'Frontier and early-stage development regions',
        'regions': [
            # Remote Coastal Zones
            'tegal_brebes_coastal',
            'jember_southern_coast',
            'anyer_carita_coastal',
            
            # NOTE: Gunungkidul regions are actually part of DIY Yogyakarta
            # but classified as Tier 4 due to remote/karst geography
            # They are NOT included in java_regions list, so omitted here
            # If you add them later, they belong in this tier
        ],
        'benchmarks': {
            'avg_price_m2': 1_500_000,   # IDR per m² (±Rp 750K-2.5M range)
            'expected_growth': 0.06,      # 6% annual appreciation
            'liquidity': 'low',           # <10 transactions/month
            'market_depth': 'very_limited',  # Mostly local/speculative
            'infrastructure_baseline': 30  # Expected infrastructure score
        },
        'characteristics': {
            'population_metro': '<200K',
            'gdp_metro': '<$500M',
            'airport': 'None or very small',
            'port': 'Local fishing (coastal only)',
            'highways': 'Basic national roads',
            'railways': 'None',
            'typical_focus': 'Coastal resort potential, agricultural, speculative'
        }
    }
}


# ============================================================================
# TIER 1+ ULTRA-PREMIUM ZONES (Phase 2B.3)
# ============================================================================
# These Tier 1 regions command significantly higher prices than standard metros
# due to ultra-premium positioning, international business districts, or
# established luxury residential corridors. Use 9.5M IDR/m² benchmark vs 8M.

TIER_1_PLUS_REGIONS = [
    # Jakarta Ultra-Premium Corridors
    'jakarta_south_suburbs',        # Senopati, Cipete - lifestyle corridor
    'jakarta_central_scbd',         # SCBD business district (if exists in regions)
    'jakarta_south_pondok_indah',   # Pondok Indah - established luxury
    'jakarta_south_kemang',         # Kemang - expat/lifestyle district
    
    # Tangerang BSD - Established new city
    'tangerang_bsd_corridor',       # BSD City - master-planned ultra-premium
    
    # Bekasi Premium Zones (if applicable)
    'bekasi_summarecon',            # Summarecon Bekasi (if exists)
    
    # Cikarang Silicon Valley
    'cikarang_delta_silicon',       # Delta Silicon industrial park (if exists)
]


# ============================================================================
# TIER-SPECIFIC INFRASTRUCTURE TOLERANCE (Phase 2B.4)
# ============================================================================
# Different tiers have different infrastructure variability expectations.
# Tier 1 metros have predictable infrastructure (narrow range), while frontier
# regions have high uncertainty (wide range). This affects RVI expected price
# calculation: wider tolerance = less infrastructure premium impact.

TIER_INFRA_TOLERANCE = {
    'tier_1_metros': {
        'tolerance_pct': 0.15,  # ±15% - Predictable infrastructure
        'rationale': 'Established metros have consistent infrastructure quality',
        'baseline_score': 75    # Expected infrastructure score for Tier 1
    },
    'tier_2_secondary': {
        'tolerance_pct': 0.20,  # ±20% - Standard variability
        'rationale': 'Provincial capitals have moderate infrastructure variation',
        'baseline_score': 60    # Expected infrastructure score for Tier 2
    },
    'tier_3_emerging': {
        'tolerance_pct': 0.25,  # ±25% - Higher uncertainty
        'rationale': 'Emerging regions have infrastructure in development',
        'baseline_score': 45    # Expected infrastructure score for Tier 3
    },
    'tier_4_frontier': {
        'tolerance_pct': 0.30,  # ±30% - Maximum uncertainty
        'rationale': 'Frontier regions have unpredictable infrastructure',
        'baseline_score': 30    # Expected infrastructure score for Tier 4
    }
}


def get_infrastructure_tolerance(tier: str) -> Dict[str, Any]:
    """
    Get tier-specific infrastructure tolerance parameters.
    
    Phase 2B.4: Returns tolerance percentage and baseline score for tier.
    Used in RVI calculation to adjust infrastructure premium sensitivity.
    
    Args:
        tier: Tier classification ('tier_1_metros', 'tier_2_secondary', etc.)
    
    Returns:
        Dictionary with tolerance_pct, rationale, baseline_score
        Defaults to tier_4_frontier tolerance if tier not found
    
    Examples:
        >>> get_infrastructure_tolerance('tier_1_metros')
        {'tolerance_pct': 0.15, 'rationale': '...', 'baseline_score': 75}
        >>> get_infrastructure_tolerance('tier_4_frontier')
        {'tolerance_pct': 0.30, 'rationale': '...', 'baseline_score': 30}
    """
    if tier not in TIER_INFRA_TOLERANCE:
        logger.warning(f"Tier '{tier}' not found in TIER_INFRA_TOLERANCE, using tier_4_frontier")
        return TIER_INFRA_TOLERANCE['tier_4_frontier']
    
    return TIER_INFRA_TOLERANCE[tier]


# ============================================================================
# TIER CLASSIFICATION FUNCTIONS
# ============================================================================

def classify_region_tier(region_name: str) -> str:
    """
    Classify a region into its tier based on regional hierarchy.
    
    Args:
        region_name: Name of the region (lowercase with underscores)
    
    Returns:
        Tier classification string ('tier_1_metros', 'tier_2_secondary', etc.)
        Defaults to 'tier_4_frontier' if region not found (conservative assumption)
    
    Examples:
        >>> classify_region_tier('jakarta_north_sprawl')
        'tier_1_metros'
        >>> classify_region_tier('bandung_east_tech_corridor')
        'tier_3_emerging'
        >>> classify_region_tier('unknown_region')
        'tier_4_frontier'
    """
    region_name_lower = region_name.lower().replace(' ', '_')
    
    for tier, tier_data in REGIONAL_HIERARCHY.items():
        if region_name_lower in tier_data['regions']:
            logger.debug(f"Region '{region_name}' classified as {tier}")
            return tier
    
    # Default to frontier tier for unknown regions (conservative approach)
    logger.warning(f"Region '{region_name}' not found in hierarchy, defaulting to tier_4_frontier")
    return 'tier_4_frontier'


def get_tier_benchmark(tier: str, region_name: Optional[str] = None) -> Dict:
    """
    Get benchmark data for a specific tier.
    
    Phase 2B.3 Enhancement: Checks for Tier 1+ ultra-premium zones and applies
    9.5M IDR/m² benchmark (vs standard 8M) for qualifying regions.
    
    Args:
        tier: Tier classification ('tier_1_metros', 'tier_2_secondary', etc.)
        region_name: Optional region name for Tier 1+ override check (Phase 2B.3)
    
    Returns:
        Dictionary with benchmark values (avg_price_m2, expected_growth, etc.)
        
        If region is Tier 1+ ultra-premium zone:
        - avg_price_m2: 9,500,000 IDR (vs standard 8M)
        - description: Updated to 'Tier 1+ Ultra-Premium'
    
    Raises:
        KeyError: If tier not found in REGIONAL_HIERARCHY
    
    Examples:
        >>> get_tier_benchmark('tier_1_metros')  # Standard Tier 1
        {'avg_price_m2': 8000000, ...}
        >>> get_tier_benchmark('tier_1_metros', 'tangerang_bsd_corridor')  # Tier 1+
        {'avg_price_m2': 9500000, 'description': 'Tier 1+ Ultra-Premium', ...}
    """
    if tier not in REGIONAL_HIERARCHY:
        raise KeyError(f"Tier '{tier}' not found in REGIONAL_HIERARCHY")
    
    # Get base tier benchmarks
    benchmarks = REGIONAL_HIERARCHY[tier]['benchmarks'].copy()
    
    # Phase 2B.3: Check for Tier 1+ ultra-premium override
    if tier == 'tier_1_metros' and region_name and region_name in TIER_1_PLUS_REGIONS:
        benchmarks['avg_price_m2'] = 9_500_000  # Ultra-premium benchmark
        benchmarks['tier_1_plus_override'] = True
        benchmarks['description'] = 'Tier 1+ Ultra-Premium'
        logger.debug(f"   🏆 Tier 1+ ultra-premium override: {region_name} → 9.5M IDR/m²")
    
    return benchmarks


def get_region_tier_info(region_name: str) -> Dict:
    """
    Get complete tier information for a region including benchmarks.
    
    Phase 2B.3 Enhancement: Automatically applies Tier 1+ ultra-premium benchmarks
    (9.5M IDR/m²) for qualifying regions.
    
    Args:
        region_name: Name of the region
    
    Returns:
        Dictionary with tier, benchmarks, and characteristics
        
        If region is Tier 1+ ultra-premium:
        - benchmarks['avg_price_m2']: 9,500,000 IDR
        - benchmarks['tier_1_plus_override']: True
    
    Example:
        >>> info = get_region_tier_info('jakarta_north_sprawl')  # Standard Tier 1
        >>> info['tier']
        'tier_1_metros'
        >>> info['benchmarks']['avg_price_m2']
        8000000
        >>> info = get_region_tier_info('tangerang_bsd_corridor')  # Tier 1+
        >>> info['benchmarks']['avg_price_m2']
        9500000
    """
    tier = classify_region_tier(region_name)
    tier_data = REGIONAL_HIERARCHY[tier]
    
    # Phase 2B.3: Use get_tier_benchmark with region_name to enable Tier 1+ override
    benchmarks = get_tier_benchmark(tier, region_name)
    
    return {
        'region_name': region_name,
        'tier': tier,
        'tier_description': tier_data['description'],
        'benchmarks': benchmarks,  # Now uses get_tier_benchmark for Tier 1+ support
        'characteristics': tier_data.get('characteristics', {}),
        'peer_regions': tier_data['regions']
    }


def get_all_regions_by_tier(tier: str) -> List[str]:
    """
    Get list of all regions in a specific tier.
    
    Args:
        tier: Tier classification
    
    Returns:
        List of region names in that tier
    """
    if tier not in REGIONAL_HIERARCHY:
        return []
    
    return REGIONAL_HIERARCHY[tier]['regions'].copy()


def get_tier_summary_stats() -> Dict:
    """
    Get summary statistics about tier distribution.
    
    Returns:
        Dictionary with counts per tier and other stats
    """
    stats = {}
    total_regions = 0
    
    for tier, tier_data in REGIONAL_HIERARCHY.items():
        region_count = len(tier_data['regions'])
        stats[tier] = {
            'count': region_count,
            'description': tier_data['description'],
            'avg_price': tier_data['benchmarks']['avg_price_m2'],
            'expected_growth': tier_data['benchmarks']['expected_growth']
        }
        total_regions += region_count
    
    stats['total_classified_regions'] = total_regions
    
    return stats


# ============================================================================
# VALIDATION & TESTING UTILITIES
# ============================================================================

def validate_region_classifications() -> Dict[str, List[str]]:
    """
    Validate that all regions in hierarchy are unique (no duplicates across tiers).
    
    Returns:
        Dictionary with 'valid' (bool) and 'duplicates' (list of duplicate regions)
    """
    all_regions = []
    duplicates = []
    
    for tier, tier_data in REGIONAL_HIERARCHY.items():
        for region in tier_data['regions']:
            if region in all_regions:
                duplicates.append(region)
            else:
                all_regions.append(region)
    
    is_valid = len(duplicates) == 0
    
    return {
        'valid': is_valid,
        'total_regions': len(all_regions),
        'duplicates': duplicates,
        'message': 'All regions uniquely classified' if is_valid else f'Found {len(duplicates)} duplicate(s)'
    }


def compare_to_java_regions(java_region_names: List[str]) -> Dict:
    """
    Compare tier classifications against actual Java regions list.
    Useful for finding regions that exist in code but aren't tier-classified yet.
    
    Args:
        java_region_names: List of all Java region names from indonesia_expansion_regions.py
    
    Returns:
        Dictionary with classified, unclassified, and extra regions
    """
    # Get all classified regions
    classified_regions = set()
    for tier, tier_data in REGIONAL_HIERARCHY.items():
        classified_regions.update(tier_data['regions'])
    
    java_regions_set = set(java_region_names)
    
    unclassified = java_regions_set - classified_regions
    extra = classified_regions - java_regions_set  # Classified but don't exist in code
    
    return {
        'total_java_regions': len(java_regions_set),
        'total_classified': len(classified_regions),
        'classified_and_exists': len(java_regions_set & classified_regions),
        'unclassified_regions': sorted(list(unclassified)),
        'extra_classified_regions': sorted(list(extra)),
        'coverage_pct': (len(java_regions_set & classified_regions) / len(java_regions_set) * 100) if java_regions_set else 0
    }


# ============================================================================
# MODULE INITIALIZATION
# ============================================================================

# ============================================================================
# RECENT AIRPORT DATABASE (Phase 2B.2)
# ============================================================================
# Airports opened within last 5 years that warrant +25% benchmark premium
# due to connectivity catalyst effect on land values

RECENT_AIRPORTS = {
    # Yogyakarta International Airport (YIA/NYIA)
    'yogyakarta_yia': {
        'name': 'Yogyakarta International Airport',
        'iata': 'YIA',
        'location': {'lat': -7.9, 'lon': 110.05},
        'opening_date': '2020-08-29',  # Opened August 2020
        'impact_radius_km': 30,  # 30km radius impact zone
        'affected_regions': [
            'yogyakarta_north',
            'yogyakarta_south',
            'kulonprogo_west',
            'sleman_north',
            'bantul_south'
        ],
        'premium_justification': 'New international airport opened 2020, significant connectivity improvement'
    },
    
    # Banyuwangi Airport Expansion
    'banyuwangi_expansion': {
        'name': 'Banyuwangi Airport (Blimbingsari)',
        'iata': 'BWX',
        'location': {'lat': -8.31, 'lon': 114.34},
        'opening_date': '2021-06-15',  # Major expansion 2021
        'impact_radius_km': 25,
        'affected_regions': [
            'banyuwangi_coastal',
            'banyuwangi_north'
        ],
        'premium_justification': 'Major runway expansion 2021, enables larger aircraft and tourism growth'
    },
    
    # Kertajati International Airport (West Java)
    'kertajati_intl': {
        'name': 'Kertajati International Airport',
        'iata': 'KJT',
        'location': {'lat': -6.65, 'lon': 108.17},
        'opening_date': '2018-05-24',  # Opened May 2018 (still within 5-7 year window)
        'impact_radius_km': 35,
        'affected_regions': [
            'majalengka_area',
            'cirebon_suburbs'
        ],
        'premium_justification': 'New international airport 2018, strategic cargo hub development'
    }
}


def check_airport_premium(region_name: str, current_year: int = 2025) -> Dict:
    """
    Check if region qualifies for airport premium based on recent airport openings.
    
    Phase 2B.2: Regions with airports opened in last 5 years get +25% benchmark premium
    
    Args:
        region_name: Region to check
        current_year: Current year for date calculations (default 2025)
    
    Returns:
        Dict with:
            - has_premium: Whether region qualifies for airport premium (bool)
            - premium_multiplier: 1.25 if qualifies, 1.0 otherwise (float)
            - airport_name: Name of qualifying airport (str or None)
            - opening_year: Year airport opened (int or None)
            - years_since_opening: Years since airport opened (int or None)
    """
    for airport_id, airport_data in RECENT_AIRPORTS.items():
        if region_name in airport_data.get('affected_regions', []):
            # Parse opening date (YYYY-MM-DD)
            opening_date_str = airport_data['opening_date']
            opening_year = int(opening_date_str.split('-')[0])
            years_since = current_year - opening_year
            
            # Airport premium applies if opened within last 5 years
            if years_since <= 5:
                logger.info(f"   ✈️ Airport premium applied: {airport_data['name']} "
                           f"(opened {opening_year}, {years_since} years ago)")
                return {
                    'has_premium': True,
                    'premium_multiplier': 1.25,  # +25% premium
                    'airport_name': airport_data['name'],
                    'airport_iata': airport_data.get('iata'),
                    'opening_year': opening_year,
                    'years_since_opening': years_since,
                    'justification': airport_data['premium_justification']
                }
    
    # No recent airport found
    return {
        'has_premium': False,
        'premium_multiplier': 1.0,
        'airport_name': None,
        'airport_iata': None,
        'opening_year': None,
        'years_since_opening': None,
        'justification': None
    }


def _initialize_market_config():
    """Initialize market configuration and run validation checks."""
    validation = validate_region_classifications()
    
    if not validation['valid']:
        logger.error(f"⚠️ Market config validation failed: {validation['message']}")
        logger.error(f"   Duplicate regions: {validation['duplicates']}")
    else:
        logger.info(f"✅ Market config validated: {validation['total_regions']} regions classified")
    
    # Log tier distribution
    stats = get_tier_summary_stats()
    logger.info(f"   Tier 1 Metros: {stats['tier_1_metros']['count']} regions")
    logger.info(f"   Tier 2 Secondary: {stats['tier_2_secondary']['count']} regions")
    logger.info(f"   Tier 3 Emerging: {stats['tier_3_emerging']['count']} regions")
    logger.info(f"   Tier 4 Frontier: {stats['tier_4_frontier']['count']} regions")


# Run initialization when module is imported
_initialize_market_config()
