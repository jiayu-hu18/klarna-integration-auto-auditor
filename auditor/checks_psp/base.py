"""
Base class for PSP-specific checks. Future: run by platform/PSP (e.g. if Stripe in profile.psp).
"""
from abc import ABC, abstractmethod
from typing import Any, Optional
from playwright.async_api import Page
from auditor.detection.types import MerchantProfile


class PSPCheck(ABC):
    """Base for Stripe/Shopify/Adyen etc. checks. execute(page, profile, ...) — to be wired by runner."""

    CHECK_ID: str = ""

    @abstractmethod
    async def execute(
        self,
        page: Page,
        profile: MerchantProfile,
        **kwargs: Any,
    ) -> Any:
        """Run check; return result (e.g. CheckResult)."""
        pass
