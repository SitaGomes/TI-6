"""
Step 3c: Run Tests on Original Code.

Runs pytest on the original code to establish baseline test results.
This is used later to compare with refactored code test results.
"""

import os
import sys
import argparse
import logging
from utils import (
    ORIGINAL_CODE_DIR, METRICS_DIR, ensure_dir, save_json,
    run_tests_with_pytest
)

log = logging.getLogger(__name__)

def run_original_tests(repo_name: str):
    """Runs tests on the original code and saves results."""
    repo_path = os.path.join(ORIGINAL_CODE_DIR, repo_name)
    if not os.path.isdir(repo_path):
        log.error(f"Repository directory not found: {repo_path}")
        return False

    log.info(f"--- Running Tests on Original Code: {repo_name} ---")
    
    # Output directory for metrics
    metrics_output_dir = os.path.join(METRICS_DIR, repo_name)
    ensure_dir(metrics_output_dir)
    
    # Run tests
    test_results = run_tests_with_pytest(repo_path)
    
    if test_results is None:
        log.error(f"Failed to run tests for {repo_name}")
        return False
    
    # Save results
    output_file = os.path.join(metrics_output_dir, "original_tests.json")
    save_json(test_results, output_file)
    
    # Log summary
    if test_results.get("tests_found", False):
        passed = test_results.get("passed", 0)
        total = test_results.get("total", 0)
        log.info(f"Original tests completed: {passed}/{total} passed")
    else:
        log.info("No tests found in original code")
    
    log.info(f"Test results saved to: {output_file}")
    log.info(f"--- Finished Running Original Tests: {repo_name} ---")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run tests on original code for a specific repository.")
    parser.add_argument("repo_name", help="Name of the repository directory within original_code/")
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    if not run_original_tests(args.repo_name):
        log.error(f"Failed to run tests on original code for repository: {args.repo_name}")
        sys.exit(1)
    else:
        log.info(f"Successfully ran tests on original code for repository: {args.repo_name}") 