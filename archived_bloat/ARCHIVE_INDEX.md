# Archived Documentation & Scripts

**Archive Date:** October 18, 2025  
**Reason:** Cleanup of documentation bloat - consolidated into README.md and TECHNICAL_SCORING_DOCUMENTATION.md

---

## What's Archived Here

### `docs_archive_oct18/` - 26 Documentation Files

Status/progress tracking documents that were created during development:

**API & Fixes:**
- API_AND_PDF_FIXES_COMPLETED.md
- API_FAILURE_ROOT_CAUSE.md
- API_FIX_SUMMARY.md

**Scoring System:**
- SCORING_FIX_SUMMARY.md
- SCORING_SYSTEM_DISCREPANCY_REPORT.md
- CORRECTED_SCORING_DEPLOYMENT_PLAN.md

**PDF Enhancements:**
- PDF_ENHANCEMENTS_COMPLETE.md
- PDF_ENHANCEMENTS_OCT11.md
- PDF_IMPROVEMENTS_NEEDED.md
- ENHANCED_PDF_PREVIEW.md

**Status Tracking:**
- CURRENT_STATUS.md
- MONITORING_LIVE_STATUS.md
- PRODUCTION_TEST_SUMMARY.md
- JAVA_API_TEST_RUN.md

**Phase Documentation:**
- PHASE_1_INTEGRATION_COMPLETE.md
- PHASE_2_COMPLETE.md
- OPTION_B_IMPLEMENTATION_SUMMARY.md

**Setup Guides:**
- SETUP_GUIDE.md (redundant with README.md)
- QUICKSTART.md (consolidated into README.md)
- EARTH_ENGINE_SETUP.md (moved to README.md)
- GITHUB_SETUP.md
- GITHUB_SUCCESS.md

**Strategy/Planning:**
- INDONESIA_NATIONWIDE_EXPANSION.md
- INVESTMENT_SCORING_METHODOLOGY.md (replaced by TECHNICAL_SCORING_DOCUMENTATION.md)
- DOCUMENTATION_VERIFICATION_REPORT.md

**Old README:**
- README.old.md (backup of previous README before simplification)

### `scripts_archive_oct18/` - Development Scripts

**Check/Monitor Scripts:**
- check_java_progress.sh - Monitoring progress checker
- check_java_status.sh - Status checker
- check_progress.sh - Generic progress checker

**Test/Validation Scripts:**
- test_api_confidence_fix.py - Testing API confidence tracking fix
- validate_corrected_scoring.py - Validating scoring system fixes

**One-off Utilities:**
- regenerate_pdf.py - PDF regeneration utility
- generate_java_pdf.py - Java PDF generation utility
- run_java_priority1_monitor.py - Priority region monitoring (deprecated)

### `logs_archive_oct18/` - Old Log Files

**Full Monitoring Runs:**
- full_corrected_run.log (Oct 7)
- full_corrected_run_java.log (Oct 7)
- full_java_corrected_run.log (Oct 8)
- java_monitoring_run_20251011_115640.log
- java_monitoring_run_20251011_115720.log (383 KB)

**Test/Production Logs:**
- production_test_results.log
- test_fallback_scoring.log

---

## Active Documentation (Root Directory)

After cleanup, only these documentation files remain in the root:

1. **README.md** - Main project README
   - Quick start guide
   - Installation instructions
   - Usage examples
   - Configuration
   - Troubleshooting

2. **TECHNICAL_SCORING_DOCUMENTATION.md** - Complete technical reference
   - System architecture
   - Data sources & APIs (Google Earth Engine, OSM Overpass)
   - Detailed scoring algorithms with formulas
   - Component specifications
   - Confidence calculation methodology
   - PDF report generation
   - Formula reference card

---

## Why Archived?

These files were created during iterative development to track:
- Bug fixes and their solutions
- Status updates during long-running work
- Multiple versions of setup guides
- Progress tracking for monitoring runs
- Test results and validations

All essential information has been consolidated into:
- **README.md** for setup and general usage
- **TECHNICAL_SCORING_DOCUMENTATION.md** for technical details

The archived files are preserved for historical reference but are no longer needed for day-to-day development.

---

## Restoration

If you need any of these files:

```bash
# Copy back from archive
cp archived_bloat/docs_archive_oct18/[filename] .

# Or view without copying
cat archived_bloat/docs_archive_oct18/[filename]
```

---

**Last Updated:** October 18, 2025
