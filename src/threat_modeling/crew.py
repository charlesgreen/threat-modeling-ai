from typing import List
from pydantic import BaseModel, Field
from pathlib import Path
import yaml

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.tools import BaseTool  # <-- Add this import for ToolProxy
from langfuse import Langfuse

# Import your custom tools
from threat_modeling.tools.gcp_metadata_tool import GCPMetadataTool
from threat_modeling.tools.pdf_reader_tool import PDFReaderTool
from threat_modeling.tools.image_diagram_tool import ImageDiagramTool
from threat_modeling.tools.stride_threat_modeler_tool import STRIDEThreatModelerTool
from threat_modeling.tools.csv_risk_exporter import CSVRiskExporterTool

langfuse = Langfuse()

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

    agents_config_path = str(CONFIG_PATH / "agents.yaml")
    tasks_config_path = str(CONFIG_PATH / "tasks.yaml")

    def __init__(self):
        # Load YAML configs as dicts
        with open(self.agents_config_path, 'r') as f:
            self.agents_config = yaml.safe_load(f)
        with open(self.tasks_config_path, 'r') as f:
            self.tasks_config = yaml.safe_load(f)
        print(f"[DEBUG] Loaded agents_config keys: {list(self.agents_config.keys())}")
        print(f"[DEBUG] Loaded tasks_config keys: {list(self.tasks_config.keys())}")

        # --- Config validation ---
        required_agent_fields = ["role", "goal", "backstory"]
        for agent_name, agent_cfg in self.agents_config.items():
            for field in required_agent_fields:
                if field not in agent_cfg or not agent_cfg[field]:
                    raise ValueError(f"Agent config '{agent_name}' missing required field: '{field}'")
        required_task_fields = ["description", "expected_output"]
        for task_name, task_cfg in self.tasks_config.items():
            for field in required_task_fields:
                if field not in task_cfg or not task_cfg[field]:
                    raise ValueError(f"Task config '{task_name}' missing required field: '{field}'")
        print("[DEBUG] Agent/task config validation passed.")

    # AGENTS

    @agent
    def resource_extraction_agent(self) -> Agent:
        cfg = self.agents_config["resource_extraction_agent"]
        trace = langfuse.trace(name="resource-extraction", input={"task": "extract_resources"})
        # Debug: print agent creation
        print(f"[DEBUG] Creating resource_extraction_agent with tools: GCPMetadataTool, PDFReaderTool, ImageDiagramTool")
        agent = Agent(
            role=cfg["role"],
            goal=cfg["goal"],
            backstory=cfg["backstory"],
            config=cfg,
            tools=[
                GCPMetadataTool(),
                PDFReaderTool(),
                ImageDiagramTool()
            ],
            allow_delegation=False,
            verbose=True,
        )
        return agent

    @agent
    def threat_modeling_agent(self) -> Agent:
        cfg = self.agents_config["threat_modeling_agent"]
        trace = langfuse.trace(name="threat-modeling", input={"task": "stride_threat_modeling"})
        import json
        class ToolProxy(BaseTool):
            def __init__(self, wrapped_tool):
                super().__init__(name=wrapped_tool.name, description=wrapped_tool.description)
                self._wrapped_tool = wrapped_tool
            def _run(self, *args, **kwargs):
                print(f"[DEBUG] [threat_modeling_agent] ToolProxy for {self.name} called with args: {args}, kwargs: {kwargs}")
                # Always pass a single keyword arg: summarized_input=<string>
                summarized_input = None
                if args and len(args) == 1:
                    if isinstance(args[0], dict):
                        summarized_input = json.dumps(args[0])
                    elif isinstance(args[0], str):
                        summarized_input = args[0]
                    else:
                        summarized_input = str(args[0])
                elif kwargs and 'summarized_input' in kwargs:
                    summarized_input = kwargs['summarized_input']
                elif kwargs:
                    # If kwargs is a dict, dump as JSON
                    summarized_input = json.dumps(kwargs)
                else:
                    summarized_input = ""
                print(f"[DEBUG] [threat_modeling_agent] Passing summarized_input to STRIDEThreatModelerTool: {summarized_input[:200]}...")
                return self._wrapped_tool._run(summarized_input=summarized_input)
            def __getattr__(self, attr):
                if attr in ("_wrapped_tool", "__class__", "__dict__", "__weakref__", "__module__", "__init__", "_run", "__getattr__"):
                    return object.__getattribute__(self, attr)
                return getattr(self._wrapped_tool, attr)
        agent = Agent(
            role=cfg["role"],
            goal=cfg["goal"],
            backstory=cfg["backstory"],
            config=cfg,
            tools=[
                ToolProxy(STRIDEThreatModelerTool())
            ],
            allow_delegation=False,
            verbose=True,
        )
        return agent

    @agent
    def risk_export_agent(self) -> Agent:
        cfg = self.agents_config["risk_export_agent"]
        trace = langfuse.trace(name="risk-export", input={"task": "export_risks"})
        agent = Agent(
            role=cfg["role"],
            goal=cfg["goal"],
            backstory=cfg["backstory"],
            config=cfg,
            tools=[
                CSVRiskExporterTool()
            ],
            allow_delegation=False,
            verbose=True,
        )
        return agent

    # TASKS

    @task
    def extract_resources_task(self) -> Task:
        cfg = self.tasks_config["extract_resources_task"]
        description = cfg["description"]
        # After resource extraction, summarized GCP data is cached by GCPMetadataTool
        return Task(
            description=description,
            expected_output=cfg["expected_output"],
            agent=self.resource_extraction_agent(),
        )

    @task
    def stride_threat_modeling_task(self) -> Task:
        cfg = self.tasks_config["stride_threat_modeling_task"]
        # Load summarized GCP data from cache (if available)
        import os, json
        CACHE_DIR = ".gcp_metadata_cache"
        from dotenv import load_dotenv
        load_dotenv()
        project_id = os.environ.get("PROJECT_ID")
        summary_path = os.path.join(CACHE_DIR, f"{project_id}_summary.json")
        gcp_summary = ""
        if os.path.exists(summary_path):
            with open(summary_path, "r") as f:
                gcp_summary = f.read()
        else:
            gcp_summary = "[ERROR] GCP summary not found. Run resource extraction first."
        # Pass only the summarized GCP data as the task description
        description = (
            cfg["description"]
            + "\n\nGCP Metadata Summary (for threat modeling, do not request full details):\n"
            + gcp_summary
        )
        return Task(
            description=description,
            expected_output=cfg["expected_output"],
            agent=self.threat_modeling_agent(),
        )

    @task
    def export_risks_task(self) -> Task:
        cfg = self.tasks_config["export_risks_task"]
        return Task(
            description=cfg["description"],
            expected_output=cfg["expected_output"],
            agent=self.risk_export_agent(),
            output_file="threat_model.csv",  # Saves final CSV to file
        )

    # CREW

    @crew
    def crew(self, inputs=None) -> Crew:
        """Creates the Threat Modeling Crew"""
        return Crew(
            agents=[
                self.resource_extraction_agent(),
                self.threat_modeling_agent(),
                self.risk_export_agent(),
            ],
            tasks=[
                self.extract_resources_task(),
                self.stride_threat_modeling_task(),
                self.export_risks_task(),
            ],
            process=Process.sequential,  # Executes tasks in order
            verbose=True,
        )
