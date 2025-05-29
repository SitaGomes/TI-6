# Concurrent Processing Features

This document describes the concurrent processing optimizations added to the AI refactoring workflow to significantly improve performance.

## Overview

The workflow now supports concurrent processing in several key areas:

1. **Repository Fetching**: Clone multiple repositories simultaneously
2. **AI API Calls**: Make multiple AI requests concurrently with rate limiting
3. **Static Analysis**: Run multiple analysis tools in parallel
4. **File Processing**: Process multiple files concurrently within each step

## Performance Improvements

With concurrent processing, you can expect:

- **3-5x faster repository cloning** (depending on network bandwidth)
- **2-4x faster AI analysis** (limited by API rate limits)
- **2-3x faster static analysis** (depending on CPU cores)
- **Overall workflow speedup of 2-4x** for typical workloads

## Configuration Options

### Command Line Arguments

The main script now accepts several concurrency options:

```bash
python main.py \
  --num-repos 5 \
  --max-concurrent-repos 3 \
  --max-concurrent-api 2 \
  --max-concurrent-analysis 4 \
  --api-rate-limit 60
```

### Configuration Profiles

Use predefined configuration profiles in `config.py`:

```python
# Development (fast, limited processing)
python -c "from config import apply_config; apply_config('dev')"

# Production (balanced performance)
python -c "from config import apply_config; apply_config('prod')"

# High Performance (maximum speed)
python -c "from config import apply_config; apply_config('high_perf')"
```

### Individual Script Options

Each script now supports concurrency options:

```bash
# Generate tests with 3 concurrent API calls
python scripts/generate_tests.py repo_name --max-concurrent 3

# Run analysis with 6 concurrent tools
python scripts/analyze_refactored.py repo_name --max-concurrent 6

# Detect smells with 2 concurrent API calls
python scripts/detect_smells_ai.py repo_name --max-concurrent 2
```

## Rate Limiting

The system includes intelligent rate limiting to respect API limits:

- **Automatic throttling**: Waits when approaching rate limits
- **Configurable limits**: Set your API's rate limit per minute
- **Thread-safe**: Safe for concurrent operations

```python
from utils import set_rate_limit
set_rate_limit(120)  # 120 calls per minute
```

## Recommended Settings

### For Free API Tiers

```bash
--max-concurrent-api 1 \
--api-rate-limit 30 \
--max-concurrent-repos 2 \
--max-concurrent-analysis 2
```

### For Paid API Tiers

```bash
--max-concurrent-api 5 \
--api-rate-limit 120 \
--max-concurrent-repos 5 \
--max-concurrent-analysis 8
```

### For High-Performance Systems

```bash
--max-concurrent-api 10 \
--api-rate-limit 300 \
--max-concurrent-repos 10 \
--max-concurrent-analysis 16
```

## System Requirements

### Minimum Requirements

- **CPU**: 2 cores
- **RAM**: 4GB
- **Network**: Stable internet connection
- **API**: Basic tier with rate limiting

### Recommended for Optimal Performance

- **CPU**: 8+ cores
- **RAM**: 16GB+
- **Network**: High-bandwidth connection
- **API**: Paid tier with higher rate limits

## Monitoring and Debugging

### Progress Tracking

The system provides real-time progress updates:

```
2024-01-15 10:30:15 - INFO - Cloning progress: 3/5 repositories processed
2024-01-15 10:30:20 - INFO - Analysis progress: 4/5 tools completed
2024-01-15 10:30:25 - INFO - Progress: 15/20 completed
```

### Error Handling

Concurrent operations include robust error handling:

- **Individual failures don't stop the workflow**
- **Detailed error logging for debugging**
- **Graceful degradation when resources are limited**

### Logging Configuration

Adjust logging level for debugging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)  # Verbose output
logging.basicConfig(level=logging.INFO)   # Standard output
logging.basicConfig(level=logging.WARNING) # Minimal output
```

## Troubleshooting

### Common Issues

1. **Rate Limit Errors**

   - Reduce `--max-concurrent-api`
   - Increase `--api-rate-limit` delay
   - Check your API subscription limits

2. **Memory Issues**

   - Reduce `--max-concurrent-analysis`
   - Limit file processing with `MAX_FILES_PER_REPO`
   - Process fewer repositories at once

3. **Network Timeouts**

   - Reduce `--max-concurrent-repos`
   - Check network stability
   - Increase timeout values in config

4. **CPU Overload**
   - Reduce `--max-concurrent-analysis`
   - Match concurrency to CPU core count
   - Monitor system resources

### Performance Tuning

1. **Find Optimal Settings**

   ```bash
   # Start conservative
   python main.py --max-concurrent-api 1 --max-concurrent-analysis 2

   # Gradually increase
   python main.py --max-concurrent-api 2 --max-concurrent-analysis 4

   # Monitor system resources and adjust
   ```

2. **Monitor Resource Usage**

   ```bash
   # Monitor CPU and memory
   htop

   # Monitor network
   iftop

   # Monitor API usage
   # Check your API provider's dashboard
   ```

## Examples

### Basic Usage (Conservative)

```bash
python main.py \
  --num-repos 3 \
  --max-concurrent-repos 2 \
  --max-concurrent-api 1 \
  --max-concurrent-analysis 2
```

### Balanced Performance

```bash
python main.py \
  --num-repos 10 \
  --max-concurrent-repos 5 \
  --max-concurrent-api 3 \
  --max-concurrent-analysis 6
```

### Maximum Performance

```bash
python main.py \
  --num-repos 20 \
  --max-concurrent-repos 10 \
  --max-concurrent-api 8 \
  --max-concurrent-analysis 12 \
  --api-rate-limit 200
```

## Implementation Details

### Thread Safety

- All concurrent operations are thread-safe
- Rate limiting uses thread-safe queues
- File operations are properly synchronized

### Resource Management

- Automatic cleanup of threads and processes
- Proper exception handling in concurrent contexts
- Memory-efficient processing of large datasets

### Scalability

- Linear scaling with available resources
- Graceful degradation under resource constraints
- Configurable limits to prevent system overload

## Future Improvements

Planned enhancements:

- **Adaptive rate limiting** based on API response times
- **Dynamic concurrency adjustment** based on system load
- **Distributed processing** across multiple machines
- **Caching mechanisms** to avoid redundant API calls
- **Progress persistence** to resume interrupted workflows
