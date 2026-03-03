"""
Legacy checks (footer Klarna logo, PDP OSM) — heavy scroll/overlay logic.
Not run by default; set ENABLE_LEGACY_FOOTER_CHECKS=true to include in pipeline.
See docs/legacy_checks.md.
"""
from auditor.legacy_checks.footer_klarna_logo import FooterKlarnaLogoCheck
from auditor.legacy_checks.pdp_osm import PDPOSMCheck

__all__ = ["FooterKlarnaLogoCheck", "PDPOSMCheck"]
