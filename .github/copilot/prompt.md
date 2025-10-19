# GitHub Copilot Instructions for CloudClearingAPI

You are an expert Python developer specializing in geospatial analysis, financial modeling, and web scraping. Your primary role is to assist in developing the CloudClearingAPI.

## 1. Core Project Objective

The system identifies land development investment opportunities in Indonesia by analyzing satellite data for physical changes and then enriching this with infrastructure quality and financial viability metrics. The final output is an automated PDF report.

---

## 2. Key Technologies & Libraries

- **Primary Language:** Python 3.10+
- **Geospatial:** `earthengine-api` for satellite data.
- **Infrastructure:** `requests` to query the OpenStreetMap Overpass API.
- **Financial Data:** `requests` and `BeautifulSoup4` for web scraping real estate portals (Lamudi, Rumah.com).
- **PDF Generation:** `reportlab` is the **only** library used for creating PDF reports.
- **Configuration:** `PyYAML` for loading settings from `config.yaml`.
- **Data Structures:** Use `@dataclass` for simple data containers.

---

## 3. Architectural Principles

The system has three main, distinct stages. Always maintain this separation of concerns.

### Stage 1: Core Scoring (Activity Score)

- **File:** `src/core/corrected_scoring.py`
- **Purpose:** To generate a base "Activity Score" from 0-40 based **only** on satellite data.
- **Logic:** This score is then adjusted by Infrastructure and Market multipliers. Do not mix financial calculations into this core score.

### Stage 2: Financial Projection Engine

- **File:** `src/core/financial_metrics.py`
- **Purpose:** This engine runs *after* the core scoring is complete. It takes the satellite, infrastructure, and market data as inputs to calculate ROI, land value, and development costs.
- **Data Source:** It uses the `LandPriceOrchestrator` which has a cascading logic: **Live Scrape > Cache > Static Benchmark**. This pattern is critical.

### Stage 3: PDF Report Generation

- **File:** `src/core/pdf_report_generator.py`
- **Purpose:** To take the final scoring results and financial projections and render them into a multi-page PDF using `reportlab`.

---

## 4. Important Coding Patterns & Rules

- **Strict Type Hinting:** All function signatures and variables should have type hints (`str`, `Dict`, `List`, `Optional`).
- **Use Dataclasses:** For data transfer objects like `FinancialProjection` or `ScrapeResult`, always prefer using `@dataclass`.
- **Configuration Management:** Never hardcode URLs, file paths, or thresholds. These values must be loaded from a `config.yaml` file via the `Config` class.
- **Error Handling:** All network requests (`requests.get`, `ee.ImageCollection`) must be wrapped in `try...except` blocks that handle timeouts and connection errors gracefully.
- **Logging, Not Printing:** Use the `logging` module for all debugging and informational output. Avoid using `print()`.
- **Web Scraping Rules:** When working on scrapers, always include user-agent rotation and a rate limit (e.g., `time.sleep(2)`).

By following these instructions, you will provide highly relevant, context-aware code that fits perfectly within the existing CloudClearingAPI architecture.
