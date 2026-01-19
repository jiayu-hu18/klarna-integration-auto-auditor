# Test Addresses Management

This directory contains test addresses for different countries used during Phase 0 checkout testing.

## File Structure

Edit `addresses.json` to add or update test addresses for different countries.

## Address Format

Each country entry should follow this structure:

```json
{
  "COUNTRY_CODE": {
    "first_name": "Test",
    "last_name": "User",
    "email": "test+klarna@example.com",
    "phone": "+46123456789",
    "street": "Testgatan 1",
    "postal_code": "11122",
    "region": "Stockholm",  // Optional: State/Province/Region
    "city": "Stockholm",
    "country": "SE"  // ISO country code (must match key)
  }
}
```

## Adding a New Country

1. Open `addresses.json`
2. Add a new entry with the country code as the key (e.g., "FI" for Finland)
3. Fill in all required fields
4. Save the file

Example for Finland:

```json
{
  "FI": {
    "first_name": "Test",
    "last_name": "User",
    "email": "test+klarna@example.com",
    "phone": "+358123456789",
    "street": "Testikatu 1",
    "postal_code": "00100",
    "region": "Uusimaa",
    "city": "Helsinki",
    "country": "FI"
  }
}
```

## Usage

The address manager will automatically:
- Load addresses from this file when the auditor starts
- Use the appropriate address based on the country code
- Auto-detect country from URL if not specified (e.g., .dk → DK, .se → SE)

## Country Code Detection

If `--test-address-country` is not provided, the system will try to detect the country from the base URL:
- `.dk` → DK (Denmark)
- `.se` → SE (Sweden)
- `.no` → NO (Norway)
- `.fi` → FI (Finland)
- etc.

## Notes

- Email addresses should be valid but can use test domains
- Phone numbers should follow international format with country code
- Postal codes should be valid for the respective country
- The file is automatically loaded by `AddressManager` - no restart needed after editing
