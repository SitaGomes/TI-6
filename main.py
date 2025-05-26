"""
Main workflow orchestration script.

Fetches N repositories, processes each one through the analysis and refactoring pipeline,
aggregates the final metrics, and optionally cleans up working directories.
"""

import os
import sys
import subprocess
import argparse
import shutil
import logging

# --- Configuration ---
PYTHON_EXECUTABLE = sys.executable # Use the same python that runs this script
SCRIPTS_DIR = "scripts"
ORIGINAL_CODE_DIR = "original_code"
REFACTORED_CODE_DIR = "refactored_code"
METRICS_DIR = "metrics"
# Removed SMELL_STRATEGIES since we only use zero-shot now

# Define the sequence of scripts to run for each repo
# Use the new, simplified script names in fixed order
REPO_PROCESSING_SCRIPTS = [
    "detect_smells_local.py", # Was 02
    "detect_smells_ai.py",    # Was 03
    "compare_smells.py",      # Was 03b
    "generate_tests.py",      # Was 04
    "refactor_code.py",       # Was 05
    "analyze_refactored.py",  # Was 06
]

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

def run_script(script_name: str, args: list[str] = [], repo_name_for_log: str = "N/A") -> bool:
    """Runs a script from the scripts directory using subprocess."""
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    command = [PYTHON_EXECUTABLE, script_path] + args
    log.info(f"--- Running script: {script_name} for repo: {repo_name_for_log} ---")
    log.info(f"Executing: {' '.join(command)}")
    
    try:
        # Run the script and stream output, check for errors
        process = subprocess.run(command, check=True, text=True, encoding='utf-8', 
                                 stdout=sys.stdout, stderr=sys.stderr)
        log.info(f"--- Script {script_name} completed successfully (Exit Code: {process.returncode}) ---")
        return True
    except FileNotFoundError:
        log.error(f"Error: Script not found at {script_path}")
        return False
    except subprocess.CalledProcessError as e:
        log.error(f"Error executing script: {script_name} (Exit Code: {e.returncode})")
        # Output was already streamed to stderr
        return False
    except Exception as e:
        log.error(f"An unexpected error occurred while running {script_name}: {e}")
        return False

def perform_cleanup():
    """Deletes the original_code and refactored_code directories."""
    log.info("--- Starting Cleanup --- ")
    deleted_original = False
    deleted_refactored = False
    if os.path.exists(ORIGINAL_CODE_DIR):
        try:
            shutil.rmtree(ORIGINAL_CODE_DIR)
            log.info(f"Successfully removed {ORIGINAL_CODE_DIR}")
            deleted_original = True
        except Exception as e:
            log.error(f"Error removing {ORIGINAL_CODE_DIR}: {e}")
    else:
        log.info(f"{ORIGINAL_CODE_DIR} not found, skipping removal.")
        deleted_original = True # Considered clean if not found
        
    if os.path.exists(REFACTORED_CODE_DIR):
        try:
            shutil.rmtree(REFACTORED_CODE_DIR)
            log.info(f"Successfully removed {REFACTORED_CODE_DIR}")
            deleted_refactored = True
        except Exception as e:
            log.error(f"Error removing {REFACTORED_CODE_DIR}: {e}")
    else:
         log.info(f"{REFACTORED_CODE_DIR} not found, skipping removal.")
         deleted_refactored = True
         
    log.info("--- Cleanup Finished --- ")
    return deleted_original and deleted_refactored


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the full AI refactoring analysis workflow.")
    parser.add_argument("-n", "--num-repos", type=int, default=1, 
                        help="Number of top repositories to fetch and process.")
    parser.add_argument("--skip-fetch", action="store_true", 
                        help="Skip fetching, assume repos exist in original_code/")
    parser.add_argument("--skip-cleanup", action="store_true", 
                        help="Skip deleting original_code and refactored_code directories at the end.")
    parser.add_argument("--start-from", type=str, default="01",
                        help="Start the workflow from a specific script number (e.g., '02', '05'). Requires --skip-fetch and assumes previous steps are done.")
# Removed smell strategy arguments since we only use zero-shot now

    args = parser.parse_args()

    # --- Step 1: Fetch Repos (or identify existing) ---
    fetched_repo_names = []
    if args.skip_fetch:
        if not os.path.exists(ORIGINAL_CODE_DIR):
             log.error(f"--skip-fetch used, but '{ORIGINAL_CODE_DIR}' not found.")
             sys.exit(1)
        fetched_repo_names = [d for d in os.listdir(ORIGINAL_CODE_DIR) 
                              if os.path.isdir(os.path.join(ORIGINAL_CODE_DIR, d))]
        if not fetched_repo_names:
             log.error(f"--skip-fetch used, but no repositories found in '{ORIGINAL_CODE_DIR}'.")
             sys.exit(1)
        log.info(f"Skipping fetch. Found existing repositories: {fetched_repo_names}")
        # Adjust NUM_REPOS in 01_fetch_repos.py based on args.num_repos if needed
        # This requires reading/writing the script file, which is complex. 
        # Easier: User should ensure 01_fetch_repos.py has the correct N or use -n with run_workflow
        # For now, if not skipping fetch, we rely on the N set inside 01_fetch_repos.py
    else:
        log.info(f"Running fetch script (fetch_repos.py) with N={args.num_repos} (Set N inside the script if this is not desired)")
        # Run the fetch script using the helper - use new name
        if not run_script("fetch_repos.py", repo_name_for_log="Fetch Step"):
            log.error("Fetching repositories failed. Aborting.")
            sys.exit(1)
        
        # List the directories created by the fetch script
        if not os.path.exists(ORIGINAL_CODE_DIR):
             log.error(f"Fetch script ran, but '{ORIGINAL_CODE_DIR}' directory not created.")
             sys.exit(1)
        fetched_repo_names = [d for d in os.listdir(ORIGINAL_CODE_DIR) 
                              if os.path.isdir(os.path.join(ORIGINAL_CODE_DIR, d))]
        if not fetched_repo_names:
            log.error("Fetch script ran but no repository directories found in original_code.")
            sys.exit(1)
        log.info(f"Fetch script completed. Found repositories: {fetched_repo_names}")

    # Limit processing to args.num_repos if specified and not skipping fetch 
    # (If skipping fetch, we process all found repos)
    if not args.skip_fetch and len(fetched_repo_names) > args.num_repos:
         log.warning(f"Fetch script might have cloned more than {args.num_repos} repos. Processing only the first {args.num_repos}.")
         fetched_repo_names = fetched_repo_names[:args.num_repos]

    log.info(f"Processing repositories: {fetched_repo_names}")
    
    # --- Steps 2-6: Process Each Repository ---
    failed_repos = []
    # Determine scripts to run based on start_from argument - Simplified logic
    start_index = 0
    start_script_name_map = {
        "02": "detect_smells_local.py",
        "03": "detect_smells_ai.py",
        "03b": "compare_smells.py", # Allow 03b for clarity
        "04": "generate_tests.py",
        "05": "refactor_code.py",
        "06": "analyze_refactored.py",
    }
    
    if args.start_from != "01": # Start-from applies to steps 02-06
        start_script_name = start_script_name_map.get(args.start_from.replace("_", "")) # Allow e.g. 03b
        if start_script_name and start_script_name in REPO_PROCESSING_SCRIPTS:
            start_index = REPO_PROCESSING_SCRIPTS.index(start_script_name)
        else:
             log.error(f"Invalid --start-from value '{args.start_from}'. Expected 02-06.")
             sys.exit(1)
             
    log.info(f"Starting processing loop from script: {REPO_PROCESSING_SCRIPTS[start_index]}")

    for repo_name in fetched_repo_names:
        log.info(f"===== Processing Repository: {repo_name} =====")
        repo_failed = False
        repo_warnings = []
        
        # Run scripts from the calculated start index using the fixed list
        for script_basename in REPO_PROCESSING_SCRIPTS[start_index:]:
            # Run all scripts normally with just repo_name argument
            if not run_script(script_basename, args=[repo_name], repo_name_for_log=repo_name):
                log.warning(f"Script {script_basename} failed for repo {repo_name}, but continuing with next steps.")
                repo_warnings.append(f"Script {script_basename} failed")
                
                # If a critical script fails that would break the workflow chain,
                # we might need to skip the rest of the processing
                if script_basename in ["detect_smells_local.py"]:
                    log.error(f"Critical script {script_basename} failed. Skipping remaining steps for repo {repo_name}.")
                    repo_failed = True
                    break
                
        if repo_failed:
            failed_repos.append(repo_name)
            log.error(f"===== Repository processing incomplete for: {repo_name} due to critical errors =====")
        else:
            if repo_warnings:
                log.warning(f"===== Processed Repository: {repo_name} with warnings: =====")
                for warning in repo_warnings:
                    log.warning(f"- {warning}")
                # Still add to failed repos for reporting, but processing continued
                failed_repos.append(repo_name)
            else:
                log.info(f"===== Successfully processed Repository: {repo_name} =====")

    if failed_repos:
        log.error("--- Workflow halted due to failures in processing the following repositories: ---")
        for repo in failed_repos:
            log.error(f"- {repo}")
        # Decide whether to proceed to aggregation or stop
        log.warning("Proceeding to aggregation with potentially incomplete data.")
        # sys.exit(1) # Option to exit now

    # --- Step 7: Aggregate All Results ---
    if not run_script("aggregate_metrics.py"):
        log.error("Metric aggregation failed. Final CSV might be missing or incomplete.")
        # Don't cleanup if aggregation fails
        sys.exit(1)
    else:
         log.info("Metric aggregation completed successfully.")

    # --- Step 8: Optional Cleanup ---
    if not args.skip_cleanup:
        if not failed_repos: # Only cleanup if all repos processed successfully
            perform_cleanup()
        else:
            log.warning("Skipping cleanup due to failures during repository processing.")
    else:
        log.info("Cleanup skipped as requested by --skip-cleanup.")

    log.info("--- Workflow Finished --- ")
    if failed_repos:
         sys.exit(1) # Exit with error code if any repo failed 