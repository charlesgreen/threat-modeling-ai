from typing import List
from pydantic import BaseModel, Field
from pathlib import Path

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

# Import your custom tools
from threat_modeling.tools.gcp_metadata_tool import GCPMetadataTool
from threat_modeling.tools.pdf_reader_tool import PDFReaderTool
from threat_modeling.tools.image_diagram_tool import ImageDiagramTool
from threat_modeling.tools.stride_threat_modeler_tool import STRIDEThreatModelerTool
from threat_modeling.tools.csv_risk_exporter import CSVRiskExporterTool

# Optional schema for validating threat output
class ThreatEntry(BaseModel):
    threat: str
    asset: str
    category: str
    likelihood: str
    impact: str
    mitigation: str

# Dynamically resolve the config file paths relative to this file
CONFIG_PATH = Path(__file__).parent / "config"

@CrewBase
class ThreatModelingCrew:
    """Threat Modeling Crew"""

    agents_config = str(CONFIG_PATH / "agents.yaml")  # ✅ Cast to string
    tasks_config = str(CONFIG_PATH / "tasks.yaml")    # ✅ Cast to string

    # AGENTS

    @agent
    def resource_extraction_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["resource_extraction_agent"],
            tools=[
                GCPMetadataTool(),
                PDFReaderTool(),
                ImageDiagramTool()
            ],
            allow_delegation=False,
            verbose=True,
        )

    @agent
    def threat_modeling_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["threat_modeling_agent"],
            tools=[
                STRIDEThreatModelerTool()
            ],
            allow_delegation=False,
            verbose=True,
        )

    @agent
    def risk_export_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["risk_export_agent"],
            tools=[
                CSVRiskExporterTool()
            ],
            allow_delegation=False,
            verbose=True,
        )

    # TASKS

    @task
    def extract_resources_task(self) -> Task:
        return Task(
            config=self.tasks_config["extract_resources_task"],
            agent=self.resource_extraction_agent(),
        )

    @task
    def stride_threat_modeling_task(self) -> Task:
        return Task(
            config=self.tasks_config["stride_threat_modeling_task"],
            agent=self.threat_modeling_agent(),
        )

    @task
    def export_risks_task(self) -> Task:
        return Task(
            config=self.tasks_config["export_risks_task"],
            agent=self.risk_export_agent(),
            output_file="threat_model.csv",  # Saves final CSV to file
        )

    # CREW

    @crew
    def crew(self) -> Crew:
        """Creates the Threat Modeling Crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,  # Executes tasks in order
            verbose=True,
        )
