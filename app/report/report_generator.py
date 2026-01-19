"""
Report generator for audit results
"""
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class AuditResult:
    """Audit result for a merchant"""
    merchant_id: str
    merchant_name: str
    base_url: str
    audit_status: str  # "completed" | "failed" | "skipped"
    audit_timestamp: str
    rule_id: str
    rule_description: str
    passed: bool
    confidence: float
    matched_selectors: List[str]
    screenshot_path: Optional[str]
    message: str
    error: Optional[str] = None


class ReportGenerator:
    """Generate JSON reports from audit results"""

    def __init__(self, output_dir: str):
        """
        Initialize report generator
        
        Args:
            output_dir: Output directory for reports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, results: List[AuditResult], filename: str = None) -> str:
        """
        Generate JSON report from audit results
        
        Args:
            results: List of audit results
            filename: Optional filename (default: audit_YYYYMMDD_HHMMSS.json)
            
        Returns:
            Path to generated report file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"audit_{timestamp}.json"

        report_path = self.output_dir / filename

        # Create report structure
        report = {
            "audit_metadata": {
                "audit_id": f"AUDIT_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "timestamp": datetime.now().isoformat() + "Z",
                "version": "1.0.0",
                "total_merchants": len(results)
            },
            "summary": {
                "total_merchants_audited": len([r for r in results if r.audit_status == "completed"]),
                "total_merchants_passed": len([r for r in results if r.passed]),
                "total_merchants_failed": len([r for r in results if not r.passed and r.audit_status == "completed"]),
                "total_merchants_skipped": len([r for r in results if r.audit_status == "skipped"])
            },
            "merchants": [self._format_result(result) for result in results]
        }

        # Write JSON file
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return str(report_path)

    def _format_result(self, result: AuditResult) -> Dict[str, Any]:
        """Format single audit result"""
        return {
            "merchant_id": result.merchant_id,
            "merchant_name": result.merchant_name,
            "base_url": result.base_url,
            "audit_status": result.audit_status,
            "audit_timestamp": result.audit_timestamp,
            "rule_id": result.rule_id,
            "rule_description": result.rule_description,
            "status": "passed" if result.passed else "failed",
            "expected": True,
            "actual": result.passed,
            "confidence": result.confidence,
            "evidence": {
                "screenshot_path": result.screenshot_path,
                "matched_selectors": result.matched_selectors,
                "url": result.base_url,
                "timestamp": result.audit_timestamp
            },
            "message": result.message,
            "error": result.error
        }
