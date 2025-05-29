"""
Step 6: Post-Refactor Analysis.

Runs static analysis tools (Pylint, Radon CC/MI, Pyright, Bandit) on each
refactored code directory corresponding to a specific strategy concurrently.
"""

import os
import sys
import subprocess
import json
from utils import (
    REFACTORED_CODE_DIR, METRICS_DIR, ensure_dir, save_json,
    ORIGINAL_CODE_DIR, STRATEGIES, run_tests_with_pytest,
    process_items_concurrently, DEFAULT_MAX_CONCURRENT_ANALYSIS
)
import logging
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

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

def run_single_analysis_tool(tool_info):
    """Run a single analysis tool. Used for concurrent processing."""
    tool_name, command, output_file, working_dir, use_output_flag = tool_info
    
    try:
        success = run_analysis_tool(command, output_file, working_dir, use_output_flag)
        return {
            "tool": tool_name,
            "success": success,
            "output_file": output_file
        }
    except Exception as e:
        log.error(f"Error running {tool_name}: {e}")
        return {
            "tool": tool_name,
            "success": False,
            "output_file": output_file,
            "error": str(e)
        }

def analyze_refactored_code(repo_name: str, strategy: str, max_concurrent_tools: int = None):
    """Runs all analysis tools on a specific refactored version of the code concurrently."""
    if max_concurrent_tools is None:
        max_concurrent_tools = DEFAULT_MAX_CONCURRENT_ANALYSIS
        
    strategy_repo_path = os.path.join(REFACTORED_CODE_DIR, strategy, repo_name)
    if not os.path.isdir(strategy_repo_path):
        log.warning(f"Refactored directory not found: {strategy_repo_path}. Skipping analysis for this strategy.")
        return True  # Return True to indicate "not an error", just missing

    # Output directory for this specific strategy's metrics
    metrics_output_dir = os.path.join(METRICS_DIR, repo_name, strategy)
    ensure_dir(metrics_output_dir)

    log.info(f"--- Analyzing Refactored Code ({strategy}) for: {repo_name} ---")
    log.info(f"Source: {strategy_repo_path}")
    log.info(f"Output Metrics Dir: {metrics_output_dir}")

    # Prepare all analysis tools to run concurrently
    analysis_tools = []

    # 1. Pylint
    pylint_output_file = os.path.join(metrics_output_dir, "pylint.json")
    pylint_command = [
        sys.executable, "-m", "pylint", 
        strategy_repo_path, 
        "--output-format=json", 
        "--recursive=y", 
        "--disable=C0114,C0115,C0116,R0903", # Same disables as before
        "--exit-zero"
    ]
    analysis_tools.append(("Pylint", pylint_command, pylint_output_file, '.', False))

    # 2. Radon CC
    radon_cc_output_file = os.path.join(metrics_output_dir, "radon_cc.json")
    radon_cc_command = [
        sys.executable, "-m", "radon", "cc", 
        strategy_repo_path, 
        "-s", "-j"
    ]
    analysis_tools.append(("Radon CC", radon_cc_command, radon_cc_output_file, '.', False))

    # 3. Radon MI
    radon_mi_output_file = os.path.join(metrics_output_dir, "radon_mi.json")
    radon_mi_command = [
        sys.executable, "-m", "radon", "mi", 
        strategy_repo_path, 
        "-s", "-j" # Use -j for JSON output
    ]
    analysis_tools.append(("Radon MI", radon_mi_command, radon_mi_output_file, '.', False))

    # 4. Pyright
    pyright_output_file = os.path.join(metrics_output_dir, "pyright.json")
    # Note: Pyright needs to be installed (e.g., npm install -g pyright or pip install pyright)
    # Running via python -m pyright might not work depending on installation method
    # Using direct command assuming it's in PATH
    pyright_command = [
        "pyright", 
        strategy_repo_path, 
        "--outputjson" # Request JSON output
    ]
    analysis_tools.append(("Pyright", pyright_command, pyright_output_file, '.', False))

    # 5. Bandit
    bandit_output_file = os.path.join(metrics_output_dir, "bandit.json")
    bandit_command = [
        sys.executable, "-m", "bandit", 
        "-r", # Recursive
        strategy_repo_path, 
        "-f", "json", # Format JSON
        "-o", bandit_output_file # Output file flag
        # Add severity filters if needed, e.g., -ll for medium+, -iii for high
    ]
    analysis_tools.append(("Bandit", bandit_command, bandit_output_file, '.', True))

    log.info(f"Running {len(analysis_tools)} analysis tools concurrently with {max_concurrent_tools} workers...")

    # Run analysis tools concurrently
    results = process_items_concurrently(
        analysis_tools,
        run_single_analysis_tool,
        max_workers=max_concurrent_tools,
        executor_type="thread",  # Most tools are I/O bound
        progress_callback=lambda completed, total: log.info(f"Analysis progress: {completed}/{total} tools completed"),
        error_callback=lambda tool_info, error: log.error(f"Failed to run {tool_info[0]}: {error}")
    )

    # Process results
    analysis_success = True
    successful_tools = []
    failed_tools = []

    for tool_info, result, error in results:
        tool_name = tool_info[0]
        
        if error:
            failed_tools.append(tool_name)
            analysis_success = False
            continue
            
        if result and result.get("success", False):
            successful_tools.append(tool_name)
            log.info(f"{tool_name} completed successfully")
        else:
            failed_tools.append(tool_name)
            analysis_success = False
            log.error(f"{tool_name} failed")

    # 6. Run Tests (separately, as it's different from static analysis)
    tests_output_file = os.path.join(metrics_output_dir, "tests.json")
    log.info("Running Tests...")
    test_results = run_tests_with_pytest(strategy_repo_path)
    if test_results is not None:
        save_json(test_results, tests_output_file)
        if test_results.get("tests_found", False):
            passed = test_results.get("passed", 0)
            total = test_results.get("total", 0)
            log.info(f"Tests completed: {passed}/{total} passed")
            successful_tools.append("Tests")
        else:
            log.info("No tests found in refactored code")
            successful_tools.append("Tests (none found)")
    else:
        log.error(f"Test execution failed for {strategy}/{repo_name}.")
        failed_tools.append("Tests")
        analysis_success = False

    # Summary
    log.info(f"--- Analysis Summary ({strategy}) for: {repo_name} ---")
    log.info(f"Successful tools: {', '.join(successful_tools)}")
    if failed_tools:
        log.warning(f"Failed tools: {', '.join(failed_tools)}")

    log.info(f"--- Finished Analysis ({strategy}) for: {repo_name} ---")
    return analysis_success

def main_analysis_logic(repo_name: str, max_concurrent_tools: int = None):
    """Runs the post-refactor analysis for a specific repository."""
    log.info(f"--- Starting Post-Refactor Analysis for Repository: {repo_name} ---")

    overall_success = True
    failed_strategies = []
    analyzed_strategies = []
    missing_strategies = []

    for strategy in STRATEGIES:
        strategy_path = os.path.join(REFACTORED_CODE_DIR, strategy, repo_name)
        if not os.path.exists(strategy_path):
            log.warning(f"Refactored directory for strategy '{strategy}' not found at {strategy_path}. Skipping analysis.")
            missing_strategies.append(strategy)
            continue
            
        analyzed_strategies.append(strategy)
        if not analyze_refactored_code(repo_name, strategy, max_concurrent_tools):
            overall_success = False
            failed_strategies.append(strategy)

    log.info("\n--- Post-Refactor Analysis Summary --- ")
    
    # If we didn't analyze any strategies, warn but don't fail
    if not analyzed_strategies:
        log.warning(f"No refactored code found for any strategy for repository {repo_name}.")
        log.warning(f"Missing strategies: {', '.join(missing_strategies)}")
        log.info(f"--- Post-Refactor Analysis Completed for Repository: {repo_name} (No strategies to analyze) ---")
        return True  # Return success to allow the workflow to continue
        
    if overall_success:
        log.info(f"All analyses completed successfully for repository: {repo_name}")
        log.info(f"Analyzed strategies: {', '.join(analyzed_strategies)}")
    else:
        log.warning(f"One or more analyses failed for repository: {repo_name}")
        log.warning(f"Failed strategies/analyses: {', '.join(failed_strategies)}")
        log.info(f"Successfully analyzed strategies: {', '.join([s for s in analyzed_strategies if s not in failed_strategies])}")
        
    if missing_strategies:
        log.info(f"Skipped strategies (no refactored code): {', '.join(missing_strategies)}")

    log.info(f"--- Post-Refactor Analysis Completed for Repository: {repo_name} ---")
    # Always return True to allow the workflow to continue, failures will be reported in the logs
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run post-refactor analysis for a specific repository.")
    parser.add_argument("repo_name", help="Name of the repository directory (should exist in refactored_code/ for each strategy)")
    parser.add_argument("--max-concurrent", type=int, default=None, 
                        help="Maximum number of concurrent analysis tools")
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Basic check if refactored directories likely exist
    found_any_refactored = False
    for strategy in STRATEGIES:
        if os.path.exists(os.path.join(REFACTORED_CODE_DIR, strategy, args.repo_name)):
            found_any_refactored = True
            break
    if not found_any_refactored:
         log.warning(f"Did not find refactored code for repo '{args.repo_name}' in any strategy directory. Did step 5 run?")
         # Continue anyway, the main logic will skip strategies if dirs are missing.
         
    if not main_analysis_logic(args.repo_name, args.max_concurrent):
        log.error(f"Post-refactor analysis failed for repository: {args.repo_name}")
        sys.exit(1)
    else:
        log.info(f"Post-refactor analysis completed for repository: {args.repo_name}")
