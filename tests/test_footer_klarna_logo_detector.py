"""
Test for FOOTER_KLARNA_LOGO detector
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.detectors.footer_klarna_logo_detector import FooterKlarnaLogoDetector, DetectionResult


@pytest.mark.asyncio
async def test_detector_finds_klarna_keyword_in_footer():
    """Test that detector finds Klarna keyword in footer"""
    detector = FooterKlarnaLogoDetector()
    
    # Mock browser manager
    browser_manager = MagicMock()
    footer_elem = AsyncMock()
    footer_elem.inner_text = AsyncMock(return_value="Powered by Klarna")
    
    # Setup find_elements to return footer for 'footer' selector, empty for others
    async def find_elements_side_effect(selector):
        if selector == 'footer':
            return [footer_elem]
        elif selector == '[class*="footer"]':
            return []
        elif selector == '[id*="footer"]':
            return []
        elif selector == 'img':
            return []
        return []
    
    browser_manager.find_elements = AsyncMock(side_effect=find_elements_side_effect)
    
    # Page source with Klarna in footer
    page_source = """
    <html>
        <body>
            <footer>
                <p>Powered by Klarna</p>
            </footer>
        </body>
    </html>
    """
    
    result = await detector.detect(page_source, browser_manager)
    
    assert isinstance(result, DetectionResult)
    assert result.rule_id == "FOOTER_KLARNA_LOGO"
    assert result.passed is True
    assert result.actual is True
    assert result.expected is True
    assert result.confidence > 0.0
    assert len(result.matched_selectors) > 0
    assert "klarna" in result.message.lower()


@pytest.mark.asyncio
async def test_detector_finds_klarna_in_img_alt():
    """Test that detector finds Klarna in img alt attribute"""
    detector = FooterKlarnaLogoDetector()
    
    # Mock browser manager
    browser_manager = MagicMock()
    
    # Mock footer element (empty)
    footer_elem = AsyncMock()
    footer_elem.inner_text = AsyncMock(return_value="")
    
    # Mock img element
    img_elem = MagicMock()
    img_elem.get_attribute = AsyncMock(side_effect=lambda attr: {
        'alt': 'Klarna Logo',
        'src': '/images/klarna.png'
    }.get(attr, None))
    
    # Setup find_elements to return different results based on selector
    async def find_elements_side_effect(selector):
        if selector == 'footer':
            return []
        elif selector == '[class*="footer"]':
            return []
        elif selector == '[id*="footer"]':
            return []
        elif selector == 'img':
            return [img_elem]
        return []
    
    browser_manager.find_elements = AsyncMock(side_effect=find_elements_side_effect)
    
    page_source = """
    <html>
        <body>
            <footer>
                <img alt="Klarna Logo" src="/images/klarna.png" />
            </footer>
        </body>
    </html>
    """
    
    result = await detector.detect(page_source, browser_manager)
    
    assert isinstance(result, DetectionResult)
    assert result.rule_id == "FOOTER_KLARNA_LOGO"
    assert result.passed is True
    assert result.confidence > 0.0
    assert any("img" in sel for sel in result.matched_selectors)


@pytest.mark.asyncio
async def test_detector_not_finds_klarna():
    """Test that detector returns False when Klarna is not found"""
    detector = FooterKlarnaLogoDetector()
    
    # Mock browser manager
    browser_manager = MagicMock()
    footer_elem = AsyncMock()
    footer_elem.inner_text = AsyncMock(return_value="Powered by Other Payment")
    
    # Setup find_elements to return footer without Klarna
    async def find_elements_side_effect(selector):
        if selector == 'footer':
            return [footer_elem]
        elif selector == '[class*="footer"]':
            return []
        elif selector == '[id*="footer"]':
            return []
        elif selector == 'img':
            return []
        return []
    
    browser_manager.find_elements = AsyncMock(side_effect=find_elements_side_effect)
    
    # Page source without Klarna
    page_source = """
    <html>
        <body>
            <footer>
                <p>Powered by Other Payment</p>
            </footer>
        </body>
    </html>
    """
    
    result = await detector.detect(page_source, browser_manager)
    
    assert isinstance(result, DetectionResult)
    assert result.rule_id == "FOOTER_KLARNA_LOGO"
    assert result.passed is False
    assert result.actual is False
    assert result.confidence == 0.0
    assert "not found" in result.message.lower()
