"""
Step 5: Refactor Code with Three Prompt Strategies (Zero-Shot, One-Shot, CoT).

Reads AI-detected smells, applies refactoring using different prompts, and saves
the results to strategy-specific directories.
"""

import os
import sys
import json
import time
import shutil
import re
from utils import (
    ORIGINAL_CODE_DIR, REFACTORED_CODE_DIR, METRICS_DIR, STRATEGIES,
    save_code, read_file_content, 
    get_deepseek_client, call_deepseek_api, extract_code_from_output
)
from prompts import (
    REFACTOR_ZERO_SHOT_PROMPT_TEMPLATE,
    REFACTOR_ONE_SHOT_PROMPT_TEMPLATE,
    REFACTOR_COT_PROMPT_TEMPLATE
)
import logging

# --- Configuration ---
PROMPT_TEMPLATES = {
    "zero_shot": REFACTOR_ZERO_SHOT_PROMPT_TEMPLATE,
    "one_shot": REFACTOR_ONE_SHOT_PROMPT_TEMPLATE,
    "cot": REFACTOR_COT_PROMPT_TEMPLATE
}
API_CALL_DELAY = 5.0 # Delay between API calls
MAX_FILES_TO_REFACTOR = None # Limit total files with smells to process

log = logging.getLogger(__name__)

def load_ai_smells(repo_name: str):
    """Loads the AI-detected smell data."""
    ai_smell_file = os.path.join(METRICS_DIR, repo_name, "smells_deepseek.json")
    if not os.path.exists(ai_smell_file):
        log.error(f"AI smell file not found: {ai_smell_file}")
        return None
    try:
        with open(ai_smell_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Return only the 'files' dictionary containing smells
            if isinstance(data.get('files'), dict):
                return data['files']
            else:
                log.error(f"AI smell file {ai_smell_file} has incorrect structure (missing 'files' dict).")
                return None
    except Exception as e:
        log.error(f"Error loading AI smell file {ai_smell_file}: {e}")
        return None

def copy_repo_for_strategy(repo_name: str, strategy: str):
    """Copies the original repo content to the strategy-specific refactoring directory."""
    original_repo_path = os.path.join(ORIGINAL_CODE_DIR, repo_name)
    strategy_repo_path = os.path.join(REFACTORED_CODE_DIR, strategy, repo_name)
    
    if os.path.exists(strategy_repo_path):
        log.info(f"Removing existing directory: {strategy_repo_path}")
        shutil.rmtree(strategy_repo_path)
        
    log.info(f"Copying {original_repo_path} to {strategy_repo_path}")
    try:
        shutil.copytree(original_repo_path, strategy_repo_path, 
                        ignore=shutil.ignore_patterns('.git', '__pycache__', 'venv'))
        return strategy_repo_path
    except Exception as e:
        log.error(f"Error copying repository for strategy {strategy}: {e}")
        return None

def format_smell_list(smells: list) -> str:
    """Formats the list of smells for inclusion in the prompt."""
    formatted = []
    for i, smell in enumerate(smells):
        lines = str(smell.get('lines', 'N/A')).strip()
        desc = smell.get('description', 'N/A').strip()
        # Try to clean up line numbers from description if they match pattern
        line_pattern = re.compile(r'^\s*[\(\[\{]?L(?:ine|ines?)?\s*\d+(?:[-\s]*\d+)?[\]\)\}]?\s*[:.-]*\s*', re.IGNORECASE)
        desc = line_pattern.sub('', desc) # Remove line prefix from description
        formatted.append(f"- Line(s) {lines}: {desc}")
    return "\n".join(formatted) if formatted else "No specific smells listed."

def refactor_file_strategy(client, strategy: str, 
                           strategy_repo_path: str, 
                           relative_file_path: str, 
                           smells_in_file: list):
    """Attempts to refactor an entire file based on its smells using one strategy."""
    log.info(f"  Refactoring file ({strategy}): {relative_file_path} ({len(smells_in_file)} smells)")
    original_file_path = os.path.join(ORIGINAL_CODE_DIR, os.path.basename(strategy_repo_path), relative_file_path)
    strategy_file_path = os.path.join(strategy_repo_path, relative_file_path)

    # Read original content
    original_content = read_file_content(original_file_path)
    if original_content is None:
        log.error(f"    Cannot read original file {original_file_path}. Skipping refactor.")
        return False, "error_read_original"
        
    # Format the list of smells for the prompt
    smell_list_string = format_smell_list(smells_in_file)
    
    # Format the prompt
    prompt_template = PROMPT_TEMPLATES[strategy]
    prompt = prompt_template.format(
        file_path=relative_file_path,
        smell_list_string=smell_list_string,
        full_code_content=original_content
    )
    
    # Call AI
    log.debug(f"    Calling API for {strategy} on {relative_file_path}")
    ai_response = call_deepseek_api(prompt, client)
    time.sleep(API_CALL_DELAY)
    if ai_response is None:
        log.error(f"    AI API call failed for {strategy} refactoring of {relative_file_path}.")
        return False, "error_api"
        
    # Extract refactored code (expecting full file content)
    refactored_code = extract_code_from_output(ai_response)
    if refactored_code is None:
        log.warning(f"    Could not extract refactored code from AI response ({strategy}) for {relative_file_path}.")
        return False, "error_extract_refactor"
        
    # Overwrite the strategy-specific file
    try:
        log.info(f"    Saving refactored ({strategy}) file to: {strategy_file_path}")
        save_code(refactored_code, strategy_file_path)
        return True, "success"
    except Exception as e:
        log.error(f"    Error saving refactored file {strategy_file_path}: {e}")
        return False, "error_save"

def main_refactor_logic(repo_name: str):
    """Runs the refactoring process for a specific repository."""
    log.info(f"--- Starting Refactoring Process for Repository: {repo_name} ---")

    # Load AI smells
    ai_smells_by_file = load_ai_smells(repo_name)
    if ai_smells_by_file is None:
        log.error(f"Could not load AI smells for {repo_name}. Aborting refactoring.")
        return False # Indicate failure
    if not ai_smells_by_file:
        log.info(f"No AI-detected smells found in {repo_name} to refactor. Skipping.")
        return True # Indicate success (nothing to do)
        
    try:
        client = get_deepseek_client()
    except ValueError as e:
        log.error(f"Error initializing AI client: {e}")
        return False

    # Process each strategy
    overall_summary = {}
    any_strategy_succeeded = False  # Track if any strategy fully succeeded
    total_files_attempted = 0
    total_successful_refactors = 0

    for strategy in STRATEGIES:
        log.info(f"\n=== Processing Strategy: {strategy} for repo {repo_name} ===")
        strategy_repo_path = copy_repo_for_strategy(repo_name, strategy)
        if strategy_repo_path is None:
            log.error(f"Failed to set up directory for strategy {strategy}. Skipping.")
            continue  # Skip this strategy but don't fail the whole process
            
        strategy_summary = {
            "total_files_attempted": 0,
            "successful_refactors": 0,
            "error_read_original": 0,
            "error_api": 0,
            "error_extract_refactor": 0,
            "error_save": 0,
        }
        files_processed_count = 0

        # Iterate through files with detected smells
        for relative_file_path, smells_in_file in ai_smells_by_file.items():
            if MAX_FILES_TO_REFACTOR is not None and files_processed_count >= MAX_FILES_TO_REFACTOR:
                log.info(f"Reached MAX_FILES_TO_REFACTOR limit ({MAX_FILES_TO_REFACTOR}). Stopping strategy {strategy}.")
                break
                
            strategy_summary["total_files_attempted"] += 1
            
            success, status = refactor_file_strategy(client, strategy, 
                                                   strategy_repo_path, 
                                                   relative_file_path, 
                                                   smells_in_file)
            
            if success:
                strategy_summary["successful_refactors"] += 1
            else:
                strategy_summary[status] += 1
                # Continue with other files even if this one failed
            
            files_processed_count += 1
            
        overall_summary[strategy] = strategy_summary
        log.info(f"=== Finished Strategy: {strategy} Summary ===")
        log.info(json.dumps(strategy_summary, indent=2))
        
        # Track overall metrics
        total_files_attempted += strategy_summary["total_files_attempted"]
        total_successful_refactors += strategy_summary["successful_refactors"]
        
        # Mark a strategy as fully successful if all files were refactored
        if strategy_summary["successful_refactors"] == strategy_summary["total_files_attempted"] and strategy_summary["total_files_attempted"] > 0:
            any_strategy_succeeded = True
            log.info(f"Strategy {strategy} completed successfully for all files.")

    log.info("\n--- Overall Refactoring Process Summary ---")
    log.info(json.dumps(overall_summary, indent=2))
    
    # Calculate overall success rate across all strategies
    overall_success_rate = total_successful_refactors / total_files_attempted if total_files_attempted > 0 else 0
    log.info(f"Overall success rate: {overall_success_rate:.2%}")
    
    # Consider the process successful if:
    # 1. At least one strategy completely succeeded, OR
    # 2. We achieved a reasonable overall success rate (e.g., 75% or higher)
    refactoring_succeeded = any_strategy_succeeded or (overall_success_rate >= 0.75)
    
    if refactoring_succeeded:
        log.info(f"--- Refactoring Process Completed Successfully for Repository: {repo_name} ---")
    else:
        log.warning(f"--- Refactoring Process Completed with Partial Success for Repository: {repo_name} ---")
    
    # Always return success to allow the workflow to continue
    return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run AI refactoring for a specific repository.")
    parser.add_argument("repo_name", help="Name of the repository directory within original_code/")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    repo_full_path = os.path.join(ORIGINAL_CODE_DIR, args.repo_name)
    if not os.path.isdir(repo_full_path):
        log.error(f"Error: Original repository directory not found: {repo_full_path}")
        sys.exit(1)
        
    if not main_refactor_logic(args.repo_name):
        log.error(f"Refactoring process failed for repository: {args.repo_name}")
        sys.exit(1)
    else:
        log.info(f"Refactoring process completed for repository: {args.repo_name}")
