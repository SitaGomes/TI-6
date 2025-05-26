"""
Stores the prompts used for interacting with the DeepSeek API.
"""

# Zero-Shot smell detection prompt - direct and to the point
SMELL_ZERO_SHOT_PROMPT_TEMPLATE = """
Analyze the following Python code and identify code smells.
List each smell you find with its line number(s) and a brief description.
Focus on these smell types: Long Method, Large Class, Feature Envy, Data Clumps, 
Code Duplication, Comments, Magic Numbers, Long Parameter List, Complex Conditionals.

Code:
```python
{code_content}
```

Detected Smells (Line number(s): Description):
"""

# Placeholder - Refine as needed
TEST_GENERATION_PROMPT_TEMPLATE = """
Generate comprehensive pytest unit tests for the following Python code.
Ensure the tests cover various scenarios, including edge cases and potential errors.
Output only the Python code for the tests. Assume necessary imports like 'pytest' are handled.

Code to test:
```python
{code_content}
```

Generated pytest code:
```python
# Test code goes here
```
"""

# Placeholder - Refine as needed
REFACTOR_ZERO_SHOT_PROMPT_TEMPLATE = """
Refactor the entire Python code to address the code smells listed below. 
Apply the most appropriate refactoring techniques to improve overall code quality, maintainability, and readability based on these smells.
Output ONLY the complete refactored code for the entire file. Do not include explanations, comments about changes, or markdown formatting.

Identified Smells:
{smell_list_string}

Original Code:
```python
{full_code_content}
```

Refactored Code:
```python
# Full refactored code goes here
```
"""

# Placeholder - Needs a concrete example related to whole-file refactoring
REFACTOR_ONE_SHOT_PROMPT_TEMPLATE = """
Refactor the entire Python code to address the code smells listed below, following the example format.
Apply the most appropriate refactoring techniques to improve overall code quality.
Output ONLY the complete refactored code for the entire file.

Example:
File: 'calculator_with_smells.py'
Smells:
- Lines 5-6: Magic Number (3.14159)
- Lines 10-15: Long Method (add_and_log)
Original Code:
```python
import logging

def calculate_area(radius):
    return 3.14159 * radius * radius

def add_and_log(a, b):
    result = a + b
    logging.basicConfig(level=logging.INFO)
    logging.info(f"Adding {{a}} and {{b}} resulted in {{result}}")

    print(f"Debug: {{result}}") 
    return result
```
Refactored Code:
```python
import logging
import math

logging.basicConfig(level=logging.INFO)

PI = math.pi

def calculate_area(radius):
    return PI * radius * radius

def log_addition(a, b, result):
    logging.info(f"Adding {{a}} and {{b}} resulted in {{result}}")
    print(f"Debug: {{result}}")
    
def add_and_log(a, b):
    result = a + b
    log_addition(a, b, result) # Calls separate logging
    return result
```

---

Problem:
Smells:
{smell_list_string}
Original Code:
```python
{full_code_content}
```

Refactored Code:
```python
# Full refactored code goes here
```
"""

# Placeholder - Refine as needed
REFACTOR_COT_PROMPT_TEMPLATE = """
Refactor the entire Python code from to address the code smells listed below.
First, think step-by-step about how to address all the identified smells holistically.
Then, apply the refactorings.
Output ONLY the final, complete refactored code for the entire file.

Thought Process:
1. Analyze the list of smells ({smell_list_string}) and their locations in the code.
2. Consider refactoring techniques for each smell (e.g., Extract Method, Introduce Parameter Object, Replace Magic Number, etc.).
3. Plan how to apply these refactorings to the entire file, considering potential interactions between changes.
4. Execute the refactoring plan on the full code.

Original Code:
```python
{full_code_content}
```

Refactored Code:
```python
# Full refactored code goes here
```
"""
