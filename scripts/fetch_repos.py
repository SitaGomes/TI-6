"""
Step 1: Fetch Top N Python Repositories from GitHub.
"""

import os
import subprocess
from github import Github
from utils import (
    get_github_token, ORIGINAL_CODE_DIR, ensure_dir, 
    process_items_concurrently, DEFAULT_MAX_CONCURRENT_REPOS
)
import sys
import logging

NUM_REPOS = 30 # Increased from 1 to fetch 30 repos for analysis

log = logging.getLogger(__name__)

def clone_repository(repo_info):
    """Clone a single repository. Used for concurrent processing."""
    repo, target_path = repo_info
    
    if os.path.exists(target_path):
        log.info(f"Repository {repo.name} already exists. Skipping clone.")
        return {"status": "exists", "repo_name": repo.full_name, "path": target_path}

    try:
        # Use subprocess to run git clone
        # Consider adding --depth 1 for faster clones if full history isn't needed
        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo.clone_url, target_path], 
            check=True, 
            capture_output=True, 
            text=True,
            timeout=300  # 5 minute timeout per clone
        )
        log.info(f"Successfully cloned {repo.full_name} to {target_path}")
        return {"status": "cloned", "repo_name": repo.full_name, "path": target_path}
    except subprocess.TimeoutExpired:
        log.error(f"Timeout cloning {repo.full_name}")
        return {"status": "timeout", "repo_name": repo.full_name, "path": target_path, "error": "Timeout"}
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else str(e)
        log.error(f"Failed to clone {repo.full_name}. Error: {error_msg}")
        return {"status": "failed", "repo_name": repo.full_name, "path": target_path, "error": error_msg}
    except Exception as e:
        log.error(f"An unexpected error occurred while cloning {repo.full_name}: {e}")
        return {"status": "error", "repo_name": repo.full_name, "path": target_path, "error": str(e)}

def fetch_repos(token: str, num_repos: int, max_concurrent_clones: int = None):
    """Fetches and clones the top N starred Python repositories concurrently."""
    if max_concurrent_clones is None:
        max_concurrent_clones = min(DEFAULT_MAX_CONCURRENT_REPOS, num_repos)
    
    g = Github(token)
    repo_list = []
    repos_to_clone = []

    log.info(f"Searching for the top {num_repos} starred Python repositories...")
    repositories = g.search_repositories(query="language:python", sort="stars", order="desc")

    ensure_dir(ORIGINAL_CODE_DIR)

    # Collect repositories to clone
    collected_count = 0
    for repo in repositories:
        if collected_count >= num_repos:
            break

        if not repo.fork and not repo.archived:
            log.info(f"Found repository: {repo.full_name} (Stars: {repo.stargazers_count})")
            target_path = os.path.join(ORIGINAL_CODE_DIR, repo.name)
            repos_to_clone.append((repo, target_path))
            collected_count += 1
        else:
            log.debug(f"Skipping repository: {repo.full_name} (Fork: {repo.fork}, Archived: {repo.archived})")

    if not repos_to_clone:
        log.error("No suitable repositories found to clone.")
        return []

    log.info(f"Starting concurrent cloning of {len(repos_to_clone)} repositories with {max_concurrent_clones} workers...")

    # Progress callback
    def progress_callback(completed, total):
        log.info(f"Cloning progress: {completed}/{total} repositories processed")

    # Error callback
    def error_callback(repo_info, error):
        repo, target_path = repo_info
        log.error(f"Failed to process {repo.full_name}: {error}")

    # Clone repositories concurrently
    results = process_items_concurrently(
        repos_to_clone,
        clone_repository,
        max_workers=max_concurrent_clones,
        executor_type="thread",  # I/O bound operation
        progress_callback=progress_callback,
        error_callback=error_callback
    )

    # Process results
    successful_clones = []
    failed_clones = []
    
    for (repo, target_path), result, error in results:
        if error:
            failed_clones.append(repo.full_name)
            continue
            
        if result and result["status"] in ["cloned", "exists"]:
            successful_clones.append(result["repo_name"])
            repo_list.append(result["repo_name"])
        else:
            failed_clones.append(repo.full_name)

    # Summary
    log.info(f"\n--- Cloning Summary ---")
    log.info(f"Successfully processed: {len(successful_clones)}/{len(repos_to_clone)} repositories")
    log.info(f"Failed: {len(failed_clones)} repositories")
    
    if failed_clones:
        log.warning(f"Failed repositories: {', '.join(failed_clones)}")
    
    if len(successful_clones) < num_repos:
        log.warning(f"Only processed {len(successful_clones)} repositories out of the requested {num_repos}.")
        
    log.info("Finished fetching repositories.")
    return repo_list # Return list of successfully processed repo names (full_name)

def main():
    """Main function to fetch repos and return their names."""
    try:
        github_token = get_github_token()
        # Use NUM_REPOS defined at the top of the file
        successfully_cloned = fetch_repos(github_token, NUM_REPOS) 
        log.info("\nSuccessfully processed repositories:")
        for repo_name in successfully_cloned:
            log.info(f"- {repo_name}")
        return successfully_cloned # Return the list of names
    except ValueError as e:
        log.error(f"Error: {e}")
        return [] # Return empty list on error
    except Exception as e:
        log.error(f"An unexpected error occurred: {e}")
        return [] # Return empty list on error

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # When run directly, just execute main, output handled within
    fetched_repo_names = main()
    if not fetched_repo_names:
        sys.exit(1)
