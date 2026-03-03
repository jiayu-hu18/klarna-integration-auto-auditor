"""
Unified data structures for platform/PSP detection.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class FingerprintHit:
    """Single fingerprint match: name, weight, and what matched."""
    name: str
    weight: float
    matched: List[str] = field(default_factory=list)


@dataclass
class MerchantProfile:
    """Result of platform/PSP detection for one merchant URL."""
    url: str
    platform: Optional[str] = None  # e.g. "Shopify", "Custom", "Magento", "Headless"
    psp: List[str] = field(default_factory=list)  # e.g. ["Stripe"], ["Adyen"], ["Shopify Payments"]
    evidence: Dict[str, Any] = field(default_factory=dict)  # fingerprint hits, request URLs, script srcs, etc.
    confidence: float = 0.0  # 0~1
    notes: List[str] = field(default_factory=list)
