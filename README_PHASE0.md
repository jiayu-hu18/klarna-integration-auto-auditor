# Klarna Integration Auto Auditor - Phase 0

Single merchant audit script for verifying Klarna Best Practice minimum closed loop.

## Installation

1. **Create virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate  # Windows
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Playwright browsers**:
   ```bash
   playwright install chromium
   ```

## Usage

### Basic Usage

Run the audit for a merchant (default: jula.se):

```bash
python -m auditor.run --out-dir out
python -m auditor.run --out-dir out --merchant https://www.aliexpress.com
python -m auditor.run --out-dir out --merchant https://www.shein.com
```

### Command Line Options

- `--out-dir` (required): Output directory for reports and screenshots
- `--merchant` (optional): Merchant URL or domain (default: `https://www.jula.se`)
- `--headless` (optional): Run browser in headless mode (default: `true`)
- `--headed`: Run with visible browser (overrides `--headless`)
- `--slowmo` (optional): Delay in ms (e.g. 200 for debugging)
- `--locale` (optional): Browser locale (default: guessed from merchant URL)

### Examples

```bash
# Run with visible browser (for debugging)
python -m auditor.run --out-dir out --headless false

# Run with slow motion (for debugging)
python -m auditor.run --out-dir out --headless false --slowmo 200

# Run with different locale
python -m auditor.run --out-dir out --headless true --locale en-US
```

## Output

The script generates output in `out/<merchant>/` (e.g. `out/aliexpress.com/`, `out/shein.com/`):

### Directory Structure

```
out/<merchant>/
├── report.json                           # JSON audit report
├── debug/                                # Footer check debug/evidence
│   ├── footer_payments_section_attempt*.png   # Pay with section screenshot (evidence when PASS)
│   ├── footer_evidence_attempt*.png          # Viewport when payments section not found (debug)
│   └── footer_roi_match_debug_attempt*_score*.png  # Match overlay (green bbox)
├── pdp_full_*.png                        # PDP OSM full-page screenshot
└── ...
```

**FOOTER_KLARNA_LOGO:** Evidence is the **payments section** element screenshot only (no full viewport match), so PASS evidence must visibly show Klarna in the “Pay with” area. Template-specific aspect-ratio filter (wordmark ≥1.8, pink badge ≥1.15) avoids false positives (e.g. “Choice” in product grid).

### Report JSON Format

```json
{
  "merchant": "humac.dk",
  "run_id": "20260119_150000",
  "timestamp": "2026-01-19T15:00:00Z",
  "results": [
    {
      "check_id": "FOOTER_KLARNA_LOGO",
      "status": "PASS",
      "timestamp": "2026-01-19T15:00:30Z",
      "evidence": {
        "screenshot_path": "out/humac.dk/footer_20260119_150030.png",
        "matched_selector": "footer img[src*='klarna']",
        "matched_text": null
      }
    },
    {
      "check_id": "PDP_OSM",
      "status": "PASS",
      "timestamp": "2026-01-19T15:00:45Z",
      "evidence": {
        "screenshot_path": "out/humac.dk/pdp_osm_20260119_150045.png",
        "matched_selector": null,
        "matched_text": "Klarna, Del op"
      }
    },
    {
      "check_id": "CART_KLARNA",
      "status": "PASS",
      "timestamp": "2026-01-19T15:01:00Z",
      "evidence": {
        "screenshot_path": "out/humac.dk/cart_20260119_150100.png",
        "matched_selector": null,
        "matched_text": "Klarna"
      }
    },
    {
      "check_id": "CHECKOUT_PAYMENT_POSITION",
      "status": "PASS",
      "timestamp": "2026-01-19T15:01:15Z",
      "evidence": {
        "screenshot_path": "out/humac.dk/checkout_payment_20260119_150115.png",
        "matched_selector": null,
        "matched_text": "Payment method at position 2"
      },
      "payment_methods": [
        "Credit Card",
        "Klarna",
        "PayPal"
      ],
      "klarna_index": 2
    }
  ],
  "summary": {
    "passed": 4,
    "failed": 0,
    "warned": 0,
    "total": 4
  }
}
```

## Checks Performed

The script performs 4 automatic checks:

1. **FOOTER_KLARNA_LOGO** (HOME)
   - Scrolls to true bottom (wheel) to trigger lazy-loaded footer; clears overlays; brings footer into view.
   - Locates “Pay with” / “Payment methods” / “We accept” etc. by text; takes **element screenshot of that section only** (no full viewport match to avoid false positives like “Choice” in product grid).
   - Multi-template match with template-specific aspect-ratio filter (wordmark ≥1.8, pink badge ≥1.15).
   - Evidence: `footer_payments_section_attempt*.png` (must visibly show Klarna). If payments section not found → FAIL (viewport saved for debug only).

2. **PDP_OSM** (Product Detail Page)
   - Detects Klarna On-Site Messaging keywords
   - Keywords: "Klarna", "Del op", "Pay in 3", etc.
   - Captures price/OSM area screenshot

3. **CART_KLARNA** (Cart Page)
   - Detects Klarna keyword in cart
   - Captures cart summary area screenshot (or full page)

4. **CHECKOUT_PAYMENT_POSITION** (Checkout)
   - Detects Klarna in payment methods list
   - Records Klarna position (1-based index)
   - Captures payment methods area screenshot
   - If checkout cannot be reached, captures error screenshot

## Error Handling

- **Error Isolation**: Each check failure does not block other checks
- **Timeouts**: Navigation timeout 30s, element wait 10s
- **Cookie Banner**: Automatically tries to accept cookie banners (non-blocking)
- **Retries**: Each check can retry up to 2 times (configurable)

## Logging

The script prints progress to stdout:

```
============================================================
Klarna Integration Auto Auditor - Phase 0
============================================================
Output directory: out
Headless: True
Locale: da-DK
============================================================
[FOOTER_KLARNA_LOGO] Starting check...
[FOOTER_KLARNA_LOGO] PASS - Screenshot: out/humac.dk/footer_20260119_150030.png
[PDP_OSM] Starting check...
[PDP_OSM] PASS - Screenshot: out/humac.dk/pdp_osm_20260119_150045.png
...
============================================================
Audit Summary
============================================================
Total checks: 4
Passed: 4
Failed: 0
Report: out/humac.dk/report.json
============================================================
```

## Troubleshooting

### Browser not found
If you see "Executable doesn't exist" error:
```bash
playwright install chromium
```

### Checkout fails
If checkout check fails, check the error_reason in report.json:
- "Login required" - Site requires login
- "Checkout button not found" - Cannot find checkout button
- "Payment methods not loaded" - Payment methods didn't load in time

### Screenshots not generated
- Check that output directory is writable
- Check browser permissions
- Try running with `--headless false` to see what's happening

## Notes

- The script supports any **single merchant** (default: jula.se; use `--merchant` for aliexpress.com, shein.com, etc.)
- Test addresses are loaded from `data/addresses/addresses.json`
- All screenshots are saved with timestamp in filename
- The script automatically handles cookie banners
