"""
Service module for MLflow API interactions.
Provides functions to interact with MLflow API endpoints.
"""

import time
import requests
import json
import traceback
from typing import Optional, Tuple, Dict, List, Any
from backend.core.config import settings

def get_experiment_id_by_name(exp_name: str) -> Optional[str]:
    """
    Get experiment ID by name from MLflow with enhanced debugging.
    """
    print(f"[DEBUG] Looking up experiment ID for name: '{exp_name}'")
    
    try:
        # First, try direct lookup with the API
        url = f"{settings.MLFLOW_TRACKING_URI}/api/2.0/mlflow/experiments/get-by-name"
        params = {"experiment_name": exp_name}
        
        print(f"[DEBUG] Making request to: {url} with params: {params}")
        
        res = requests.get(url, params=params, timeout=10)
        
        print(f"[DEBUG] API response code: {res.status_code}")
        if res.status_code != 200:
            print(f"[DEBUG] API error response: {res.text}")
        
        if res.ok:
            data = res.json()
            exp_id = data["experiment"]["experiment_id"]
            print(f"[DEBUG] Found experiment ID: {exp_id}")
            return exp_id
        
        # List all experiments as fallback
        print("[DEBUG] Direct lookup failed, listing all experiments as fallback")
        list_url = f"{settings.MLFLOW_TRACKING_URI}/api/2.0/mlflow/experiments/list"
        list_res = requests.get(list_url, timeout=10)
        
        if list_res.ok:
            experiments = list_res.json().get("experiments", [])
            print(f"[DEBUG] Found {len(experiments)} total experiments")
            
            # Try exact match first
            for exp in experiments:
                print(f"[DEBUG] Comparing '{exp.get('name')}' with '{exp_name}'")
                if exp.get("name") == exp_name:
                    print(f"[DEBUG] Found exact match with ID: {exp.get('experiment_id')}")
                    return exp.get("experiment_id")
            
            print("[DEBUG] No matching experiment found")
        else:
            print(f"[DEBUG] Failed to list experiments. Status: {list_res.status_code}")
        
    except requests.RequestException as e:
        print(f"[DEBUG] Request exception: {str(e)}")
    except Exception as e:
        print(f"[DEBUG] Unexpected error in get_experiment_id_by_name: {str(e)}")
        traceback.print_exc()
    
    print(f"[DEBUG] No experiment found with name: '{exp_name}'")
    return None

def get_experiment_by_id(experiment_id: str) -> Tuple[bool, str, Optional[Dict]]:
    """
    Get experiment details by ID from MLflow with enhanced debugging.
    """
    print(f"[DEBUG] Getting experiment details for ID: '{experiment_id}'")
    
    try:
        url = f"{settings.MLFLOW_TRACKING_URI}/api/2.0/mlflow/experiments/get"
        params = {"experiment_id": experiment_id}
        
        print(f"[DEBUG] Making request to: {url} with params: {params}")
        
        res = requests.get(url, params=params, timeout=10)
        
        print(f"[DEBUG] API response code: {res.status_code}")
        if res.status_code != 200:
            print(f"[DEBUG] API error response: {res.text}")
        
        if res.ok:
            data = res.json()
            print(f"[DEBUG] Got experiment details: {json.dumps(data, indent=2)[:200]}...")
            return True, "Experiment details retrieved successfully", data["experiment"]
        
        error_message = f"Failed to retrieve experiment details: {res.text}"
        print(f"[DEBUG] {error_message}")
        return False, error_message, None
        
    except requests.RequestException as e:
        error_message = f"Request error: {str(e)}"
        print(f"[DEBUG] {error_message}")
        return False, error_message, None
    except Exception as e:
        error_message = f"Unexpected error in get_experiment_by_id: {str(e)}"
        print(f"[DEBUG] {error_message}")
        traceback.print_exc()
        return False, error_message, None

def create_experiment(experiment_name: str) -> Tuple[bool, str]:
    """
    Create a new experiment in MLflow.
    
    Args:
        experiment_name: Name for the new experiment
        
    Returns:
        Tuple of (success, result_or_error_message)
    """
    create_url = f"{settings.MLFLOW_TRACKING_URI}/api/2.0/mlflow/experiments/create"
    headers = {"Content-Type": "application/json"}
    payload = {"name": experiment_name}
    try:
        mlflow_res = requests.post(create_url, json=payload, headers=headers)
        if mlflow_res.ok:
            mlflow_data = mlflow_res.json()
            exp_id = mlflow_data.get("experiment_id", "UNKNOWN")
            return True, exp_id
        else:
            return False, mlflow_res.text
    except requests.RequestException as e:
        return False, str(e)

def create_run(experiment_id: str, run_name: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
    """
    Create a new run in MLflow.
    
    Args:
        experiment_id: The experiment ID to create the run in
        run_name: Optional name for the run
        
    Returns:
        Tuple of (success, message, run_id)
    """
    run_url = f"{settings.MLFLOW_TRACKING_URI}/api/2.0/mlflow/runs/create"
    headers = {"Content-Type": "application/json"}
    run_payload = {"experiment_id": experiment_id}
    if run_name:
        run_payload["tags"] = [{"key": "mlflow.runName", "value": run_name}]

    try:
        run_res = requests.post(run_url, json=run_payload, headers=headers)
        if run_res.ok:
            run_data = run_res.json()
            run_id = run_data["run"]["info"]["run_id"]
            return True, f"Run created in experiment {experiment_id}, run_id: {run_id}", run_id
        else:
            return False, run_res.text, None
    except requests.RequestException as e:
        return False, str(e), None

def log_param(run_id: str, key: str, value: str) -> Tuple[bool, str]:
    """
    Log a parameter to a run in MLflow.
    
    Args:
        run_id: The run ID to log to
        key: Parameter name
        value: Parameter value
        
    Returns:
        Tuple of (success, message)
    """
    url = f"{settings.MLFLOW_TRACKING_URI}/api/2.0/mlflow/runs/log-parameter"
    payload = {"run_id": run_id, "key": key, "value": value}
    headers = {"Content-Type": "application/json"}
    try:
        res = requests.post(url, json=payload, headers=headers)
        if res.ok:
            return True, f"Logged param '{key}':'{value}' to run {run_id}"
        else:
            return False, res.text
    except requests.RequestException as e:
        return False, str(e)

def log_metric(run_id: str, key: str, value: float, step: Optional[int] = 0) -> Tuple[bool, str]:
    """
    Log a metric to a run in MLflow.
    
    Args:
        run_id: The run ID to log to
        key: Metric name
        value: Metric value
        step: Step number (default: 0)
        
    Returns:
        Tuple of (success, message)
    """
    url = f"{settings.MLFLOW_TRACKING_URI}/api/2.0/mlflow/runs/log-metric"
    payload = {"run_id": run_id, "key": key, "value": value, "timestamp": int(time.time()), "step": step}
    headers = {"Content-Type": "application/json"}
    try:
        res = requests.post(url, json=payload, headers=headers)
        if res.ok:
            return True, f"Logged metric '{key}':{value} to run {run_id} at step {step}"
        else:
            return False, res.text
    except requests.RequestException as e:
        return False, str(e)

def delete_experiment(experiment_id: str) -> Tuple[bool, str]:
    """
    Archives (deletes) an experiment by ID using MLflow's experiments/delete endpoint.
    
    Args:
        experiment_id: The experiment ID to delete
        
    Returns:
        Tuple of (success, message)
    """
    delete_url = f"{settings.MLFLOW_TRACKING_URI}/api/2.0/mlflow/experiments/delete"
    headers = {"Content-Type": "application/json"}
    payload = {"experiment_id": experiment_id}
    try:
        res = requests.post(delete_url, json=payload, headers=headers)
        if res.ok:
            return True, f"Experiment {experiment_id} was deleted."
        else:
            return False, res.text
    except requests.RequestException as e:
        return False, str(e)

def delete_run(run_id: str) -> Tuple[bool, str]:
    """
    Deletes a run by ID using MLflow's runs/delete endpoint.
    
    Args:
        run_id: The run ID to delete
        
    Returns:
        Tuple of (success, message)
    """
    delete_url = f"{settings.MLFLOW_TRACKING_URI}/api/2.0/mlflow/runs/delete"
    headers = {"Content-Type": "application/json"}
    payload = {"run_id": run_id}
    try:
        res = requests.post(delete_url, json=payload, headers=headers)
        if res.ok:
            return True, f"Run {run_id} was deleted."
        else:
            return False, res.text
    except requests.RequestException as e:
        return False, str(e)
    


def list_experiments() -> Tuple[bool, str, List[Dict]]:
    """
    List all experiments in MLflow.
    
    Returns:
        Tuple of (success, message, experiments_list)
    """
    try:
        url = f"{settings.MLFLOW_TRACKING_URI}/api/2.0/mlflow/experiments/list"
        res = requests.get(url)
        if res.ok:
            data = res.json()
            return True, "Experiments retrieved successfully", data.get("experiments", [])
        return False, f"Failed to list experiments: {res.text}", []
    except requests.RequestException as e:
        return False, f"Request error: {str(e)}", []

def list_runs(experiment_id: str) -> Tuple[bool, str, List[Dict]]:
    """
    List all runs for an experiment in MLflow.
    
    Args:
        experiment_id: The experiment ID to list runs for
        
    Returns:
        Tuple of (success, message, runs_list)
    """
    try:
        url = f"{settings.MLFLOW_TRACKING_URI}/api/2.0/mlflow/runs/search"
        payload = {"experiment_ids": [experiment_id]}
        res = requests.post(url, json=payload)
        if res.ok:
            data = res.json()
            return True, "Runs retrieved successfully", data.get("runs", [])
        return False, f"Failed to list runs: {res.text}", []
    except requests.RequestException as e:
        return False, f"Request error: {str(e)}", []

def get_mlflow_summary_stats() -> Dict[str, Any]:
    """
    Get summary statistics about MLflow experiments and models.
    
    Returns:
        Dictionary with summary statistics
    """
    try:
        # Get experiment count
        exp_success, _, experiments = list_experiments()
        experiment_count = len(experiments) if exp_success else 0
        
        # Get registered model count
        models_url = f"{settings.MLFLOW_TRACKING_URI}/api/2.0/mlflow/registered-models/list"
        models_res = requests.get(models_url)
        registered_models = []
        if models_res.ok:
            registered_models = models_res.json().get("registered_models", [])
        
        # Get total run count across all experiments
        total_runs = 0
        active_runs = 0
        for exp in experiments:
            exp_id = exp.get("experiment_id")
            runs_success, _, runs = list_runs(exp_id)
            if runs_success:
                total_runs += len(runs)
                active_runs += sum(1 for r in runs if r.get("info", {}).get("status") == "RUNNING")
        
        return {
            "experiment_count": experiment_count,
            "registered_model_count": len(registered_models),
            "total_runs": total_runs,
            "active_runs": active_runs,
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "error": str(e),
            "timestamp": time.time()
        }

def get_model_versions(model_name: str) -> Tuple[bool, str, List[Dict]]:
    """
    Get versions for a specific registered model.
    
    Args:
        model_name: Name of the registered model
        
    Returns:
        Tuple of (success, message, model_versions)
    """
    try:
        url = f"{settings.MLFLOW_TRACKING_URI}/api/2.0/mlflow/model-versions/search"
        payload = {"filter": f"name='{model_name}'"}
        res = requests.post(url, json=payload)
        
        if res.ok:
            data = res.json()
            versions = data.get("model_versions", [])
            return True, f"Found {len(versions)} versions for model '{model_name}'", versions
        return False, f"Failed to get model versions: {res.text}", []
    except requests.RequestException as e:
        return False, f"Request error: {str(e)}", []

def get_registered_models() -> Tuple[bool, str, List[Dict]]:
    """
    Get all registered models from MLflow.
    
    Returns:
        Tuple of (success, message, registered_models)
    """
    try:
        url = f"{settings.MLFLOW_TRACKING_URI}/api/2.0/mlflow/registered-models/list"
        res = requests.get(url)
        
        if res.ok:
            data = res.json()
            models = data.get("registered_models", [])
            return True, f"Found {len(models)} registered models", models
        return False, f"Failed to get registered models: {res.text}", []
    except requests.RequestException as e:
        return False, f"Request error: {str(e)}", []

def get_model_details(model_name: str, version: Optional[str] = None) -> Tuple[bool, str, Dict]:
    """
    Get detailed information about a specific model version.
    
    Args:
        model_name: Name of the registered model
        version: Optional specific version to retrieve (latest if not specified)
        
    Returns:
        Tuple of (success, message, model_details)
    """
    try:
        # First get all versions if no specific version is requested
        if not version:
            success, _, versions = get_model_versions(model_name)
            if not success or not versions:
                return False, f"No versions found for model '{model_name}'", {}
            # Get the latest version
            versions.sort(key=lambda v: int(v.get("version", 0)), reverse=True)
            version = versions[0].get("version")
        
        # Get details for the specific version
        url = f"{settings.MLFLOW_TRACKING_URI}/api/2.0/mlflow/model-versions/get"
        params = {"name": model_name, "version": version}
        res = requests.get(url, params=params)
        
        if res.ok:
            data = res.json().get("model_version", {})
            return True, f"Retrieved details for {model_name} version {version}", data
        return False, f"Failed to get model details: {res.text}", {}
    except requests.RequestException as e:
        return False, f"Request error: {str(e)}", {}

def get_recently_updated_models(limit: int = 5) -> Tuple[bool, str, List[Dict]]:
    """
    Get the most recently updated registered models.
    
    Args:
        limit: Maximum number of models to return
        
    Returns:
        Tuple of (success, message, models)
    """
    try:
        success, _, models = get_registered_models()
        if not success or not models:
            return False, "No registered models found", []
        
        # Sort by last updated timestamp (descending)
        sorted_models = sorted(
            models,
            key=lambda m: m.get("last_updated_timestamp", 0),
            reverse=True
        )
        
        # Take the top N models
        top_models = sorted_models[:limit]
        
        return True, f"Retrieved {len(top_models)} recently updated models", top_models
    except Exception as e:
        return False, f"Error retrieving recent models: {str(e)}", []

def batch_create_experiments(experiment_names: List[str]) -> List[Dict[str, Any]]:
    """
    Create multiple experiments in MLflow.
    
    Args:
        experiment_names: List of names for new experiments
        
    Returns:
        List of dictionaries with experiment creation results
    """
    results = []
    for name in experiment_names:
        success, result = create_experiment(name)
        results.append({
            "experiment_name": name,
            "success": success,
            "result": result
        })
    return results

def get_runs_with_model_info(experiment_id: str) -> Tuple[bool, str, List[Dict]]:
    """
    Get runs for an experiment with model information if available.
    
    Args:
        experiment_id: The experiment ID to list runs for
        
    Returns:
        Tuple of (success, message, enhanced_runs_list)
    """
    try:
        success, msg, runs = list_runs(experiment_id)
        if not success:
            return False, msg, []
        
        enhanced_runs = []
        for run in runs:
            run_id = run.get("info", {}).get("run_id")
            
            # Get artifacts for this run
            artifacts_url = f"{settings.MLFLOW_TRACKING_URI}/api/2.0/mlflow/artifacts/list"
            params = {"run_id": run_id}
            artifacts_res = requests.get(artifacts_url, params=params)
            
            model_info = {}
            if artifacts_res.ok:
                artifacts = artifacts_res.json().get("files", [])
                # Check for MLmodel file which indicates a model was logged
                model_files = [a for a in artifacts if a.get("path", "").endswith("MLmodel")]
                if model_files:
                    model_info["has_model"] = True
                    model_info["model_artifacts"] = model_files
            
            # Add model info to the run
            run["model_info"] = model_info
            enhanced_runs.append(run)
        
        return True, f"Retrieved {len(enhanced_runs)} runs with model information", enhanced_runs
    except requests.RequestException as e:
        return False, f"Request error: {str(e)}", []
    
def get_recently_used_models(limit: int = 5) -> Tuple[bool, str, List[Dict]]:
    """
    Get most recently used models based on recent runs.
    
    Args:
        limit: Maximum number of models to return
        
    Returns:
        Tuple of (success, message, model_usage_info)
    """
    try:
        # First get all registered models
        success, _, models = get_registered_models()
        if not success or not models:
            return False, "No registered models found", []
        
        # Map of model name to its usage info
        model_usage = {}
        
        # Get recent active runs across all experiments
        exp_success, _, experiments = list_experiments()
        if not exp_success:
            return False, "Failed to retrieve experiments", []
        
        # Collect recent runs with model references
        all_recent_runs = []
        for exp in experiments:
            exp_id = exp.get("experiment_id")
            runs_success, _, runs = list_runs(exp_id)
            if runs_success:
                all_recent_runs.extend(runs)
        
        # Sort by start time (most recent first)
        all_recent_runs.sort(
            key=lambda r: int(r.get("info", {}).get("start_time", 0)),
            reverse=True
        )
        
        # Take top runs
        top_recent_runs = all_recent_runs[:100]  # Consider up to 100 recent runs
        
        # For each run, check if it has model references
        for run in top_recent_runs:
            run_id = run.get("info", {}).get("run_id")
            
            # Look for model versions associated with this run
            for model in models:
                model_name = model.get("name")
                
                # Get versions for this model
                version_success, _, versions = get_model_versions(model_name)
                if version_success:
                    # Check if any version is associated with this run
                    for version in versions:
                        if version.get("run_id") == run_id:
                            # This run is associated with this model
                            if model_name not in model_usage:
                                model_usage[model_name] = {
                                    "name": model_name,
                                    "recent_runs": [],
                                    "latest_timestamp": 0
                                }
                            
                            # Add run info to model usage
                            start_time = int(run.get("info", {}).get("start_time", 0))
                            model_usage[model_name]["recent_runs"].append({
                                "run_id": run_id,
                                "timestamp": start_time,
                                "version": version.get("version")
                            })
                            
                            # Update latest timestamp if newer
                            if start_time > model_usage[model_name]["latest_timestamp"]:
                                model_usage[model_name]["latest_timestamp"] = start_time
        
        # Sort models by latest timestamp
        sorted_models = sorted(
            model_usage.values(),
            key=lambda m: m.get("latest_timestamp", 0),
            reverse=True
        )
        
        # Take top N models
        top_models = sorted_models[:limit]
        
        return True, f"Retrieved {len(top_models)} recently used models", top_models
    except Exception as e:
        return False, f"Error retrieving recently used models: {str(e)}", []
    
def batch_create_experiments(experiment_names: List[str]) -> List[Dict[str, Any]]:
    """
    Create multiple experiments in MLflow.
    
    Args:
        experiment_names: List of names for new experiments
        
    Returns:
        List of dictionaries with experiment creation results
    """
    results = []
    for name in experiment_names:
        success, result = create_experiment(name)
        results.append({
            "experiment_name": name,
            "success": success,
            "result": result
        })
    return results

def batch_create_runs(experiment_id: str, run_names: List[str]) -> List[Dict[str, Any]]:
    """
    Create multiple runs in an MLflow experiment.
    
    Args:
        experiment_id: The experiment ID to create runs in
        run_names: List of names for new runs
        
    Returns:
        List of dictionaries with run creation results
    """
    results = []
    for name in run_names:
        success, msg, run_id = create_run(experiment_id, name)
        results.append({
            "run_name": name,
            "success": success,
            "message": msg,
            "run_id": run_id if success else None
        })
    return results