# 🌐 Polyglot Code Translator

An internal developer tool built during an internship to automate the translation and migration of Python codebases across languages and versions. Designed to reduce the manual effort of large-scale code migrations within engineering teams.

---

## Overview

Polyglot Code Translator takes Python source code — either a single file or an entire ZIP of a project — and translates it to a target language or migrates it to a specific Python version. It uses an LLM pipeline backed by OpenAI, an AST-based dependency-aware chunking system, lint validation, and sandboxed code execution to produce clean, runnable output.

An AI overview report is generated after each translation, summarising potential issues, compatibility concerns, and recommended manual tweaks for the developer to review.

---

## Features

- **Multi-language translation** — converts Python to R, Java, or PySpark
- **Python version migration** — upgrade or downgrade code between Python 2.7 and 3.11, preserving equivalent functionality
- **Dependency-aware chunking** — uses AST parsing and a directed dependency graph to split code into semantically meaningful chunks before translation, preserving function relationships
- **Parallel processing** — chunks are translated concurrently using a thread pool for faster throughput on large files
- **Lint validation** — translated code is validated and auto-fixed before being returned
- **Sandboxed execution** — each translated chunk is executed in an isolated environment and the result (success/failure + output) is shown per chunk
- **Side-by-side diff view** — pastel-highlighted diff table comparing original and translated code line by line
- **ZIP support** — upload an entire Python project as a ZIP and download the fully translated project as a new ZIP
- **AI overview report** — post-translation analysis of potential issues, manual tweaks needed, and refactoring suggestions

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| LLM Orchestration | LangChain + OpenAI (`gpt-3.5-turbo` / `text-davinci`) |
| Code Analysis | Python `ast` module, NetworkX (dependency graphs) |
| Execution Sandbox | Custom `ExecutionService` |
| Lint Validation | Custom `LintService` |
| Environment Config | `python-dotenv` |

---

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Set your OpenAI API key**

Create a `.env` file in the project root:
```
OPENAI_API_KEY=your_key_here
```

**4. Run the app**
```bash
streamlit run app.py
```

---

## How to Use

### Single file or pasted code
1. Select an operation mode — **Translate to another language** or **Update/Downgrade Python version**
2. Choose your target language or Python version from the dropdown
3. Upload a `.py` file or paste code directly into the text area
4. Click **Run 🚀**
5. Review the translated code, diff view, per-chunk execution results, and AI overview report

### ZIP project upload
1. Select your operation mode and target
2. Upload a `.zip` containing Python files
3. Click **Run**
4. Download the processed ZIP — all `.py` files will be translated and output with the correct file extension for the target language

---

## Project Structure

```
/
├── app.py                  # Streamlit UI and file handling
├── pipeline.py             # LLM pipelines (PolyglotPipeline, PythonVersionPipeline, AIOverviewAgent)
├── chunk_code.py           # AST-based dependency graph chunker
├── services/
│   ├── lint_service.py     # Lint validation and auto-fix
│   └── execution_service.py # Sandboxed code execution
├── requirements.txt
├── .env                    # API keys (not committed)
├── test.py                 # Sample Python input for testing
└── test.java               # Sample Java output for reference
```

---

## Architecture

```
Input Code
    │
    ▼
AST Chunker (chunk_code.py)
  - Parses code into an AST
  - Builds a function dependency graph with NetworkX
  - Groups strongly connected components into chunks
  - Splits oversized chunks by token limit
    │
    ▼
LLM Translation Pipeline (pipeline.py)
  - Sends each chunk to OpenAI via LangChain with a language-specific prompt
  - Chunks processed in parallel (ThreadPoolExecutor)
    │
    ▼
Lint Validation → Execution Sandbox
    │
    ▼
Output: Translated code + diff + execution results + AI report
```

---

## Roadmap

From the project todo list — items completed during the internship are marked:

- [x] Dependency-aware chunking with token limit enforcement
- [x] Correction and validation agent (LintService)
- [x] Parallel chunk processing
- [x] Python version upgrade/downgrade pipeline
- [X] Judging agent — metric-based scoring of translation quality
- [X] AI identification of language-specific library failures and suggested alternatives
- [X] Test case generation and execution within the sandbox
- [X] Custom parameters and natural language instructions per translation run
- [ ] Dependency package upgrade support for version migrations

---

## Notes

- The `.env` file containing your OpenAI API key should never be committed — it is included in `.gitignore`
- Java output is automatically wrapped in a `TranslatedProgram` class with a `main` method for valid compilation
- Very large files are handled by the token-aware chunker which splits on approximately 4,000 tokens per chunk
- The AI overview report is generated from a single prompt comparing the full original and translated code — for very large files this may approach context limits
