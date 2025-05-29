#!/usr/bin/env python3
"""
Benchmark script to demonstrate the performance improvements of concurrent processing.
"""

import time
import logging
from scripts.utils import process_items_concurrently

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

def simulate_work(item):
    """Simulate some work that takes time (like an API call or file processing)."""
    time.sleep(0.5)  # Simulate 500ms of work
    return f"Processed {item}"

def benchmark_sequential_vs_concurrent():
    """Compare sequential vs concurrent processing performance."""
    items = list(range(1, 11))  # 10 items to process
    
    log.info("=== Performance Benchmark: Sequential vs Concurrent ===")
    log.info(f"Processing {len(items)} items, each taking ~500ms")
    
    # Sequential processing
    log.info("\n--- Sequential Processing ---")
    start_time = time.time()
    sequential_results = []
    for item in items:
        result = simulate_work(item)
        sequential_results.append(result)
    sequential_time = time.time() - start_time
    log.info(f"Sequential time: {sequential_time:.2f} seconds")
    
    # Concurrent processing with 3 workers
    log.info("\n--- Concurrent Processing (3 workers) ---")
    start_time = time.time()
    concurrent_results = process_items_concurrently(
        items, 
        simulate_work, 
        max_workers=3,
        executor_type="thread"
    )
    concurrent_time = time.time() - start_time
    log.info(f"Concurrent time: {concurrent_time:.2f} seconds")
    
    # Calculate speedup
    speedup = sequential_time / concurrent_time
    log.info(f"\n--- Results ---")
    log.info(f"Sequential: {sequential_time:.2f}s")
    log.info(f"Concurrent: {concurrent_time:.2f}s")
    log.info(f"Speedup: {speedup:.2f}x faster")
    log.info(f"Time saved: {sequential_time - concurrent_time:.2f}s ({((sequential_time - concurrent_time) / sequential_time * 100):.1f}%)")
    
    return speedup

def benchmark_different_worker_counts():
    """Test performance with different numbers of workers."""
    items = list(range(1, 21))  # 20 items
    worker_counts = [1, 2, 4, 8]
    
    log.info(f"\n=== Worker Count Benchmark ===")
    log.info(f"Processing {len(items)} items with different worker counts")
    
    results = {}
    
    for workers in worker_counts:
        log.info(f"\n--- Testing with {workers} workers ---")
        start_time = time.time()
        
        concurrent_results = process_items_concurrently(
            items, 
            simulate_work, 
            max_workers=workers,
            executor_type="thread"
        )
        
        elapsed_time = time.time() - start_time
        results[workers] = elapsed_time
        log.info(f"Time with {workers} workers: {elapsed_time:.2f}s")
    
    # Find optimal worker count
    best_workers = min(results, key=results.get)
    best_time = results[best_workers]
    
    log.info(f"\n--- Worker Count Results ---")
    for workers, elapsed_time in results.items():
        efficiency = results[1] / elapsed_time
        log.info(f"{workers} workers: {elapsed_time:.2f}s (efficiency: {efficiency:.2f}x)")
    
    log.info(f"\nOptimal worker count: {best_workers} workers ({best_time:.2f}s)")
    
    return results

def simulate_real_workflow():
    """Simulate a realistic workflow with different types of operations."""
    log.info("\n=== Realistic Workflow Simulation ===")
    
    # Simulate different types of operations
    def simulate_api_call(item):
        time.sleep(0.3)  # API calls
        return f"API result for {item}"
    
    def simulate_file_processing(item):
        time.sleep(0.1)  # File I/O
        return f"File processed: {item}"
    
    def simulate_analysis(item):
        time.sleep(0.2)  # Analysis tools
        return f"Analysis of {item}"
    
    operations = [
        ("API Calls", simulate_api_call, 10),
        ("File Processing", simulate_file_processing, 20),
        ("Static Analysis", simulate_analysis, 15)
    ]
    
    total_sequential = 0
    total_concurrent = 0
    
    for op_name, op_func, item_count in operations:
        items = list(range(1, item_count + 1))
        
        log.info(f"\n--- {op_name} ({item_count} items) ---")
        
        # Sequential
        start_time = time.time()
        for item in items:
            op_func(item)
        seq_time = time.time() - start_time
        total_sequential += seq_time
        
        # Concurrent
        start_time = time.time()
        process_items_concurrently(items, op_func, max_workers=4)
        conc_time = time.time() - start_time
        total_concurrent += conc_time
        
        speedup = seq_time / conc_time
        log.info(f"Sequential: {seq_time:.2f}s, Concurrent: {conc_time:.2f}s, Speedup: {speedup:.2f}x")
    
    overall_speedup = total_sequential / total_concurrent
    time_saved = total_sequential - total_concurrent
    
    log.info(f"\n--- Overall Workflow Results ---")
    log.info(f"Total sequential time: {total_sequential:.2f}s")
    log.info(f"Total concurrent time: {total_concurrent:.2f}s")
    log.info(f"Overall speedup: {overall_speedup:.2f}x")
    log.info(f"Total time saved: {time_saved:.2f}s ({(time_saved/total_sequential*100):.1f}%)")
    
    return overall_speedup

if __name__ == "__main__":
    log.info("Starting concurrent processing benchmarks...")
    
    try:
        # Run benchmarks
        basic_speedup = benchmark_sequential_vs_concurrent()
        worker_results = benchmark_different_worker_counts()
        workflow_speedup = simulate_real_workflow()
        
        # Summary
        log.info("\n" + "="*60)
        log.info("BENCHMARK SUMMARY")
        log.info("="*60)
        log.info(f"Basic concurrent speedup: {basic_speedup:.2f}x")
        log.info(f"Workflow speedup: {workflow_speedup:.2f}x")
        log.info(f"Optimal worker count: {min(worker_results, key=worker_results.get)} workers")
        log.info("\nConcurrent processing provides significant performance improvements!")
        log.info("Adjust worker counts based on your system resources and API limits.")
        
    except KeyboardInterrupt:
        log.info("\nBenchmark interrupted by user")
    except Exception as e:
        log.error(f"Benchmark failed: {e}")
        raise 