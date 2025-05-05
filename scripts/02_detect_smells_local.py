"""
Step 2: Detect Code Smells using Local Libraries (Pylint, Radon).
"""

import os
import subprocess
import json
import sys
from utils import ORIGINAL_CODE_DIR, METRICS_DIR, ensure_dir, save_json

def run_analysis_tool(command: list, output_file: str, repo_path: str):
    """Runs a static analysis tool command and saves the output."""
    print(f"Running command: {' '.join(command)}")
    try:
        # Pylint might exit with non-zero status even if JSON is generated (e.g., errors found)
        # Capture stdout directly. Radon might print to stderr on errors.
        # We will attempt to capture stdout and save it, checking stderr for fatal errors.
        result = subprocess.run(command, cwd='.', capture_output=True, text=True, encoding='utf-8', check=False) # Don't check=True initially

        # Check stderr for actual execution errors (tool not found, etc.)
        if "command not found" in result.stderr.lower() or "No such file or directory" in result.stderr:
             print(f"Error running {' '.join(command)}: {result.stderr}", file=sys.stderr)
             return False
        elif result.returncode != 0 and not result.stdout:
            # If there was a non-zero exit code AND no stdout produced, likely a real error
            print(f"Error running {' '.join(command)} (Exit Code: {result.returncode}): {result.stderr}", file=sys.stderr)
            return False

        # Attempt to save stdout (which should be JSON if successful)
        try:
            # Ensure the output is valid JSON before saving
            parsed_json = json.loads(result.stdout)
            save_json(parsed_json, output_file)
            print(f"Successfully saved output to {output_file}")
            return True
        except json.JSONDecodeError:
            print(f"Warning: Output from {' '.join(command)} was not valid JSON. Saving raw output.")
            print(f"Stdout:\n{result.stdout}")
            print(f"Stderr:\n{result.stderr}")
            ensure_dir(os.path.dirname(output_file))
            output_file_raw = output_file.replace('.json', '.txt')
            with open(output_file_raw, 'w', encoding='utf-8') as f:
                f.write(f"--- STDOUT ---\n{result.stdout}\n--- STDERR ---\n{result.stderr}")
            print(f"Raw output saved to {output_file_raw}")
            # Consider if this should be treated as a failure depending on strictness
            return False # Treat invalid JSON as failure for now
        except Exception as e:
            print(f"Error saving output to {output_file}: {e}", file=sys.stderr)
            print(f"Stdout:\n{result.stdout}")
            print(f"Stderr:\n{result.stderr}")
            return False
            
    except FileNotFoundError:
        print(f"Error: Command '{command[0]}' not found. Make sure it's installed and in PATH.", file=sys.stderr)
        return False
    except Exception as e:
        print(f"An unexpected error occurred while running {' '.join(command)}: {e}", file=sys.stderr)
        return False


def analyze_repository(repo_name: str):
    """Runs Pylint and Radon on a specific repository."""
    repo_path = os.path.join(ORIGINAL_CODE_DIR, repo_name)
    if not os.path.isdir(repo_path):
        print(f"Error: Repository directory not found: {repo_path}", file=sys.stderr)
        return False

    metrics_repo_dir = os.path.join(METRICS_DIR, repo_name)
    ensure_dir(metrics_repo_dir)

    print(f"\n--- Analyzing Repository: {repo_name} ---")

    # 1. Run Pylint
    pylint_output_file = os.path.join(metrics_repo_dir, "smells_lib_pylint.json")
    # Use '--recursive=y' if pylint version supports it, otherwise rely on path target
    pylint_command = [
        sys.executable, # Use the current python executable to run the module
        "-m", 
        "pylint", 
        repo_path, 
        "--output-format=json",
        "--recursive=y", # Attempt recursive analysis
        # Add '--load-plugins pylint.extensions.json_reporter' if needed, but output-format=json should suffice
        # Disable specific messages or categories if needed, e.g. --disable=C0114,C0115,C0116 for missing docstrings
        "--disable=C0114,C0115,C0116,R0903", # Disable missing-docstring, too-few-public-methods
        "--exit-zero" # Ensure pylint exits with 0 even if issues are found, rely on JSON output
    ]
    print("Running Pylint...")
    pylint_success = run_analysis_tool(pylint_command, pylint_output_file, repo_path)
    if not pylint_success:
        print(f"Pylint analysis failed for {repo_name}. See errors above.")
        # Decide if we should stop or continue with Radon

    # 2. Run Radon (Cyclomatic Complexity)
    # Note: README mentioned 'smells_lib_radon.json'. Running cc and mi separately might be better,
    # but sticking to README for now. Radon cc -j provides complexity per function/method.
    radon_cc_output_file = os.path.join(metrics_repo_dir, "smells_lib_radon_cc.json") # Changed name for clarity
    radon_command = [
        sys.executable, 
        "-m",
        "radon", 
        "cc", 
        repo_path, 
        "-s", # Show average complexity
        "-j"  # JSON output
        # Consider -a for average complexity if needed in summary later
    ]
    print("\nRunning Radon CC...")
    radon_success_cc = run_analysis_tool(radon_command, radon_cc_output_file, repo_path)
    if not radon_success_cc:
        print(f"Radon CC analysis failed for {repo_name}. See errors above.")

    # 3. Run Radon (Maintainability Index)
    radon_mi_output_file = os.path.join(metrics_repo_dir, "radon_mi.json") # Added MI output
    radon_mi_command = [
        sys.executable,
        "-m",
        "radon",
        "mi",
        repo_path,
        "-s", # Show average MI
        "-j"  # JSON output
    ]
    print("\nRunning Radon MI...")
    radon_success_mi = run_analysis_tool(radon_mi_command, radon_mi_output_file, repo_path)
    if not radon_success_mi:
        print(f"Radon MI analysis failed for {repo_name}. See errors above.")

    print(f"--- Finished Analyzing: {repo_name} ---")
    # Return overall success status
    return pylint_success and radon_success_cc and radon_success_mi 

if __name__ == "__main__":
    if not os.path.exists(ORIGINAL_CODE_DIR) or not os.listdir(ORIGINAL_CODE_DIR):
        print(f"Error: '{ORIGINAL_CODE_DIR}' directory is empty or does not exist.", file=sys.stderr)
        print(f"Please run '01_fetch_repos.py' first.", file=sys.stderr)
        sys.exit(1)

    processed_repo_count = 0
    failed_repo_count = 0
    # Iterate through all directories in original_code/ (for future N>1)
    for repo_name in os.listdir(ORIGINAL_CODE_DIR):
        repo_full_path = os.path.join(ORIGINAL_CODE_DIR, repo_name)
        if os.path.isdir(repo_full_path):
            if analyze_repository(repo_name):
                processed_repo_count += 1
            else:
                failed_repo_count += 1
        else:
             print(f"Skipping non-directory item: {repo_name}")


    print("\n--- Local Smell Detection Summary ---")
    print(f"Successfully analyzed: {processed_repo_count} repositories")
    print(f"Failed to analyze:    {failed_repo_count} repositories")
    
    if failed_repo_count > 0:
         sys.exit(1) # Exit with error if any repo failed
