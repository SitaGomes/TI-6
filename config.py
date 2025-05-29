"""
Configuration file for the AI refactoring workflow.
Adjust these settings based on your system resources and API limits.
"""

# --- Repository Processing ---
# Number of repositories to fetch and process by default
DEFAULT_NUM_REPOS = 1

# --- Concurrency Settings ---
# Maximum number of concurrent repository clones
# Increase this if you have good network bandwidth and want faster cloning
MAX_CONCURRENT_REPOS = 3

# Maximum number of concurrent AI API calls
# Adjust based on your API rate limits and subscription tier
# For free tiers, keep this low (1-2)
# For paid tiers, you can increase (5-10)
MAX_CONCURRENT_API_CALLS = 2

# Maximum number of concurrent static analysis tools
# Adjust based on your CPU cores and memory
# Generally safe to set to number of CPU cores
MAX_CONCURRENT_ANALYSIS = 4

# --- API Rate Limiting ---
# Maximum API calls per minute
# Adjust based on your API provider's limits
API_RATE_LIMIT_PER_MINUTE = 60

# --- File Processing Limits ---
# Maximum file size to process (in bytes)
# Large files can be expensive to process with AI
MAX_FILE_SIZE_BYTES = 100 * 1024  # 100 KB

# Maximum number of files to process per repository
# Set to None to process all files, or a number to limit for testing/cost control
MAX_FILES_PER_REPO = None

# --- Performance Tuning ---
# Git clone depth (set to 1 for shallow clones to save time/space)
GIT_CLONE_DEPTH = 1

# Timeout for individual operations (in seconds)
GIT_CLONE_TIMEOUT = 300  # 5 minutes
PYTEST_TIMEOUT = 300     # 5 minutes
ANALYSIS_TOOL_TIMEOUT = 180  # 3 minutes

# --- Logging ---
# Log level: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL = "INFO"

# --- Model Configuration ---
# AI model to use (adjust based on your setup)
AI_MODEL = "deepseek-r1:1.5b"

# --- Directory Configuration ---
ORIGINAL_CODE_DIR = "original_code"
REFACTORED_CODE_DIR = "refactored_code"
METRICS_DIR = "metrics"

# --- Example configurations for different scenarios ---

# Configuration for development/testing (fast, limited processing)
DEV_CONFIG = {
    "MAX_CONCURRENT_REPOS": 2,
    "MAX_CONCURRENT_API_CALLS": 1,
    "MAX_CONCURRENT_ANALYSIS": 2,
    "API_RATE_LIMIT_PER_MINUTE": 30,
    "MAX_FILES_PER_REPO": 5,
    "DEFAULT_NUM_REPOS": 1
}

# Configuration for production (balanced performance)
PROD_CONFIG = {
    "MAX_CONCURRENT_REPOS": 5,
    "MAX_CONCURRENT_API_CALLS": 5,
    "MAX_CONCURRENT_ANALYSIS": 8,
    "API_RATE_LIMIT_PER_MINUTE": 120,
    "MAX_FILES_PER_REPO": None,
    "DEFAULT_NUM_REPOS": 10
}

# Configuration for high-performance systems (maximum speed)
HIGH_PERF_CONFIG = {
    "MAX_CONCURRENT_REPOS": 10,
    "MAX_CONCURRENT_API_CALLS": 10,
    "MAX_CONCURRENT_ANALYSIS": 16,
    "API_RATE_LIMIT_PER_MINUTE": 300,
    "MAX_FILES_PER_REPO": None,
    "DEFAULT_NUM_REPOS": 50
}

def apply_config(config_name="default"):
    """Apply a predefined configuration."""
    import sys
    current_module = sys.modules[__name__]
    
    if config_name == "dev":
        config = DEV_CONFIG
    elif config_name == "prod":
        config = PROD_CONFIG
    elif config_name == "high_perf":
        config = HIGH_PERF_CONFIG
    else:
        return  # Use default values
    
    for key, value in config.items():
        setattr(current_module, key, value)

# Usage example:
# from config import apply_config
# apply_config("dev")  # Apply development configuration 