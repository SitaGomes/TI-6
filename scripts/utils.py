"""
Utility functions for the refactoring workflow.
"""

import os
import json
from openai import OpenAI, RateLimitError, APIError
import time
import re
import logging

# --- Constants ---
ORIGINAL_CODE_DIR = "original_code"
REFACTORED_CODE_DIR = "refactored_code"
METRICS_DIR = "metrics"
STRATEGIES = ["zero_shot", "one_shot", "cot"] # Added shared constant

# --- Logging Setup ---
log = logging.getLogger(__name__) # Initialize logger for this module

# --- Environment & Configuration ---

def get_deepseek_client():
    """Initializes and returns the OpenAI client configured for DeepSeek via OpenRouter."""
    # Expects the OpenRouter API key to be set in this environment variable
    api_key = ""
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY environment variable not set (expected OpenRouter key).")
    
    # Using OpenAI library compatibility pointed at OpenRouter
    client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1") 
    return client

def get_github_token():
    """Retrieves the GitHub token from environment variables."""
    token = ""
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable not set.")
    return token

# --- API Interaction (Placeholder) ---

# Configure based on DeepSeek model availability via OpenRouter
# Using the free model identifier potentially used by OpenRouter
DEEPSEEK_MODEL = "deepseek/deepseek-prover-v2:free" 
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5

def call_deepseek_api(prompt: str, client: OpenAI):
    """Calls the DeepSeek Chat Completion API with retry logic."""
    retries = 0
    while retries < MAX_RETRIES:
        try:
            response = client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[
                    #{"role": "system", "content": "You are a helpful coding assistant specializing in Python refactoring."}, # Optional: Add system message if needed
                    {"role": "user", "content": prompt}
                ],
                stream=False
                # Add other parameters like temperature, max_tokens if needed
            )
            return response.choices[0].message.content
        except RateLimitError as e:
            print(f"Rate limit reached. Retrying in {RETRY_DELAY_SECONDS} seconds... ({retries + 1}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY_SECONDS)
            retries += 1
        except APIError as e:
            print(f"DeepSeek API error: {e}. Retrying in {RETRY_DELAY_SECONDS} seconds... ({retries + 1}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY_SECONDS)
            retries += 1
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            # Decide if retry is appropriate for other errors
            # For now, we'll break the loop on unexpected errors
            break 

    print(f"Failed to get response from DeepSeek API after {MAX_RETRIES} retries.")
    return None # Indicate failure

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
    """Extracts the global Pylint score. Pylint JSON output is a list of messages.
       The score is not directly in the JSON messages. 
       Requires running pylint WITHOUT --exit-zero and capturing the score message from stdout/stderr.
       Alternatively, parse messages to approximate a score (complex).
       Current approach: Placeholder - returns None. Needs adjustment based on how score is obtained.
    """
    log.warning("Pylint score extraction is complex from JSON message list. Returning None.")
    # If you capture the summary line like "Your code has been rated at X.XX/10", parse it here.
    # Placeholder: If score were available in a dict format, it might look like:
    # if isinstance(data, dict) and 'global_note' in data:
    #     return data['global_note'] 
    return None 

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
