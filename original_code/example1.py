import sys

def process_data(data_list):
    """
    This function processes a list of data with high complexity.
    It includes nested loops and multiple conditional branches.
    """
    results = []
    if not data_list:
        print("Data list is empty.", file=sys.stderr)
        return None # Early exit

    for i, item in enumerate(data_list):
        processed_item = None
        # Complex condition
        if isinstance(item, (int, float)) and item > 0:
            if item % 2 == 0:
                # Nested loop
                temp_val = 0
                for j in range(int(item / 2)):
                    temp_val += (j * 2)
                processed_item = temp_val * item
            else:
                # Another branch
                processed_item = (item + 1) * 3
        elif isinstance(item, str):
            if len(item) > 5 and "complex" in item:
                # String processing
                processed_item = item.upper().replace(" ", "_")
            elif len(item) <= 5:
                processed_item = item + "_short"
            else:
                processed_item = "default_string"
        else:
            # Default case for other types or negative numbers
            processed_item = f"unsupported_{type(item).__name__}_{i}"

        # Add non-None results
        if processed_item is not None:
            results.append(processed_item)
        else:
            # Redundant else, could be combined
            pass

    # Poor variable name
    final_res = results
    if len(final_res) > 10:
        # Arbitrary slicing
        return final_res[:10]
    elif not final_res: # Check if empty
        return []
    else:
        return final_res

# Example usage
if __name__ == "__main__":
    data = [10, 5, "simple string", 15.5, "this is complex", -3, None, "short", 8, 12, 1, 0, "another complex string", 2.0]
    output = process_data(data)
    print(f"Processed Output: {output}")