"""
Complete Workflow Script with Test Integration.

This script runs the complete refactoring analysis workflow including:
1. Clone repositories
2. Detect smells with libraries and AI
3. Run tests on original code
4. Compare smells
5. Generate tests if missing
6. Refactor code
7. Analyze refactored code (including running tests)
8. Aggregate all metrics including test results
"""

import os
import sys
import subprocess
import argparse
import logging

# Add scripts directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

log = logging.getLogger(__name__)

def run_script(script_name: str, repo_name: str, additional_args: list = None):
    """Runs a script with the given repository name and additional arguments."""
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    cmd = [sys.executable, script_path, repo_name]
    if additional_args:
        cmd.extend(additional_args)
    
    log.info(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        log.error(f"Script {script_name} failed for {repo_name}")
        log.error(f"STDOUT: {result.stdout}")
        log.error(f"STDERR: {result.stderr}")
        return False
    else:
        log.info(f"Script {script_name} completed successfully for {repo_name}")
        return True

def run_workflow_for_repo(repo_name: str, repo_url: str = None):
    """Runs the complete workflow for a single repository."""
    log.info(f"\n{'='*60}")
    log.info(f"Starting workflow for repository: {repo_name}")
    log.info(f"{'='*60}")
    
    # Step 1: Clone repository (if URL provided)
    if repo_url:
        if not run_script("clone_repo.py", repo_name, [repo_url]):
            return False
    
    # Step 2: Detect smells with libraries
    if not run_script("detect_smells_lib.py", repo_name):
        return False
    
    # Step 3a: Detect smells with AI
    if not run_script("detect_smells_ai.py", repo_name):
        return False
    
    # Step 3b: Compare smells
    if not run_script("compare_smells.py", repo_name):
        return False
    
    # Step 3c: Run tests on original code
    if not run_script("run_original_tests.py", repo_name):
        log.warning(f"Original test execution failed for {repo_name}, continuing...")
    
    # Step 4: Generate tests if missing
    if not run_script("generate_tests.py", repo_name):
        log.warning(f"Test generation failed for {repo_name}, continuing...")
    
    # Step 5: Refactor code
    if not run_script("refactor_code.py", repo_name):
        return False
    
    # Step 6: Analyze refactored code (includes running tests)
    if not run_script("analyze_refactored.py", repo_name):
        return False
    
    log.info(f"Workflow completed successfully for repository: {repo_name}")
    return True

def main():
    parser = argparse.ArgumentParser(description="Run complete refactoring analysis workflow")
    parser.add_argument("repo_name", help="Name of the repository")
    parser.add_argument("--repo-url", help="URL of the repository to clone (optional)")
    parser.add_argument("--aggregate-only", action="store_true", 
                       help="Skip individual repo processing and only run aggregation")
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'workflow_{args.repo_name}.log')
        ]
    )
    
    if args.aggregate_only:
        log.info("Running aggregation only...")
        if not run_script("aggregate_metrics.py", ""):
            log.error("Aggregation failed")
            sys.exit(1)
        log.info("Aggregation completed successfully")
        return
    
    # Run workflow for the specified repository
    success = run_workflow_for_repo(args.repo_name, args.repo_url)
    
    if success:
        log.info(f"\n{'='*60}")
        log.info("WORKFLOW COMPLETED SUCCESSFULLY")
        log.info(f"{'='*60}")
        
        # Optionally run aggregation for this single repo
        log.info("Running metrics aggregation...")
        if run_script("aggregate_metrics.py", ""):
            log.info("Metrics aggregation completed successfully")
        else:
            log.warning("Metrics aggregation failed, but workflow completed")
    else:
        log.error(f"\n{'='*60}")
        log.error("WORKFLOW FAILED")
        log.error(f"{'='*60}")
        sys.exit(1)

if __name__ == "__main__":
    main() 