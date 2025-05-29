"""
Step 3: Identify Code Smells with DeepSeek/OpenRouter using concurrent processing.
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
    parse_smell_output, concurrent_api_calls, DEFAULT_MAX_CONCURRENT_API_CALLS
)
from prompts import SMELL_ZERO_SHOT_PROMPT_TEMPLATE

# --- Configuration ---
# Limit number of files processed per repo for testing/cost control
# Set to None to process all files
MAX_FILES_PER_REPO = None 
# Skip files larger than this size in bytes to avoid excessive API costs/time
# Set to None to process all file sizes
MAX_FILE_SIZE_BYTES = 100 * 1024 # 100 KB limit

log = logging.getLogger(__name__)

def prepare_file_for_analysis(file_info):
    """Prepare a file for AI analysis. Returns (prompt, file_data) or None if should skip."""
    file_path, repo_path, repo_name = file_info
    relative_file_path = os.path.relpath(file_path, repo_path)
    
    # Check file size
    try:
        file_size = os.path.getsize(file_path)
        if MAX_FILE_SIZE_BYTES is not None and file_size > MAX_FILE_SIZE_BYTES:
            log.warning(f"Skipping large file: {relative_file_path} ({file_size / 1024:.1f} KB > {MAX_FILE_SIZE_BYTES / 1024:.1f} KB)")
            return None
    except OSError as e:
        log.error(f"Error getting size for file {relative_file_path}: {e}")
        return None
        
    code_content = read_file_content(file_path)
    if code_content is None:
        log.error(f"Could not read file content: {relative_file_path}")
        return None

    # Handle potentially empty files
    if not code_content.strip():
        log.info(f"Skipping empty file: {relative_file_path}")
        return None
        
    # Use only zero-shot prompt template
    prompt = SMELL_ZERO_SHOT_PROMPT_TEMPLATE.format(
        file_path=relative_file_path, 
        code_content=code_content
    )
    
    file_data = {
        "file_path": file_path,
        "relative_path": relative_file_path,
        "repo_path": repo_path,
        "repo_name": repo_name
    }
    
    return (prompt, file_data)

def analyze_file_with_ai(prompt, file_data):
    """Analyze a single file with AI. Used for concurrent processing."""
    try:
        client = get_deepseek_client()
        ai_response = call_deepseek_api(prompt, client)
        
        if ai_response is None:
            return {
                "status": "error_api", 
                "file_data": file_data,
                "smells": None
            }

        detected_smells = parse_smell_output(ai_response)
        log.info(f"Detected {len(detected_smells)} smells in {file_data['relative_path']}")
        
        return {
            "status": "success", 
            "file_data": file_data,
            "smells": detected_smells
        }
        
    except Exception as e:
        log.error(f"Error analyzing file {file_data['relative_path']}: {e}")
        return {
            "status": "error", 
            "file_data": file_data,
            "smells": None,
            "error": str(e)
        }

def detect_ai_smells(repo_name: str, max_concurrent_calls: int = None):
    """Detects smells in a repository using the AI model with concurrent processing."""
    if max_concurrent_calls is None:
        max_concurrent_calls = DEFAULT_MAX_CONCURRENT_API_CALLS
        
    repo_path = os.path.join(ORIGINAL_CODE_DIR, repo_name)
    if not os.path.isdir(repo_path):
        log.error(f"Repository directory not found: {repo_path}")
        return False

    metrics_repo_dir = os.path.join(METRICS_DIR, repo_name)
    ensure_dir(metrics_repo_dir)
    
    # Use single output filename
    output_file = os.path.join(metrics_repo_dir, "smells_deepseek.json")

    log.info(f"\n--- Detecting AI Smells for Repository: {repo_name} ---")
    
    # Collect all Python files that need analysis
    files_to_process = []
    files_processed_count = 0

    for root, _, files in os.walk(repo_path):
        # Optional: Skip specific directories like .git, venv, etc.
        if '.git' in root or 'venv' in root or '__pycache__' in root:
            continue
            
        for file in files:
            if file.endswith('.py'):
                if MAX_FILES_PER_REPO is not None and files_processed_count >= MAX_FILES_PER_REPO:
                    log.info(f"Reached MAX_FILES_PER_REPO limit ({MAX_FILES_PER_REPO}). Stopping collection.")
                    break
                    
                file_path = os.path.join(root, file)
                files_to_process.append((file_path, repo_path, repo_name))
                files_processed_count += 1

        if MAX_FILES_PER_REPO is not None and files_processed_count >= MAX_FILES_PER_REPO:
            break

    if not files_to_process:
        log.info(f"No Python files found for analysis in {repo_name}")
        # Save empty results
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
        }
        save_json(all_smells_data, output_file)
        return True

    log.info(f"Found {len(files_to_process)} Python files for analysis")

    # Prepare prompts for concurrent processing
    prompts_and_data = []
    for file_info in files_to_process:
        prepared = prepare_file_for_analysis(file_info)
        if prepared:
            prompts_and_data.append(prepared)

    if not prompts_and_data:
        log.info(f"No files suitable for analysis after filtering")
        # Save empty results but count skipped files
        all_smells_data = {
            "repository": repo_name,
            "files": {},
            "summary": {
                "total_files_processed": 0,
                "total_files_skipped_size": len(files_to_process),
                "total_files_skipped_read_error": 0,
                "total_files_skipped_empty": 0,
                "total_files_failed_api": 0,
                "total_smells_detected": 0
            }
        }
        save_json(all_smells_data, output_file)
        return True

    log.info(f"Analyzing {len(prompts_and_data)} files using {max_concurrent_calls} concurrent API calls...")

    # Analyze files concurrently
    results = concurrent_api_calls(
        prompts_and_data,
        analyze_file_with_ai,
        max_workers=max_concurrent_calls
    )

    # Process results
    all_smells_data = {
        "repository": repo_name,
        "files": {},
        "summary": {
            "total_files_processed": 0,
            "total_files_skipped_size": len(files_to_process) - len(prompts_and_data),
            "total_files_skipped_read_error": 0,
            "total_files_skipped_empty": 0,
            "total_files_failed_api": 0,
            "total_smells_detected": 0
        }
    }

    for (prompt, file_data), result, error in results:
        if error:
            all_smells_data["summary"]["total_files_failed_api"] += 1
            continue
            
        if not result:
            all_smells_data["summary"]["total_files_failed_api"] += 1
            continue
            
        status = result.get("status", "unknown")
        
        if status == "success":
            all_smells_data["summary"]["total_files_processed"] += 1
            smells = result.get("smells", [])
            
            if smells:  # Only add files with detected smells to the 'files' dict
                relative_path = file_data["relative_path"]
                all_smells_data["files"][relative_path] = smells
                all_smells_data["summary"]["total_smells_detected"] += len(smells)
                
        elif status == "error_api":
            all_smells_data["summary"]["total_files_failed_api"] += 1
        else:
            all_smells_data["summary"]["total_files_failed_api"] += 1

    log.info(f"\nSaving AI smell detection results to {output_file}")
    # TODO: Implement comparison logic with Pylint/Radon results here
    # Load results from smells_lib_pylint.json / smells_lib_radon_cc.json
    # Compare findings per file/line
    # Calculate num_false_positives, num_false_negatives
    # Add these to the all_smells_data['summary']
    log.warning("Comparison with local library results is not yet implemented.")

    save_json(all_smells_data, output_file)
    log.info(f"--- Finished AI Smell Detection: {repo_name} ---")
    log.info(f"Summary: {all_smells_data['summary']}")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run AI smell detection on a specific repository.")
    parser.add_argument("repo_name", help="Name of the repository directory within original_code/")
    parser.add_argument("--max-concurrent", type=int, default=None, 
                        help="Maximum number of concurrent API calls")
    args = parser.parse_args()

    repo_full_path = os.path.join(ORIGINAL_CODE_DIR, args.repo_name)
    if not os.path.isdir(repo_full_path):
        log.error(f"Repository directory not found: {repo_full_path}")
        sys.exit(1)

    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        
    log.info(f"\n--- Running AI Smell Detection for: {args.repo_name} ---")
    if detect_ai_smells(args.repo_name, args.max_concurrent):
        log.info(f"--- Successfully completed AI smell detection for: {args.repo_name} ---")
    else:
        log.error(f"--- AI smell detection failed for: {args.repo_name} ---")
        sys.exit(1)
