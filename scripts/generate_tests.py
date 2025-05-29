"""
Step 4: Generate Tests if Missing.

Checks for existing test files. If none are found, attempts to generate
pytest tests for Python source files using the AI model concurrently.
"""

import os
import sys
import time
from utils import (
    ORIGINAL_CODE_DIR, ensure_dir, save_code,
    get_deepseek_client, call_deepseek_api, read_file_content,
    extract_code_from_output, concurrent_api_calls, DEFAULT_MAX_CONCURRENT_API_CALLS
)
from prompts import TEST_GENERATION_PROMPT_TEMPLATE
import logging
import argparse

# --- Configuration ---
# Limit number of files processed per repo for testing/cost control
MAX_FILES_FOR_TEST_GENERATION = None # Set to None to process all eligible files
# Skip files larger than this size in bytes 
MAX_FILE_SIZE_BYTES = 100 * 1024 # 100 KB limit (same as smell detection)
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

def prepare_file_for_test_generation(file_info):
    """Prepare a file for test generation. Returns (prompt, file_data) or None if should skip."""
    file_path, repo_path, repo_name = file_info
    relative_file_path = os.path.relpath(file_path, repo_path)
    
    # Check file size
    try:
        file_size = os.path.getsize(file_path)
        if MAX_FILE_SIZE_BYTES is not None and file_size > MAX_FILE_SIZE_BYTES:
            log.warning(f"Skipping large file: {relative_file_path} ({file_size / 1024:.1f} KB)")
            return None
    except OSError as e:
        log.error(f"Error getting size for file {relative_file_path}: {e}")
        return None
        
    code_content = read_file_content(file_path)
    if code_content is None:
        log.error(f"Could not read file content: {relative_file_path}")
        return None

    if not code_content.strip():
        log.info(f"Skipping empty file: {relative_file_path}")
        return None

    prompt = TEST_GENERATION_PROMPT_TEMPLATE.format(
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

def generate_test_with_ai(prompt, file_data):
    """Generate test for a single file using AI. Used for concurrent processing."""
    try:
        client = get_deepseek_client()
        ai_response = call_deepseek_api(prompt, client)
        
        if ai_response is None:
            return {"status": "error_api", "file_data": file_data}

        extracted_test_code = extract_code_from_output(ai_response)

        if extracted_test_code:
            return {
                "status": "generated", 
                "file_data": file_data, 
                "test_code": extracted_test_code
            }
        else:
            return {"status": "error_extract", "file_data": file_data}
            
    except Exception as e:
        log.error(f"Error generating test for {file_data['relative_path']}: {e}")
        return {"status": "error", "file_data": file_data, "error": str(e)}

def generate_missing_tests(repo_name: str, max_concurrent_calls: int = None):
    """Generates tests for Python files in a repo if no tests exist."""
    if max_concurrent_calls is None:
        max_concurrent_calls = DEFAULT_MAX_CONCURRENT_API_CALLS
        
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
    
    test_output_dir = os.path.join(repo_path, TEST_DIR_NAME)
    ensure_dir(test_output_dir)
    
    # Collect all Python files that need test generation
    files_to_process = []
    files_processed_count = 0

    for root, _, files in os.walk(repo_path):
        # Skip common non-code and test directories
        if any(d in root for d in ['.git', 'venv', '__pycache__', TEST_DIR_NAME]):
            continue
            
        for file in files:
            # Only process Python files that are NOT tests themselves
            if file.endswith('.py') and not file.startswith('test_') and not file.endswith('_test.py'):
                
                if MAX_FILES_FOR_TEST_GENERATION is not None and files_processed_count >= MAX_FILES_FOR_TEST_GENERATION:
                    log.info(f"Reached MAX_FILES_FOR_TEST_GENERATION limit ({MAX_FILES_FOR_TEST_GENERATION}). Stopping collection.")
                    break
                    
                file_path = os.path.join(root, file)
                files_to_process.append((file_path, repo_path, repo_name))
                files_processed_count += 1

        if MAX_FILES_FOR_TEST_GENERATION is not None and files_processed_count >= MAX_FILES_FOR_TEST_GENERATION:
            break

    if not files_to_process:
        log.info(f"No Python files found for test generation in {repo_name}")
        return True

    log.info(f"Found {len(files_to_process)} Python files for test generation")

    # Prepare prompts for concurrent processing
    prompts_and_data = []
    for file_info in files_to_process:
        prepared = prepare_file_for_test_generation(file_info)
        if prepared:
            prompts_and_data.append(prepared)

    if not prompts_and_data:
        log.info(f"No files suitable for test generation after filtering")
        return True

    log.info(f"Generating tests for {len(prompts_and_data)} files using {max_concurrent_calls} concurrent API calls...")

    # Generate tests concurrently
    results = concurrent_api_calls(
        prompts_and_data,
        generate_test_with_ai,
        max_workers=max_concurrent_calls
    )

    # Process results and save test files
    summary = {
        "files_scanned": len(files_to_process),
        "files_processed": len(prompts_and_data),
        "tests_generated": 0,
        "skipped_size": 0,
        "skipped_empty": 0,
        "errors_read": 0,
        "errors_api": 0,
        "errors_extract": 0,
        "errors_other": 0
    }

    for (prompt, file_data), result, error in results:
        if error:
            summary["errors_other"] += 1
            continue
            
        if not result:
            summary["errors_other"] += 1
            continue
            
        status = result.get("status", "unknown")
        
        if status == "generated":
            summary["tests_generated"] += 1
            # Save the generated test
            file_path = file_data["file_path"]
            original_filename_no_ext = os.path.splitext(os.path.basename(file_path))[0]
            test_filename = f"test_{original_filename_no_ext}.py"
            test_save_path = os.path.join(test_output_dir, test_filename)
            
            log.info(f"Saving generated test for {file_data['relative_path']} to: {test_save_path}")
            save_code(result["test_code"], test_save_path)
            
        elif status == "error_api":
            summary["errors_api"] += 1
        elif status == "error_extract":
            summary["errors_extract"] += 1
        else:
            summary["errors_other"] += 1

    log.info(f"\n--- Test Generation Summary for {repo_name} ---")
    log.info(f"Files scanned for potential test generation: {summary['files_scanned']}")
    log.info(f"Files processed (after filtering): {summary['files_processed']}")
    log.info(f"Test files successfully generated: {summary['tests_generated']}")
    log.info(f"Errors - API: {summary['errors_api']}, Extract: {summary['errors_extract']}, Other: {summary['errors_other']}")
    
    # Note: We are NOT running the generated tests here. That requires pytest setup.
    log.warning("Generated tests have been saved but NOT executed/validated.")
    
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate tests for a specific repository if none exist.")
    parser.add_argument("repo_name", help="Name of the repository directory within original_code/")
    parser.add_argument("--max-concurrent", type=int, default=None, 
                        help="Maximum number of concurrent API calls")
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    repo_full_path = os.path.join(ORIGINAL_CODE_DIR, args.repo_name)
    if not os.path.isdir(repo_full_path):
        log.error(f"Error: Repository directory not found: {repo_full_path}")
        sys.exit(1)
        
    if not generate_missing_tests(args.repo_name, args.max_concurrent):
        log.error(f"Test generation process failed for repository: {args.repo_name}")
        sys.exit(1)
    else:
        log.info(f"Test generation process completed for repository: {args.repo_name}")
