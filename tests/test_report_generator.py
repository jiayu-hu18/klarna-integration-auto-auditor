"""
Test for report generator
"""
import json
import pytest
from pathlib import Path
from datetime import datetime
from app.report.report_generator import ReportGenerator, AuditResult


def test_report_generator_creates_json_file(tmp_path):
    """Test that report generator creates JSON file with correct structure"""
    output_dir = tmp_path / "reports"
    generator = ReportGenerator(str(output_dir))
    
    # Create test audit results
    results = [
        AuditResult(
            merchant_id="MERCHANT_001",
            merchant_name="Test Store",
            base_url="https://example.com",
            audit_status="completed",
            audit_timestamp=datetime.now().isoformat() + "Z",
            rule_id="FOOTER_KLARNA_LOGO",
            rule_description="Detect Klarna logo in footer",
            passed=True,
            confidence=0.95,
            matched_selectors=["keyword:klarna"],
            screenshot_path="screenshots/test.png",
            message="Klarna logo found in footer",
            error=None
        ),
        AuditResult(
            merchant_id="MERCHANT_002",
            merchant_name="Another Store",
            base_url="https://another.com",
            audit_status="completed",
            audit_timestamp=datetime.now().isoformat() + "Z",
            rule_id="FOOTER_KLARNA_LOGO",
            rule_description="Detect Klarna logo in footer",
            passed=False,
            confidence=0.0,
            matched_selectors=[],
            screenshot_path=None,
            message="Klarna logo not found in footer",
            error=None
        )
    ]
    
    # Generate report
    report_path = generator.generate(results)
    
    # Verify file exists
    assert Path(report_path).exists()
    
    # Read and verify JSON structure
    with open(report_path, 'r', encoding='utf-8') as f:
        report = json.load(f)
    
    # Verify structure
    assert "audit_metadata" in report
    assert "summary" in report
    assert "merchants" in report
    
    # Verify metadata
    assert report["audit_metadata"]["version"] == "1.0.0"
    assert report["audit_metadata"]["total_merchants"] == 2
    
    # Verify summary
    assert report["summary"]["total_merchants_audited"] == 2
    assert report["summary"]["total_merchants_passed"] == 1
    assert report["summary"]["total_merchants_failed"] == 1
    assert report["summary"]["total_merchants_skipped"] == 0
    
    # Verify merchants
    assert len(report["merchants"]) == 2
    assert report["merchants"][0]["merchant_id"] == "MERCHANT_001"
    assert report["merchants"][0]["status"] == "passed"
    assert report["merchants"][1]["merchant_id"] == "MERCHANT_002"
    assert report["merchants"][1]["status"] == "failed"
    
    # Verify evidence structure
    assert "evidence" in report["merchants"][0]
    assert "screenshot_path" in report["merchants"][0]["evidence"]
    assert "matched_selectors" in report["merchants"][0]["evidence"]
    assert "url" in report["merchants"][0]["evidence"]
    assert "timestamp" in report["merchants"][0]["evidence"]


def test_report_generator_with_custom_filename(tmp_path):
    """Test that report generator accepts custom filename"""
    output_dir = tmp_path / "reports"
    generator = ReportGenerator(str(output_dir))
    
    results = [
        AuditResult(
            merchant_id="MERCHANT_001",
            merchant_name="Test Store",
            base_url="https://example.com",
            audit_status="completed",
            audit_timestamp=datetime.now().isoformat() + "Z",
            rule_id="FOOTER_KLARNA_LOGO",
            rule_description="Detect Klarna logo in footer",
            passed=True,
            confidence=0.95,
            matched_selectors=[],
            screenshot_path=None,
            message="Test",
            error=None
        )
    ]
    
    custom_filename = "custom_report.json"
    report_path = generator.generate(results, filename=custom_filename)
    
    assert Path(report_path).name == custom_filename
    assert Path(report_path).exists()


def test_report_generator_handles_skipped_merchants(tmp_path):
    """Test that report generator correctly handles skipped merchants"""
    output_dir = tmp_path / "reports"
    generator = ReportGenerator(str(output_dir))
    
    results = [
        AuditResult(
            merchant_id="MERCHANT_001",
            merchant_name="Test Store",
            base_url="https://example.com",
            audit_status="skipped",
            audit_timestamp=datetime.now().isoformat() + "Z",
            rule_id="FOOTER_KLARNA_LOGO",
            rule_description="Detect Klarna logo in footer",
            passed=False,
            confidence=0.0,
            matched_selectors=[],
            screenshot_path=None,
            message="Skipped",
            error=None
        )
    ]
    
    report_path = generator.generate(results)
    
    with open(report_path, 'r', encoding='utf-8') as f:
        report = json.load(f)
    
    assert report["summary"]["total_merchants_skipped"] == 1
    assert report["summary"]["total_merchants_audited"] == 0
    assert report["merchants"][0]["audit_status"] == "skipped"
