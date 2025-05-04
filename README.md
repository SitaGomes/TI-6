# Automated Refactoring & Metric Collection Workflow

This README outlines the exact steps and code requirements to implement the methodology for evaluating DeepSeek’s AI-powered refactoring on popular Python open-source projects. By following this guide, your scripts will perform repository retrieval, smell detection, test generation, AI-driven refactoring, metric extraction, and result aggregation in CSV format.

---

## 📋 Prerequisites

- **Python 3.9+** installed
- **GitHub Personal Access Token** with `repo` scope
- **DeepSeek Free API Key**
- Install required Python libraries:

  ```bash
  pip install requests PyGithub radon bandit pylint pyright pandas
  ```

---

## 🔧 Setup

1. **Environment Variables**

   - `GITHUB_TOKEN`: your GitHub PAT
   - `DEEPSEEK_API_KEY`: your DeepSeek free API key

2. **Directory Structure**

   ```
   project-root/
   ├── original_code/         # Repositories cloned from GitHub
   ├── refactored_code/       # Output folders per prompt strategy
   │   ├── zero_shot/
   │   ├── one_shot/
   │   └── cot/
   ├── metrics/               # JSON and CSV results
   ├── scripts/               # Python scripts for each step
   └── README.md              # This file
   ```

---

## 🚀 Workflow Steps

### 1. Fetch Top Python Repositories

- Use GitHub API (via `PyGithub`) to search and clone the top _N_ most starred Python repositories.
- Filter out forks and archived projects.

**Example snippet:**

```python
from github import Github

g = Github(os.getenv("GITHUB_TOKEN"))
for repo in g.search_repositories("language:python", sort="stars", order="desc")[:N]:
    if not repo.fork and not repo.archived:
        repo.clone_url  # git clone into original_code/
```

### 2. Detect Code Smells with Local Libraries

- Run static analysis with **PyLint** and **Radon** on each cloned repo.
- Save results in `metrics/{repo_name}/smells_lib.json`.

```bash
pylint original_code/{repo}/ --output-format=json > metrics/{repo}/smells_lib_pylint.json
radon cc original_code/{repo}/ -s -j > metrics/{repo}/smells_lib_radon.json
```

### 3. Identify Code Smells with DeepSeek

- Send each file path and content to DeepSeek’s `/detect_smells` endpoint using a single consistent prompt.
- Compare and map DeepSeek’s detected smells to the library results.
- Record mismatches (false positives/negatives) in `metrics/{repo}/smells_deepseek.json`.

```python
import requests

def detect_smells_with_deepseek(code: str):
    r = requests.post(
        "https://api.deepseek.ai/detect_smells",
        headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
        json={"prompt": STANDARD_SMELL_PROMPT, "code": code}
    )
    return r.json()
```

### 4. Generate Tests if Missing

- Check for existing test files; if none or incomplete, call DeepSeek’s `/generate_tests` endpoint with the same prompt.
- Save generated tests under `original_code/{repo}/tests/` and ensure they pass before refactoring.

### 5. Refactor Code with Three Prompt Strategies

For each smell location:

- **Zero-Shot**: call `/refactor` with zero-shot prompt
- **One-Shot**: include one example in the prompt
- **Chain-of-Thought (CoT)**: include reasoning steps in the prompt

Save each refactored file tree under `refactored_code/{strategy}/{repo}/`.

### 6. Post-Refactor Analysis

- Run **PyLint**, **Radon**, **PyRight**, and **Bandit** on each refactored directory.
- Store outputs in `metrics/{repo}/{strategy}/`:

  - `pylint.json`
  - `radon_cc.json`, `radon_mi.json`
  - `pyright.json`
  - `bandit.json`

### 7. Aggregate Metrics & CSV Export

- Write a Python aggregation script that:

  1. Reads all JSON metric files
  2. Computes delta against original metrics
  3. Records:

     - `repository_name`
     - `strategy` (zero_shot, one_shot, cot)
     - `num_smells_detected_lib`
     - `num_smells_detected_deepseek`
     - `num_false_positives`
     - `num_false_negatives`
     - `pylint_score_delta`
     - `avg_cyclomatic_delta`
     - `maintainability_index_delta`
     - `pyright_error_delta`
     - `bandit_vuln_delta`

  4. Saves final table as `metrics/summary.csv` using **pandas**.

**Example aggregation snippet:**

```python
import pandas as pd
# ... load JSON metrics and compute deltas ...
rows = []
# for each repo and strategy, append dict to rows
summary_df = pd.DataFrame(rows)
summary_df.to_csv("metrics/summary.csv", index=False)
```

---

## 🎯 Expected Outcomes

- A complete CSV summarizing how DeepSeek’s refactoring (per prompt) impacts code quality and technical debt.
- Direct comparison between library-based vs. AI-based smell detection.
- Clear data to answer research questions on prompt efficiency and refactoring effectiveness.

---

Follow each step precisely in your scripts under `scripts/` to ensure reproducibility and consistency across experiments.
