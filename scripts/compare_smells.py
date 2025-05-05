"""
Step 3b: Compare AI-detected smells with Library-detected smells.

Calculates True Positives, False Positives, and False Negatives based on
line number overlap between AI results and Pylint/Radon results, reporting
metrics separately for Pylint and Radon as ground truths.
"""

import os
import sys
import json
import re
from utils import (
    METRICS_DIR, ORIGINAL_CODE_DIR, 
    save_json, parse_line_range, lines_overlap
)
import logging

# --- Configuration ---
# Radon CC complexity threshold - only consider functions/methods above this
# Set to None to consider all entries from Radon.
RADON_COMPLEXITY_THRESHOLD = 10 # Keep threshold as per previous run

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

def load_json_file(file_path: str):
    """Loads data from a JSON file."""
    if not os.path.exists(file_path):
        log.error(f"File not found: {file_path}")
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        log.error(f"Error decoding JSON from {file_path}: {e}")
        return None
    except Exception as e:
        log.error(f"Error reading file {file_path}: {e}")
        return None

def extract_pylint_smells(pylint_data, repo_name: str):
    """Extracts smell locations from Pylint data."""
    pylint_smells = {}
    total_pylint_smells = 0
    if pylint_data and isinstance(pylint_data, list):
        for msg_idx, msg in enumerate(pylint_data):
            if all(k in msg for k in ['path', 'line', 'message']):
                try:
                    relative_path = os.path.relpath(msg['path'], os.path.join(ORIGINAL_CODE_DIR, repo_name))
                except ValueError:
                    relative_path = msg['path']
                    
                file_path = relative_path.replace('\\', '/')
                start_line = msg['line']
                # Use 'endLine' if available and valid, otherwise default to start_line
                end_line = msg.get('endLine')
                if not isinstance(end_line, int) or end_line < start_line:
                    end_line = start_line 
                
                if file_path not in pylint_smells:
                    pylint_smells[file_path] = []
                
                pylint_smells[file_path].append({
                    "tool": "pylint",
                    "start_line": start_line,
                    "end_line": end_line,
                    "description": f"{msg.get('symbol', '')}: {msg['message']}",
                    "internal_id": (file_path, msg_idx) # Unique ID for matching
                })
                total_pylint_smells += 1
            else:
                log.warning(f"Skipping Pylint message with missing keys: {msg}")
    else:
        log.warning("Pylint data is missing, empty, or not a list.")
    return pylint_smells, total_pylint_smells

def extract_radon_smells(radon_data, repo_name: str):
    """Extracts smell locations from Radon data."""
    radon_smells = {}
    total_radon_smells = 0
    if radon_data and isinstance(radon_data, dict):
        for file_path_abs, functions in radon_data.items():
            if isinstance(functions, list):
                try:
                    relative_path = os.path.relpath(file_path_abs, os.path.join(ORIGINAL_CODE_DIR, repo_name))
                except ValueError:
                    relative_path = file_path_abs
                file_path = relative_path.replace('\\', '/')
                for func_idx, func in enumerate(functions):
                    complexity = func.get('complexity')
                    func_type = func.get('type')
                    if func_type in ['function', 'method'] and isinstance(complexity, (int, float)):
                        if RADON_COMPLEXITY_THRESHOLD is None or complexity >= RADON_COMPLEXITY_THRESHOLD:
                            if all(k in func for k in ['lineno', 'endline', 'name']):
                                if file_path not in radon_smells:
                                    radon_smells[file_path] = []
                                radon_smells[file_path].append({
                                    "tool": "radon",
                                    "start_line": func['lineno'],
                                    "end_line": func['endline'],
                                    "description": f"High Complexity ({func_type} '{func['name']}': {complexity})",
                                    "internal_id": (file_path, func_idx) # Unique ID for matching
                                })
                                total_radon_smells += 1
                            else:
                                log.warning(f"Skipping Radon entry with missing keys: {func}")       
            else:
                log.warning(f"Skipping Radon entry with unexpected format for file '{file_path_abs}': {functions}")
    else:
        log.warning("Radon data is missing, empty, or not a dict.")
    return radon_smells, total_radon_smells

def extract_ai_smells(ai_data):
    """Extracts AI smell locations, parsing line ranges robustly.
    Attempts to find line ranges like '(Lines X-Y)' in the description first,
    then falls back to parsing the 'lines' field after cleaning.
    """
    ai_smells = {}
    total_ai_smells_reported = 0 # Total smells listed in the json
    total_ai_smells_parsed = 0   # Total smells where location could be parsed
    
    # Regex to find patterns like (Lines X-Y), (Line X), L X-Y, Line X
    # Makes numbers optional for single line cases like (Line 10)
    line_pattern = re.compile(r'[\(\[\{]?L(?:ine|ines?)?\s*(\d+)(?:[-\s]*(\d+))?[\)\]\}]?', re.IGNORECASE)

    if ai_data and isinstance(ai_data.get('files'), dict):
        for file_path, smells in ai_data['files'].items():
            normalized_path = file_path.replace('\\', '/')
            ai_smells[normalized_path] = []
            if not isinstance(smells, list):
                 log.warning(f"Unexpected format for AI smells in file '{normalized_path}': {smells}")
                 continue # Skip this file if smells is not a list
                
            for smell_idx, smell in enumerate(smells):
                total_ai_smells_reported += 1
                start_line, end_line = None, None
                description = smell.get('description', '')
                lines_field = str(smell.get('lines', '')) # Ensure string

                # 1. Try parsing from description first
                if description:
                    match = line_pattern.search(description)
                    if match:
                        s_start = match.group(1)
                        s_end = match.group(2) # Might be None
                        try:
                            start_line = int(s_start)
                            end_line = int(s_end) if s_end else start_line
                            log.debug(f"Parsed from description '{description[:50]}...': L{start_line}-{end_line}")
                        except ValueError:
                            log.warning(f"Found pattern in description but failed to convert to int: {match.groups()} in '{description}'")
                            start_line, end_line = None, None # Reset on failure

                # 2. If not found in description, try parsing the 'lines' field
                if start_line is None and lines_field:
                    # Clean the lines field: remove potential list numbers, bullets, whitespace etc.
                    # Corrected regex to avoid 'multiple repeat' error
                    cleaned_lines = re.sub(r'^[ \t#*.-]*', '', lines_field).strip()
                    # Attempt parsing the cleaned string (might be '10-15', '10', or still junk)
                    start_line, end_line = parse_line_range(cleaned_lines)
                    if start_line is not None:
                        log.debug(f"Parsed from cleaned lines field '{lines_field}' -> '{cleaned_lines}': L{start_line}-{end_line}")
                    else:
                        log.debug(f"Failed to parse cleaned lines field: '{cleaned_lines}' from original '{lines_field}'")
                        
                # 3. Add to list if parsing succeeded
                if start_line is not None and end_line is not None:
                    ai_smells[normalized_path].append({
                        "start_line": start_line,
                        "end_line": end_line,
                        "description": description, # Keep original description
                        "original_lines_field": lines_field, # Store for debugging
                        "internal_id": (normalized_path, smell_idx) 
                    })
                    total_ai_smells_parsed += 1
                else:
                    log.warning(f"Could not extract valid line range for AI smell in {normalized_path}: Lines='{lines_field}', Desc='{description[:50]}...'")
    else:
        log.warning("AI data is missing or has incorrect structure ('files' dict not found).")
        # Get total reported count from summary if possible
        total_ai_smells_reported = ai_data.get('summary', {}).get('total_smells_detected', 0)
       
    # Use the count derived from successfully parsed smells for comparisons
    # Report both total reported and total parsed for clarity
    log.info(f"AI Smells: Reported={total_ai_smells_reported}, Parsed Location={total_ai_smells_parsed}")
    return ai_smells, total_ai_smells_parsed # Return dict and PARSED count

def compare_smells_detailed(pylint_smells_by_file: dict, radon_smells_by_file: dict, ai_smells_by_file: dict):
    """Compares AI smells against Pylint and Radon separately based on line overlap."""
    
    matched_pylint_ids = set()
    matched_radon_ids = set()
    fp_ai_ids = set() # Store IDs of AI smells that are False Positives

    log.debug("--- Starting Detailed Comparison ---")
    # Iterate through AI smells to find overlaps and mark FPs
    for file_path, ai_file_smells in ai_smells_by_file.items():
        pylint_file_smells = pylint_smells_by_file.get(file_path, [])
        radon_file_smells = radon_smells_by_file.get(file_path, [])
        
        for ai_smell in ai_file_smells:
            ai_start, ai_end = ai_smell['start_line'], ai_smell['end_line']
            ai_id = ai_smell['internal_id']
            ai_desc = ai_smell['description']
            log.debug(f"Checking AI Smell: {file_path} L{ai_start}-{ai_end} ({ai_desc[:30]}...) ID: {ai_id}")
            
            overlaps_pylint = False
            for pylint_smell in pylint_file_smells:
                pylint_start, pylint_end = pylint_smell['start_line'], pylint_smell['end_line']
                if lines_overlap(ai_start, ai_end, pylint_start, pylint_end):
                    pylint_id = pylint_smell['internal_id']
                    log.debug(f"  -> Overlaps Pylint: L{pylint_start}-{pylint_end} ID: {pylint_id}")
                    matched_pylint_ids.add(pylint_id)
                    overlaps_pylint = True
                    # Don't break, an AI smell might overlap multiple lib smells
                    
            overlaps_radon = False
            for radon_smell in radon_file_smells:
                radon_start, radon_end = radon_smell['start_line'], radon_smell['end_line']
                if lines_overlap(ai_start, ai_end, radon_start, radon_end):
                    radon_id = radon_smell['internal_id']
                    log.debug(f"  -> Overlaps Radon: L{radon_start}-{radon_end} ID: {radon_id}")
                    matched_radon_ids.add(radon_id)
                    overlaps_radon = True
                    # Don't break here either
            
            # If AI smell overlaps neither, it's an FP
            if not overlaps_pylint and not overlaps_radon:
                log.debug(f"  -> No Overlap Found. Marking as FP.")
                fp_ai_ids.add(ai_id)

    # Calculate TP and FN for Pylint
    total_pylint_smells = 0
    fn_pylint_ids = set()
    for file_path, pylint_file_smells in pylint_smells_by_file.items():
        total_pylint_smells += len(pylint_file_smells)
        for pylint_smell in pylint_file_smells:
            pylint_id = pylint_smell['internal_id']
            if pylint_id not in matched_pylint_ids:
                fn_pylint_ids.add(pylint_id)
                p_start, p_end = pylint_smell['start_line'], pylint_smell['end_line']
                log.debug(f"Pylint FN: {file_path} L{p_start}-{p_end} ID: {pylint_id}")

    tp_pylint = len(matched_pylint_ids)
    fn_pylint = len(fn_pylint_ids)
    assert tp_pylint + fn_pylint == total_pylint_smells

    # Calculate TP and FN for Radon
    total_radon_smells = 0
    fn_radon_ids = set()
    for file_path, radon_file_smells in radon_smells_by_file.items():
        total_radon_smells += len(radon_file_smells)
        for radon_smell in radon_file_smells:
            radon_id = radon_smell['internal_id']
            if radon_id not in matched_radon_ids:
                fn_radon_ids.add(radon_id)
                r_start, r_end = radon_smell['start_line'], radon_smell['end_line']
                log.debug(f"Radon FN: {file_path} L{r_start}-{r_end} ID: {radon_id}")
                
    tp_radon = len(matched_radon_ids)
    fn_radon = len(fn_radon_ids)
    assert tp_radon + fn_radon == total_radon_smells

    fp_ai = len(fp_ai_ids)
    log.debug(f"--- Comparison Finished ---")
    log.debug(f"Matched Pylint IDs: {len(matched_pylint_ids)}, Matched Radon IDs: {len(matched_radon_ids)}, AI FP IDs: {len(fp_ai_ids)}")
    log.debug(f"Pylint FN IDs: {len(fn_pylint_ids)}, Radon FN IDs: {len(fn_radon_ids)}")

    return {
        "tp_pylint": tp_pylint, "fn_pylint": fn_pylint, 
        "tp_radon": tp_radon, "fn_radon": fn_radon,
        "fp_ai": fp_ai
    }

def calculate_prf1(tp, fp, fn):
    """Calculates Precision, Recall, and F1-score."""
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    return precision, recall, f1

def main(repo_name: str):
    """Performs the smell comparison for the given repository."""
    log.info(f"--- Comparing Smells for Repository: {repo_name} ---")
    # Set logging level to DEBUG to see detailed overlap checks
    # log.setLevel(logging.DEBUG)

    metrics_repo_dir = os.path.join(METRICS_DIR, repo_name)
    if not os.path.isdir(metrics_repo_dir):
        log.error(f"Metrics directory not found for repo {repo_name} at {metrics_repo_dir}. Run previous steps.")
        return False # Indicate failure
        
    pylint_file = os.path.join(metrics_repo_dir, "smells_lib_pylint.json")
    radon_file = os.path.join(metrics_repo_dir, "smells_lib_radon_cc.json")
    ai_file = os.path.join(metrics_repo_dir, "smells_deepseek.json")
    output_file = os.path.join(metrics_repo_dir, "comparison_summary_detailed.json")

    # Load data
    pylint_data = load_json_file(pylint_file)
    radon_data = load_json_file(radon_file)
    ai_data = load_json_file(ai_file)

    if pylint_data is None or radon_data is None or ai_data is None:
        log.error("Failed to load one or more necessary metric files. Aborting comparison.")
        return False

    # Extract smells separately
    pylint_smells, num_pylint_detected = extract_pylint_smells(pylint_data, repo_name)
    radon_smells, num_radon_detected = extract_radon_smells(radon_data, repo_name)
    ai_smells, num_ai_parsed = extract_ai_smells(ai_data)
    num_ai_reported = ai_data.get('summary', {}).get('total_smells_detected', num_ai_parsed)

    log.info(f"Extracted Libs: Pylint={num_pylint_detected}, Radon={num_radon_detected}")
    log.info(f"Extracted AI: Reported={num_ai_reported}, Parsed Location={num_ai_parsed}")

    # Compare
    comparison_results = compare_smells_detailed(pylint_smells, radon_smells, ai_smells)

    tp_pylint = comparison_results["tp_pylint"]
    fn_pylint = comparison_results["fn_pylint"]
    tp_radon = comparison_results["tp_radon"]
    fn_radon = comparison_results["fn_radon"]
    fp_ai = comparison_results["fp_ai"]

    # Calculate metrics separately
    precision_pylint, recall_pylint, f1_pylint = calculate_prf1(tp_pylint, fp_ai, fn_pylint)
    precision_radon, recall_radon, f1_radon = calculate_prf1(tp_radon, fp_ai, fn_radon)

    # Prepare summary
    summary = {
        "repository": repo_name,
        "counts": {
            "pylint_detected": num_pylint_detected,
            "radon_detected": num_radon_detected,
            "ai_detected_reported": num_ai_reported,
            "ai_detected_parsed_location": num_ai_parsed,
        },
        "comparison_vs_pylint": {
            "true_positives": tp_pylint,
            "false_negatives_pylint": fn_pylint,
            "precision": precision_pylint,
            "recall": recall_pylint,
            "f1_score": f1_pylint
        },
        "comparison_vs_radon": {
            "true_positives": tp_radon,
            "false_negatives_radon": fn_radon,
            "precision": precision_radon,
            "recall": recall_radon,
            "f1_score": f1_radon
        },
        "ai_false_positives": fp_ai
    }

    log.info("\nComparison Results Summary:")
    log.info(json.dumps(summary, indent=2))

    # Save summary
    save_json(summary, output_file)
    log.info(f"\nDetailed comparison summary saved to: {output_file}")
    log.info(f"--- Finished Smell Comparison: {repo_name} ---")
    return True # Indicate success

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Compare AI vs Library smells for a specific repository.")
    parser.add_argument("repo_name", help="Name of the repository directory within original_code/ (used for path context and finding metrics)")
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    if not main(args.repo_name):
        sys.exit(1)
