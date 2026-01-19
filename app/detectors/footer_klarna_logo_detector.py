"""
FOOTER_KLARNA_LOGO detector
Detects Klarna logo in footer by checking keywords or img alt/src attributes
"""
import re
from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class DetectionResult:
    """Detection result"""
    rule_id: str
    passed: bool
    expected: bool
    actual: bool
    confidence: float
    matched_selectors: List[str]
    message: str


class FooterKlarnaLogoDetector:
    """Detect Klarna logo in footer"""

    RULE_ID = "FOOTER_KLARNA_LOGO"

    def __init__(self):
        """Initialize detector"""
        # Keywords to search for
        self.keywords = ['klarna', 'klarna logo', 'powered by klarna']
        # Patterns for img alt/src attributes
        self.img_patterns = [
            r'klarna',
            r'klarna.*logo',
            r'logo.*klarna'
        ]

    async def detect(self, page_source: str, browser_manager) -> DetectionResult:
        """
        Detect Klarna logo in footer
        
        Args:
            page_source: HTML page source
            browser_manager: Browser manager instance
            
        Returns:
            DetectionResult object
        """
        page_source_lower = page_source.lower()
        matched_selectors = []
        found = False

        # Check for keywords in footer area
        # Try to find footer element first
        footer_elements = await browser_manager.find_elements('footer')
        if not footer_elements:
            # Try alternative footer selectors
            footer_elements = await browser_manager.find_elements('[class*="footer"]')
            if not footer_elements:
                footer_elements = await browser_manager.find_elements('[id*="footer"]')

        footer_text = ""
        if footer_elements:
            for elem in footer_elements[:1]:  # Check first footer element
                try:
                    footer_text = (await elem.inner_text()).lower()
                except Exception:
                    pass

        # Check keywords in footer text
        for keyword in self.keywords:
            if keyword in footer_text or keyword in page_source_lower:
                matched_selectors.append(f"keyword:{keyword}")
                found = True
                break

        # Check img elements with klarna in alt or src
        img_elements = await browser_manager.find_elements('img')
        for img in img_elements:
            try:
                alt = await img.get_attribute('alt') or ''
                src = await img.get_attribute('src') or ''
                alt_lower = alt.lower()
                src_lower = src.lower()

                # Check if alt or src contains klarna
                for pattern in self.img_patterns:
                    if re.search(pattern, alt_lower, re.IGNORECASE) or \
                       re.search(pattern, src_lower, re.IGNORECASE):
                        matched_selectors.append(f"img:alt={alt},src={src}")
                        found = True
                        break
            except Exception:
                continue

        # Calculate confidence
        confidence = 0.95 if found else 0.0
        if found and len(matched_selectors) > 1:
            confidence = 1.0

        return DetectionResult(
            rule_id=self.RULE_ID,
            passed=found,
            expected=True,
            actual=found,
            confidence=confidence,
            matched_selectors=matched_selectors,
            message="Klarna logo found in footer" if found else "Klarna logo not found in footer"
        )
