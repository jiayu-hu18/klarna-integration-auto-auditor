"""
CLI entry point for the auditor
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path

from app.data.merchant_loader import MerchantLoader
from app.core.auditor import Auditor
from app.report.report_generator import ReportGenerator


def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Klarna Integration Auto Auditor'
    )
    parser.add_argument(
        '--input',
        required=True,
        help='Path to merchant registry CSV file'
    )
    parser.add_argument(
        '--out',
        required=True,
        help='Output directory for reports and screenshots'
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        default=True,
        help='Run browser in headless mode (default: True)'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=30000,
        help='Page load timeout in milliseconds (default: 30000)'
    )
    parser.add_argument(
        '--max-retries',
        type=int,
        default=2,
        help='Maximum number of retries for failed audits (default: 2)'
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)

    # Validate input file
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input file not found: {args.input}")
        sys.exit(1)

    # Create output directory
    output_dir = Path(args.out)
    output_dir.mkdir(parents=True, exist_ok=True)
    screenshot_dir = output_dir / "screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Load merchants
        logger.info(f"Loading merchants from {args.input}")
        merchants = MerchantLoader.load(str(input_path))
        logger.info(f"Loaded {len(merchants)} merchants")

        # Initialize auditor
        auditor = Auditor(
            headless=args.headless,
            timeout=args.timeout,
            max_retries=args.max_retries
        )

        # Run audits
        logger.info("Starting audits...")
        results = await auditor.audit_all(merchants, str(screenshot_dir))

        # Generate report
        logger.info("Generating report...")
        report_generator = ReportGenerator(str(output_dir))
        report_path = report_generator.generate(results)
        logger.info(f"Report saved to: {report_path}")

        # Print summary
        passed = sum(1 for r in results if r.passed)
        failed = sum(1 for r in results if not r.passed and r.audit_status == "completed")
        skipped = sum(1 for r in results if r.audit_status == "skipped")
        
        print("\n" + "="*60)
        print("Audit Summary")
        print("="*60)
        print(f"Total merchants: {len(merchants)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Skipped: {skipped}")
        print(f"Report: {report_path}")
        print("="*60)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
