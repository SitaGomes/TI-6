"""
Step 3: Identify Code Smells with DeepSeek/OpenRouter.
"""

import os
import sys
import json
import time
import logging
import argparse
from utils import (
    ORIGINAL_CODE_DIR, METRICS_DIR, STRATEGIES, ensure_dir, save_json,
    get_deepseek_client, call_deepseek_api, read_file_content,
    parse_smell_output
)
from prompts import SMELL_ZERO_SHOT_PROMPT_TEMPLATE

# --- Configuration ---
# Limit number of files processed per repo for testing/cost control
# Set to None to process all files
MAX_FILES_PER_REPO = None 
# Skip files larger than this size in bytes to avoid excessive API costs/time
# Set to None to process all file sizes
MAX_FILE_SIZE_BYTES = 100 * 1024 # 100 KB limit
# Delay between API calls in seconds to respect potential rate limits
API_CALL_DELAY = 1.0 

def analyze_file_with_ai(file_path: str, client, repo_name: str):
    """Reads a file, calls the AI for smell detection using zero-shot prompt, and parses the result."""
    print(f"  Analyzing file: {file_path}")
    
    # Check file size
    try:
        file_size = os.path.getsize(file_path)
        if MAX_FILE_SIZE_BYTES is not None and file_size > MAX_FILE_SIZE_BYTES:
            print(f"    Skipping large file: {file_path} ({file_size / 1024:.1f} KB > {MAX_FILE_SIZE_BYTES / 1024:.1f} KB)")
            return None # Indicate skipped file
    except OSError as e:
        print(f"    Error getting size for file {file_path}: {e}")
        return None # Indicate error
        
    code_content = read_file_content(file_path)
    if code_content is None:
        print(f"    Could not read file content: {file_path}")
        return None # Indicate error

    # Handle potentially empty files
    if not code_content.strip():
        print(f"    Skipping empty file: {file_path}")
        return [] # No smells in empty file
        
    # Relative path for the prompt context
    relative_file_path = os.path.relpath(file_path, os.path.join(ORIGINAL_CODE_DIR, repo_name))

    # Use only zero-shot prompt template
    prompt = SMELL_ZERO_SHOT_PROMPT_TEMPLATE.format(
        file_path=relative_file_path, 
        code_content=code_content
    )
    
    ai_response = call_deepseek_api(prompt, client)
    time.sleep(API_CALL_DELAY) # Add delay between calls

    if ai_response is None:
        print(f"    Failed to get AI response for: {file_path}")
        return None # Indicate failure

    detected_smells = parse_smell_output(ai_response)
    print(f"    Detected {len(detected_smells)} smells in {relative_file_path}")
    return detected_smells

def detect_ai_smells(repo_name: str):
    """Detects smells in a repository using the AI model with zero-shot prompt."""
    repo_path = os.path.join(ORIGINAL_CODE_DIR, repo_name)
    if not os.path.isdir(repo_path):
        print(f"Error: Repository directory not found: {repo_path}", file=sys.stderr)
        return False

    metrics_repo_dir = os.path.join(METRICS_DIR, repo_name)
    ensure_dir(metrics_repo_dir)
    
    # Use single output filename
    output_file = os.path.join(metrics_repo_dir, "smells_deepseek.json")

    print(f"\n--- Detecting AI Smells for Repository: {repo_name} ---")
    
    try:
        client = get_deepseek_client()
    except ValueError as e:
        print(f"Error initializing AI client: {e}", file=sys.stderr)
        return False

    all_smells_data = {
        "repository": repo_name,
        "files": {},
        "summary": {
            "total_files_processed": 0,
            "total_files_skipped_size": 0,
            "total_files_skipped_read_error": 0,
            "total_files_skipped_empty": 0,
            "total_files_failed_api": 0,
            "total_smells_detected": 0
        }
        # TODO: Add comparison fields later (false_positives, false_negatives)
    }
    files_processed_count = 0

    for root, _, files in os.walk(repo_path):
        # Optional: Skip specific directories like .git, venv, etc.
        if '.git' in root or 'venv' in root or '__pycache__' in root:
            continue
            
        for file in files:
            if file.endswith('.py'):
                if MAX_FILES_PER_REPO is not None and files_processed_count >= MAX_FILES_PER_REPO:
                    print(f"Reached MAX_FILES_PER_REPO limit ({MAX_FILES_PER_REPO}). Stopping scan.")
                    break # Stop processing files in this directory
                    
                file_path = os.path.join(root, file)
                relative_file_path = os.path.relpath(file_path, repo_path)
                
                smells = analyze_file_with_ai(file_path, client, repo_name)
                
                # Update summary based on outcome
                if smells is None:
                    # Distinguish between skipped due to size and other errors if needed later
                    # For now, lump API failures and read errors together
                    if MAX_FILE_SIZE_BYTES is not None and os.path.getsize(file_path) > MAX_FILE_SIZE_BYTES:
                         all_smells_data["summary"]["total_files_skipped_size"] += 1
                    # Add checks here if read_file_content or other steps returned specific error codes
                    else:
                         all_smells_data["summary"]["total_files_failed_api"] += 1 
                         # Note: This currently catches read errors, API errors, etc.
                else:
                    all_smells_data["summary"]["total_files_processed"] += 1
                    if not smells: # Empty list means processed but no smells found or empty file
                        if not read_file_content(file_path).strip(): # Double check if it was empty
                           all_smells_data["summary"]["total_files_skipped_empty"] += 1
                        # Else: file was processed, no smells found by AI - reflected in total_smells_detected

                    if smells: # Only add files with detected smells to the 'files' dict
                        all_smells_data["files"][relative_file_path] = smells
                        all_smells_data["summary"]["total_smells_detected"] += len(smells)
                
                files_processed_count += 1 # Increment total files encountered

        if MAX_FILES_PER_REPO is not None and files_processed_count >= MAX_FILES_PER_REPO:
            break # Stop walking directories

    print(f"\nSaving AI smell detection results to {output_file}")
    # TODO: Implement comparison logic with Pylint/Radon results here
    # Load results from smells_lib_pylint.json / smells_lib_radon_cc.json
    # Compare findings per file/line
    # Calculate num_false_positives, num_false_negatives
    # Add these to the all_smells_data['summary']
    print("Warning: Comparison with local library results is not yet implemented.")

    save_json(all_smells_data, output_file)
    print(f"--- Finished AI Smell Detection: {repo_name} ---")
    print(f"Summary: {all_smells_data['summary']}")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run AI smell detection on a specific repository.")
    parser.add_argument("repo_name", help="Name of the repository directory within original_code/")
    args = parser.parse_args()

    repo_full_path = os.path.join(ORIGINAL_CODE_DIR, args.repo_name)
    if not os.path.isdir(repo_full_path):
        print(f"Error: Repository directory not found: {repo_full_path}", file=sys.stderr)
        sys.exit(1)

    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        
    print(f"\n--- Running AI Smell Detection for: {args.repo_name} ---")
    if detect_ai_smells(args.repo_name):
        print(f"--- Successfully completed AI smell detection for: {args.repo_name} ---")
    else:
        print(f"--- AI smell detection failed for: {args.repo_name} ---", file=sys.stderr)
        sys.exit(1)
