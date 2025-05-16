import subprocess
import json
import re
import os
import hashlib
import time
from pydantic import BaseModel, ValidationError, Field, constr
from crewai.tools import BaseTool

CACHE_DIR = ".gcp_metadata_cache"
CACHE_TTL_SECONDS = 3600  # 1 hour

# ----------------------------------------
# 📦 Pydantic schema for input validation
# ----------------------------------------


class GCPMetadataInput(BaseModel):
    project_id: str = Field(
        ...,
        description="GCP project ID to extract metadata from",
        min_length=6,
        max_length=30,
        pattern=r"^[a-z][a-z0-9\-]{4,28}[a-z0-9]$",
    )

# ----------------------------------------
# 🧠 GCPMetadataTool with validation
# ----------------------------------------


class GCPMetadataTool(BaseTool):
    name: str = "GCP Metadata Extractor"
    description: str = (
        "Use this tool to collect high-level metadata from a Google Cloud project. "
        "It checks if each API is enabled and fetches resource metadata like Compute instances, "
        "Storage buckets, Cloud Functions, Pub/Sub topics, Cloud Run services, and BigQuery datasets/tables. "
        "Requires that the gcloud and bq CLIs are authenticated and installed."
    )

    def _run(self, **kwargs) -> str:
        project_id = kwargs.get("project_id")
        if not project_id:
            project_id = os.environ.get("PROJECT_ID")
        print(f"[DEBUG] [GCPMetadataTool] Using project_id: {project_id}")
        if not project_id:
            raise ValueError("PROJECT_ID must be set in the environment or passed as an argument.")
        try:
            validated = GCPMetadataInput(project_id=project_id)
            project_id = validated.project_id

            def get_cache_path(command):
                os.makedirs(CACHE_DIR, exist_ok=True)
                key = hashlib.sha256(" ".join(command).encode()).hexdigest()
                return os.path.join(CACHE_DIR, f"{project_id}_{key}.json")

            def run_gcloud(command, silent=False):
                cache_path = get_cache_path(command)
                # Check cache
                if os.path.exists(cache_path):
                    mtime = os.path.getmtime(cache_path)
                    if time.time() - mtime < CACHE_TTL_SECONDS:
                        try:
                            with open(cache_path, "r") as f:
                                print(f"[INFO] [GCPMetadataTool] Loaded cached result for: {' '.join(command)}")
                                return json.load(f)
                        except Exception:
                            pass  # Ignore cache read errors
                # Run command if not cached
                try:
                    result = subprocess.run(
                        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True)
                    try:
                        data = json.loads(result.stdout)
                        # Save to cache
                        with open(cache_path, "w") as f:
                            json.dump(data, f)
                        return data
                    except json.JSONDecodeError:
                        if not silent:
                            print(
                                f"[ERROR] Failed to parse JSON from: {' '.join(command)}")
                            print("[DEBUG] Output:")
                            print(result.stdout)
                        return None
                except subprocess.CalledProcessError as e:
                    if not silent:
                        print(f"[WARN] Command failed: {' '.join(command)}")
                        print(e.stderr)
                    return None

            def is_api_enabled(api_name):
                command = [
                    "gcloud", "services", "list",
                    "--enabled",
                    f"--project={project_id}",
                    "--format=json"
                ]
                services = run_gcloud(command, silent=True)
                if not services:
                    return False
                return any(api_name in svc["config"]["name"] for svc in services)

            def get_metadata_if_enabled(api_name, fetch_function):
                return fetch_function() if is_api_enabled(api_name) else None

            def get_compute_instances():
                return run_gcloud(["gcloud", "compute", "instances", "list", "--project", project_id, "--format=json"])

            def get_storage_buckets():
                return run_gcloud(["gcloud", "storage", "buckets", "list", "--project", project_id, "--format=json"])

            def get_cloud_functions():
                return run_gcloud(["gcloud", "functions", "list", "--project", project_id, "--format=json"])

            def get_cloud_run_services():
                return run_gcloud(["gcloud", "run", "services", "list", "--platform=managed", "--project", project_id, "--format=json"])

            def get_pubsub_topics():
                return run_gcloud(["gcloud", "pubsub", "topics", "list", "--project", project_id, "--format=json"])

            def get_bigquery_datasets_with_bq():
                datasets = run_gcloud(
                    ["bq", "ls", "--project_id", project_id, "--format=prettyjson"])
                if not datasets:
                    return None

                enriched = []
                for dataset in datasets:
                    dataset_id = dataset.get(
                        "datasetReference", {}).get("datasetId")
                    if not dataset_id:
                        continue
                    tables = run_gcloud(["bq", "ls", "--project_id", project_id,
                                        "--dataset_id", dataset_id, "--format=prettyjson"], silent=True)
                    dataset["tables"] = tables if tables else []
                    enriched.append(dataset)
                return enriched

            def get_project_iam_policy():
                return run_gcloud(["gcloud", "projects", "get-iam-policy", project_id, "--format=json"])

            metadata = {
                "compute_instances": get_metadata_if_enabled("compute.googleapis.com", get_compute_instances),
                "storage_buckets": get_metadata_if_enabled("storage.googleapis.com", get_storage_buckets),
                "cloud_functions": get_metadata_if_enabled("cloudfunctions.googleapis.com", get_cloud_functions),
                "cloud_run_services": get_metadata_if_enabled("run.googleapis.com", get_cloud_run_services),
                "pubsub_topics": get_metadata_if_enabled("pubsub.googleapis.com", get_pubsub_topics),
                "bigquery_datasets": get_metadata_if_enabled("bigquery.googleapis.com", get_bigquery_datasets_with_bq),
                "iam_policy": get_project_iam_policy()
            }

            # --- Summarization helpers ---
            def summarize_compute_instances(instances):
                summary = []
                if not instances:
                    return summary
                for inst in instances:
                    summary.append({
                        "name": inst.get("name"),
                        "zone": inst.get("zone", "").split("/")[-1],
                        "machineType": inst.get("machineType", "").split("/")[-1],
                        "publicIP": any(
                            ni.get("accessConfigs") and any(ac.get("natIP") for ac in ni["accessConfigs"])
                            for ni in inst.get("networkInterfaces", [])
                        ),
                        "serviceAccounts": [sa.get("email") for sa in inst.get("serviceAccounts", [])]
                    })
                return summary

            def summarize_storage_buckets(buckets):
                summary = []
                if not buckets:
                    return summary
                for b in buckets:
                    summary.append({
                        "name": b.get("name"),
                        "location": b.get("location"),
                        "storageClass": b.get("storageClass"),
                        "iamConfiguration": b.get("iamConfiguration", {})
                    })
                return summary

            def summarize_cloud_functions(funcs):
                summary = []
                if not funcs:
                    return summary
                for f in funcs:
                    summary.append({
                        "name": f.get("name"),
                        "entryPoint": f.get("entryPoint"),
                        "runtime": f.get("runtime"),
                        "httpsTrigger": f.get("httpsTrigger"),
                        "eventTrigger": f.get("eventTrigger")
                    })
                return summary

            def summarize_cloud_run_services(services):
                summary = []
                if not services:
                    return summary
                for s in services:
                    summary.append({
                        "name": s.get("metadata", {}).get("name"),
                        "url": s.get("status", {}).get("url"),
                        "latestCreatedRevisionName": s.get("status", {}).get("latestCreatedRevisionName")
                    })
                return summary

            def summarize_pubsub_topics(topics):
                summary = []
                if not topics:
                    return summary
                for t in topics:
                    summary.append({
                        "name": t.get("name")
                    })
                return summary

            def summarize_bigquery_datasets(datasets):
                summary = []
                if not datasets:
                    return summary
                for d in datasets:
                    summary.append({
                        "datasetId": d.get("datasetReference", {}).get("datasetId"),
                        "tables": [tbl.get("tableReference", {}).get("tableId") for tbl in d.get("tables", [])]
                    })
                return summary

            def summarize_iam_policy(policy):
                if not policy:
                    return {}
                return {
                    "bindings_count": len(policy.get("bindings", [])),
                    "roles": list({b.get("role") for b in policy.get("bindings", []) if b.get("role")})
                }

            # --- Summarize and cache full + summary ---
            summary = {
                "compute_instances": summarize_compute_instances(metadata["compute_instances"]),
                "storage_buckets": summarize_storage_buckets(metadata["storage_buckets"]),
                "cloud_functions": summarize_cloud_functions(metadata["cloud_functions"]),
                "cloud_run_services": summarize_cloud_run_services(metadata["cloud_run_services"]),
                "pubsub_topics": summarize_pubsub_topics(metadata["pubsub_topics"]),
                "bigquery_datasets": summarize_bigquery_datasets(metadata["bigquery_datasets"]),
                "iam_policy": summarize_iam_policy(metadata["iam_policy"])
            }
            # Cache summary to file
            summary_cache_path = os.path.join(CACHE_DIR, f"{project_id}_summary.json")
            with open(summary_cache_path, "w") as f:
                json.dump(summary, f, indent=2)
            print(f"[INFO] [GCPMetadataTool] Wrote summarized metadata to {summary_cache_path}")
            return json.dumps(summary, indent=2)

        except ValidationError as ve:
            return f"[ERROR] Input validation failed: {ve.json(indent=2)}"
