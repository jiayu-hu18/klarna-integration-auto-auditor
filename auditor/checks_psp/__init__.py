"""
PSP-specific checks (Stripe, Shopify, Adyen). Future: if "Stripe" in profile.psp run stripe_checks, etc.
"""
from auditor.checks_psp.base import PSPCheck

__all__ = ["PSPCheck"]
