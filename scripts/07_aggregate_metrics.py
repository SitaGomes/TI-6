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
    get_pyright_error_count, get_bandit_vuln_count
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
    if comparison_data is None:
        log.error(f"Could not load comparison summary for {repo_name}. Aborting aggregation for this repo.")
        return None
        
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
    # Pyright and Bandit are not run on original code in this workflow

    orig_pylint_score = get_pylint_score(orig_pylint_data) 
    orig_avg_cc = get_radon_cc_average(orig_radon_cc_data)
    orig_avg_mi = get_radon_mi_average(orig_radon_mi_data)
    # Original errors/vulns are assumed 0 for delta calculation as they weren't measured
    orig_pyright_errors = 0 
    orig_bandit_vulns = 0 
    
    log.info(f"Original Metrics: PylintScore={orig_pylint_score}, AvgCC={orig_avg_cc}, AvgMI={orig_avg_mi}")

    # 3. Process Each Strategy
    for strategy in STRATEGIES:
        log.info(f"  Processing strategy: {strategy}")
        strategy_metrics_dir = os.path.join(repo_metrics_dir, strategy)
        if not os.path.isdir(strategy_metrics_dir):
            log.warning(f"Metrics directory for strategy '{strategy}' not found. Skipping.")
            continue
            
        # Load post-refactor metrics
        pylint_data = safe_load_json(os.path.join(strategy_metrics_dir, "pylint.json"))
        radon_cc_data = safe_load_json(os.path.join(strategy_metrics_dir, "radon_cc.json"))
        radon_mi_data = safe_load_json(os.path.join(strategy_metrics_dir, "radon_mi.json"))
        pyright_data = safe_load_json(os.path.join(strategy_metrics_dir, "pyright.json"))
        bandit_data = safe_load_json(os.path.join(strategy_metrics_dir, "bandit.json"))
        
        # Extract post-refactor values
        pylint_score = get_pylint_score(pylint_data)
        avg_cc = get_radon_cc_average(radon_cc_data)
        avg_mi = get_radon_mi_average(radon_mi_data)
        pyright_errors = get_pyright_error_count(pyright_data)
        bandit_vulns = get_bandit_vuln_count(bandit_data)
        
        log.debug(f"    {strategy} metrics: Pylint={pylint_score}, CC={avg_cc}, MI={avg_mi}, Pyright={pyright_errors}, Bandit={bandit_vulns}")

        # Calculate deltas
        pylint_delta = calculate_delta(pylint_score, orig_pylint_score)
        cc_delta = calculate_delta(avg_cc, orig_avg_cc)
        mi_delta = calculate_delta(avg_mi, orig_avg_mi)
        pyright_delta = calculate_delta(pyright_errors, orig_pyright_errors)
        bandit_delta = calculate_delta(bandit_vulns, orig_bandit_vulns)
        
        log.debug(f"    {strategy} deltas: Pylint={pylint_delta}, CC={cc_delta}, MI={mi_delta}, Pyright={pyright_delta}, Bandit={bandit_delta}")
        
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
            "bandit_vuln_delta": bandit_delta   # Lower is better
        }
        rows.append(row)

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
        log.error(f"No repository metric directories found in '{METRICS_DIR}'.")
        sys.exit(1)

    for repo_name in repo_names:
        repo_data = aggregate_repo_metrics(repo_name)
        if repo_data:
            all_repo_rows.extend(repo_data)
            processed_repos += 1
        else:
            failed_repos += 1
            log.error(f"Aggregation failed for repository: {repo_name}")

    if not all_repo_rows:
        log.error("No data aggregated. Cannot create summary CSV.")
        sys.exit(1)

    # Create DataFrame
    summary_df = pd.DataFrame(all_repo_rows)
    
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
        "bandit_vuln_delta"
    ]
    summary_df = summary_df[column_order] # Reorder columns

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
    
    if failed_repos > 0:
        sys.exit(1) # Indicate partial failure
        
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
