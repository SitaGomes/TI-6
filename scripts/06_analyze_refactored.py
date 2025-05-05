"""
Step 6: Post-Refactor Analysis.

Runs static analysis tools (Pylint, Radon CC/MI, Pyright, Bandit) on each
refactored code directory corresponding to a specific strategy.
"""

import os
import sys
import subprocess
import json
from utils import (
    REFACTORED_CODE_DIR, METRICS_DIR, ensure_dir, save_json,
    ORIGINAL_CODE_DIR
)
import logging

STRATEGIES = ["zero_shot", "one_shot", "cot"]

log = logging.getLogger(__name__)

def run_analysis_tool(command: list, output_file: str, working_dir: str, use_output_flag=False):
    """Runs a static analysis tool command and saves the output, handling stdout or -o flag."""
    log.info(f"Running command: {' '.join(command)} in {working_dir}")
    ensure_dir(os.path.dirname(output_file))
    
    stdout_content = None
    stderr_content = None
    return_code = -1
    
    try:
        if use_output_flag:
            # Tool handles output via -o flag, command already includes output_file
            result = subprocess.run(command, cwd=working_dir, capture_output=True, text=True, encoding='utf-8', check=False)
            stdout_content = result.stdout
            stderr_content = result.stderr
            return_code = result.returncode
            # Check if the command itself failed fundamentally
            # Check if tool ran at all - look for common errors in stderr
            if return_code != 0 and any(err in stderr_content for err in ["command not found", "No such file or directory", "ModuleNotFoundError"]):
                 log.error(f"Tool command failed to execute: {' '.join(command)} (Exit Code: {return_code}): {stderr_content}")
                 return False
                 
            # Check if the output file was created, regardless of exit code (Bandit exits non-zero on findings)
            output_exists = os.path.exists(output_file)
            if output_exists:
                if return_code == 0:
                    log.info(f"Successfully saved output via -o flag to {output_file} (Exit Code: 0)")
                else:
                    # Log non-zero exit but treat as success if file exists
                    log.warning(f"Command {' '.join(command)} exited with code {return_code}, but output file {output_file} was created. Treating as success.")
                return True # Success if file exists
            else:
                # File doesn't exist
                log.error(f"Output file {output_file} was not found after running command (Exit Code: {return_code}). Stderr: {stderr_content}")
                return False
        else:
            # Tool outputs JSON to stdout, redirect it
            with open(output_file, 'w', encoding='utf-8') as f_out:
                result = subprocess.run(command, cwd=working_dir, stdout=f_out, stderr=subprocess.PIPE, text=True, encoding='utf-8', check=False)
                stderr_content = result.stderr
                return_code = result.returncode
            
            # Check for fundamental errors
            if "command not found" in stderr_content.lower() or "No such file or directory" in stderr_content:
                 log.error(f"Error running {' '.join(command)}: {stderr_content}")
                 # Clean up potentially empty file
                 if os.path.exists(output_file): os.remove(output_file)
                 return False
            
            # Check if output file is valid JSON (read back) - Pylint/Radon often exit non-zero
            try:
                with open(output_file, 'r', encoding='utf-8') as f_in:
                    json.load(f_in)
                log.info(f"Successfully saved and validated JSON output to {output_file}")
                return True
            except json.JSONDecodeError:
                log.warning(f"Output from {' '.join(command)} was not valid JSON (Exit code: {return_code}). Check {output_file}. Stderr: {stderr_content}")
                # Keep the invalid file for debugging, but report as failure
                return False 
            except FileNotFoundError:
                 log.error(f"Output file {output_file} was not created. Stderr: {stderr_content}")
                 return False

    except FileNotFoundError:
        log.error(f"Command '{command[0]}' not found. Make sure it's installed and in PATH.")
        return False
    except Exception as e:
        log.error(f"An unexpected error occurred while running {' '.join(command)}: {e}")
        # Log stderr if available
        if stderr_content:
             log.error(f"Stderr: {stderr_content}")
        return False

def analyze_refactored_code(repo_name: str, strategy: str):
    """Runs all analysis tools on a specific refactored version of the code."""
    strategy_repo_path = os.path.join(REFACTORED_CODE_DIR, strategy, repo_name)
    if not os.path.isdir(strategy_repo_path):
        log.error(f"Refactored directory not found: {strategy_repo_path}")
        return False

    # Output directory for this specific strategy's metrics
    metrics_output_dir = os.path.join(METRICS_DIR, repo_name, strategy)
    ensure_dir(metrics_output_dir)

    log.info(f"--- Analyzing Refactored Code ({strategy}) for: {repo_name} ---")
    log.info(f"Source: {strategy_repo_path}")
    log.info(f"Output Metrics Dir: {metrics_output_dir}")

    analysis_success = True

    # 1. Run Pylint
    pylint_output_file = os.path.join(metrics_output_dir, "pylint.json")
    pylint_command = [
        sys.executable, "-m", "pylint", 
        strategy_repo_path, 
        "--output-format=json", 
        "--recursive=y", 
        "--disable=C0114,C0115,C0116,R0903", # Same disables as before
        "--exit-zero"
    ]
    log.info("Running Pylint...")
    if not run_analysis_tool(pylint_command, pylint_output_file, '.', use_output_flag=False):
        log.error(f"Pylint analysis failed for {strategy}/{repo_name}.")
        analysis_success = False

    # 2. Run Radon CC
    radon_cc_output_file = os.path.join(metrics_output_dir, "radon_cc.json")
    radon_cc_command = [
        sys.executable, "-m", "radon", "cc", 
        strategy_repo_path, 
        "-s", "-j"
    ]
    log.info("Running Radon CC...")
    if not run_analysis_tool(radon_cc_command, radon_cc_output_file, '.', use_output_flag=False):
        log.error(f"Radon CC analysis failed for {strategy}/{repo_name}.")
        analysis_success = False

    # 3. Run Radon MI
    radon_mi_output_file = os.path.join(metrics_output_dir, "radon_mi.json")
    radon_mi_command = [
        sys.executable, "-m", "radon", "mi", 
        strategy_repo_path, 
        "-s", "-j" # Use -j for JSON output
    ]
    log.info("Running Radon MI...")
    if not run_analysis_tool(radon_mi_command, radon_mi_output_file, '.', use_output_flag=False):
        log.error(f"Radon MI analysis failed for {strategy}/{repo_name}.")
        analysis_success = False

    # 4. Run Pyright
    pyright_output_file = os.path.join(metrics_output_dir, "pyright.json")
    # Note: Pyright needs to be installed (e.g., npm install -g pyright or pip install pyright)
    # Running via python -m pyright might not work depending on installation method
    # Using direct command assuming it's in PATH
    pyright_command = [
        "pyright", 
        strategy_repo_path, 
        "--outputjson" # Request JSON output
    ]
    log.info("Running Pyright...")
    if not run_analysis_tool(pyright_command, pyright_output_file, '.', use_output_flag=False):
        log.error(f"Pyright analysis failed for {strategy}/{repo_name}. Ensure pyright is installed and in PATH.")
        analysis_success = False

    # 5. Run Bandit
    bandit_output_file = os.path.join(metrics_output_dir, "bandit.json")
    bandit_command = [
        sys.executable, "-m", "bandit", 
        "-r", # Recursive
        strategy_repo_path, 
        "-f", "json", # Format JSON
        "-o", bandit_output_file # Output file flag
        # Add severity filters if needed, e.g., -ll for medium+, -iii for high
    ]
    log.info("Running Bandit...")
    # Bandit uses -o flag, so set use_output_flag=True
    if not run_analysis_tool(bandit_command, bandit_output_file, '.', use_output_flag=True):
        log.error(f"Bandit analysis failed for {strategy}/{repo_name}.")
        analysis_success = False

    log.info(f"--- Finished Analysis ({strategy}) for: {repo_name} ---")
    return analysis_success

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Find the repo name (assuming one based on previous steps)
    repo_name = None
    if os.path.exists(ORIGINAL_CODE_DIR):
        for item in os.listdir(ORIGINAL_CODE_DIR):
            if os.path.isdir(os.path.join(ORIGINAL_CODE_DIR, item)):
                repo_name = item
                break
    if not repo_name:
        log.error(f"No repository found in '{ORIGINAL_CODE_DIR}'. Run 01_fetch_repos.py first.")
        sys.exit(1)

    log.info(f"--- Starting Post-Refactor Analysis for Repository: {repo_name} ---")

    overall_success = True
    failed_strategies = []

    for strategy in STRATEGIES:
        strategy_path = os.path.join(REFACTORED_CODE_DIR, strategy, repo_name)
        if not os.path.exists(strategy_path):
            log.warning(f"Refactored directory for strategy '{strategy}' not found at {strategy_path}. Skipping analysis.")
            continue
            
        if not analyze_refactored_code(repo_name, strategy):
            overall_success = False
            failed_strategies.append(strategy)

    log.info("\n--- Post-Refactor Analysis Summary ---")
    if overall_success:
        log.info(f"All analyses completed successfully for repository: {repo_name}")
    else:
        log.error(f"One or more analyses failed for repository: {repo_name}")
        log.error(f"Failed strategies/analyses: {', '.join(failed_strategies)}")
        sys.exit(1)

    log.info(f"--- Post-Refactor Analysis Completed for Repository: {repo_name} ---")
