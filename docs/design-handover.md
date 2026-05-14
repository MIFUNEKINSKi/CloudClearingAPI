# CloudClearingAPI — Design Handover

**Prepared:** 2026-05-14 · **For:** Claude design team · **Maintainer:** Chris Moore

---

## 1. What this project is (2-minute context)

CloudClearingAPI is an **automated land-investment analyst for Indonesia**. Every
week it scores 68 regions by fusing four data sources — Sentinel-2 optical +
Sentinel-1 SAR satellite change detection, live Lamudi market scraping,
OpenStreetMap infrastructure analysis, and Indonesian-press development news —
into a single 0–100 investment score with a STRONG_BUY / BUY / WATCH / PASS tier.

The output is a **weekly briefing**: a plain-text email + an attached PDF
executive summary. The pipeline runs on a laptop via a `launchd` cron, Sundays
9am, ~90 minutes per run.

**North-star goal:** "see Indonesian land-investment opportunities early and
make money." Trade-offs favor signal trustworthiness over breadth.

**Stage / who uses it:** Pre-product-market-fit. The cohort is **N=1** — the
founder reads the briefing himself each week and (eventually) acts on it by
investigating regions, contacting Indonesian notaris/PPAT, filing land
acquisitions. There is no second user yet. This matters for design scope: this
is a **personal analytical instrument**, not a consumer product. It does not
need branding, onboarding, or marketing surfaces.

The engineering is mature (≈25 versions shipped; signal-quality, feasibility,
portfolio, and prediction-review layers all built). What the project has
**not** had is a deliberate design pass on how that intelligence is presented.
That is the ask.

---

## 2. The design-relevant surfaces

There are two shipping surfaces today, plus one that doesn't exist yet.

### Surface A — The weekly email  ⭐ primary

- **What it is:** the briefing the founder reads every Sunday. Plain-text,
  assembled as a list of strings in `run_weekly_java_monitor.py`
  (`_send_report_email`). ~250 lines.
- **Sample artifact:** `docs/sample_weekly_email.txt` (real output from the
  2026-05-14 run — read this first).
- **Section order:** Portfolio Overview → Tier Changes Since Last Run →
  Prediction Review → Priority Opportunities (STRONG_BUY + BUY, up to 10, each
  with score breakdown / feasibility / action links / SAR breakdown) → Watch
  List → Pass Summary → Your Portfolio (if positions configured).
- **Current state:** information-complete, dense, monospace-grid plain text.
  Uses emoji as the only visual hierarchy (🔥 ⬆ ⬇ ⚠ ✅ 📌 🛰️ 🔗). It works,
  but scanning 11 STRONG_BUYs each with 8–10 sub-lines is a wall of text.

### Surface B — The PDF executive summary

- **What it is:** an attached PDF "permanent reference," generated
  programmatically via **ReportLab** in `src/core/pdf_report_generator.py`
  (2,701 lines, 11 `_build_*` sections).
- **Sample artifact:** `output/reports/executive_summary_20260514_135724.pdf`
  (latest run — open this).
- **Sections:** header, executive summary, Your Portfolio, Prediction Review,
  monitoring results, **decision matrix** (13-column table × 68 region rows),
  investment analysis (top-5 detailed cards), satellite imagery summary,
  regional breakdown, alerts, footer.
- **Current state:** functional, color-coded, but visually it's "engineer made
  a report" — table-heavy, no deliberate typographic hierarchy, the 13-column
  decision matrix is cramped on A4.

### Surface C — An interactive data portal  (does not exist)

- The project archives rich time-series: 68 regions × weekly price history,
  satellite imagery, scores, drift, tier transitions, a forecast log. None of
  it is browsable — it lives in JSON/JSONL files.
- **Design note:** I'd flag this as **premature**, not a current ask. With N=1
  the founder gets everything he needs from the weekly briefing. A portal
  becomes worth designing if/when there's a second user or the founder
  explicitly wants exploratory analysis. Listed here for completeness so the
  team has the full picture, not as a request.

---

## 3. Prioritized asks — what would genuinely move the needle

Ranked by leverage against the north-star (help the founder act on real
opportunities faster and with more confidence).

### P1 — Weekly email: redesign as HTML  ⭐ highest leverage

The single surface the founder touches every week. Plain text → a scannable
HTML email is the biggest friction-reduction win available.

**The design problem:** how do you present a ranked list of ~11 investment
opportunities, each carrying ~10 dimensions of context (score, score
breakdown, confidence, feasibility flag, ownership pathway, zoning, liquidity,
weeks-at-tier streak, ROI, action links, SAR signal warnings), such that the
founder can triage it in 3 minutes and know exactly which 2–3 regions to
investigate this week?

**Specific things worth a designer's eye:**
- The **Priority Opportunities** list is the heart of it. Each entry currently
  spans 8–10 plain-text lines. What's the right card / row treatment?
- **Tier Changes** (11 up, 11 down this week) — this is the "see early" signal.
  Should it be more prominent? It's currently buried below Portfolio Overview.
- **Score breakdown** renders as a text string today:
  `activity 32 × infra 1.15 × market 1.10 × conf 1.00 × news 1.05 × momentum 1.00 = 52.2`.
  This is begging to be a visual (waterfall? stacked bar? sparkline?).
- The **feasibility flag** system (✅ HGB via PT PMA · industrial · high
  liquidity / ⚠️ leasehold · coastal_protection / 🚫 restricted) — is the
  glyph + text string the right encoding?
- **Action links** (Lamudi listing / Google Maps satellite / OSM map) — these
  are the friction-reduction payoff; they should be obvious tap targets.

**Constraint:** the email is assembled in Python. An HTML redesign means adding
a parallel `MIMEText(html_body, 'html')` path. Designers can mock in whatever
tool; I'll translate the approved design into the Python templating. Keep it
**email-client-safe** (table-based layout, inline CSS — it's read in Gmail).

### P2 — The decision matrix: rethink the 68×13 grid

`pdf_report_generator._build_decision_matrix` renders all 68 regions as a
13-column table (Region, Score, Action, Feas, Wks, Price/m², Heat, RVI, Mom.,
3Y ROI, Sat, Mkt, Data). On A4 it's genuinely cramped — 7pt font, columns
fighting for width.

**The design problem:** is a table even the right form for "compare 68 regions
across many dimensions"? Could be a heatmap, small-multiples, a
bump/ranking chart, a tiered layout. This is a real information-design problem
worth expert attention — I don't think the answer is "make the table prettier."

**Constraint:** rendered via ReportLab flowables. If the design needs richer
rendering, the realistic alternative is an HTML→PDF path (WeasyPrint) — propose
it if the table format genuinely can't carry the design. That's a bigger
engineering lift but doable.

### P3 — Score-reasoning visualization

Tied to P1's score-breakdown point but applies to the PDF too. The system
computes *why* each region scored what it did (the multiplier chain). Right now
it's exposed as text. A consistent visual language for "here's how this score
was assembled" would build trust in the number — and trust drives action.
Wherever a score appears (email, PDF decision matrix, PDF investment-analysis
cards), the same visual treatment should apply.

### P4 — Satellite imagery presentation

The PDF embeds before/after optical, false-color, and NDVI-change maps per
top region (`_build_satellite_imagery_summary`). This is the most visually
compelling raw material the project has — actual satellite evidence of land
clearing and construction — and it's currently presented flatly. A designer
could make the change-detection story *pop*: this is the literal "we can see
the development happening" proof. Lower leverage than P1–P3 (it's
supporting evidence, not the decision surface) but high visual upside.

---

## 4. Explicitly out of scope — please don't gild these

- **Branding / logo / visual identity.** It's a personal instrument, not a
  product. No marketing surfaces.
- **Onboarding / first-run / empty states.** N=1, the user is the author.
- **The internal CLI tools** (`tools/backtest.py`, `tools/liquidity_audit.py`)
  — operator-facing, plain terminal output is correct for them.
- **Color theming for its own sake.** Color should encode meaning (tier,
  confidence, direction) — not decoration.
- **Mobile app / native anything.** Email + PDF is the medium.

---

## 5. Constraints the design must live within

- **Email:** read primarily in Gmail. Table-based layout + inline CSS only. No
  external assets, no JS, no web fonts that won't fall back gracefully.
- **PDF:** generated by ReportLab (Python). Designs must be expressible in
  ReportLab flowables (Paragraph, Table, Image, Spacer, custom flowables) OR
  the team proposes switching to an HTML→PDF renderer (WeasyPrint) — flag that
  explicitly if needed, it's a real engineering cost but acceptable.
- **Cadence:** one briefing per week. No real-time anything.
- **Data realities the design should respect honestly:**
  - The **Prediction Review** section is mostly empty right now — the
    forecast-tracking data won't be meaningful until ~late May 2026. The design
    needs a graceful "not enough history yet" state, not a hero metric.
  - Many numbers carry **honesty caveats** (SAR-only confidence reduction,
    listing-pool-shift flags, pre-fix-anchor warnings, "ann saturated" when a
    figure is a data artifact). The design must keep these legible, not bury
    them — truthfulness over polish is a core project value.
  - Scores cluster: 11 STRONG_BUYs this week, 4 of them within 1 point of the
    threshold. The design should not over-dramatize small score differences.

---

## 6. What to look at, in order

1. **`docs/sample_weekly_email.txt`** — the real 2026-05-14 email body. This is
   P1, the primary surface. Start here.
2. **`output/reports/executive_summary_20260514_135724.pdf`** — the latest PDF.
   P2 (decision matrix ~page 4) and P4 (satellite imagery section).
3. **`README.md`** — project overview + the scoring methodology, if you want
   to understand what the numbers mean.
4. **`DEVELOPMENT_ROADMAP.md`** — the Track A (investment alpha) / Track B
   (optional polish) framing. Design work is mostly Track-B-adjacent; P1 is
   the most Track-A-aligned because friction reduction directly serves the
   goal.

## 7. Handover logistics

- Mock in whatever tool the team prefers. For the email, an HTML file or
  Figma frame both work — I translate the approved design into the Python
  email templating.
- For the PDF, if the recommendation stays within ReportLab's capability,
  annotated mocks are enough. If the recommendation is "switch to WeasyPrint,"
  say so explicitly with reasoning — it's a justified call, just needs to be
  a deliberate one.
- Round-trip: send back annotated mocks + rationale; I implement; we iterate
  against a real weekly run.
- **If you only have bandwidth for one thing: do P1 (the HTML email).** It's
  the surface that's touched every week, and it's the one where good design
  most directly serves "act on real opportunities faster."
