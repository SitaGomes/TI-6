"""
Step 1: Fetch Top N Python Repositories from GitHub.
"""

import os
import subprocess
from github import Github
from utils import get_github_token, ORIGINAL_CODE_DIR, ensure_dir

NUM_REPOS = 1 # As requested, start with 1 repo for testing

def fetch_repos(token: str, num_repos: int):
    """Fetches and clones the top N starred Python repositories."""
    g = Github(token)
    cloned_count = 0
    repo_list = []

    print(f"Searching for the top {num_repos} starred Python repositories...")
    repositories = g.search_repositories(query="language:python", sort="stars", order="desc")

    ensure_dir(ORIGINAL_CODE_DIR)

    for repo in repositories:
        if cloned_count >= num_repos:
            break

        if not repo.fork and not repo.archived:
            print(f"Found repository: {repo.full_name} (Stars: {repo.stargazers_count}) - Cloning...")
            clone_url = repo.clone_url
            repo_name = repo.name
            target_path = os.path.join(ORIGINAL_CODE_DIR, repo_name)

            if os.path.exists(target_path):
                print(f"Repository {repo_name} already exists. Skipping clone.")
                repo_list.append(repo.full_name)
                cloned_count += 1
                continue

            try:
                # Use subprocess to run git clone
                # Consider adding --depth 1 for faster clones if full history isn't needed
                subprocess.run(["git", "clone", clone_url, target_path], check=True, capture_output=True)
                print(f"Successfully cloned {repo.full_name} to {target_path}")
                repo_list.append(repo.full_name)
                cloned_count += 1
            except subprocess.CalledProcessError as e:
                print(f"Failed to clone {repo.full_name}. Error: {e.stderr.decode()}")
            except Exception as e:
                 print(f"An unexpected error occurred while cloning {repo.full_name}: {e}")
        else:
            print(f"Skipping repository: {repo.full_name} (Fork: {repo.fork}, Archived: {repo.archived})")
            
    if cloned_count < num_repos:
        print(f"Warning: Only cloned {cloned_count} repositories out of the requested {num_repos}.")
        
    print("\nFinished fetching repositories.")
    return repo_list # Return list of successfully processed repo names (full_name)

if __name__ == "__main__":
    try:
        github_token = get_github_token()
        successfully_cloned = fetch_repos(github_token, NUM_REPOS)
        print("\nSuccessfully processed repositories:")
        for repo_name in successfully_cloned:
            print(f"- {repo_name}")
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
