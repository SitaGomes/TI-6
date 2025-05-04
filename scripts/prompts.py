"""
Stores the prompts used for interacting with the DeepSeek API.
"""

# Placeholder - Refine as needed
STANDARD_SMELL_PROMPT_TEMPLATE = """
Analyze the following Python code block from the file '{file_path}' and identify potential code smells.
List only the smells you find, specifying the line number(s) and a brief description for each.
Focus on common smells like Long Method, Large Class, Feature Envy, Data Clump, Code Duplication, etc.
Do not suggest refactorings, just identify the smells.

Code:
```python
{code_content}
```

Detected Smells (Line number(s): Description):
"""

# Placeholder - Refine as needed
TEST_GENERATION_PROMPT_TEMPLATE = """
Generate comprehensive pytest unit tests for the following Python code from the file '{file_path}'.
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
Refactor the following Python code block from the file '{file_path}' to address the code smell identified around line {line_number}: '{smell_description}'.
Apply the most appropriate refactoring technique to improve code quality (e.g., Extract Method, Move Field, Replace Magic Number with Symbolic Constant).
Output only the refactored Python code block. Do not include explanations or surrounding code.

Original Code Block:
```python
{code_block}
```

Refactored Code Block:
```python
# Refactored code goes here
```
"""

# Placeholder - Needs a concrete example
REFACTOR_ONE_SHOT_PROMPT_TEMPLATE = """
Refactor the following Python code block from the file '{file_path}' to address the code smell identified around line {line_number}: '{smell_description}'.
Apply the most appropriate refactoring technique. Follow the example provided.

Example:
Smell: Magic Number
Original Code Block from 'calculator.py' (Smell: 'Magic Number' near line 5):
```python
def calculate_area(radius):
    return 3.14159 * radius * radius
```
Refactored Code Block:
```python
import math

def calculate_area(radius):
    PI = math.pi # Replace magic number with symbolic constant
    return PI * radius * radius
```

---

Problem:
Original Code Block from '{file_path}' (Smell: '{smell_description}' near line {line_number}):
```python
{code_block}
```

Refactored Code Block (Output only the code):
```python
# Refactored code goes here
```
"""

# Placeholder - Refine as needed
REFACTOR_COT_PROMPT_TEMPLATE = """
Refactor the following Python code block from the file '{file_path}' to address the code smell identified around line {line_number}: '{smell_description}'.
First, think step-by-step about the smell and the best refactoring technique.
Then, apply the refactoring.
Output only the final refactored Python code block.

Original Code Block:
```python
{code_block}
```

Thought Process:
1.  Identify the specific issue related to '{smell_description}'.
2.  Consider potential refactoring techniques (e.g., Extract Method, Introduce Parameter Object, etc.).
3.  Select the most suitable technique based on the context.
4.  Outline the steps to apply the chosen technique.
5.  Execute the refactoring steps.

Refactored Code Block:
```python
# Refactored code goes here
```
"""
