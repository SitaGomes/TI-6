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
    ORIGINAL_CODE_DIR, REFACTORED_CODE_DIR, METRICS_DIR,
    ensure_dir, save_code, read_file_content, 
    get_deepseek_client, call_deepseek_api, extract_code_from_output,
    parse_line_range, extract_code_block, replace_code_block
)
from prompts import (
    REFACTOR_ZERO_SHOT_PROMPT_TEMPLATE,
    REFACTOR_ONE_SHOT_PROMPT_TEMPLATE,
    REFACTOR_COT_PROMPT_TEMPLATE
)
import logging

# --- Configuration ---
STRATEGIES = ["zero_shot", "one_shot", "cot"]
PROMPT_TEMPLATES = {
    "zero_shot": REFACTOR_ZERO_SHOT_PROMPT_TEMPLATE,
    "one_shot": REFACTOR_ONE_SHOT_PROMPT_TEMPLATE,
    "cot": REFACTOR_COT_PROMPT_TEMPLATE
}
API_CALL_DELAY = 1.0 # Delay between API calls
MAX_SMELLS_PER_FILE = None # Limit refactoring attempts per file (for testing/cost)
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

def refactor_smell(client, strategy: str, repo_path: str, 
                   relative_file_path: str, smell_info: dict, 
                   original_file_content: str):
    """Attempts to refactor a single smell using the specified strategy."""
    
    log.info(f"  Refactoring ({strategy}): {relative_file_path} - Smell: {smell_info.get('description', 'N/A')[:50]}...")
    
    # Extract line numbers - Use the logic from 03b
    start_line, end_line = None, None
    lines_field = str(smell_info.get('lines', ''))
    description = smell_info.get('description', '')
    line_pattern = re.compile(r'[\(\[\{]?L(?:ine|ines?)?\s*(\d+)(?:[-\s]*(\d+))?[\)\]\}]?', re.IGNORECASE)
    
    if description:
        match = line_pattern.search(description)
        if match:
            try:
                start_line = int(match.group(1))
                end_line = int(match.group(2)) if match.group(2) else start_line
            except ValueError:
                pass # Will try lines_field next

    if start_line is None and lines_field:
        cleaned_lines = re.sub(r'^[ \t#*.-]*', '', lines_field).strip()
        start_line, end_line = parse_line_range(cleaned_lines)
        
    if start_line is None or end_line is None:
        log.warning(f"    Could not determine line numbers for smell: {smell_info}. Skipping refactor.")
        return False, "error_lines"

    log.debug(f"    Target lines: {start_line}-{end_line}")
    
    # Extract the code block to send to the AI
    code_block = extract_code_block(original_file_content, start_line, end_line)
    if code_block is None:
        log.warning(f"    Could not extract original code block for lines {start_line}-{end_line}. Skipping.")
        return False, "error_extract_block"
        
    # Format the prompt
    prompt_template = PROMPT_TEMPLATES[strategy]
    prompt = prompt_template.format(
        file_path=relative_file_path,
        line_number=start_line, # Provide starting line for context
        smell_description=description,
        code_block=code_block
    )
    
    # Call AI
    ai_response = call_deepseek_api(prompt, client)
    time.sleep(API_CALL_DELAY)
    if ai_response is None:
        log.error(f"    AI API call failed for {strategy} refactoring.")
        return False, "error_api"
        
    # Extract refactored code
    refactored_code = extract_code_from_output(ai_response)
    if refactored_code is None:
        log.warning(f"    Could not extract refactored code from AI response ({strategy}).")
        return False, "error_extract_refactor"
        
    # Replace in the strategy-specific file
    strategy_file_path = os.path.join(repo_path, relative_file_path)
    try:
        current_strategy_content = read_file_content(strategy_file_path)
        if current_strategy_content is None:
             log.error(f"    Could not read current strategy file content: {strategy_file_path}")
             return False, "error_read_strategy_file"
             
        new_content = replace_code_block(current_strategy_content, start_line, end_line, refactored_code)
        
        if new_content is None:
            log.error(f"    Failed to replace code block in strategy file content ({strategy}).")
            return False, "error_replace"
            
        save_code(new_content, strategy_file_path)
        log.info(f"    Successfully refactored and saved: {strategy_file_path} (Lines {start_line}-{end_line}) -> {strategy}")
        return True, "success"
        
    except Exception as e:
        log.error(f"    Error processing/saving refactored file {strategy_file_path}: {e}")
        return False, "error_save"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    # log.setLevel(logging.DEBUG) # Uncomment for detailed logs, including API prompts
    
    # Find the repo name (assuming one for now)
    repo_name = None
    if os.path.exists(ORIGINAL_CODE_DIR):
        for item in os.listdir(ORIGINAL_CODE_DIR):
            if os.path.isdir(os.path.join(ORIGINAL_CODE_DIR, item)):
                repo_name = item
                break
    if not repo_name:
        log.error(f"No repository found in '{ORIGINAL_CODE_DIR}'. Run 01_fetch_repos.py first.")
        sys.exit(1)
        
    log.info(f"--- Starting Refactoring Process for Repository: {repo_name} ---")

    # Load AI smells
    ai_smells_by_file = load_ai_smells(repo_name)
    if ai_smells_by_file is None:
        log.error("Could not load AI smells. Aborting refactoring.")
        sys.exit(1)
    if not ai_smells_by_file:
        log.info("No AI-detected smells found to refactor. Skipping refactoring step.")
        sys.exit(0)
        
    try:
        client = get_deepseek_client()
    except ValueError as e:
        log.error(f"Error initializing AI client: {e}")
        sys.exit(1)

    # Process each strategy
    overall_summary = {}
    files_processed_count = 0

    for strategy in STRATEGIES:
        log.info(f"\n=== Processing Strategy: {strategy} ===")
        strategy_repo_path = copy_repo_for_strategy(repo_name, strategy)
        if strategy_repo_path is None:
            log.error(f"Failed to set up directory for strategy {strategy}. Skipping.")
            continue
            
        strategy_summary = {
            "total_smells_attempted": 0,
            "successful_refactors": 0,
            "error_lines": 0,
            "error_extract_block": 0,
            "error_api": 0,
            "error_extract_refactor": 0,
            "error_read_strategy_file": 0,
            "error_replace": 0,
            "error_save": 0
        }
        files_with_smells_count = 0

        # Iterate through files with detected smells
        for relative_file_path, smells in ai_smells_by_file.items():
            if MAX_FILES_TO_REFACTOR is not None and files_with_smells_count >= MAX_FILES_TO_REFACTOR:
                log.info(f"Reached MAX_FILES_TO_REFACTOR limit ({MAX_FILES_TO_REFACTOR}). Stopping strategy {strategy}.")
                break
                
            original_file_path = os.path.join(ORIGINAL_CODE_DIR, repo_name, relative_file_path)
            log.info(f"Processing file: {relative_file_path}")
            
            original_content = read_file_content(original_file_path)
            if original_content is None:
                log.warning(f"  Cannot read original file {original_file_path}. Skipping refactors for this file.")
                continue
                
            smells_attempted_in_file = 0
            for smell_info in smells:
                if MAX_SMELLS_PER_FILE is not None and smells_attempted_in_file >= MAX_SMELLS_PER_FILE:
                    log.info(f"  Reached MAX_SMELLS_PER_FILE limit ({MAX_SMELLS_PER_FILE}) for {relative_file_path}. Moving to next file.")
                    break
                
                strategy_summary["total_smells_attempted"] += 1
                success, status = refactor_smell(client, strategy, strategy_repo_path, 
                                                 relative_file_path, smell_info, 
                                                 original_content)
                
                if success:
                    strategy_summary["successful_refactors"] += 1
                    # Read the *updated* content for the next smell in the same file
                    # This makes refactorings sequential within a file for a strategy
                    original_content = read_file_content(os.path.join(strategy_repo_path, relative_file_path))
                    if original_content is None:
                         log.error(f"  CRITICAL: Failed to re-read file {relative_file_path} after successful refactor. Stopping file processing.")
                         # Mark remaining smells in file as failed? Or just break?
                         break # Stop processing this file for this strategy
                else:
                    strategy_summary[status] += 1
                    # If a refactor fails, we might want to stop processing subsequent smells
                    # in the same file for this strategy to avoid cascading errors.
                    # Alternatively, continue with the original content (more complex to manage).
                    # For simplicity, let's stop processing this file on failure.
                    log.warning(f"  Refactoring failed for a smell in {relative_file_path}. Skipping remaining smells in this file for strategy {strategy}.")
                    break 
                    
                smells_attempted_in_file += 1
                
            files_with_smells_count += 1
            
        overall_summary[strategy] = strategy_summary
        log.info(f"=== Finished Strategy: {strategy} Summary ===")
        log.info(json.dumps(strategy_summary, indent=2))

    log.info("\n--- Overall Refactoring Process Summary ---")
    log.info(json.dumps(overall_summary, indent=2))
    # Optionally save overall_summary to a file in metrics/
    # save_json(overall_summary, os.path.join(METRICS_DIR, repo_name, "refactoring_summary.json"))
    
    log.info(f"--- Refactoring Process Completed for Repository: {repo_name} ---")
