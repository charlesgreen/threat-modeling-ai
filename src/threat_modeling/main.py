#!/usr/bin/env python

from langfuse.openai import openai
from typing import Optional

import sys
import os
from dotenv import load_dotenv
import typer
from threat_modeling.crew import ThreatModelingCrew

load_dotenv()  # Ensure .env is loaded at startup
app = typer.Typer()
print(f"[DEBUG] PROJECT_ID from .env: {os.getenv('PROJECT_ID')}")

REQUIRED_INPUT_KEYS = [
    "gcp_metadata",
    "architecture_summary",
    "diagram_insights",
    "component_list",
    "threat_list"
]

def build_inputs(
    project_id: Optional[str] = None,
    pdf_path: Optional[str] = None,
    diagram_path: Optional[str] = None
) -> dict:
    # Allow fallback to .env if values not passed via CLI
    project_id = project_id or os.getenv("PROJECT_ID")
    pdf_path = pdf_path or os.getenv("PDF_PATH")
    diagram_path = diagram_path or os.getenv("DIAGRAM_PATH")

    print(f"[DEBUG] build_inputs resolved project_id: {project_id}")
    print(f"[DEBUG] build_inputs resolved pdf_path: {pdf_path}")
    print(f"[DEBUG] build_inputs resolved diagram_path: {diagram_path}")

    inputs = {}
    if project_id: inputs["project_id"] = project_id
    if pdf_path: inputs["pdf_path"] = pdf_path
    if diagram_path: inputs["diagram_path"] = diagram_path

    # Ensure all required template keys are included
    for key in REQUIRED_INPUT_KEYS:
        inputs.setdefault(key, "")

    return inputs

def validate_inputs(inputs: dict):
    if not any(inputs.get(k) for k in ["project_id", "pdf_path", "diagram_path"]):
        typer.echo("\n❌ No valid inputs provided.")
        typer.echo("Please supply at least one of the following:\n")
        typer.echo("  --project-id <PROJECT_ID>")
        typer.echo("  --pdf-path <PDF_PATH>")
        typer.echo("  --diagram-path <DIAGRAM_PATH>")
        typer.echo("\nYou can also use a .env file with keys: PROJECT_ID, PDF_PATH, DIAGRAM_PATH\n")
        raise typer.Exit(1)

@app.command()
def run(
    project_id: str = typer.Option(None, envvar="PROJECT_ID", help="GCP Project ID (optional, will use .env if not provided)"),
    pdf_path: str = typer.Option(None),
    diagram_path: str = typer.Option(None),
):
    """Run full threat modeling pipeline"""
    inputs = build_inputs(project_id, pdf_path, diagram_path)
    validate_inputs(inputs)

    typer.echo("✅ Starting Threat Modeling Crew with:")
    for k, v in inputs.items():
        typer.echo(f"  {k}: {v if v else '[empty]'}")

    ThreatModelingCrew().crew().kickoff(inputs=inputs)

@app.command()
def train(iterations: int, filename: str, project_id: str = typer.Option(..., help="GCP Project ID (required)")):
    inputs = build_inputs(project_id)
    validate_inputs(inputs)
    inputs = build_inputs()
    validate_inputs(inputs)
    ThreatModelingCrew().crew().train(n_iterations=iterations, filename=filename, inputs=inputs)

@app.command()
def test(iterations: int, openai_model_name: str):
    inputs = build_inputs()
    validate_inputs(inputs)
    ThreatModelingCrew().crew().test(n_iterations=iterations, eval_llm=openai_model_name, inputs=inputs)

@app.command()
def replay(task_id: str):
    ThreatModelingCrew().crew().replay(task_id=task_id)

if __name__ == "__main__":
    app()
