"""
Pipeline runner: detection-only by default; legacy checks when ENABLE_LEGACY_FOOTER_CHECKS=true.
"""
import os
import asyncio
from typing import List, Optional
from playwright.async_api import async_playwright
from auditor.detection import collect_page_signals, attach_network_collector, detect
from auditor.detection.types import MerchantProfile

# When true, run.py will also run legacy footer/PDP checks
ENABLE_LEGACY_FOOTER_CHECKS = os.environ.get("ENABLE_LEGACY_FOOTER_CHECKS", "false").strip().lower() == "true"


async def run_detection_for_url(
    url: str,
    page,
    wait_after_load: float = 1.5,
) -> MerchantProfile:
    """
    Navigate to url, collect signals (with network listener), run detection.
    Does not scroll, does not handle overlays/footer. Lightweight.
    """
    if not url.startswith("http"):
        url = "https://" + url
    network_urls = attach_network_collector(page)
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
    except Exception as e:
        profile = detect(
            {"final_url": page.url, "script_srcs": [], "link_hrefs": [], "cookies": [], "global_vars_presence": {}, "network_requests_seen": []},
            url,
        )
        profile.notes.append(f"goto error: {e}")
        return profile
    signals = await collect_page_signals(page, wait_after_load=wait_after_load)
    signals["network_requests_seen"] = list(network_urls)
    return detect(signals, url)


async def run_detection_pipeline(
    urls: List[str],
    out_dir: str,
    headless: bool = True,
    locale: str = "en-US",
) -> List[MerchantProfile]:
    """
    For each URL: new context/page, run detection, append profile to list.
    Does not run legacy checks. Returns list of MerchantProfile.
    """
    profiles: List[MerchantProfile] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        for url in urls:
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                locale=locale,
            )
            page = await context.new_page()
            page.set_default_navigation_timeout(15000)
            try:
                profile = await run_detection_for_url(url, page)
                profiles.append(profile)
                print(f"[DETECTION] {url} -> platform={profile.platform} psp={profile.psp} confidence={profile.confidence}")
            except Exception as e:
                from auditor.detection.types import MerchantProfile
                profiles.append(MerchantProfile(url=url, platform="Unknown", notes=[f"Error: {e}"]))
            finally:
                await context.close()
        await browser.close()
    return profiles
