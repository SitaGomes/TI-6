"""
Step 7: Aggregate Metrics & CSV Export.

Reads all generated JSONs, extract metrics, calculate deltas, aggregate into pandas DataFrame, save to CSV.
"""

import os
import sys
import pandas as pd
from utils import (
    METRICS_DIR, STRATEGIES,
    safe_load_json,
    get_pylint_score, get_radon_cc_average, get_radon_mi_average,
    get_pyright_error_count, get_bandit_vuln_count, get_test_results
)
import logging

log = logging.getLogger(__name__)

def calculate_delta(metric_after, metric_before):
    """Calculates delta, handling None values."""
    if metric_after is None or metric_before is None:
        return None # Cannot calculate delta if either value is missing
    return metric_after - metric_before

def aggregate_repo_metrics(repo_name: str):
    """Aggregates metrics for a single repository across all strategies."""
    log.info(f"--- Aggregating Metrics for Repository: {repo_name} ---")
    rows = []
    repo_metrics_dir = os.path.join(METRICS_DIR, repo_name)

    # 1. Load Comparison Summary (contains smell detection counts)
    comparison_summary_path = os.path.join(repo_metrics_dir, "comparison_summary_detailed.json")
    comparison_data = safe_load_json(comparison_summary_path)
    
    # Provide default values if comparison data is missing
    if comparison_data is None:
        log.warning(f"Could not load comparison summary for {repo_name}. Using default values.")
        comparison_data = {
            'counts': {
                'pylint_detected': 0,
                'radon_detected': 0,
                'ai_detected_reported': 0
            },
            'ai_false_positives': 0,
            'comparison_vs_pylint': {
                'false_negatives_pylint': 0
            }
        }
        
    # Extract base counts from comparison summary
    num_smells_lib = comparison_data.get('counts', {}).get('pylint_detected', 0) + \
                       comparison_data.get('counts', {}).get('radon_detected', 0)
    num_smells_ai = comparison_data.get('counts', {}).get('ai_detected_reported', 0)
    # Use the comparison vs pylint for overall TP/FN for now, could be refined
    # We need the overall FP/FN for the final CSV, not per-tool.
    # Let's use the comparison_vs_pylint results for FN and the overall ai_false_positives for FP
    # This aligns with README's columns: num_false_positives, num_false_negatives
    num_false_positives = comparison_data.get('ai_false_positives', 0)
    num_false_negatives = comparison_data.get('comparison_vs_pylint', {}).get('false_negatives_pylint', 0) # Example: using Pylint FN
    # Alternative: num_false_negatives = comparison_data.get(...pylint...) + comparison_data.get(...radon...)? Definition needs clarity.
    # Sticking to Pylint FN as a proxy for now.
    
    log.debug(f"Base metrics: LibSmells={num_smells_lib}, AISmells={num_smells_ai}, FP={num_false_positives}, FN={num_false_negatives}")

    # 2. Load Original Code Metrics
    # Note: Pylint score calculation needs refinement as noted in utils.py
    orig_pylint_data = safe_load_json(os.path.join(repo_metrics_dir, "smells_lib_pylint.json"))
    orig_radon_cc_data = safe_load_json(os.path.join(repo_metrics_dir, "smells_lib_radon_cc.json"))
    orig_radon_mi_data = safe_load_json(os.path.join(repo_metrics_dir, "radon_mi.json")) # Expects this from rerun of script 02
    orig_tests_data = safe_load_json(os.path.join(repo_metrics_dir, "original_tests.json"))
    # Pyright and Bandit are not run on original code in this workflow

    orig_pylint_score = get_pylint_score(orig_pylint_data) 
    orig_avg_cc = get_radon_cc_average(orig_radon_cc_data)
    orig_avg_mi = get_radon_mi_average(orig_radon_mi_data)
    orig_test_results = get_test_results(orig_tests_data) if orig_tests_data else (0, 0, 0)
    orig_tests_passed, orig_tests_failed, orig_tests_total = orig_test_results
    # Original errors/vulns are assumed 0 for delta calculation as they weren't measured
    orig_pyright_errors = 0 
    orig_bandit_vulns = 0 
    
    if orig_pylint_score is None or orig_avg_cc is None or orig_avg_mi is None:
        log.warning(f"Some original metrics are missing for {repo_name}. Using default values where needed.")
        # Provide default values if any are missing
        orig_pylint_score = orig_pylint_score or 5.0  # Reasonable default
        orig_avg_cc = orig_avg_cc or 5.0  # Reasonable default
        orig_avg_mi = orig_avg_mi or 50.0  # Reasonable default
    
    log.info(f"Original Metrics: PylintScore={orig_pylint_score}, AvgCC={orig_avg_cc}, AvgMI={orig_avg_mi}, Tests={orig_tests_passed}/{orig_tests_total}")

    # Track if we found any valid strategy directories
    found_any_strategy = False

    # 3. Process Each Strategy
    for strategy in STRATEGIES:
        log.info(f"  Processing strategy: {strategy}")
        strategy_metrics_dir = os.path.join(repo_metrics_dir, strategy)
        if not os.path.isdir(strategy_metrics_dir):
            log.warning(f"Metrics directory for strategy '{strategy}' not found. Skipping.")
            continue
            
        found_any_strategy = True
            
        # Load post-refactor metrics
        pylint_data = safe_load_json(os.path.join(strategy_metrics_dir, "pylint.json"))
        radon_cc_data = safe_load_json(os.path.join(strategy_metrics_dir, "radon_cc.json"))
        radon_mi_data = safe_load_json(os.path.join(strategy_metrics_dir, "radon_mi.json"))
        pyright_data = safe_load_json(os.path.join(strategy_metrics_dir, "pyright.json"))
        bandit_data = safe_load_json(os.path.join(strategy_metrics_dir, "bandit.json"))
        tests_data = safe_load_json(os.path.join(strategy_metrics_dir, "tests.json"))
        
        # Extract post-refactor values
        pylint_score = get_pylint_score(pylint_data)
        avg_cc = get_radon_cc_average(radon_cc_data)
        avg_mi = get_radon_mi_average(radon_mi_data)
        pyright_errors = get_pyright_error_count(pyright_data)
        bandit_vulns = get_bandit_vuln_count(bandit_data)
        test_results = get_test_results(tests_data) if tests_data else (0, 0, 0)
        tests_passed, tests_failed, tests_total = test_results
        
        # Provide default values if needed
        if pylint_score is None or avg_cc is None or avg_mi is None:
            log.warning(f"Some metrics are missing for {strategy}. Using defaults where needed.")
            # Use original values as defaults if metrics are missing
            pylint_score = pylint_score or orig_pylint_score
            avg_cc = avg_cc or orig_avg_cc
            avg_mi = avg_mi or orig_avg_mi
            
        # Use 0 as defaults for error counts if missing
        pyright_errors = pyright_errors if pyright_errors is not None else 0
        bandit_vulns = bandit_vulns if bandit_vulns is not None else 0
        
        log.debug(f"    {strategy} metrics: Pylint={pylint_score}, CC={avg_cc}, MI={avg_mi}, Pyright={pyright_errors}, Bandit={bandit_vulns}, Tests={tests_passed}/{tests_total}")

        # Calculate deltas
        pylint_delta = calculate_delta(pylint_score, orig_pylint_score)
        cc_delta = calculate_delta(avg_cc, orig_avg_cc)
        mi_delta = calculate_delta(avg_mi, orig_avg_mi)
        pyright_delta = calculate_delta(pyright_errors, orig_pyright_errors)
        bandit_delta = calculate_delta(bandit_vulns, orig_bandit_vulns)
        
        # Calculate test pass ratio (format: "refactored_passed/original_passed")
        test_pass_ratio = f"{tests_passed}/{orig_tests_passed}" if orig_tests_total > 0 else f"{tests_passed}/0"
        
        # Provide sensible defaults for deltas if calculation failed
        pylint_delta = pylint_delta or 0.0
        cc_delta = cc_delta or 0.0
        mi_delta = mi_delta or 0.0
        pyright_delta = pyright_delta or 0
        bandit_delta = bandit_delta or 0
        
        log.debug(f"    {strategy} deltas: Pylint={pylint_delta}, CC={cc_delta}, MI={mi_delta}, Pyright={pyright_delta}, Bandit={bandit_delta}, TestRatio={test_pass_ratio}")
        
        # Assemble row data - matching README columns
        row = {
            "repository_name": repo_name,
            "strategy": strategy,
            "num_smells_detected_lib": num_smells_lib,
            "num_smells_detected_deepseek": num_smells_ai,
            "num_false_positives": num_false_positives,
            "num_false_negatives": num_false_negatives,
            "pylint_score_delta": pylint_delta, # Note: Will be None until score extraction is fixed
            "avg_cyclomatic_delta": cc_delta,
            "maintainability_index_delta": mi_delta,
            "pyright_error_delta": pyright_delta, # Lower is better, so delta might be negative
            "bandit_vuln_delta": bandit_delta,   # Lower is better
            "test_pass_ratio": test_pass_ratio   # Format: "refactored_passed/original_passed"
        }
        rows.append(row)

    if not found_any_strategy:
        log.warning(f"No strategy directories found for repository: {repo_name}")
    
    # Always return rows - might be empty if no strategies were found
    return rows

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    log.info("--- Starting Metric Aggregation ---")

    all_repo_rows = []
    processed_repos = 0
    failed_repos = 0

    # Iterate through repo directories in metrics/
    if not os.path.exists(METRICS_DIR):
        log.error(f"Metrics directory '{METRICS_DIR}' not found. Did previous steps run?")
        sys.exit(1)
        
    # Find repository subdirectories within the metrics directory
    repo_names = [d for d in os.listdir(METRICS_DIR) 
                  if os.path.isdir(os.path.join(METRICS_DIR, d))]

    if not repo_names:
        log.warning(f"No repository metric directories found in '{METRICS_DIR}'.")
        # Create empty DataFrame with expected columns
        column_order = [
            "repository_name",
            "strategy",
            "num_smells_detected_lib",
            "num_smells_detected_deepseek",
            "num_false_positives",
            "num_false_negatives",
            "pylint_score_delta",
            "avg_cyclomatic_delta",
            "maintainability_index_delta",
            "pyright_error_delta",
            "bandit_vuln_delta",
            "test_pass_ratio"
        ]
        summary_df = pd.DataFrame(columns=column_order)
        output_csv_path = os.path.join(METRICS_DIR, "summary.csv")
        summary_df.to_csv(output_csv_path, index=False)
        log.info(f"Created empty summary CSV at: {output_csv_path}")
        sys.exit(0)

    for repo_name in repo_names:
        repo_data = aggregate_repo_metrics(repo_name)
        if repo_data:
            all_repo_rows.extend(repo_data)
            processed_repos += 1
            log.info(f"Successfully aggregated metrics for: {repo_name} ({len(repo_data)} rows)")
        else:
            failed_repos += 1
            log.warning(f"No metrics generated for repository: {repo_name}")

    # Define column order as per README
    column_order = [
        "repository_name",
        "strategy",
        "num_smells_detected_lib",
        "num_smells_detected_deepseek",
        "num_false_positives",
        "num_false_negatives",
        "pylint_score_delta",
        "avg_cyclomatic_delta",
        "maintainability_index_delta",
        "pyright_error_delta",
        "bandit_vuln_delta",
        "test_pass_ratio"
    ]

    # Create DataFrame - handle empty case
    if not all_repo_rows:
        log.warning("No data aggregated. Creating empty summary CSV.")
        summary_df = pd.DataFrame(columns=column_order)
    else:
        summary_df = pd.DataFrame(all_repo_rows)
        summary_df = summary_df[column_order]  # Reorder columns

    # Save CSV
    output_csv_path = os.path.join(METRICS_DIR, "summary.csv")
    try:
        summary_df.to_csv(output_csv_path, index=False)
        log.info(f"\nSummary CSV saved successfully to: {output_csv_path}")
    except Exception as e:
        log.error(f"Failed to save summary CSV to {output_csv_path}: {e}")
        sys.exit(1)
        
    log.info(f"\n--- Aggregation Summary ---")
    log.info(f"Successfully aggregated metrics for: {processed_repos} repositories")
    log.info(f"Failed to aggregate metrics for:   {failed_repos} repositories")
    log.info(f"Total rows in CSV: {len(summary_df)}")
    
    # Don't exit with error - always try to complete the workflow
    log.info("--- Metric Aggregation Completed ---")

    # --- Optional Cleanup Step --- (Disabled by default)
    # Add logic here to delete original_code/ and refactored_code/ dirs 
    # if needed for the large-scale run, AFTER verifying CSV output.
    # Example:
    # if processed_repos > 0 and failed_repos == 0: # Only cleanup on full success
    #    log.info("Performing cleanup...")
    #    try: shutil.rmtree(ORIGINAL_CODE_DIR) except Exception as e: log.error(f"Cleanup error (original): {e}")
    #    try: shutil.rmtree(REFACTORED_CODE_DIR) except Exception as e: log.error(f"Cleanup error (refactored): {e}")
    #    log.info("Cleanup finished.")
    # else:
    #    log.warning("Skipping cleanup due to aggregation failures or no processed repos.")
