"""
Utility functions for the refactoring workflow.
"""

import os
import json
from openai import OpenAI, RateLimitError, APIError
import time
import re
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from functools import wraps
import queue

# --- Constants ---
ORIGINAL_CODE_DIR = "original_code"
REFACTORED_CODE_DIR = "refactored_code"
METRICS_DIR = "metrics"
STRATEGIES = ["zero_shot", "one_shot", "cot"] # Added shared constant

# --- Concurrency Configuration ---
# These can be overridden by environment variables or command line args
DEFAULT_MAX_CONCURRENT_REPOS = 3  # For git cloning
DEFAULT_MAX_CONCURRENT_API_CALLS = 2  # For AI API calls
DEFAULT_MAX_CONCURRENT_ANALYSIS = 4  # For static analysis tools
DEFAULT_API_RATE_LIMIT_PER_MINUTE = 60  # Adjust based on your API limits

# --- Logging Setup ---
log = logging.getLogger(__name__) # Initialize logger for this module

# --- Rate Limiting for API Calls ---
class RateLimiter:
    """Thread-safe rate limiter for API calls."""
    
    def __init__(self, max_calls_per_minute=DEFAULT_API_RATE_LIMIT_PER_MINUTE):
        self.max_calls_per_minute = max_calls_per_minute
        self.calls = queue.Queue()
        self.lock = threading.Lock()
    
    def wait_if_needed(self):
        """Wait if we're hitting rate limits."""
        with self.lock:
            now = time.time()
            
            # Remove calls older than 1 minute
            temp_calls = []
            while not self.calls.empty():
                call_time = self.calls.get()
                if now - call_time < 60:  # Within last minute
                    temp_calls.append(call_time)
            
            # Put back recent calls
            for call_time in temp_calls:
                self.calls.put(call_time)
            
            # Check if we need to wait
            if self.calls.qsize() >= self.max_calls_per_minute:
                # Wait until the oldest call is more than 1 minute old
                oldest_call = min(temp_calls) if temp_calls else now
                wait_time = 60 - (now - oldest_call) + 1  # +1 for safety
                if wait_time > 0:
                    log.info(f"Rate limit reached. Waiting {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
            
            # Record this call
            self.calls.put(now)

# Global rate limiter instance
_rate_limiter = RateLimiter()

def set_rate_limit(calls_per_minute):
    """Set the global rate limit for API calls."""
    global _rate_limiter
    _rate_limiter = RateLimiter(calls_per_minute)

# --- Environment & Configuration ---

def get_deepseek_client():
    """Initializes and returns the OpenAI client configured for DeepSeek via OpenRouter."""
    # Expects the OpenRouter API key to be set in this environment variable
    api_key = "ollama"
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY environment variable not set (expected OpenRouter key).")
    
    # Using OpenAI library compatibility pointed at OpenRouter
    client = OpenAI(api_key=api_key, base_url="http://localhost:11434/v1") 
    return client

def get_github_token():
    """Retrieves the GitHub token from .env file or environment variables."""
    # First try to load from .env file
    env_file_path = os.path.join(os.path.dirname(__file__), '.env')
    
    if os.path.exists(env_file_path):
        try:
            with open(env_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('GITHUB_TOKEN='):
                        token = line.split('=', 1)[1].strip()
                        # Remove quotes if present
                        if token.startswith('"') and token.endswith('"'):
                            token = token[1:-1]
                        elif token.startswith("'") and token.endswith("'"):
                            token = token[1:-1]
                        if token:
                            return token
        except Exception as e:
            log.warning(f"Error reading .env file: {e}")
    
    # Fallback to environment variable
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN not found in .env file or environment variables.")
    return token

# --- API Interaction with Concurrency Support ---

# Configure based on DeepSeek model availability via OpenRouter
# Using the free model identifier potentially used by OpenRouter
DEEPSEEK_MODEL = "deepseek-r1:1.5b" 
MAX_RETRIES = 5
RETRY_DELAY_SECONDS = 5

def call_deepseek_api(prompt: str, client: OpenAI, use_rate_limiter=True):
    """Calls the DeepSeek Chat Completion API with retry logic and rate limiting."""
    if use_rate_limiter:
        _rate_limiter.wait_if_needed()
    
    retries = 0
    while retries < MAX_RETRIES:
        response = None # Ensure response is defined in the loop scope
        try:
            log.debug(f"Calling API (Attempt {retries + 1}/{MAX_RETRIES}) Model: {DEEPSEEK_MODEL}")
            response = client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                stream=False
            )
            log.debug(f"API Response received: {response}") # Log the raw response object

            # --- Add more robust checks before accessing attributes --- 
            if response and response.choices:
                if len(response.choices) > 0:
                    first_choice = response.choices[0]
                    if first_choice.message:
                        if first_choice.message.content is not None:
                            return first_choice.message.content
                        else:
                            log.error(f"API Error: Response choice message content is None. Choice: {first_choice}")
                            # Decide if retry is appropriate? Probably not if content is None.
                            break # Stop retrying
                    else:
                        log.error(f"API Error: Response choice message is None. Choice: {first_choice}")
                        break # Stop retrying
                else:
                    # This case might happen due to content filters
                    log.error(f"API Error: Response choices list is empty. Response: {response}")
                    # Check for finish reason, e.g., content filter
                    finish_reason = response.choices[0].finish_reason if response.choices else 'unknown'
                    log.error(f"Finish Reason (if available): {finish_reason}")                        
                    break # Stop retrying if choices empty
            else:
                log.error(f"API Error: Invalid response structure (no choices attribute or response is None). Response: {response}")
                break # Stop retrying
                
        except RateLimitError as e:
            log.warning(f"Rate limit reached. Retrying in {RETRY_DELAY_SECONDS} seconds... ({retries + 1}/{MAX_RETRIES})")
            retries += 1
            time.sleep(RETRY_DELAY_SECONDS)
        except APIError as e:
            log.warning(f"DeepSeek API error: {e}. Retrying in {RETRY_DELAY_SECONDS} seconds... ({retries + 1}/{MAX_RETRIES})")
            retries += 1
            time.sleep(RETRY_DELAY_SECONDS)
        except Exception as e:
            log.error(f"An unexpected error occurred during API call or response processing: {e}")
            log.error(f"Response object at time of error: {response}") # Log response if available
            # Stop retrying on unexpected errors during processing
            break 

    log.error(f"Failed to get valid response from API after {retries + 1} attempts.")
    return None # Indicate failure

# --- Concurrent Processing Utilities ---

def process_items_concurrently(items, process_func, max_workers=None, executor_type="thread", 
                             progress_callback=None, error_callback=None):
    """
    Process a list of items concurrently using ThreadPoolExecutor or ProcessPoolExecutor.
    
    Args:
        items: List of items to process
        process_func: Function to call for each item (should take one argument)
        max_workers: Maximum number of concurrent workers
        executor_type: "thread" or "process"
        progress_callback: Optional callback for progress updates (called with completed_count, total_count)
        error_callback: Optional callback for errors (called with item, exception)
    
    Returns:
        List of (item, result, error) tuples
    """
    if max_workers is None:
        max_workers = min(len(items), DEFAULT_MAX_CONCURRENT_REPOS if executor_type == "thread" else DEFAULT_MAX_CONCURRENT_ANALYSIS)
    
    executor_class = ThreadPoolExecutor if executor_type == "thread" else ProcessPoolExecutor
    results = []
    
    with executor_class(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_item = {executor.submit(process_func, item): item for item in items}
        
        completed_count = 0
        total_count = len(items)
        
        # Process completed tasks
        for future in as_completed(future_to_item):
            item = future_to_item[future]
            error = None
            result = None
            
            try:
                result = future.result()
            except Exception as e:
                error = e
                log.error(f"Error processing {item}: {e}")
                if error_callback:
                    error_callback(item, e)
            
            results.append((item, result, error))
            completed_count += 1
            
            if progress_callback:
                progress_callback(completed_count, total_count)
            
            log.info(f"Progress: {completed_count}/{total_count} completed")
    
    return results

def concurrent_api_calls(prompts_and_data, api_call_func, max_workers=None):
    """
    Make concurrent API calls with rate limiting.
    
    Args:
        prompts_and_data: List of (prompt, additional_data) tuples
        api_call_func: Function that takes (prompt, additional_data) and returns result
        max_workers: Maximum concurrent API calls
    
    Returns:
        List of (prompt_data, result, error) tuples
    """
    if max_workers is None:
        max_workers = DEFAULT_MAX_CONCURRENT_API_CALLS
    
    def safe_api_call(prompt_data):
        prompt, data = prompt_data
        try:
            return api_call_func(prompt, data)
        except Exception as e:
            log.error(f"API call failed: {e}")
            return None
    
    return process_items_concurrently(
        prompts_and_data, 
        safe_api_call, 
        max_workers=max_workers, 
        executor_type="thread"
    )

# --- File System Utilities ---

def ensure_dir(directory_path):
    """Ensures that a directory exists, creating it if necessary."""
    os.makedirs(directory_path, exist_ok=True)

def save_json(data, file_path):
    """Saves data to a JSON file."""
    ensure_dir(os.path.dirname(file_path))
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def read_file_content(file_path):
    """Reads the content of a text file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return None
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None

def save_code(code_content, file_path):
    """Saves code content to a file."""
    ensure_dir(os.path.dirname(file_path))
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(code_content)
    except Exception as e:
        print(f"Error writing file {file_path}: {e}")

# --- Placeholder Functions (to be implemented in main scripts) ---

def parse_smell_output(output: str):
    """Parses the AI's smell detection output.
    Assumes output is a list of lines like 'Line number(s): Description'.
    Returns a list of dictionaries, e.g., [{'lines': '10-15', 'description': 'Long Method'}].
    This is a basic parser and might need refinement based on actual API output.
    """
    smells = []
    if not output:
        return smells
    
    lines = output.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Simple parsing: look for a colon separating line numbers and description
        parts = line.split(':', 1)
        if len(parts) == 2:
            line_part = parts[0].strip()
            # Clean up potential prefixes like "Line number(s)", "Lines", etc.
            line_part = line_part.replace("Line number(s)", "").replace("Lines", "").replace("Line", "").strip()
            description = parts[1].strip()
            if line_part and description:
                smells.append({"lines": line_part, "description": description})
        else:
            # If parsing fails, maybe the whole line is a description? Or format is unexpected.
            # Log this for potential refinement.
            print(f"[Parser Warning] Could not parse line: {line}")
            # Optionally, add the whole line as a generic smell description
            # smells.append({"lines": "Unknown", "description": line})
            
    if not smells and len(lines) > 0:
         print(f"[Parser Warning] No smells parsed from output:\n{output}")
         # Could indicate the AI found no smells, or the format was totally unexpected.

    return smells

def extract_code_from_output(output: str):
    """Extracts Python code from the AI's response (e.g., tests or refactored code).
    Handles common markdown code block formats.
    Returns the extracted code content as a string, or None if no code block is found.
    """
    if not output:
        return None

    # Regex to find ```python ... ``` or ``` ... ``` blocks
    # It captures the content within the block, handling potential leading/trailing newlines
    # Uses re.DOTALL to make '.' match newlines
    match = re.search(r"```(?:python)?\s*\n(.*?)```", output, re.DOTALL | re.IGNORECASE)
    
    if match:
        extracted_code = match.group(1).strip()
        logging.debug(f"Extracted code block (length {len(extracted_code)}). Preview: {extracted_code[:100]}...")
        return extracted_code
    else:
        # Fallback: If no explicit block found, check if the *entire* output seems like code
        # Heuristic: more than N lines and doesn't contain typical conversational phrases.
        # This is less reliable and can be disabled if needed.
        lines = output.strip().split('\n')
        if len(lines) > 3 and not any(phrase in output.lower() for phrase in ["here is the code", "sure, i can", "generated test"]):
            logging.debug("No code block found, assuming entire output is code.")
            return output.strip()
        else:
            logging.warning(f"Could not extract Python code block from output. Preview: {output[:200]}...")
            return None # Indicate failure or no code found

# --- Comparison Helpers ---

def parse_line_range(line_str: str) -> tuple[int | None, int | None]:
    """Parses a line string like '10' or '15-20' into (start, end) lines.
    Returns (None, None) if parsing fails.
    """
    line_str = str(line_str).strip() # Ensure string
    try:
        if '-' in line_str:
            start, end = map(int, line_str.split('-', 1))
            return start, end
        else:
            line_num = int(line_str)
            return line_num, line_num # Single line
    except ValueError:
        print(f"[Parser Warning] Could not parse line range: '{line_str}'")
        return None, None

def lines_overlap(start1: int | None, end1: int | None, start2: int | None, end2: int | None) -> bool:
    """Checks if two line ranges overlap.
    Assumes inclusive ranges. Handles None values gracefully.
    """
    if start1 is None or end1 is None or start2 is None or end2 is None:
        return False # Cannot compare if any part is None
        
    # Ensure start <= end
    if start1 > end1: start1, end1 = end1, start1
    if start2 > end2: start2, end2 = end2, start2
    
    # Check for overlap: (StartA <= EndB) and (EndA >= StartB)
    return start1 <= end2 and end1 >= start2

# --- Refactoring Helpers ---

def extract_code_block(file_content: str, start_line: int, end_line: int) -> str | None:
    """Extracts a block of code from file content based on 1-indexed lines."""
    try:
        lines = file_content.splitlines()
        # Adjust for 0-based indexing
        start_idx = start_line - 1
        end_idx = end_line # Exclusive index for slicing
        
        if 0 <= start_idx < len(lines) and start_idx < end_idx:
            # Slice might go beyond end of file, but that's okay
            block_lines = lines[start_idx:min(end_idx, len(lines))]
            return "\n".join(block_lines)
        else:
            log.warning(f"Invalid line range for extraction: {start_line}-{end_line} for file with {len(lines)} lines.")
            return None
    except Exception as e:
        log.error(f"Error extracting code block ({start_line}-{end_line}): {e}")
        return None

def replace_code_block(original_content: str, start_line: int, end_line: int, replacement_code: str) -> str | None:
    """Replaces a block of code in original content based on 1-indexed lines."""
    try:
        lines = original_content.splitlines()
        replacement_lines = replacement_code.splitlines()
        # Adjust for 0-based indexing
        start_idx = start_line - 1
        # The range to replace is lines[start_idx:end_idx]
        # end_idx should correspond to the line *after* the last line to remove
        end_idx = end_line 
        
        if 0 <= start_idx < len(lines) and start_idx <= end_idx:
            # Construct the new list of lines
            new_lines = lines[:start_idx] + replacement_lines + lines[end_idx:]
            return "\n".join(new_lines)
        else:
             log.warning(f"Invalid line range for replacement: {start_line}-{end_line} for file with {len(lines)} lines.")
             return None
    except Exception as e:
        log.error(f"Error replacing code block ({start_line}-{end_line}): {e}")
        return None

# --- Metric Extraction Helpers ---

def safe_load_json(file_path: str) -> dict | list | None:
    """Safely loads JSON data from a file, returning None on error."""
    if not os.path.exists(file_path):
        log.warning(f"Metric file not found: {file_path}")
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log.error(f"Error loading/parsing JSON from {file_path}: {e}")
        return None

def get_pylint_score(data: list) -> float | None:
    """Calculates an approximated Pylint score from JSON message list.
    
    Since the score is not directly in the JSON output when using --output-format=json,
    this function calculates an approximation based on message types.
    
    The default Pylint scoring formula is:
    10.0 - ((5 * error + warning + refactor + convention) / statement) * 10
    
    Since we don't have statement count, we'll use a simpler formula based on
    counts of different message types, with weights, with a base score of 10.
    """
    if not data or not isinstance(data, list):
        return None
        
    # Count message types
    error_count = 0
    warning_count = 0
    refactor_count = 0
    convention_count = 0
    
    for msg in data:
        if not isinstance(msg, dict):
            continue
            
        msg_type = msg.get('type')
        if msg_type == 'error':
            error_count += 1
        elif msg_type == 'warning':
            warning_count += 1
        elif msg_type == 'refactor':
            refactor_count += 1
        elif msg_type == 'convention':
            convention_count += 1
    
    # If no messages were found, return perfect score
    total_messages = error_count + warning_count + refactor_count + convention_count
    if total_messages == 0:
        return 10.0
        
    # Calculate simplified score
    # Weights: errors are most severe, then warnings, etc.
    # These weights are approximations of Pylint's actual formula
    weighted_score = 10.0 - min(10.0, (
        (5.0 * error_count) + 
        (1.0 * warning_count) + 
        (0.5 * refactor_count) + 
        (0.25 * convention_count)
    ) / 10)
    
    # Ensure score is between 0 and 10
    return max(0.0, min(10.0, weighted_score))

def get_radon_cc_average(data: dict) -> float | None:
    """Extracts the average Cyclomatic Complexity from Radon CC JSON (-s flag output)."""
    # Radon cc -s -j output is a dict where keys are file paths.
    # The average is not directly included in the per-file JSON when using -j.
    # Need to calculate it manually or run radon cc -a separately.
    # Calculating manually:
    total_complexity = 0
    total_blocks = 0
    if isinstance(data, dict):
        for file_path, blocks in data.items():
            if isinstance(blocks, list):
                for block in blocks:
                    # Consider only functions/methods for average complexity
                    if block.get('type') in ['function', 'method'] and isinstance(block.get('complexity'), int):
                        total_complexity += block['complexity']
                        total_blocks += 1
    if total_blocks > 0:
        return total_complexity / total_blocks
    log.warning(f"Could not calculate average CC from Radon data: {data}")
    return None

def get_radon_mi_average(data: dict) -> float | None:
    """Extracts the average Maintainability Index from Radon MI JSON (-s flag output)."""
    # Radon mi -s -j output format: {"filepath": {"mi": score, ...}}
    # We need the average across all files.
    total_mi = 0.0
    file_count = 0
    if isinstance(data, dict):
        for file_path, metrics in data.items():
            if isinstance(metrics, dict) and 'mi' in metrics and isinstance(metrics['mi'], (float, int)):
                total_mi += metrics['mi']
                file_count += 1
            else:
                 log.debug(f"Skipping file in MI calculation due to unexpected format: {file_path} -> {metrics}")

    if file_count > 0:
        return total_mi / file_count
    log.warning(f"Could not calculate average MI from Radon data: {data}")
    return None

def get_pyright_error_count(data: dict) -> int | None:
    """Extracts the total error count from Pyright JSON output."""
    if isinstance(data, dict) and 'summary' in data:
        return data['summary'].get('errorCount', 0) # Default to 0 if key missing
    log.warning(f"Could not extract Pyright error count from data: {data}")
    return None

def get_bandit_vuln_count(data: dict) -> int | None:
    """Extracts the total number of detected vulnerabilities from Bandit JSON output."""
    # Consider filtering by severity/confidence if needed later
    if isinstance(data, dict) and 'results' in data:
        return len(data['results']) # Count the number of issues found
    # Bandit might output errors object instead of results if scan fails badly
    if isinstance(data, dict) and 'errors' in data and not data.get('results'):
         log.warning(f"Bandit output contains errors but no results: {len(data['errors'])} errors.")
         return 0 # Or handle as error? Returning 0 vulns for now.
    log.warning(f"Could not extract Bandit vulnerability count from data: {data}")
    return None

# --- Test Running Utilities ---

def run_tests_with_pytest(code_directory: str, test_directory: str = None) -> dict | None:
    """Runs pytest on the specified directory and returns test results.
    
    Args:
        code_directory: Path to the code directory to test
        test_directory: Optional specific test directory. If None, looks for 'tests' in code_directory
    
    Returns:
        Dict with test results or None if tests couldn't be run
    """
    import subprocess
    import sys
    
    if not os.path.exists(code_directory):
        log.error(f"Code directory not found: {code_directory}")
        return None
    
    # Determine test directory
    if test_directory is None:
        test_directory = os.path.join(code_directory, "tests")
    
    if not os.path.exists(test_directory):
        log.warning(f"Test directory not found: {test_directory}")
        return {"tests_found": False, "passed": 0, "failed": 0, "total": 0, "error": "No test directory found"}
    
    # Check if there are any test files
    test_files = []
    for root, dirs, files in os.walk(test_directory):
        for file in files:
            if file.startswith("test_") and file.endswith(".py") or file.endswith("_test.py"):
                test_files.append(os.path.join(root, file))
    
    if not test_files:
        log.warning(f"No test files found in: {test_directory}")
        return {"tests_found": False, "passed": 0, "failed": 0, "total": 0, "error": "No test files found"}
    
    log.info(f"Running pytest on {len(test_files)} test files in: {test_directory}")
    
    # Run pytest with JSON output
    pytest_command = [
        sys.executable, "-m", "pytest", 
        test_directory,
        "--tb=short",  # Short traceback format
        "--quiet",     # Reduce output verbosity
        "--json-report", "--json-report-file=/tmp/pytest_report.json"  # JSON output
    ]
    
    try:
        # Run pytest
        result = subprocess.run(
            pytest_command, 
            cwd=code_directory,
            capture_output=True, 
            text=True, 
            encoding='utf-8',
            timeout=300  # 5 minute timeout
        )
        
        # Try to parse JSON report if available
        json_report_path = "/tmp/pytest_report.json"
        test_results = {
            "tests_found": True,
            "passed": 0,
            "failed": 0,
            "total": 0,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
        
        if os.path.exists(json_report_path):
            try:
                with open(json_report_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                    summary = json_data.get('summary', {})
                    test_results["passed"] = summary.get('passed', 0)
                    test_results["failed"] = summary.get('failed', 0)
                    test_results["total"] = summary.get('total', 0)
                    test_results["duration"] = json_data.get('duration', 0)
                # Clean up temp file
                os.remove(json_report_path)
            except Exception as e:
                log.warning(f"Could not parse pytest JSON report: {e}")
                # Fallback: parse from stdout
                test_results.update(_parse_pytest_stdout(result.stdout))
        else:
            # Fallback: parse from stdout
            test_results.update(_parse_pytest_stdout(result.stdout))
        
        log.info(f"Test results: {test_results['passed']}/{test_results['total']} passed")
        return test_results
        
    except subprocess.TimeoutExpired:
        log.error(f"Pytest timed out after 5 minutes for: {test_directory}")
        return {"tests_found": True, "passed": 0, "failed": 0, "total": 0, "error": "Timeout"}
    except FileNotFoundError:
        log.error("pytest not found. Make sure pytest is installed.")
        return {"tests_found": True, "passed": 0, "failed": 0, "total": 0, "error": "pytest not installed"}
    except Exception as e:
        log.error(f"Error running pytest: {e}")
        return {"tests_found": True, "passed": 0, "failed": 0, "total": 0, "error": str(e)}

def _parse_pytest_stdout(stdout: str) -> dict:
    """Fallback parser for pytest stdout when JSON report is not available."""
    import re
    
    results = {"passed": 0, "failed": 0, "total": 0}
    
    # Look for patterns like "2 passed, 1 failed" or "5 passed"
    pattern = r'(\d+)\s+(passed|failed|error|skipped)'
    matches = re.findall(pattern, stdout, re.IGNORECASE)
    
    for count, status in matches:
        count = int(count)
        if status.lower() in ['passed']:
            results["passed"] = count
        elif status.lower() in ['failed', 'error']:
            results["failed"] += count
    
    results["total"] = results["passed"] + results["failed"]
    
    # Alternative pattern: "= X failed, Y passed in Z seconds ="
    alt_pattern = r'=.*?(\d+)\s+failed.*?(\d+)\s+passed'
    alt_match = re.search(alt_pattern, stdout, re.IGNORECASE)
    if alt_match:
        results["failed"] = int(alt_match.group(1))
        results["passed"] = int(alt_match.group(2))
        results["total"] = results["passed"] + results["failed"]
    
    return results

def get_test_results(data: dict) -> tuple[int, int, int] | None:
    """Extracts test results from test runner JSON output.
    
    Returns:
        Tuple of (passed, failed, total) or None if data is invalid
    """
    if not isinstance(data, dict):
        return None
    
    if not data.get("tests_found", False):
        return (0, 0, 0)  # No tests found
    
    passed = data.get("passed", 0)
    failed = data.get("failed", 0)
    total = data.get("total", 0)
    
    return (passed, failed, total)
