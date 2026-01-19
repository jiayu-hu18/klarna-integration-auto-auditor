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

Run the audit for humac.dk:

```bash
python -m auditor.run --out-dir out --headless true
```

### Command Line Options

- `--out-dir` (required): Output directory for reports and screenshots
- `--headless` (optional): Run browser in headless mode (default: `true`)
  - Use `--headless false` to see the browser (useful for debugging)
- `--slowmo` (optional): Slow down operations by milliseconds (for debugging)
  - Example: `--slowmo 200` to add 200ms delay between actions
- `--locale` (optional): Browser locale (default: `da-DK`)
  - Example: `--locale en-US` for English

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

The script generates output in the `out/humac.dk/` directory:

### Directory Structure

```
out/humac.dk/
├── report.json                    # JSON audit report
├── footer_20260119_150030.png     # Footer screenshot
├── pdp_osm_20260119_150045.png    # PDP OSM screenshot
├── cart_20260119_150100.png       # Cart screenshot
└── checkout_payment_20260119_150115.png  # Checkout payment screenshot
```

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
   - Detects Klarna logo in footer (img src/alt or text)
   - Captures footer area screenshot

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

- The script is designed for **humac.dk** only
- Test addresses are loaded from `data/addresses/addresses.json`
- All screenshots are saved with timestamp in filename
- The script automatically handles cookie banners
