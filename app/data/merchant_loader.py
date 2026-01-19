"""
Merchant data loader
"""
import csv
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path


@dataclass
class Merchant:
    """Merchant data model"""
    merchant_id: str
    merchant_name: str
    base_url: str
    checkout_url: Optional[str] = None
    product_url: Optional[str] = None
    cart_url: Optional[str] = None
    status: str = "active"
    priority: int = 5
    notes: Optional[str] = None

    @property
    def homepage_url(self) -> str:
        """Get homepage URL (base_url)"""
        return self.base_url


class MerchantLoader:
    """Load merchant data from CSV file"""

    @staticmethod
    def load(csv_path: str) -> List[Merchant]:
        """
        Load merchants from CSV file
        
        Args:
            csv_path: Path to CSV file
            
        Returns:
            List of Merchant objects
            
        Raises:
            FileNotFoundError: If CSV file doesn't exist
            ValueError: If CSV format is invalid
        """
        csv_path_obj = Path(csv_path)
        if not csv_path_obj.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        merchants = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                try:
                    merchant = Merchant(
                        merchant_id=row.get('merchant_id', '').strip(),
                        merchant_name=row.get('merchant_name', '').strip(),
                        base_url=row.get('base_url', '').strip(),
                        checkout_url=row.get('checkout_url', '').strip() or None,
                        product_url=row.get('product_url', '').strip() or None,
                        cart_url=row.get('cart_url', '').strip() or None,
                        status=row.get('status', 'active').strip(),
                        priority=int(row.get('priority', 5)) if row.get('priority') else 5,
                        notes=row.get('notes', '').strip() or None
                    )
                    
                    # Validate required fields
                    if not merchant.merchant_id or not merchant.merchant_name or not merchant.base_url:
                        raise ValueError(f"Row {row_num}: Missing required fields")
                    
                    merchants.append(merchant)
                except (ValueError, KeyError) as e:
                    raise ValueError(f"Row {row_num}: Invalid data - {e}")

        return merchants
