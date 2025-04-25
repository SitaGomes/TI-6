# Evaluating Technical Debt Reduction from AI-based Code Refactoring

This repository provides a structured approach to evaluate technical debt reduction in Python code refactored using AI tools such as DeepSeek. It leverages open-source Python libraries to automatically analyze and compare code quality before and after refactoring.

---

## ⚙️ Setup

### 1. Clone this Repository

Ensure you have both the original and refactored code versions structured in separate directories, for example:

```
project/
├── original_code/
└── refactored_code/
```

### 2. Install Required Python Libraries

Execute the following commands in your terminal to install the required analysis libraries:

```bash
pip install radon bandit pylint
```

---

## 📊 Running the Analyses

The analysis compares metrics collected by Radon, Bandit, and PyLint.

### Radon: Complexity and Maintainability

Radon computes code complexity (Cyclomatic Complexity - CC) and Maintainability Index (MI).

Run Radon analyses with these commands:

```bash
# Complexity (Cyclomatic Complexity)
radon cc original_code/ -s -j > radon_complex_original.json
radon cc refactored_code/ -s -j > radon_complex_refactored.json

# Maintainability Index
radon mi original_code/ -s -j > radon_mi_original.json
radon mi refactored_code/ -s -j > radon_mi_refactored.json
```

These commands:

- Analyze all Python files in each directory.
- Output results in JSON format for automated parsing.

### Bandit: Security Analysis

Bandit performs static security analysis, detecting potential vulnerabilities:

```bash
bandit -r original_code/ -f json -o bandit_original.json
bandit -r refactored_code/ -f json -o bandit_refactored.json
```

These commands:

- Scan directories recursively for security vulnerabilities.
- Save the results into JSON files.

### PyLint: Code Quality and Style

PyLint identifies style issues, potential bugs, and coding errors:

```bash
pylint original_code/ --output-format=json > pylint_original.json
pylint refactored_code/ --output-format=json > pylint_refactored.json
```

These commands:

- Produce a detailed JSON-formatted report of issues.

---

## 📌 Automated Metrics Calculation

### Running the Python Script

Create a Python script (`evaluate_tech_debt.py`) in the root directory:

```python
import json

def load_json(path):
    with open(path, 'r') as file:
        return json.load(file)

def average_complexity(radon_cc):
    complexities = [f["complexity"] for f in radon_cc.values()]
    return sum(complexities) / len(complexities)

def average_mi(radon_mi):
    indices = [f["mi"] for f in radon_mi.values()]
    return sum(indices) / len(indices)

def vulnerabilities_count(bandit):
    return len(bandit["results"])

def pylint_issues_count(pylint):
    return len(pylint)

folders = ["original", "refactored"]
metrics = {}

for folder in folders:
    metrics[folder] = {}
    radon_cc = load_json(f"radon_complex_{folder}.json")
    radon_mi = load_json(f"radon_mi_{folder}.json")
    bandit = load_json(f"bandit_{folder}.json")
    pylint = load_json(f"pylint_{folder}.json")

    metrics[folder]["avg_complexity"] = average_complexity(radon_cc)
    metrics[folder]["avg_mi"] = average_mi(radon_mi)
    metrics[folder]["vulnerabilities"] = vulnerabilities_count(bandit)
    metrics[folder]["pylint_issues"] = pylint_issues_count(pylint)

for metric in ["avg_complexity", "avg_mi", "vulnerabilities", "pylint_issues"]:
    original = metrics["original"][metric]
    refactored = metrics["refactored"][metric]
    print(f"{metric}: Original={original:.2f}, Refactored={refactored:.2f}, Change={refactored - original:.2f}")
```

Run this script:

```bash
python evaluate_tech_debt.py
```

---

## 📈 Interpreting Results

Sample output:

```
avg_complexity: Original=9.20, Refactored=5.30, Change=-3.90
avg_mi: Original=67.50, Refactored=79.80, Change=12.30
vulnerabilities: Original=12.00, Refactored=4.00, Change=-8.00
pylint_issues: Original=40.00, Refactored=15.00, Change=-25.00
```

**Interpretation:**

- A negative change in `avg_complexity`, `vulnerabilities`, and `pylint_issues` indicates improvement.
- A positive change in `avg_mi` indicates better maintainability.

---

## 🚀 Conclusion

By following these steps, you effectively evaluate whether AI-based refactoring reduces technical debt, improving code maintainability, security, and readability, using fully automated, open-source Python libraries.
