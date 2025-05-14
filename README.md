# Threat Modeling Crew

> WIP: This is a work in progress. The project is not yet complete and the documentation may be subject to change.

[Bsides Tokyo 2025 - Threat Modeling with Multi-Agent AI](https://bsides.tokyo/en/2025/n55/).

Welcome to the Threat Modeling Crew project, powered by [crewAI](https://crewai.com). This template is designed to help you set up a multi-agent AI system with ease, leveraging the powerful and flexible framework provided by crewAI. Our goal is to enable your agents to collaborate effectively on complex tasks, maximizing their collective intelligence and capabilities.

## Installation

Ensure you have Python >=3.10 <=3.13 installed on your system. This project uses [UV](https://docs.astral.sh/uv/) for dependency management and package handling, offering a seamless setup and execution experience.

First, if you haven't already, install uv:

```bash
pip install uv
```

Next, navigate to your project directory and install the dependencies:

1. First lock the dependencies and then install them:

```bash
uv lock
uv sync
```

## 🧱 System-level Dependency for Tesseract

Make sure Tesseract is also installed on the machine (this is not installable via pip):

### macOS

```bash
brew install tesseract
```

### Ubuntu/Debian

```bash
sudo apt install tesseract-ocr
```

### Customizing

**Add your `OPENAI_API_KEY` into the `.env` file**

- Modify `src/threat_modeling/config/agents.yaml` to define your agents
- Modify `src/threat_modeling/config/tasks.yaml` to define your tasks
- Modify `src/threat_modeling/crew.py` to add your own logic, tools and specific args
- Modify `src/threat_modeling/main.py` to add custom inputs for your agents and tasks

## Running the Project

To kickstart your crew of AI agents and begin task execution, run this from the root folder of your project:

```bash
uv run threat_modeling
```

This command initializes the crewai-plus-lead-scoring Crew, assembling the agents and assigning them tasks as defined in your configuration.

This example, unmodified, will run the create a `report.md` file with the output of a research on LLMs in the root folser

## Understanding Your Crew

The crewai-plus-lead-scoring Crew is composed of multiple AI agents, each with unique roles, goals, and tools. These agents collaborate on a series of tasks, defined in `config/tasks.yaml`, leveraging their collective skills to achieve complex objectives. The `config/agents.yaml` file outlines the capabilities and configurations of each agent in your crew.

## Support

For support, questions, or feedback regarding the ThreatModeling Crew.

- [GitHub Issues](https://github.com/charlesgreen/threat-modeling-ai/issues)
- [Charles Green](https://charles.green)
