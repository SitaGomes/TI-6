# AI Refactoring Workflow

An automated workflow for analyzing and refactoring Python code using AI models, with concurrent processing for improved performance.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Command Reference](#command-reference)
- [Configuration](#configuration)
- [Performance Tuning](#performance-tuning)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

## Overview

This workflow automatically:

1. Fetches top Python repositories from GitHub
2. Detects code smells using local tools and AI
3. Generates missing tests
4. Refactors code to address identified issues
5. Analyzes the refactored code for improvements
6. Aggregates metrics and generates reports

## Features

- **Concurrent Processing**: 2-4x faster execution with parallel operations
- **AI-Powered Analysis**: Uses DeepSeek/OpenRouter for intelligent code analysis
- **Comprehensive Metrics**: Pylint, Radon, Pyright, Bandit analysis
- **Flexible Configuration**: Multiple configuration profiles and options
- **Rate Limiting**: Intelligent API rate limiting to respect limits
- **Progress Tracking**: Real-time progress updates and detailed logging

## Installation

### Prerequisites

```bash
# Python 3.8+
python3 --version

# Required tools
pip install pylint radon bandit pytest
npm install -g pyright  # or pip install pyright
```

### Dependencies

```bash
pip install openai github3.py concurrent.futures
```

### Environment Setup

Create a `.env` file in the `scripts/` directory:

```bash
# scripts/.env
GITHUB_TOKEN=your_github_token_here
```

## Quick Start

### Basic Usage

```bash
# Run the complete workflow with default settings
python3 main.py

# Process 5 repositories with concurrent processing
python3 main.py --num-repos 5 --max-concurrent-api 2
```

### Development Mode

```bash
# Fast testing with limited processing
python3 main.py \
  --num-repos 1 \
  --max-concurrent-api 1 \
  --max-concurrent-analysis 2
```

## Command Reference

### Main Workflow (`main.py`)

The primary script that orchestrates the entire workflow.

#### Basic Options

```bash
python3 main.py [OPTIONS]
```

| Option            | Type | Default | Description                                           |
| ----------------- | ---- | ------- | ----------------------------------------------------- |
| `-n, --num-repos` | int  | 1       | Number of repositories to fetch and process           |
| `--skip-fetch`    | flag | False   | Skip fetching, use existing repos in `original_code/` |
| `--skip-cleanup`  | flag | False   | Skip deleting directories at the end                  |
| `--start-from`    | str  | "01"    | Start from specific step (02, 03, 04, 05, 06)         |

#### Concurrency Options

| Option                      | Type | Default | Description                              |
| --------------------------- | ---- | ------- | ---------------------------------------- |
| `--max-concurrent-repos`    | int  | 3       | Maximum concurrent repository clones     |
| `--max-concurrent-api`      | int  | 2       | Maximum concurrent AI API calls          |
| `--max-concurrent-analysis` | int  | 4       | Maximum concurrent static analysis tools |
| `--api-rate-limit`          | int  | 60      | API rate limit per minute                |

#### Examples

```bash
# Conservative settings for free API tiers
python3 main.py \
  --num-repos 3 \
  --max-concurrent-repos 2 \
  --max-concurrent-api 1 \
  --max-concurrent-analysis 2 \
  --api-rate-limit 30

# Balanced performance
python3 main.py \
  --num-repos 10 \
  --max-concurrent-repos 5 \
  --max-concurrent-api 3 \
  --max-concurrent-analysis 6 \
  --api-rate-limit 120

# High performance
python3 main.py \
  --num-repos 20 \
  --max-concurrent-repos 10 \
  --max-concurrent-api 8 \
  --max-concurrent-analysis 12 \
  --api-rate-limit 300

# Resume from specific step
python3 main.py --skip-fetch --start-from 04

# Skip cleanup for debugging
python3 main.py --skip-cleanup
```

### Individual Scripts

Each step can be run independently for testing or debugging.

#### 1. Repository Fetching (`scripts/fetch_repos.py`)

```bash
python3 scripts/fetch_repos.py
```

**Configuration**: Edit `NUM_REPOS` variable in the script.

#### 2. Local Smell Detection (`scripts/detect_smells_local.py`)

```bash
python3 scripts/detect_smells_local.py REPO_NAME
```

**Arguments**:

- `REPO_NAME`: Name of repository directory in `original_code/`

#### 3. AI Smell Detection (`scripts/detect_smells_ai.py`)

```bash
python3 scripts/detect_smells_ai.py REPO_NAME [OPTIONS]
```

**Arguments**:

- `REPO_NAME`: Name of repository directory

**Options**:
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--max-concurrent` | int | 2 | Maximum concurrent API calls |

**Examples**:

```bash
# Basic usage
python3 scripts/detect_smells_ai.py my-repo

# With concurrent processing
python3 scripts/detect_smells_ai.py my-repo --max-concurrent 4
```

#### 4. Smell Comparison (`scripts/compare_smells.py`)

```bash
python3 scripts/compare_smells.py REPO_NAME
```

#### 5. Test Generation (`scripts/generate_tests.py`)

```bash
python3 scripts/generate_tests.py REPO_NAME [OPTIONS]
```

**Options**:
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--max-concurrent` | int | 2 | Maximum concurrent API calls |

**Examples**:

```bash
# Generate tests with default concurrency
python3 scripts/generate_tests.py my-repo

# Generate tests with higher concurrency
python3 scripts/generate_tests.py my-repo --max-concurrent 5
```

#### 6. Code Refactoring (`scripts/refactor_code.py`)

```bash
python3 scripts/refactor_code.py REPO_NAME
```

#### 7. Post-Refactor Analysis (`scripts/analyze_refactored.py`)

```bash
python3 scripts/analyze_refactored.py REPO_NAME [OPTIONS]
```

**Options**:
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--max-concurrent` | int | 4 | Maximum concurrent analysis tools |

**Examples**:

```bash
# Analyze with default concurrency
python3 scripts/analyze_refactored.py my-repo

# Analyze with higher concurrency
python3 scripts/analyze_refactored.py my-repo --max-concurrent 8
```

#### 8. Metrics Aggregation (`scripts/aggregate_metrics.py`)

```bash
python3 scripts/aggregate_metrics.py
```

### Utility Scripts

#### Performance Benchmarking

```bash
# Run performance benchmarks
python3 benchmark_concurrent.py
```

This script demonstrates the performance improvements of concurrent processing.

#### Configuration Testing

```bash
# Test concurrent utilities
python3 -c "from scripts.utils import process_items_concurrently; print('Testing...'); results = process_items_concurrently([1,2,3], lambda x: x*2, max_workers=2); print('Results:', results)"
```

## Configuration

### Configuration Profiles (`config.py`)

Use predefined configuration profiles:

```python
# Apply development configuration
from config import apply_config
apply_config("dev")

# Apply production configuration
apply_config("prod")

# Apply high-performance configuration
apply_config("high_perf")
```

### Profile Details

#### Development Profile (`dev`)

- **Use case**: Testing, development, free API tiers
- **Settings**: Conservative concurrency, limited file processing

```python
DEV_CONFIG = {
    "MAX_CONCURRENT_REPOS": 2,
    "MAX_CONCURRENT_API_CALLS": 1,
    "MAX_CONCURRENT_ANALYSIS": 2,
    "API_RATE_LIMIT_PER_MINUTE": 30,
    "MAX_FILES_PER_REPO": 5,
    "DEFAULT_NUM_REPOS": 1
}
```

#### Production Profile (`prod`)

- **Use case**: Regular production use, paid API tiers
- **Settings**: Balanced performance and resource usage

```python
PROD_CONFIG = {
    "MAX_CONCURRENT_REPOS": 5,
    "MAX_CONCURRENT_API_CALLS": 5,
    "MAX_CONCURRENT_ANALYSIS": 8,
    "API_RATE_LIMIT_PER_MINUTE": 120,
    "MAX_FILES_PER_REPO": None,
    "DEFAULT_NUM_REPOS": 10
}
```

#### High Performance Profile (`high_perf`)

- **Use case**: High-end systems, premium API tiers
- **Settings**: Maximum concurrency and throughput

```python
HIGH_PERF_CONFIG = {
    "MAX_CONCURRENT_REPOS": 10,
    "MAX_CONCURRENT_API_CALLS": 10,
    "MAX_CONCURRENT_ANALYSIS": 16,
    "API_RATE_LIMIT_PER_MINUTE": 300,
    "MAX_FILES_PER_REPO": None,
    "DEFAULT_NUM_REPOS": 50
}
```

### Environment Variables

Set these in your environment or `.env` file:

```bash
# Required
GITHUB_TOKEN=your_github_token

# Optional (for custom API endpoints)
DEEPSEEK_API_KEY=your_api_key
OPENAI_BASE_URL=http://localhost:11434/v1
```

## Performance Tuning

### System Requirements

#### Minimum Requirements

- **CPU**: 2 cores
- **RAM**: 4GB
- **Network**: Stable internet connection
- **API**: Basic tier with rate limiting

#### Recommended for Optimal Performance

- **CPU**: 8+ cores
- **RAM**: 16GB+
- **Network**: High-bandwidth connection
- **API**: Paid tier with higher rate limits

### Concurrency Guidelines

#### For Free API Tiers

```bash
--max-concurrent-api 1
--api-rate-limit 30
--max-concurrent-repos 2
--max-concurrent-analysis 2
```

#### For Paid API Tiers

```bash
--max-concurrent-api 5
--api-rate-limit 120
--max-concurrent-repos 5
--max-concurrent-analysis 8
```

#### For High-Performance Systems

```bash
--max-concurrent-api 10
--api-rate-limit 300
--max-concurrent-repos 10
--max-concurrent-analysis 16
```

### Finding Optimal Settings

1. **Start Conservative**:

   ```bash
   python3 main.py --max-concurrent-api 1 --max-concurrent-analysis 2
   ```

2. **Monitor Resources**:

   ```bash
   # Monitor CPU and memory
   htop

   # Monitor network
   iftop
   ```

3. **Gradually Increase**:

   ```bash
   python3 main.py --max-concurrent-api 2 --max-concurrent-analysis 4
   ```

4. **Check API Usage**: Monitor your API provider's dashboard for rate limit usage.

## Examples

### Complete Workflow Examples

#### Example 1: Quick Test Run

```bash
# Process 1 repository with minimal concurrency
python3 main.py \
  --num-repos 1 \
  --max-concurrent-api 1 \
  --max-concurrent-analysis 2
```

#### Example 2: Production Run

```bash
# Process 10 repositories with balanced settings
python3 main.py \
  --num-repos 10 \
  --max-concurrent-repos 5 \
  --max-concurrent-api 3 \
  --max-concurrent-analysis 6 \
  --api-rate-limit 120
```

#### Example 3: High-Performance Run

```bash
# Process 20 repositories with maximum concurrency
python3 main.py \
  --num-repos 20 \
  --max-concurrent-repos 10 \
  --max-concurrent-api 8 \
  --max-concurrent-analysis 12 \
  --api-rate-limit 300
```

#### Example 4: Resume Interrupted Workflow

```bash
# Skip fetching and start from test generation
python3 main.py \
  --skip-fetch \
  --start-from 04 \
  --max-concurrent-api 3
```

#### Example 5: Debug Mode

```bash
# Run with cleanup disabled for debugging
python3 main.py \
  --num-repos 2 \
  --skip-cleanup \
  --max-concurrent-api 1
```

### Individual Script Examples

#### Analyze Specific Repository

```bash
# Run AI smell detection on a specific repo
python3 scripts/detect_smells_ai.py tensorflow --max-concurrent 3

# Generate tests for a specific repo
python3 scripts/generate_tests.py tensorflow --max-concurrent 2

# Analyze refactored code
python3 scripts/analyze_refactored.py tensorflow --max-concurrent 6
```

#### Batch Processing

```bash
# Process multiple repositories individually
for repo in repo1 repo2 repo3; do
  python3 scripts/detect_smells_ai.py $repo --max-concurrent 2
done
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Rate Limit Errors

**Symptoms**: API errors, "Rate limit exceeded" messages
**Solutions**:

```bash
# Reduce API concurrency
--max-concurrent-api 1

# Increase rate limit delay
--api-rate-limit 30

# Check your API subscription limits
```

#### 2. Memory Issues

**Symptoms**: Out of memory errors, system slowdown
**Solutions**:

```bash
# Reduce analysis concurrency
--max-concurrent-analysis 2

# Process fewer repositories
--num-repos 3

# Limit file processing (edit config.py)
MAX_FILES_PER_REPO = 10
```

#### 3. Network Timeouts

**Symptoms**: Git clone failures, connection timeouts
**Solutions**:

```bash
# Reduce repository concurrency
--max-concurrent-repos 2

# Check network stability
ping github.com

# Use shallow clones (default in fetch_repos.py)
```

#### 4. Tool Not Found Errors

**Symptoms**: "command not found" errors
**Solutions**:

```bash
# Install missing tools
pip install pylint radon bandit pytest
npm install -g pyright

# Check PATH
which pylint
which pyright
```

#### 5. Permission Errors

**Symptoms**: File permission errors
**Solutions**:

```bash
# Check directory permissions
ls -la original_code/
ls -la refactored_code/

# Fix permissions if needed
chmod -R 755 original_code/
```

### Debug Mode

Enable verbose logging for debugging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or set in environment:

```bash
export PYTHONPATH=/path/to/project
python3 -c "import logging; logging.basicConfig(level=logging.DEBUG); exec(open('main.py').read())"
```

### Performance Monitoring

Monitor system resources during execution:

```bash
# Terminal 1: Run the workflow
python3 main.py --num-repos 5

# Terminal 2: Monitor resources
watch -n 1 'ps aux | grep python; free -h; df -h'
```

## Output Structure

The workflow creates the following directory structure:

```
project/
├── original_code/          # Cloned repositories
│   ├── repo1/
│   └── repo2/
├── refactored_code/        # Refactored versions
│   ├── zero_shot/
│   ├── one_shot/
│   └── cot/
├── metrics/                # Analysis results
│   ├── repo1/
│   │   ├── smells_deepseek.json
│   │   ├── pylint.json
│   │   └── ...
│   └── aggregated_metrics.csv
└── logs/                   # Log files (if configured)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Add your license information here]

## Support

For issues and questions:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review the logs for error details
3. Open an issue with detailed information about your setup and the problem
