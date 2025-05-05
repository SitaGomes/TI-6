"""
Step 4: Generate Tests if Missing.

Checks for existing test files. If none are found, attempts to generate
pytest tests for Python source files using the AI model.
"""

import os
import sys
import time
from utils import (
    ORIGINAL_CODE_DIR, ensure_dir, save_code,
    get_deepseek_client, call_deepseek_api, read_file_content,
    extract_code_from_output
)
from prompts import TEST_GENERATION_PROMPT_TEMPLATE
import logging
import argparse

# --- Configuration ---
# Limit number of files processed per repo for testing/cost control
MAX_FILES_FOR_TEST_GENERATION = None # Set to None to process all eligible files
# Skip files larger than this size in bytes 
MAX_FILE_SIZE_BYTES = 100 * 1024 # 100 KB limit (same as smell detection)
# Delay between API calls in seconds
API_CALL_DELAY = 1.0 
# Standard test directory name
TEST_DIR_NAME = "tests"

log = logging.getLogger(__name__)

def check_existing_tests(repo_path: str):
    """Checks if likely test files or directories exist in the repository."""
    has_tests = False
    test_files_found = []
    for root, dirs, files in os.walk(repo_path):
        # Skip common non-code directories
        if any(d in root for d in ['.git', 'venv', '__pycache__']):
            continue
        
        # Check for standard test directory names
        if TEST_DIR_NAME in dirs:
            log.info(f"Found likely test directory: {os.path.join(root, TEST_DIR_NAME)}")
            has_tests = True
            # Could potentially break here if finding one test dir is enough
            
        # Check for standard test file naming conventions
        for file in files:
            if file.startswith("test_") and file.endswith(".py") or file.endswith("_test.py"):
                test_path = os.path.join(root, file)
                log.info(f"Found likely test file: {test_path}")
                test_files_found.append(test_path)
                has_tests = True
                
    if has_tests:
        log.info(f"Repository {os.path.basename(repo_path)} appears to have existing tests ({len(test_files_found)} files found). Skipping generation.")
    else:
        log.info(f"No common test directories or files found in {os.path.basename(repo_path)}. Proceeding with test generation.")
        
    return has_tests

def generate_test_for_file(file_path: str, client, repo_name: str, repo_path: str):
    """Generates a test file for a given source file using the AI."""
    relative_file_path = os.path.relpath(file_path, repo_path)
    log.info(f"  Attempting to generate test for: {relative_file_path}")

    # Check file size
    try:
        file_size = os.path.getsize(file_path)
        if MAX_FILE_SIZE_BYTES is not None and file_size > MAX_FILE_SIZE_BYTES:
            log.warning(f"    Skipping large file: {relative_file_path} ({file_size / 1024:.1f} KB)")
            return None, "skipped_size"
    except OSError as e:
        log.error(f"    Error getting size for file {relative_file_path}: {e}")
        return None, "error_size"
        
    code_content = read_file_content(file_path)
    if code_content is None:
        log.error(f"    Could not read file content: {relative_file_path}")
        return None, "error_read"

    if not code_content.strip():
        log.info(f"    Skipping empty file: {relative_file_path}")
        return None, "skipped_empty"

    prompt = TEST_GENERATION_PROMPT_TEMPLATE.format(
        file_path=relative_file_path, 
        code_content=code_content
    )
    
    ai_response = call_deepseek_api(prompt, client)
    time.sleep(API_CALL_DELAY)

    if ai_response is None:
        log.error(f"    Failed to get AI response for: {relative_file_path}")
        return None, "error_api"

    extracted_test_code = extract_code_from_output(ai_response)

    if extracted_test_code:
        log.info(f"    Successfully extracted test code (length {len(extracted_test_code)}). Preview: {extracted_test_code[:100]}...")
        return extracted_test_code, "generated"
    else:
        log.warning(f"    Failed to extract test code from AI response for: {relative_file_path}")
        return None, "error_extract"

def generate_missing_tests(repo_name: str):
    """Generates tests for Python files in a repo if no tests exist."""
    repo_path = os.path.join(ORIGINAL_CODE_DIR, repo_name)
    if not os.path.isdir(repo_path):
        log.error(f"Repository directory not found: {repo_path}")
        return False

    log.info(f"\n--- Checking for Tests in Repository: {repo_name} ---")
    
    if check_existing_tests(repo_path):
        # Tests exist, do nothing further in this step
        return True 
        
    # If we reach here, no tests were found, proceed with generation
    log.info(f"\n--- Generating Missing Tests for Repository: {repo_name} ---")
    
    try:
        client = get_deepseek_client()
    except ValueError as e:
        log.error(f"Error initializing AI client: {e}")
        return False

    test_output_dir = os.path.join(repo_path, TEST_DIR_NAME)
    ensure_dir(test_output_dir)
    
    summary = {
        "files_scanned": 0,
        "tests_generated": 0,
        "skipped_size": 0,
        "skipped_empty": 0,
        "errors_read": 0,
        "errors_api": 0,
        "errors_extract": 0,
        "errors_size": 0
    }
    files_processed_count = 0

    for root, _, files in os.walk(repo_path):
        # Skip common non-code and test directories
        if any(d in root for d in ['.git', 'venv', '__pycache__', TEST_DIR_NAME]):
            continue
            
        for file in files:
            # Only process Python files that are NOT tests themselves
            if file.endswith('.py') and not file.startswith('test_') and not file.endswith('_test.py'):
                
                if MAX_FILES_FOR_TEST_GENERATION is not None and files_processed_count >= MAX_FILES_FOR_TEST_GENERATION:
                    log.info(f"Reached MAX_FILES_FOR_TEST_GENERATION limit ({MAX_FILES_FOR_TEST_GENERATION}). Stopping generation.")
                    break # Stop processing files
                    
                file_path = os.path.join(root, file)
                summary["files_scanned"] += 1
                
                test_code, status = generate_test_for_file(file_path, client, repo_name, repo_path)
                
                if status == "generated":
                    summary["tests_generated"] += 1
                    # Construct test file path
                    original_filename_no_ext = os.path.splitext(file)[0]
                    test_filename = f"test_{original_filename_no_ext}.py"
                    test_save_path = os.path.join(test_output_dir, test_filename)
                    log.info(f"    Saving generated test to: {test_save_path}")
                    save_code(test_code, test_save_path)
                elif status.startswith("skipped_"):
                    summary[status] += 1
                elif status.startswith("error_"):
                    summary[status] += 1
                
                files_processed_count += 1

        if MAX_FILES_FOR_TEST_GENERATION is not None and files_processed_count >= MAX_FILES_FOR_TEST_GENERATION:
            break # Stop walking directories

    log.info(f"\n--- Test Generation Summary for {repo_name} ---")
    log.info(f"Files scanned for potential test generation: {summary['files_scanned']}")
    log.info(f"Test files successfully generated: {summary['tests_generated']}")
    log.info(f"Files skipped (Size > {MAX_FILE_SIZE_BYTES / 1024}KB): {summary['skipped_size']}")
    log.info(f"Files skipped (Empty): {summary['skipped_empty']}")
    log.info(f"Errors (Read): {summary['errors_read']}, Errors (API): {summary['errors_api']}, Errors (Extract): {summary['errors_extract']}, Errors (Size Check): {summary['errors_size']}")
    
    # Note: We are NOT running the generated tests here. That requires pytest setup.
    log.warning("Generated tests have been saved but NOT executed/validated.")
    
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate tests for a specific repository if none exist.")
    parser.add_argument("repo_name", help="Name of the repository directory within original_code/")
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    # log.setLevel(logging.DEBUG) # Uncomment for more detailed logs
    
    repo_full_path = os.path.join(ORIGINAL_CODE_DIR, args.repo_name)
    if not os.path.isdir(repo_full_path):
        log.error(f"Error: Repository directory not found: {repo_full_path}")
        sys.exit(1)
        
    if not generate_missing_tests(args.repo_name):
        log.error(f"Test generation process failed for repository: {args.repo_name}")
        sys.exit(1)
    else:
        log.info(f"Test generation process completed for repository: {args.repo_name}")
