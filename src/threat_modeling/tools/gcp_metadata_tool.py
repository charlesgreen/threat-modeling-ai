from crewai_tools import BaseTool
import subprocess
import json

class GCPMetadataTool(BaseTool):
    name: str = "GCP Metadata Extractor"
    description: str = (
        "Use this tool to collect high-level metadata from a Google Cloud project. "
        "It checks if each API is enabled and fetches resource metadata like Compute instances, "
        "Storage buckets, Cloud Functions, Pub/Sub topics, Cloud Run services, and BigQuery datasets/tables. "
        "Requires that the gcloud and bq CLIs are authenticated and installed."
    )

    def _run(self, project_id: str) -> str:
        def run_gcloud(command, silent=False):
            try:
                result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True)
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    if not silent:
                        print(f"[ERROR] Failed to parse JSON from: {' '.join(command)}")
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
            if is_api_enabled(api_name):
                return fetch_function()
            else:
                return None

        # Resource fetch functions
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
            datasets = run_gcloud(["bq", "ls", "--project_id", project_id, "--format=prettyjson"])
            if not datasets:
                return None

            enriched = []
            for dataset in datasets:
                dataset_id = dataset.get("datasetReference", {}).get("datasetId")
                if not dataset_id:
                    continue
                tables = run_gcloud(["bq", "ls", "--project_id", project_id, "--dataset_id", dataset_id, "--format=prettyjson"], silent=True)
                dataset["tables"] = tables if tables else []
                enriched.append(dataset)
            return enriched

        def get_project_iam_policy():
            return run_gcloud(["gcloud", "projects", "get-iam-policy", project_id, "--format=json"])

        # Collect metadata
        metadata = {
            "compute_instances": get_metadata_if_enabled("compute.googleapis.com", get_compute_instances),
            "storage_buckets": get_metadata_if_enabled("storage.googleapis.com", get_storage_buckets),
            "cloud_functions": get_metadata_if_enabled("cloudfunctions.googleapis.com", get_cloud_functions),
            "cloud_run_services": get_metadata_if_enabled("run.googleapis.com", get_cloud_run_services),
            "pubsub_topics": get_metadata_if_enabled("pubsub.googleapis.com", get_pubsub_topics),
            "bigquery_datasets": get_metadata_if_enabled("bigquery.googleapis.com", get_bigquery_datasets_with_bq),
            "iam_policy": get_project_iam_policy()
        }

        return json.dumps(metadata, indent=2)
