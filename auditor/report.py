"""
Report generation
"""
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class Evidence:
    """Evidence for a check result"""
    screenshot_path: Optional[str] = None
    matched_selector: Optional[str] = None
    matched_text: Optional[str] = None
    # PDP_OSM: full page (pdp_full_*.png) and optional element (pdp_osm_element_*.png)
    page_screenshot_path: Optional[str] = None
    element_screenshot_path: Optional[str] = None
    # FOOTER_KLARNA_LOGO: template matching + payments ROI (multi-template)
    template_match_score: Optional[float] = None
    template_bbox: Optional[List[int]] = None
    template_path: Optional[str] = None
    debug_overlay_path: Optional[str] = None
    roi_screenshot_path: Optional[str] = None
    best_template_path: Optional[str] = None
    best_score: Optional[float] = None
    best_bbox: Optional[List[int]] = None
    all_templates: Optional[List[Dict[str, Any]]] = None


@dataclass
class CheckResult:
    """Result of a single check"""
    check_id: str
    status: str  # "PASS" | "FAIL" | "WARN"
    evidence: Evidence
    timestamp: str
    error_reason: Optional[str] = None
    # For CHECKOUT_PAYMENT_POSITION only:
    payment_methods: Optional[List[str]] = None
    klarna_index: Optional[int] = None


class ReportGenerator:
    """Generate JSON report"""
    
    def __init__(self, out_dir: str, merchant: str = "humac.dk"):
        self.out_dir = Path(out_dir)
        self.merchant = merchant
        self.merchant_dir = self.out_dir / merchant
        self.merchant_dir.mkdir(parents=True, exist_ok=True)
    
    def generate(self, results: List[CheckResult]) -> str:
        """Generate JSON report"""
        report_path = self.merchant_dir / "report.json"
        
        # Generate run_id
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Calculate summary
        passed = sum(1 for r in results if r.status == "PASS")
        failed = sum(1 for r in results if r.status == "FAIL")
        warned = sum(1 for r in results if r.status == "WARN")
        
        # Build report
        report = {
            "merchant": self.merchant,
            "run_id": run_id,
            "timestamp": datetime.now().isoformat() + "Z",
            "results": [self._format_result(r) for r in results],
            "summary": {
                "passed": passed,
                "failed": failed,
                "warned": warned,
                "total": len(results)
            }
        }
        
        # Write JSON file
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return str(report_path)
    
    def _format_result(self, result: CheckResult) -> Dict[str, Any]:
        """Format single check result to JSON"""
        evidence_dict = {
            "screenshot_path": result.evidence.screenshot_path,
            "matched_selector": result.evidence.matched_selector,
            "matched_text": result.evidence.matched_text
        }
        if result.evidence.page_screenshot_path:
            evidence_dict["page_screenshot_path"] = result.evidence.page_screenshot_path
        if result.evidence.element_screenshot_path:
            evidence_dict["element_screenshot_path"] = result.evidence.element_screenshot_path
        if result.evidence.template_match_score is not None:
            evidence_dict["template_match_score"] = result.evidence.template_match_score
        if result.evidence.template_bbox is not None:
            evidence_dict["template_bbox"] = result.evidence.template_bbox
        if result.evidence.template_path:
            evidence_dict["template_path"] = result.evidence.template_path
        if result.evidence.debug_overlay_path:
            evidence_dict["debug_overlay_path"] = result.evidence.debug_overlay_path
        if result.evidence.roi_screenshot_path:
            evidence_dict["roi_screenshot_path"] = result.evidence.roi_screenshot_path
        if result.evidence.best_template_path:
            evidence_dict["best_template_path"] = result.evidence.best_template_path
        if result.evidence.best_score is not None:
            evidence_dict["best_score"] = result.evidence.best_score
        if result.evidence.best_bbox is not None:
            evidence_dict["best_bbox"] = result.evidence.best_bbox
        if result.evidence.all_templates is not None:
            evidence_dict["all_templates"] = result.evidence.all_templates
        formatted = {
            "check_id": result.check_id,
            "status": result.status,
            "timestamp": result.timestamp,
            "evidence": evidence_dict
        }
        
        # Add error_reason if FAIL
        if result.status == "FAIL" and result.error_reason:
            formatted["error_reason"] = result.error_reason
        
        # Add checkout-specific fields
        if result.check_id == "CHECKOUT_PAYMENT_POSITION":
            formatted["payment_methods"] = result.payment_methods or []
            formatted["klarna_index"] = result.klarna_index
        
        return formatted
