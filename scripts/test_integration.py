"""
Test script to verify the test integration functionality.

This script creates a simple test repository and runs the test integration
to verify everything works correctly.
"""

import os
import sys
import tempfile
import shutil
import logging
from utils import run_tests_with_pytest, get_test_results

log = logging.getLogger(__name__)

def create_test_repo():
    """Creates a temporary test repository with sample code and tests."""
    temp_dir = tempfile.mkdtemp(prefix="test_repo_")
    
    # Create main code file
    main_code = '''
def add(a, b):
    """Add two numbers."""
    return a + b

def multiply(a, b):
    """Multiply two numbers."""
    return a * b

def divide(a, b):
    """Divide two numbers."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
'''
    
    with open(os.path.join(temp_dir, "calculator.py"), "w") as f:
        f.write(main_code)
    
    # Create tests directory
    tests_dir = os.path.join(temp_dir, "tests")
    os.makedirs(tests_dir)
    
    # Create test file
    test_code = '''
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calculator import add, multiply, divide
import pytest

def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
    assert add(0, 0) == 0

def test_multiply():
    assert multiply(2, 3) == 6
    assert multiply(-1, 5) == -5
    assert multiply(0, 10) == 0

def test_divide():
    assert divide(6, 2) == 3
    assert divide(5, 2) == 2.5
    
def test_divide_by_zero():
    with pytest.raises(ValueError):
        divide(5, 0)

def test_failing():
    # This test will fail intentionally
    assert add(2, 2) == 5  # Should be 4
'''
    
    with open(os.path.join(tests_dir, "test_calculator.py"), "w") as f:
        f.write(test_code)
    
    # Create __init__.py files
    with open(os.path.join(tests_dir, "__init__.py"), "w") as f:
        f.write("")
    
    return temp_dir

def test_pytest_integration():
    """Test the pytest integration functionality."""
    log.info("Creating test repository...")
    test_repo = create_test_repo()
    
    try:
        log.info(f"Test repository created at: {test_repo}")
        
        # Test running pytest
        log.info("Running pytest integration test...")
        results = run_tests_with_pytest(test_repo)
        
        if results is None:
            log.error("Test execution returned None")
            return False
        
        log.info(f"Test results: {results}")
        
        # Verify results structure
        expected_keys = ["tests_found", "passed", "failed", "total", "exit_code"]
        for key in expected_keys:
            if key not in results:
                log.error(f"Missing key in results: {key}")
                return False
        
        # Test the get_test_results function
        parsed_results = get_test_results(results)
        if parsed_results is None:
            log.error("get_test_results returned None")
            return False
        
        passed, failed, total = parsed_results
        log.info(f"Parsed results: {passed} passed, {failed} failed, {total} total")
        
        # Verify we have some tests
        if total == 0:
            log.error("No tests were found or executed")
            return False
        
        # We expect 4 passing tests and 1 failing test
        if passed < 4:
            log.warning(f"Expected at least 4 passing tests, got {passed}")
        
        if failed < 1:
            log.warning(f"Expected at least 1 failing test, got {failed}")
        
        log.info("Test integration verification completed successfully!")
        return True
        
    except Exception as e:
        log.error(f"Test integration failed with exception: {e}")
        return False
    
    finally:
        # Clean up
        log.info(f"Cleaning up test repository: {test_repo}")
        shutil.rmtree(test_repo, ignore_errors=True)

def main():
    """Main test function."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    log.info("Starting test integration verification...")
    
    if test_pytest_integration():
        log.info("✅ All tests passed! Test integration is working correctly.")
        sys.exit(0)
    else:
        log.error("❌ Test integration verification failed.")
        sys.exit(1)

if __name__ == "__main__":
    main() 