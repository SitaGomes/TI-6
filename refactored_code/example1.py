import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

MAX_RESULTS = 10

def _process_numeric(item):
    """Helper function to process positive numeric items."""
    if item <= 0:
        return None
    
    if item % 2 == 0: # Even number
        # Simplified calculation
        half_item = item // 2
        temp_val = half_item * (half_item - 1) # Sum of 0*2, 1*2, ... (n-1)*2 = 2 * n * (n-1) / 2 = n*(n-1)
        return temp_val * item
    else: # Odd number
        return (item + 1) * 3

def _process_string(item):
    """Helper function to process string items."""
    if len(item) > 5 and "complex" in item:
        return item.upper().replace(" ", "_")
    elif len(item) <= 5:
        return item + "_short"
    else:
        return "default_string"

def process_data_refactored(data_list):
    """
    Refactored version of process_data with reduced complexity and improved readability.
    Uses helper functions and clearer logic.
    """
    if not isinstance(data_list, list):
        logging.error("Input must be a list.")
        return None
        
    if not data_list:
        logging.warning("Data list is empty.")
        return []

    results = []
    for i, item in enumerate(data_list):
        processed_item = None
        if isinstance(item, (int, float)):
            processed_item = _process_numeric(item)
        elif isinstance(item, str):
            processed_item = _process_string(item)
        else:
            # Log unsupported types instead of returning a complex string
            logging.debug(f"Item {i} has unsupported type: {type(item).__name__}")
            # Optionally, return a standard marker or None
            # processed_item = f"unsupported_{type(item).__name__}"

        if processed_item is not None:
            results.append(processed_item)
            
    # Return results, truncated if necessary
    if len(results) > MAX_RESULTS:
        logging.info(f"Returning truncated results ({MAX_RESULTS} of {len(results)} items).")
        return results[:MAX_RESULTS]
    
    return results

# Example usage
if __name__ == "__main__":
    data = [
        10, 5, "simple string", 15.5, "this is complex", -3, None, 
        "short", 8, 12, 1, 0, "another complex string", 2.0, object()
    ]
    output = process_data_refactored(data)
    
    if output is not None:
        print(f"Processed Output: {output}") 