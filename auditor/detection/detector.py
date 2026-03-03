"""
Score signals against fingerprints and produce MerchantProfile.
"""
from typing import Dict, Any, List, Tuple
from auditor.detection.types import MerchantProfile
from auditor.detection.fingerprints import FINGERPRINTS, PLATFORM_THRESHOLD, PSP_THRESHOLD


def _check_matcher(signals: Dict[str, Any], fp: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Return (any_match, list of matched strings)."""
    matched: List[str] = []
    matchers = fp.get("matchers") or {}
    # html_contains: check in concatenated script_srcs + link_hrefs + first part of final_url (we don't have full HTML)
    if "html_contains" in matchers:
        haystack = " ".join(signals.get("script_srcs", []) + signals.get("link_hrefs", []) + [signals.get("final_url", "")])
        for s in matchers["html_contains"]:
            if s and s.lower() in haystack.lower():
                matched.append(f"html_contains:{s}")
    if "script_src_contains" in matchers:
        for src in signals.get("script_srcs", []):
            for s in matchers["script_src_contains"]:
                if s and s.lower() in src.lower():
                    matched.append(f"script_src:{s}")
    if "request_url_contains" in matchers:
        for u in signals.get("network_requests_seen", []):
            for s in matchers["request_url_contains"]:
                if s and s.lower() in u.lower():
                    matched.append(f"request:{s}")
                    break
    if "cookie_names" in matchers:
        names = {c.get("name", "") for c in signals.get("cookies", []) if c.get("name")}
        for s in matchers["cookie_names"]:
            if s and any(s.lower() in n.lower() for n in names):
                matched.append(f"cookie:{s}")
    # global_vars
    globals_key = fp.get("global_vars")
    if globals_key:
        presence = signals.get("global_vars_presence") or {}
        for var in globals_key:
            if presence.get(var):
                matched.append(f"global:{var}")
    return (len(matched) > 0, list(dict.fromkeys(matched)))


def detect(signals: Dict[str, Any], url: str) -> MerchantProfile:
    """
    Run all fingerprints on signals; output MerchantProfile with platform, psp, confidence, evidence.
    """
    platform_scores: Dict[str, float] = {}
    psp_scores: Dict[str, float] = {}
    evidence_hits: List[Dict[str, Any]] = []
    all_matched: List[str] = []

    for fp in FINGERPRINTS:
        hit, matched = _check_matcher(signals, fp)
        if not hit or not matched:
            continue
        weight = float(fp.get("weight", 0.5))
        evidence_hits.append({
            "fingerprint": fp.get("id") or fp.get("name"),
            "name": fp.get("name"),
            "weight": weight,
            "matched": matched,
        })
        all_matched.extend(matched)
        if fp.get("category") == "platform" and fp.get("output_platform"):
            name = fp["output_platform"]
            platform_scores[name] = platform_scores.get(name, 0) + weight
        if fp.get("category") == "psp" and fp.get("output_psp_add"):
            name = fp["output_psp_add"]
            psp_scores[name] = psp_scores.get(name, 0) + weight

    # Best platform
    platform = None
    if platform_scores:
        platform = max(platform_scores, key=platform_scores.get)
        if platform_scores[platform] < PLATFORM_THRESHOLD:
            platform = None
    if not platform:
        platform = "Unknown"

    # PSP list above threshold
    psp = [name for name, score in psp_scores.items() if score >= PSP_THRESHOLD]
    psp = sorted(psp)

    # Confidence: normalize by max possible (e.g. top platform score / 2.0 or sum of top / 3)
    max_platform = max(platform_scores.values()) if platform_scores else 0
    max_possible = 2.0
    confidence = min(1.0, max_platform / max_possible) if max_possible else 0
    if psp and not platform_scores:
        confidence = max(confidence, min(1.0, max(psp_scores.values()) / max_possible))

    evidence = {
        "hits": evidence_hits,
        "platform_scores": platform_scores,
        "psp_scores": psp_scores,
        "matched_signals_sample": all_matched[:50],
    }

    return MerchantProfile(
        url=url,
        platform=platform,
        psp=psp,
        evidence=evidence,
        confidence=round(confidence, 4),
        notes=[],
    )
