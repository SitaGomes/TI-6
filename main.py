import subprocess
import json
import csv
import os
import logging
import sys

# --- Configuration ---
ORIGINAL_DIR = "original_code"
REFACTORED_DIR = "refactored_code"
OUTPUT_DIR = "analysis_output" # Directory to store intermediate JSON results
CSV_REPORT_FILE = "analysis_results.csv"

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Helper Functions ---

def ensure_dir(directory_path):
    """Creates a directory if it doesn't exist."""
    os.makedirs(directory_path, exist_ok=True)

def run_command(command, cwd=None, check=True):
    """Runs a shell command and logs output/errors."""
    logging.info(f"Running command: {' '.join(command)}")
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=cwd,
            check=check  # Raises CalledProcessError if command fails
        )
        logging.debug(f"Command stdout:\n{result.stdout}")
        if result.stderr:
            logging.warning(f"Command stderr:\n{result.stderr}")
        return result.stdout
    except FileNotFoundError:
        logging.error(f"Error: Command '{command[0]}' not found. Is it installed and in PATH?")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed with exit code {e.returncode}: {' '.join(command)}")
        logging.error(f"Stderr: {e.stderr}")
        logging.error(f"Stdout: {e.stdout}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"An unexpected error occurred while running command: {e}")
        sys.exit(1)

def run_analysis_tool(tool_command, output_file):
    """Runs an analysis tool command, handling JSON output either via stdout or direct file write."""
    ensure_dir(os.path.dirname(output_file))
    tool_name = tool_command[0]

    # Case 1: Tool uses -o/--output to write directly to the file (e.g., Bandit)
    if '-o' in tool_command or '--output' in tool_command:
        logging.info(f"Running {tool_name} which writes directly to {output_file}")
        try:
            # Run command; run_command handles check=True and will raise on non-zero exit
            run_command(tool_command)

            # Check if the file is empty, but don't fail the step here.
            # load_json_safe will handle empty/missing files later.
            try:
                if os.path.getsize(output_file) == 0:
                    logging.warning(f"Output file {output_file} was created by {tool_name} but is empty.")
            except FileNotFoundError:
                # This shouldn't happen if run_command succeeded with check=True,
                # but log it just in case. load_json_safe will handle this.
                logging.warning(f"Output file {output_file} not found after {tool_name} command, though command succeeded.")

            logging.info(f"{tool_name} command finished. Output expected in {output_file}")
            return True # Indicate success if command execution didn't raise error

        except Exception as e:
            # Catch exceptions from run_command (like CalledProcessError)
            logging.error(f"Error running {tool_name} command directly: {e}")
            return False

    # Case 2: Tool writes JSON to stdout (e.g., Radon -j)
    # Note: Pylint is handled separately in main() due to its exit code behavior
    elif '-j' in tool_command and tool_name == 'radon':
        logging.info(f"Running {tool_name} expecting JSON output to stdout")
        try:
            stdout_content = run_command(tool_command)
            # Validate JSON before writing
            json.loads(stdout_content)
            with open(output_file, 'w') as f:
                f.write(stdout_content)
            logging.info(f"Successfully wrote {tool_name} stdout JSON to {output_file}")
            return True
        except json.JSONDecodeError:
            logging.error(f"{tool_name} command stdout did not produce valid JSON for {output_file}.")
            # Optionally log part of the invalid output for debugging
            # logging.debug(f"Invalid stdout content: {stdout_content[:200]}...")
            return False
        except Exception as e:
            # Catch other errors during run_command or file writing
            logging.error(f"Error processing {tool_name} stdout: {e}")
            return False

    else:
        # This case should ideally not be hit for Radon/Bandit/Pylint
        logging.error(f"Command structure not recognized by run_analysis_tool: {' '.join(tool_command)}")
        return False

def load_json_safe(path):
    """Loads JSON from a file, handling errors gracefully."""
    try:
        with open(path, 'r') as file:
            # Handle potentially empty files from failed runs
            content = file.read()
            if not content:
                 logging.warning(f"JSON file is empty: {path}")
                 return None
            return json.loads(content)
    except FileNotFoundError:
        logging.error(f"JSON file not found: {path}")
        return None
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from file: {path}")
        return None
    except Exception as e:
        logging.error(f"Error reading file {path}: {e}")
        return None

def calculate_average_complexity(radon_cc_data):
    """Calculates average cyclomatic complexity from Radon cc JSON data."""
    if not radon_cc_data or not isinstance(radon_cc_data, dict):
        return 0.0
    complexities = [details.get("complexity", 0) for details in radon_cc_data.values() if isinstance(details, dict)]
    if not complexities:
        return 0.0
    return sum(complexities) / len(complexities)

def calculate_average_mi(radon_mi_data):
    """Calculates average maintainability index from Radon mi JSON data."""
    if not radon_mi_data or not isinstance(radon_mi_data, dict):
        return 0.0
    indices = [details.get("mi", 0.0) for details in radon_mi_data.values() if isinstance(details, dict)]
    if not indices:
        return 0.0
    return sum(indices) / len(indices)

def count_bandit_vulnerabilities(bandit_data):
    """Counts vulnerabilities from Bandit JSON data."""
    if not bandit_data or "results" not in bandit_data:
        return 0
    return len(bandit_data.get("results", []))

def count_pylint_issues(pylint_data):
    """Counts issues from Pylint JSON data (list format)."""
    if not pylint_data or not isinstance(pylint_data, list):
        return 0
    return len(pylint_data)

# --- Main Execution ---

def main():
    ensure_dir(OUTPUT_DIR)
    results = {}
    analysis_successful = True # Start assuming success

    for version, code_dir in [("original", ORIGINAL_DIR), ("refactored", REFACTORED_DIR)]:
        logging.info(f"--- Starting analysis for {version} code ({code_dir}) ---")
        if not os.path.isdir(code_dir):
            logging.error(f"Directory not found: {code_dir}. Please create it and add code.")
            sys.exit(1)

        # Define output paths
        radon_cc_json = os.path.join(OUTPUT_DIR, f"radon_complex_{version}.json")
        radon_mi_json = os.path.join(OUTPUT_DIR, f"radon_mi_{version}.json")
        bandit_json = os.path.join(OUTPUT_DIR, f"bandit_{version}.json")
        pylint_json = os.path.join(OUTPUT_DIR, f"pylint_{version}.json")

        # Run Analyses using run_analysis_tool where appropriate
        logging.info("Running Radon CC...")
        success = run_analysis_tool(['radon', 'cc', code_dir, '-s', '-a', '-j'], radon_cc_json)
        if not success: analysis_successful = False

        logging.info("Running Radon MI...")
        # Check analysis_successful before proceeding (optional optimization)
        if analysis_successful:
            success = run_analysis_tool(['radon', 'mi', code_dir, '-s', '-j'], radon_mi_json)
            if not success: analysis_successful = False

        logging.info("Running Bandit...")
        if analysis_successful:
            bandit_command = ['bandit', '-r', code_dir, '-f', 'json', '-o', bandit_json]
            success = run_analysis_tool(bandit_command, bandit_json)
            if not success: analysis_successful = False

        # --- Special Handling for PyLint ---
        logging.info("Running PyLint...")
        pylint_success = False # Assume failure for this specific step first
        if analysis_successful: # Only run if previous steps were okay
            pylint_command = ['pylint', code_dir, '--output-format=json']
            try:
                # Run pylint directly, allow non-zero exit code (check=False)
                pylint_output = subprocess.run(pylint_command, capture_output=True, text=True, check=False)
                logging.debug(f"Pylint raw output for {version}:\n{pylint_output.stdout}")
                if pylint_output.stderr:
                    logging.warning(f"Pylint stderr for {version}:\n{pylint_output.stderr}")

                # Try to parse JSON even if exit code != 0
                try:
                    pylint_data_check = json.loads(pylint_output.stdout)
                    with open(pylint_json, 'w') as f:
                        f.write(pylint_output.stdout)
                    logging.info(f"Successfully wrote pylint output to {pylint_json}")
                    pylint_success = True # Pylint step succeeded
                except json.JSONDecodeError:
                    logging.error(f"Pylint did not produce valid JSON output for {version}.")
                    logging.error(f"Output was:\n{pylint_output.stdout}")
                    # Don't write the file, pylint_success remains False
                except Exception as e:
                     logging.error(f"Failed to write pylint output to {pylint_json}: {e}")
                     # pylint_success remains False

            except FileNotFoundError:
                logging.error("Error: Command 'pylint' not found. Is it installed and in PATH?")
                analysis_successful = False # Mark overall analysis as failed
            except Exception as e:
                logging.error(f"An unexpected error occurred while running pylint: {e}")
                analysis_successful = False # Mark overall analysis as failed

            # Update overall status ONLY IF pylint step specifically failed
            if not pylint_success:
                 analysis_successful = False
        # --- End Special Handling for PyLint ---


        # Load and Calculate Metrics only if all analyses were marked successful so far
        if analysis_successful:
            logging.info(f"Calculating metrics for {version}...")
            radon_cc_data = load_json_safe(radon_cc_json)
            radon_mi_data = load_json_safe(radon_mi_json)
            bandit_data = load_json_safe(bandit_json)
            pylint_data = load_json_safe(pylint_json) # Load even if pylint step failed, load_json_safe handles None

            results[version] = {
                "avg_complexity": calculate_average_complexity(radon_cc_data),
                "avg_mi": calculate_average_mi(radon_mi_data),
                "vulnerabilities": count_bandit_vulnerabilities(bandit_data),
                "pylint_issues": count_pylint_issues(pylint_data), # Will be 0 if pylint_data is None
            }
            logging.info(f"Metrics for {version}: {results[version]}")
        else:
            logging.warning(f"Skipping metric calculation for {version} due to earlier analysis failures.")
            # Ensure results dict has an entry to avoid errors later, but maybe with N/A values?
            results[version] = {
                "avg_complexity": "N/A",
                "avg_mi": "N/A",
                "vulnerabilities": "N/A",
                "pylint_issues": "N/A",
            }


    # Abort CSV generation if ANY analysis step failed
    if not analysis_successful:
         logging.error("One or more analysis steps failed or produced invalid output. CSV report generation aborted.")
         sys.exit(1) # Exit before CSV writing

    # --- Prepare and Write CSV Report ---
    # (This part should only be reached if analysis_successful is True)
    logging.info("Preparing data for CSV report...")
    csv_data = []
    metrics_keys = ["avg_complexity", "avg_mi", "vulnerabilities", "pylint_issues"]
    
    if "original" not in results or "refactored" not in results:
        logging.error("Could not retrieve results for both original and refactored versions. Aborting CSV generation.")
        sys.exit(1)

    for key in metrics_keys:
        original_val = results["original"].get(key, 0)
        refactored_val = results["refactored"].get(key, 0)
        
        # Calculate change safely
        change = refactored_val - original_val if original_val is not None and refactored_val is not None else "N/A"
        
        # Format floats nicely
        if isinstance(original_val, float): original_val = f"{original_val:.2f}"
        if isinstance(refactored_val, float): refactored_val = f"{refactored_val:.2f}"
        if isinstance(change, float): change = f"{change:.2f}"

        csv_data.append({
            "Metric": key,
            "Original": original_val,
            "Refactored": refactored_val,
            "Change": change
        })

    # Write CSV Report
    logging.info(f"Writing results to {CSV_REPORT_FILE}...")
    try:
        with open(CSV_REPORT_FILE, 'w', newline='') as csvfile:
            fieldnames = ["Metric", "Original", "Refactored", "Change"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            writer.writerows(csv_data)
        logging.info(f"Successfully created CSV report: {CSV_REPORT_FILE}")
    except IOError as e:
        logging.error(f"Error writing CSV file: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"An unexpected error occurred during CSV writing: {e}")
        sys.exit(1)

    logging.info("--- Analysis complete ---")


if __name__ == "__main__":
    main()
