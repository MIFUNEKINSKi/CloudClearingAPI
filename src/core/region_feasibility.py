"""
Per-region acquisition feasibility classifier — Track A / Phase 2.

Indonesia's land system gates which regions are actually closeable for a
foreign or out-of-region investor. A STRONG_BUY in a region you can't
legally acquire (or one zoned conservation/military) is wasted alert
weight. This module attaches a feasibility profile to every region so the
weekly briefing surfaces actionability alongside score.

Three dimensions captured per region:

  1. **ownership_pathway** — practical mechanism for foreign/out-of-region
     acquisition:
       - "hgb_pt_pma"      : HGB title via PT PMA (foreign-investment company);
                             standard for industrial/commercial estates.
       - "leasehold"       : Long-term lease (Hak Sewa); 25-30 years; common
                             for tourism/villa investment.
       - "hak_pakai"       : Direct foreign individual right-to-use; available
                             with KITAS; 30 years renewable.
       - "nominee_only"    : Only structurally accessible via Indonesian
                             nominee (legal but high counterparty risk).
       - "restricted"      : Significant friction — Indigenous claims,
                             military overlap, conservation, contested zoning.
       - "off_limits"      : Foreign acquisition not practical at retail.

  2. **zoning_class** — RTRW (Rencana Tata Ruang Wilayah) primary
     classification. Determines what can legally be built.

  3. **liquidity_tier** — exit-speed proxy. Indonesia doesn't publish
     official transaction-volume data; values estimated from listing
     turnover + market_config tier benchmarks.

The profile drives a soft annotation in the email/PDF (✅ ⚠️ 🚫) — not a
hard filter. The investor still sees the score; they get told whether to
pursue, hesitate, or skip.

Sources for the 13 deep-research-validated regions: 2026-04-28 deep-research
report (Bank Indonesia, MAPPI, BPS, CBRE/Savills/Cushman, retail platforms).
Other regions use tier-based defaults with overrides for known special cases
(IKN Indigenous claims, Bali zoning enforcement, Banda Aceh Sharia province,
Papua hak ulayat).
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass(frozen=True)
class FeasibilityProfile:
    region: str
    ownership_pathway: str
    zoning_class: str
    zoning_overlays: tuple = ()  # e.g. ('coastal_protection', 'forest_conservation', 'indigenous_claim')
    liquidity_tier: str = 'moderate'  # 'very_high' | 'high' | 'moderate' | 'low' | 'very_low'
    confidence: str = 'tier_default'  # 'researched' | 'tier_default' | 'inferred'
    notes: str = ''

    @property
    def actionability_flag(self) -> str:
        """Single-glyph flag for email/PDF rendering."""
        if self.ownership_pathway in ('off_limits', 'restricted'):
            return '🚫'
        if (self.zoning_overlays and any(
                o in self.zoning_overlays for o in
                ('forest_conservation', 'military_zone', 'indigenous_claim',
                 'psn_right_of_way', 'contested_zoning'))
                or self.liquidity_tier == 'very_low'
                or self.ownership_pathway == 'nominee_only'):
            return '⚠️'
        return '✅'

    @property
    def actionability_summary(self) -> str:
        """One-line investor-facing summary."""
        flag = self.actionability_flag
        path_label = {
            'hgb_pt_pma': 'HGB via PT PMA',
            'leasehold': 'leasehold (25-30y)',
            'hak_pakai': 'hak pakai (foreign-OK)',
            'nominee_only': 'nominee only',
            'restricted': 'restricted access',
            'off_limits': 'off-limits',
        }.get(self.ownership_pathway, self.ownership_pathway)
        liq_label = self.liquidity_tier.replace('_', ' ')
        zone = self.zoning_class
        overlay = (' · ' + ', '.join(self.zoning_overlays)) if self.zoning_overlays else ''
        return f"{flag} {path_label} · {zone}{overlay} · {liq_label} liquidity"


# ============================================================================
# Region-specific feasibility profiles
# ============================================================================
# Confidence tiers:
#   "researched": entry validated by 2026-04-28 deep-research report
#   "tier_default": derived from market_config tier + island heuristics
#   "inferred": case-specific judgment based on public infrastructure data

_PROFILES: Dict[str, FeasibilityProfile] = {

    # ── Researched (2026-04-28 deep-research report) ──────────────────────

    'subang_patimban_megaport': FeasibilityProfile(
        region='subang_patimban_megaport',
        ownership_pathway='hgb_pt_pma',
        zoning_class='industrial',
        zoning_overlays=('psn_right_of_way',),  # Patimban PSN may consume periphery
        liquidity_tier='moderate',
        confidence='researched',
        notes='Smartpolitan/Kalijati formal estates HGB-ready. Pantura agrarian '
              'corridor has mixed Girik/AJB titles — institutional path only.',
    ),
    'cikarang_mega_industrial': FeasibilityProfile(
        region='cikarang_mega_industrial',
        ownership_pathway='hgb_pt_pma',
        zoning_class='industrial',
        liquidity_tier='very_high',
        confidence='researched',
        notes='MM2100/Jababeka/Lippo Cikarang/EJIP — 45 years of institutional '
              'depth. Standard PT PMA HGB closes in 4-8 weeks.',
    ),
    'karawang_industrial_corridor': FeasibilityProfile(
        region='karawang_industrial_corridor',
        ownership_pathway='hgb_pt_pma',
        zoning_class='industrial',
        liquidity_tier='high',
        confidence='researched',
        notes='Suryacipta/KIIC — Cikarang-tier liquidity. Stay south of Pedes; '
              'northern agrarian zones have rampant platform pricing errors.',
    ),
    'serang_cilegon_industrial': FeasibilityProfile(
        region='serang_cilegon_industrial',
        ownership_pathway='hgb_pt_pma',
        zoning_class='industrial',
        liquidity_tier='high',
        confidence='researched',
        notes='Petrochemical/steel/heavy logistics. Watch for "bonus gudang" '
              '(structural improvements bundled into raw land price).',
    ),
    'merak_port_corridor': FeasibilityProfile(
        region='merak_port_corridor',
        ownership_pathway='hgb_pt_pma',
        zoning_class='industrial',
        zoning_overlays=('coastal_protection',),
        liquidity_tier='moderate',
        confidence='researched',
        notes='Port-adjacent industrial; coastal zoning constraints on '
              'beachfront parcels.',
    ),
    'anyer_carita_coastal': FeasibilityProfile(
        region='anyer_carita_coastal',
        ownership_pathway='leasehold',
        zoning_class='tourism',
        zoning_overlays=('coastal_protection',),
        liquidity_tier='low',
        confidence='researched',
        notes='Resort/hospitality strip — leasehold preferred, foreign HGB '
              'possible with PT PMA. Beachfront parcels regulated by KSPN.',
    ),
    'medan_kuala_namu_corridor': FeasibilityProfile(
        region='medan_kuala_namu_corridor',
        ownership_pathway='hgb_pt_pma',
        zoning_class='industrial',
        liquidity_tier='moderate',
        confidence='researched',
        notes='Deli Serdang regency airport corridor. Logistics + light '
              'industrial. PON Sport Center development boost.',
    ),
    'medan_belawan_port': FeasibilityProfile(
        region='medan_belawan_port',
        ownership_pathway='hgb_pt_pma',
        zoning_class='industrial',
        zoning_overlays=('coastal_protection',),
        liquidity_tier='moderate',
        confidence='researched',
        notes='Port industrial; tight retail listings (institutional only).',
    ),
    'bitung_port_industrial': FeasibilityProfile(
        region='bitung_port_industrial',
        ownership_pathway='hgb_pt_pma',
        zoning_class='industrial',
        liquidity_tier='low',
        confidence='researched',
        notes='Bitung KEK (Special Economic Zone) — government-subsidized '
              'rates. Deep sub-market split: SEZ-side cheap, port-side premium.',
    ),
    'banjarmasin_port_development': FeasibilityProfile(
        region='banjarmasin_port_development',
        ownership_pathway='hgb_pt_pma',
        zoning_class='industrial',
        liquidity_tier='low',
        confidence='researched',
        notes='Commodity processing + South Kalimantan port; institutional '
              'multi-hectare market.',
    ),
    'lombok_mandalika_resort': FeasibilityProfile(
        region='lombok_mandalika_resort',
        ownership_pathway='leasehold',
        zoning_class='tourism',
        liquidity_tier='moderate',
        confidence='researched',
        notes='Mandalika SEZ (KSPN priority). USD-pegged pricing, foreign-'
              'friendly via PT PMA HGB or 30-year leasehold. MotoGP catalyst.',
    ),
    'lombok_senggigi_coast': FeasibilityProfile(
        region='lombok_senggigi_coast',
        ownership_pathway='leasehold',
        zoning_class='tourism',
        zoning_overlays=('coastal_protection',),
        liquidity_tier='moderate',
        confidence='researched',
        notes='Established resort coast — leasehold dominant for retail '
              'foreign capital; PT PMA HGB for development.',
    ),
    'batang_industrial_sez': FeasibilityProfile(
        region='batang_industrial_sez',
        ownership_pathway='hgb_pt_pma',
        zoning_class='industrial',
        liquidity_tier='low',
        confidence='researched',
        notes='Batang Industrial Park (BIP) — government-prioritized FDI '
              'destination. Lower cost than West Java; institutional-only.',
    ),
    'labuan_bajo_komodo_gateway': FeasibilityProfile(
        region='labuan_bajo_komodo_gateway',
        ownership_pathway='restricted',
        zoning_class='tourism',
        zoning_overlays=('coastal_protection', 'kspn_strict'),
        liquidity_tier='very_low',
        confidence='researched',
        notes='KSPN super-priority — strict coastal protection. Off-market '
              'trading between hospitality conglomerates; retail visibility '
              'minimal. Manual underwriter review required.',
    ),
    'nusantara_capital_core': FeasibilityProfile(
        region='nusantara_capital_core',
        ownership_pathway='restricted',
        zoning_class='mixed',
        zoning_overlays=('indigenous_claim', 'contested_zoning', 'psn_right_of_way'),
        liquidity_tier='very_low',
        confidence='researched',
        notes='IKN core. Indigenous community claims pending; environmental '
              'impact studies incomplete. Speculative platform pricing with '
              '40× source disagreement. Manual review only.',
    ),
    'nusantara_balikpapan_corridor': FeasibilityProfile(
        region='nusantara_balikpapan_corridor',
        ownership_pathway='restricted',
        zoning_class='mixed',
        zoning_overlays=('indigenous_claim', 'psn_right_of_way'),
        liquidity_tier='very_low',
        confidence='researched',
        notes='IKN connector corridor — same caveats as core; toll road '
              'progress provides long-term anchor.',
    ),

    # ── Inferred (case-specific public infrastructure / regulatory data) ──

    'banda_aceh_reconstruction': FeasibilityProfile(
        region='banda_aceh_reconstruction',
        ownership_pathway='leasehold',
        zoning_class='residential',
        zoning_overlays=('sharia_qanun',),
        liquidity_tier='very_low',
        confidence='inferred',
        notes='Aceh applies Qanun (Sharia bylaws) — non-Muslim foreign '
              'investors face additional friction. Leasehold preferred.',
    ),
    'jayapura_urban_development': FeasibilityProfile(
        region='jayapura_urban_development',
        ownership_pathway='nominee_only',
        zoning_class='mixed',
        zoning_overlays=('hak_ulayat', 'military_zone'),
        liquidity_tier='very_low',
        confidence='inferred',
        notes='Papua — strong customary land rights (hak ulayat); '
              'considerable military presence in Jayapura. Foreign HGB '
              'practically restricted. Avoid retail acquisition.',
    ),
    'ambon_tourism_expansion': FeasibilityProfile(
        region='ambon_tourism_expansion',
        ownership_pathway='leasehold',
        zoning_class='tourism',
        zoning_overlays=('coastal_protection',),
        liquidity_tier='very_low',
        confidence='inferred',
        notes='Maluku — limited retail market; leasehold dominant.',
    ),
    'kupang_urban_development': FeasibilityProfile(
        region='kupang_urban_development',
        ownership_pathway='leasehold',
        zoning_class='mixed',
        liquidity_tier='very_low',
        confidence='inferred',
        notes='NTT — thin retail market; leasehold or PT PMA.',
    ),
    'lake_toba_tourism_zone': FeasibilityProfile(
        region='lake_toba_tourism_zone',
        ownership_pathway='leasehold',
        zoning_class='tourism',
        zoning_overlays=('shoreline_conservation', 'kspn_priority'),
        liquidity_tier='very_low',
        confidence='inferred',
        notes='KSPN priority destination — strict shoreline rules. '
              'Customary Batak land arrangements common.',
    ),

    # Bali tourism (zoning enforcement is tightening 2025-2026)
    'canggu_seminyak_corridor': FeasibilityProfile(
        region='canggu_seminyak_corridor',
        ownership_pathway='leasehold',
        zoning_class='tourism',
        zoning_overlays=('saturated_supply',),
        liquidity_tier='very_high',
        confidence='inferred',
        notes='Bali southern corridor — leasehold dominant; PT PMA HGB '
              'standard. Saturated supply (75% of Bali pipeline absorbed here).',
    ),
    'nusa_dua_bukit_peninsula': FeasibilityProfile(
        region='nusa_dua_bukit_peninsula',
        ownership_pathway='leasehold',
        zoning_class='tourism',
        zoning_overlays=('coastal_protection',),
        liquidity_tier='high',
        confidence='inferred',
        notes='Established luxury hospitality zone — leasehold + PT PMA '
              'HGB. Strict cliff/coastal enforcement.',
    ),
    'denpasar_north_expansion': FeasibilityProfile(
        region='denpasar_north_expansion',
        ownership_pathway='hgb_pt_pma',
        zoning_class='mixed',
        liquidity_tier='high',
        confidence='inferred',
        notes='Bali capital — mixed urban; HGB via PT PMA standard.',
    ),
    'sanur_beach_resort': FeasibilityProfile(
        region='sanur_beach_resort',
        ownership_pathway='leasehold',
        zoning_class='tourism',
        zoning_overlays=('coastal_protection',),
        liquidity_tier='high',
        confidence='inferred',
        notes='Established beach-resort zone; leasehold + PT PMA HGB.',
    ),
    'ubud_north_highland': FeasibilityProfile(
        region='ubud_north_highland',
        ownership_pathway='leasehold',
        zoning_class='tourism',
        zoning_overlays=('cultural_heritage',),
        liquidity_tier='moderate',
        confidence='inferred',
        notes='Cultural-tourism core — village land tenure (Banjar) '
              'considerations. Leasehold dominant.',
    ),
    'tabanan_west_coast': FeasibilityProfile(
        region='tabanan_west_coast',
        ownership_pathway='leasehold',
        zoning_class='tourism',
        zoning_overlays=('coastal_protection', 'agricultural_overlay'),
        liquidity_tier='moderate',
        confidence='inferred',
        notes='Bali emerging west — rice-paddy agricultural overlay; '
              'leasehold dominant. Increasing zoning enforcement.',
    ),
}


def _tier_default(region: str, tier: Optional[str]) -> FeasibilityProfile:
    """Tier-based fallback for regions without an explicit profile.

    Conservative defaults: assumes HGB via PT PMA is workable; notes
    that the entry hasn't been individually researched.
    """
    if tier == 'tier_1_metros':
        return FeasibilityProfile(
            region=region,
            ownership_pathway='hgb_pt_pma',
            zoning_class='mixed',
            liquidity_tier='very_high',
            confidence='tier_default',
            notes='Tier-1 metro default: HGB via PT PMA standard; mixed urban zoning.',
        )
    if tier == 'tier_2_secondary':
        return FeasibilityProfile(
            region=region,
            ownership_pathway='hgb_pt_pma',
            zoning_class='mixed',
            liquidity_tier='high',
            confidence='tier_default',
            notes='Tier-2 secondary default: HGB via PT PMA workable; '
                  'verify regional restrictions.',
        )
    if tier == 'tier_3_emerging':
        return FeasibilityProfile(
            region=region,
            ownership_pathway='hgb_pt_pma',
            zoning_class='mixed',
            liquidity_tier='moderate',
            confidence='tier_default',
            notes='Tier-3 emerging default: HGB via PT PMA workable; '
                  'thinner retail market — institutional path preferred.',
        )
    if tier == 'tier_4_frontier':
        return FeasibilityProfile(
            region=region,
            ownership_pathway='leasehold',
            zoning_class='mixed',
            liquidity_tier='very_low',
            confidence='tier_default',
            notes='Tier-4 frontier default: leasehold preferred; thin '
                  'retail liquidity; institutional path required for HGB.',
        )
    return FeasibilityProfile(
        region=region,
        ownership_pathway='hgb_pt_pma',
        zoning_class='mixed',
        liquidity_tier='moderate',
        confidence='tier_default',
        notes='Default profile (tier unknown). Verify before acting.',
    )


def get_feasibility(region: str, tier: Optional[str] = None) -> FeasibilityProfile:
    """Return the FeasibilityProfile for a region.

    Resolution: explicit profile > tier-based default. The optional ``tier``
    argument should be the market_config tier name ('tier_1_metros' etc.);
    when unavailable callers can pass None and accept the generic default.
    """
    if region in _PROFILES:
        return _PROFILES[region]
    return _tier_default(region, tier)


def all_known_regions() -> List[str]:
    """Return the list of regions with explicit (non-default) profiles."""
    return sorted(_PROFILES.keys())
