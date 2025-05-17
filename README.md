# Threat Modeling Crew

> ⚠️ **Work in Progress**  
> This project is still under development. Features and documentation are subject to change.

[Bsides Tokyo 2025 - Threat Modeling with Multi-Agent AI](https://bsides.tokyo/en/2025/n55/)

Threat Modeling Crew is a multi-agent AI system built with [CrewAI](https://crewai.com) to automate cloud threat modeling using STRIDE. It analyzes GCP metadata, architecture PDFs, and image diagrams to generate a structured threat model and export a CSV report for security teams.

---

## 🚀 Features

- Automatically extract cloud metadata from GCP projects
- Interpret PDF-based documentation and image diagrams
- Apply STRIDE threat modeling to identified components
- Export actionable risks in CSV format for security testers

---

## 🛠️ Installation

This project uses [UV](https://docs.astral.sh/uv/) for fast dependency management.

### 1. Install UV (if not already)

```bash
pip install uv
```

### 2. Clone the project and set up the environment

```bash
cd threat-modeling-ai
uv venv .venv
source .venv/bin/activate
uv sync
```

This creates a virtual environment and installs all required packages.

---

## 🔍 Tesseract System Dependency (for OCR)

Tesseract is required for reading image-based diagrams.

### macOS

```bash
brew install tesseract
```

### Debian/Ubuntu

```bash
sudo apt install tesseract-ocr
```

---

## 🔧 Configuration

Create a `.env` file at the project root with the following (example):

```env
# Traces, evals, prompt management and metrics
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_HOST="https://us.cloud.langfuse.com"

# Google Search API
SERPER_API_KEY=da8ef...

# Configured to use OpenAI
OPENAI_API_KEY=sk-xxxxxx

# Execution configuration
PROJECT_ID=my-gcp-project-id
PDF_PATH=input/architecture.pdf
DIAGRAM_PATH=input/diagram.png
```

You can also pass these values via CLI.

---

## ▶️ How to Run

From the project root:

```bash
PYTHONPATH=src .venv/bin/python -m threat_modeling.main run
```

Or using command-line arguments:

```bash
PYTHONPATH=src .venv/bin/python -m threat_modeling.main run \
  --project-id=my-gcp-project-id \
  --pdf-path=input/architecture.pdf \
  --diagram-path=input/diagram.png
```

✅ You can run the model with **any combination** of inputs

> - Only GCP metadata
> - Only PDF or image  
> - All three  
> - If none are provided, a helpful error message will guide you.

---

## 🧠 Agents and Tasks

Defined in:

- `src/threat_modeling/config/agents.yaml`
- `src/threat_modeling/config/tasks.yaml`

Agents include:

- **Cloud Architecture Interpreter**
- **STRIDE Threat Analyst**
- **Security Reporting Assistant**

---

## 📝 Output

The final output is a CSV file (`threat_model.csv`) containing structured risks:

| threat               | asset              | category        | likelihood | impact   | mitigation                               |
| -------------------- | ------------------ | --------------- | ---------- | -------- | ---------------------------------------- |
| Token forgery attack | Cloud Run: web-api | Spoofing        | High       | Severe   | Use signed JWT tokens with validation    |
| Open bucket access   | GCS logs-bucket    | Info Disclosure | Medium     | Moderate | Enable IAM and Bucket-Level restrictions |

---

## 🧪 Other CLI Commands

### Train the agents

```bash
PYTHONPATH=src .venv/bin/python -m threat_modeling.main run > output.log 2>&1
```

### Replay a previous execution

```bash
PYTHONPATH=src .venv/bin/python -m threat_modeling.main replay <task_id>
```

### Run a test suite

```bash
PYTHONPATH=src .venv/bin/python -m threat_modeling.main test 1 gpt-4
```

---

## 🧰 Project Structure

```bash
threat-modeling-ai/
├── pyproject.toml
├── .env
├── src/
│   └── threat_modeling/
│       ├── config/
│       │   ├── agents.yaml
│       │   └── tasks.yaml
│       ├── tools/
│       │   ├── gcp_metadata_tool.py
│       │   ├── pdf_reader_tool.py
│       │   ├── image_diagram_tool.py
│       │   ├── stride_threat_modeler_tool.py
│       │   └── csv_risk_exporter.py
│       ├── crew.py
│       └── main.py
```

---

## 📬 Support

- [GitHub Issues](https://github.com/charlesgreen/threat-modeling-ai/issues)
- [Charles Green](https://charles.green)
