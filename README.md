# Klarna Integration Auto Auditor

An automated auditing tool for Klarna integration, designed for team collaboration.

## Installation

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate  # Windows
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install Playwright browsers:
   ```bash
   playwright install chromium
   ```

## Usage

Run the auditor with a merchant registry CSV file:

```bash
python -m app.run --input data/merchant_registry.csv --out out/
```

### Command Line Options

- `--input`: Path to merchant registry CSV file (required)
- `--out`: Output directory for reports and screenshots (required)
- `--headless`: Run browser in headless mode (default: True)
- `--timeout`: Page load timeout in milliseconds (default: 30000)
- `--max-retries`: Maximum number of retries for failed audits (default: 2)

### Example

```bash
python -m app.run --input data/merchant_registry.csv --out out/ --timeout 60000
```

## Merchant Registry CSV Format

The CSV file should have the following columns:

```csv
merchant_id,merchant_name,base_url,checkout_url,product_url,cart_url,status,priority,notes
MERCHANT_001,Example Store,https://example.com,/checkout,/product/123,/cart,active,8,Main production store
```

Required fields: `merchant_id`, `merchant_name`, `base_url`

## Output

The tool generates:

1. **JSON Report**: `out/audit_YYYYMMDD_HHMMSS.json` - Contains audit results for all merchants
2. **Screenshots**: `out/screenshots/` - Screenshots for each merchant audit

## Running Tests

```bash
pytest tests/
```

## Features

- ✅ Reads merchant registry from CSV
- ✅ Uses Playwright to visit merchant homepages
- ✅ Detects Klarna logo in footer (FOOTER_KLARNA_LOGO rule)
- ✅ Generates JSON reports with evidence
- ✅ Saves screenshots for each audit
- ✅ Timeout and retry mechanisms
- ✅ Exception isolation (one merchant failure doesn't stop others)

## License

TBD
