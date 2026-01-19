"""
Address manager for test addresses
"""
import json
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass


@dataclass
class TestAddress:
    """Test address data model"""
    first_name: str
    last_name: str
    email: str
    phone: str
    street: str
    postal_code: str
    city: str
    country: str  # ISO country code (e.g., "SE", "DK", "NO")
    region: Optional[str] = None  # State/Province/Region


class AddressManager:
    """Manage test addresses for different countries"""
    
    def __init__(self, addresses_file: str = "data/addresses/addresses.json"):
        self.addresses_file = Path(addresses_file)
        self.addresses: Dict[str, TestAddress] = {}
        self.load()
    
    def load(self) -> None:
        """Load addresses from JSON file"""
        if not self.addresses_file.exists():
            self._create_default_file()
            return
        
        try:
            with open(self.addresses_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for country_code, addr_data in data.items():
                    self.addresses[country_code.upper()] = TestAddress(**addr_data)
        except Exception as e:
            print(f"Warning: Failed to load addresses: {e}")
            self._create_default_file()
    
    def _create_default_file(self) -> None:
        """Create default addresses file with Klarna approved test data"""
        default_addresses = {
            "DK": {
                "first_name": "Test",
                "last_name": "Person-dk",
                "email": "customer@email.dk",
                "phone": "+4542555628",
                "street": "Dantes Plads 7",
                "postal_code": "1556",
                "region": "København Ø",
                "city": "København Ø",
                "country": "DK"
            }
        }
        self.addresses_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.addresses_file, 'w', encoding='utf-8') as f:
            json.dump(default_addresses, f, indent=2, ensure_ascii=False)
        self.load()
    
    def get_address(self, country_code: str) -> Optional[TestAddress]:
        """Get address for a country"""
        return self.addresses.get(country_code.upper())
