"""
Platform/PSP detection: collect signals, match fingerprints, output MerchantProfile.
"""
from auditor.detection.types import MerchantProfile, FingerprintHit
from auditor.detection.fingerprints import FINGERPRINTS
from auditor.detection.collect import collect_page_signals, attach_network_collector
from auditor.detection.detector import detect

__all__ = [
    "MerchantProfile",
    "FingerprintHit",
    "FINGERPRINTS",
    "collect_page_signals",
    "attach_network_collector",
    "detect",
]
