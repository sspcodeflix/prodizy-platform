"""
MLflow router module for handling MLflow chatbot endpoints.
"""

import json
import time
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel
import requests

from backend.models.chat import ChatRequest, ChatResponse
from backend.models.invitation import invitation_store
from backend.utils.session_store import (
    get_conversation_history,
    append_to_conversation,
    get_session_data,
    set_session_data,
)
from backend.core.services.llm_service import (
    generate_chat_response,
    get_available_providers,
    get_provider_models,
)
from backend.core.services.mlflow_service import (
    get_experiment_id_by_name,
    create_experiment,
    create_run,
    log_param,
    log_metric,
    delete_experiment,
    delete_run,
    get_experiment_by_id,
    list_experiments,
    list_runs,
    get_mlflow_summary_stats,
    get_model_details,
    get_model_versions,
    get_recently_updated_models,
    get_registered_models,
    get_runs_with_model_info,
    get_recently_used_models,
    batch_create_experiments,
    batch_create_runs,
)
from backend.core.config import settings

# Create API router
router = APIRouter()


# Models for LLM-related endpoints
class ProviderModelRequest(BaseModel):
    provider_id: str
    invitation_code: str


class LLMProviderInfo(BaseModel):
    providers: List[Dict[str, Any]]


class LLMModelsInfo(BaseModel):
    models: List[Dict[str, Any]]


# Add provider/model endpoints
@router.get("/providers", response_model=LLMProviderInfo)
async def list_llm_providers():
    """Get a list of available LLM providers."""
    return {"providers": get_available_providers()}


@router.post("/provider-models", response_model=LLMModelsInfo)
async def get_models_for_provider(request: ProviderModelRequest):
    """Get available models for a specific provider."""
    # Validate the invitation code
    validation = invitation_store.validate_code(
        request.invitation_code, "model-listing"
    )
    if not validation["valid"]:
        raise HTTPException(status_code=403, detail=validation["message"])

    # Get the models for the requested provider
    models = get_provider_models(request.provider_id)
    return {"models": models}


@router.post("/mlflow", response_model=ChatResponse)
async def chatbot_mlflow(request: ChatRequest) -> ChatResponse:
    """
    Extended MLflow Chatbot that:
      1) Creates experiments
      2) Creates runs (by name or ID)
      3) Logs parameters and metrics
      4) Handles "create_experiment_and_start_run"
      5) Provides user-friendly plain-text instructions if info is missing
      6) Remembers the last created run ID in session_data so user can omit run_id
      7) Supports "delete_experiment" and "delete_run" via new intents
      8) Supports multiple LLM providers and models
      9) Validates invitation codes and tracks request usage
    """

    # --------------------------------------------------------
    # 1) Retrieve session ID and user query
    # --------------------------------------------------------
    session_id = request.session_id
    user_query = request.query
    invitation_code = request.invitation_code

    # --------------------------------------------------------
    # 2) Validate invitation code
    # --------------------------------------------------------
    validation = invitation_store.validate_code(invitation_code, session_id)
    if not validation["valid"]:
        parsed_response = {
            "intent": "error",
            "confirmation": "needs_clarification",
            "message": f"Invitation code error: {validation['message']} \
            Please contact hey@prodizyplatform.in to request a new invitation code.",
        }
        return {"assistant_response": parsed_response}

    # --------------------------------------------------------
    # 3) Access conversation history & Append user message
    # --------------------------------------------------------
    conversation_history = get_conversation_history(session_id)
    append_to_conversation(session_id, "user", user_query)

    # (DEBUG) Print entire conversation history
    print(f"[DEBUG] session_id={session_id} - Conversation History:")
    for i, msg in enumerate(conversation_history, 1):
        print(f"  {i}. {msg['role'].upper()}: {msg['content']}")
    print("[DEBUG] End of conversation history\n")

    # --------------------------------------------------------
    # 4) System instructions
    # --------------------------------------------------------
    system_instructions = """
You are an intelligent MLflow assistant.
Below is the conversation history between you and the user.
Use this history to figure out the user's most recent request.

Respond with JSON in this format:
{
  "intent": "...",
  "entities": {...},
  "confirmation": "confirmed" | "canceled" | "needs_clarification",
  "message": "short user-facing text"
}

# Intent Selection Guidelines
- When the user asks for SPECIFIC information requiring database lookups (like "show me model X", "list runs in experiment Y"), use the appropriate specific intent.
- When the user asks GENERAL questions about MLflow (like "who created MLflow", "what is MLflow used for"), use "other_intent" with no entities.
- Never use a specific data-fetching intent like "get_model_versions" when answering general knowledge questions.

# Examples:
For "Who created MLflow?":
{
  "intent": "other_intent",
  "entities": {},
  "confirmation": "confirmed",
  "message": "MLflow was developed by Databricks, a company founded by the original creators of Apache Spark."
}

For "Show me versions of model sentiment-analysis":
{
  "intent": "get_model_versions",
  "entities": {"model_name": "sentiment-analysis"},
  "confirmation": "confirmed",
  "message": "Fetching versions for model 'sentiment-analysis'..."
}

# Specific Intent Purposes:
- get_model_versions: ONLY for retrieving specific model versions when a model name is provided
- get_experiment_details: ONLY for retrieving specific experiment details when an experiment name/ID is provided
- list_runs: ONLY for listing runs in a specific experiment
- get_registered_models: ONLY for listing all registered models in the system

Intents can be:
- create_experiment
- create_experiment_and_start_run
- create_run
- delete_experiment
- delete_run
- log_param
- log_metric
- get_experiment_details
- batch_create_experiments
- get_mlflow_summary
- get_model_versions
- get_model_details
- get_recent_models
- get_models_with_artifacts
- get_registered_models
- list_experiments
- list_runs
- batch_create_experiments
- batch_create_runs
- other_intent  # Use this for general information and questions

When a user asks about a specific experiment by name:
- Extract the FULL experiment name exactly as provided, including any spaces, numbers, or special characters
- Pay special attention to experiment names that have unusual formats like "sklearn - 1" 
- Do not split or modify the experiment name in any way

For example, for queries like:
- "Get details about experiment sklearn - 1" → extract experiment_name: "sklearn - 1"
- "Show me experiment sklearn-test" → extract experiment_name: "sklearn-test"
- "What is experiment sklearn_model" → extract experiment_name: "sklearn_model"

If the user wants to create multiple experiments at once, use "batch_create_experiments".
If the user wants to create multiple runs at once, use "batch_create_runs".
If the user asks for recently used models, use "get_recently_used_models" intent.
If the user asks questions like "how many models are there", "how many experiments exist",
use the "get_mlflow_summary" intent.
If the user asks about model versions, who logged a model, use "get_model_versions" or 
"get_model_details" as appropriate.
If the user asks about artifact locations, use "get_model_details".
If the user wants to create multiple experiments at once, use "batch_create_experiments".
If the user asks for recent models, use "get_recent_models".

If the user is missing a detail, set "confirmation" to "needs_clarification"
and in "message" provide a clear, plain-text request.
Never use 'add_metric'. Use 'log_metric' exactly. 
If the user says 'add metric', convert that request to 'log_metric' 
in your final JSON output.
No extra JSON examples. Return only valid JSON.
When the user wants to log a metric, you must use "metric_key" and "metric_value" exactly. Do not use "key", "value", or "metric_name". For instance:
{
  "intent": "log_metric",
  "entities": {
      "run_id": "...",
      "metric_key": "...",
      "metric_value": "...",
      "step": 0
  },
  "confirmation": "confirmed",
  "message": "..."
}

If the user uses synonyms, convert them to the correct JSON keys.
When the user wants to log a parameter, you must use "param_key" and "param_value" exactly.
"""

    # --------------------------------------------------------
    # 5) Build the messages for LLM
    # --------------------------------------------------------
    messages = [{"role": "system", "content": system_instructions}]
    messages.extend(conversation_history)

    # (DEBUG) Print prompt to LLM
    print("[DEBUG] Prompt to LLM:")
    for i, msg in enumerate(messages, 1):
        print(f"  {i}. {msg['role'].upper()}: {msg['content']}")
    print("[DEBUG] End of prompt\n")

    # --------------------------------------------------------
    # 6) Get LLM provider settings from session data
    # --------------------------------------------------------
    sdata = get_session_data(session_id)

    # Get LLM provider settings from session data or use defaults
    provider_id = sdata.get(
        "llm_provider_id",
        request.cached_intent.get("llm_provider_id", "openai")
        if request.cached_intent
        else "openai",
    )
    model_id = sdata.get(
        "llm_model_id",
        request.cached_intent.get("llm_model_id", "gpt-4o")
        if request.cached_intent
        else "gpt-4o",
    )

    # Store remaining requests in session data
    remaining_requests = validation["remaining_requests"]
    max_requests = validation["max_requests"]
    set_session_data(session_id, "remaining_requests", remaining_requests)
    set_session_data(session_id, "max_requests", max_requests)
    set_session_data(session_id, "invitation_code", invitation_code)

    # --------------------------------------------------------
    # 7) Call the LLM with appropriate provider
    # --------------------------------------------------------
    try:
        raw_response = generate_chat_response(
            messages=messages,
            provider_id=provider_id,
            model_id=model_id,
            temperature=0.0,
        )
        print(f"[DEBUG] LLM raw_response:\n{raw_response}\n")  # (DEBUG)
    except Exception as e:
        parsed_response = {
            "intent": "error",
            "confirmation": "needs_clarification",
            "message": f"Error accessing LLM: {str(e)}",
        }
        return {"assistant_response": parsed_response}

    # Append the assistant's response to conversation
    append_to_conversation(session_id, "assistant", raw_response)

    # --------------------------------------------------------
    # 8) Use a request from the invitation code
    # --------------------------------------------------------
    remaining = invitation_store.use_request(invitation_code, session_id)
    set_session_data(session_id, "remaining_requests", remaining)

    # --------------------------------------------------------
    # 9) Attempt to parse JSON
    # --------------------------------------------------------
    try:
        parsed_response = json.loads(raw_response)
    except json.JSONDecodeError:
        parsed_response = {
            "intent": "unknown",
            "confirmation": "needs_clarification",
            "message": f"Failed to parse JSON: {raw_response}",
        }
        return {"assistant_response": parsed_response}

    intent = parsed_response.get("intent", "")
    confirmation = parsed_response.get("confirmation", "")
    entities = parsed_response.get("entities", {})

    # --------------------------------------------------------
    # 10) Intent Handling
    # --------------------------------------------------------

    # --------------- create_experiment ---------------
    if intent == "create_experiment" and confirmation == "confirmed":
        experiment_name = entities.get("experiment_name")
        if not experiment_name:
            parsed_response["confirmation"] = "needs_clarification"
            parsed_response["message"] = (
                "Please provide an experiment name. For example: 'my_experiment'."
            )
        else:
            success, result = create_experiment(experiment_name)
            if success:
                parsed_response["message"] = (
                    f"✅ Experiment '{experiment_name}' created with ID: {result}."
                )
            else:
                parsed_response["confirmation"] = "needs_clarification"
                parsed_response["message"] = f"❌ Failed to create experiment: {result}"

    # --------------- create_experiment_and_start_run ---------------
    elif intent == "create_experiment_and_start_run" and confirmation == "confirmed":
        experiment_name = entities.get("experiment_name")
        run_name = entities.get("run_name")
        if not experiment_name:
            parsed_response["confirmation"] = "needs_clarification"
            parsed_response["message"] = (
                "Please provide an experiment name so we can create it and start a run.\n"
                "e.g. 'my_experiment'"
            )
        else:
            exp_success, exp_result = create_experiment(experiment_name)
            if not exp_success:
                parsed_response["confirmation"] = "needs_clarification"
                parsed_response["message"] = (
                    f"❌ Failed to create experiment: {exp_result}"
                )
            else:
                experiment_id = exp_result
                run_success, run_msg, run_id = create_run(experiment_id, run_name)
                if run_success:
                    parsed_response["message"] = (
                        f"✅ Created experiment '{experiment_name}' (ID: {experiment_id}) "
                        f"and started run (ID: {run_id})."
                    )
                    # Save the run ID in session_data
                    set_session_data(session_id, "current_run_id", run_id)
                else:
                    parsed_response["confirmation"] = "needs_clarification"
                    parsed_response["message"] = (
                        f"❌ Created experiment but failed to start run: {run_msg}"
                    )

    # --------------- create_run ---------------
    elif intent == "create_run" and confirmation == "confirmed":
        experiment_id = entities.get("experiment_id")
        experiment_name = entities.get("experiment_name")
        run_name = entities.get("run_name")

        if not experiment_id and not experiment_name:
            parsed_response["confirmation"] = "needs_clarification"
            parsed_response["message"] = (
                "To create a run, please specify either an 'experiment_id' or an 'experiment_name'.\n"
                "e.g. 'my_experiment'"
            )
        else:
            if not experiment_id and experiment_name:
                found_id = get_experiment_id_by_name(experiment_name)
                if not found_id:
                    parsed_response["confirmation"] = "needs_clarification"
                    parsed_response["message"] = (
                        f"No experiment found named '{experiment_name}'. "
                        f"Please create it first or provide an existing ID."
                    )
                else:
                    experiment_id = found_id

            if experiment_id:
                run_success, run_msg, run_id = create_run(experiment_id, run_name)
                if run_success:
                    parsed_response["message"] = f"✅ {run_msg}"
                    # Store the newly created run in session_data
                    set_session_data(session_id, "current_run_id", run_id)
                else:
                    parsed_response["confirmation"] = "needs_clarification"
                    parsed_response["message"] = f"❌ Failed to create run: {run_msg}"

    # --------------- delete_experiment ---------------
    elif intent == "delete_experiment" and confirmation == "confirmed":
        # The user can pass either an experiment_id or experiment_name in "entities".
        experiment_id = entities.get("experiment_id")
        experiment_name = entities.get("experiment_name")

        if not experiment_id and not experiment_name:
            parsed_response["confirmation"] = "needs_clarification"
            parsed_response["message"] = (
                "To delete an experiment, please specify 'experiment_id' or 'experiment_name'."
            )
        else:
            # If user only provided a name, look up the ID
            if not experiment_id and experiment_name:
                found_id = get_experiment_id_by_name(experiment_name)
                if not found_id:
                    parsed_response["confirmation"] = "needs_clarification"
                    parsed_response["message"] = (
                        f"No experiment found named '{experiment_name}'. "
                        f"Please provide a valid experiment name/ID."
                    )
                else:
                    experiment_id = found_id

            if experiment_id:
                del_success, del_msg = delete_experiment(experiment_id)
                if del_success:
                    parsed_response["message"] = f"✅ {del_msg}"
                else:
                    parsed_response["confirmation"] = "needs_clarification"
                    parsed_response["message"] = (
                        f"❌ Failed to delete experiment: {del_msg}"
                    )

    # --------------- delete_run ---------------
    elif intent == "delete_run" and confirmation == "confirmed":
        # The user must pass a run_id.
        run_id = entities.get("run_id")

        if not run_id:
            # If the user didn't provide one, attempt the last known run
            if "current_run_id" in sdata:
                run_id = sdata["current_run_id"]
            else:
                parsed_response["confirmation"] = "needs_clarification"
                parsed_response["message"] = (
                    "To delete a run, please provide a run_id, e.g. 'abc123'."
                )
                return {"assistant_response": parsed_response}

        del_success, del_msg = delete_run(run_id)
        if del_success:
            parsed_response["message"] = f"✅ {del_msg}"
        else:
            parsed_response["confirmation"] = "needs_clarification"
            parsed_response["message"] = f"❌ Failed to delete run: {del_msg}"

    # --------------- log_param ---------------
    elif intent == "log_param" and confirmation == "confirmed":
        run_id = entities.get("run_id")
        param_key = entities.get("param_key")
        param_value = entities.get("param_value")

        # Auto-fill run_id from session_data if not provided
        if not run_id:
            if "current_run_id" in sdata:
                run_id = sdata["current_run_id"]
                print(f"[DEBUG] Using stored run_id: {run_id}")
            else:
                parsed_response["confirmation"] = "needs_clarification"
                parsed_response["message"] = (
                    "We need a 'run_id' to log this param, and none is stored. "
                    "Please provide an actual run_id."
                )
                return {"assistant_response": parsed_response}

        if not param_key:
            parsed_response["confirmation"] = "needs_clarification"
            parsed_response["message"] = "We need the parameter key (e.g. 'alpha')."
        elif param_value is None:
            parsed_response["confirmation"] = "needs_clarification"
            parsed_response["message"] = "We need the parameter value (e.g. '0.1')."
        else:
            success, msg = log_param(run_id, param_key, str(param_value))
            if success:
                parsed_response["message"] = f"✅ {msg}"
            else:
                parsed_response["confirmation"] = "needs_clarification"
                parsed_response["message"] = f"❌ {msg}"

    # --------------- log_metric ---------------
    elif intent == "log_metric" and confirmation == "confirmed":
        run_id = entities.get("run_id")

        # Accept "metric_key", "metric_name", or "key" for the metric name
        metric_key = (
            entities.get("metric_key")
            or entities.get("metric_name")
            or entities.get("key")
        )
        # Accept "metric_value" or "value"
        metric_value = entities.get("metric_value", entities.get("value"))
        step = entities.get("step", 0)

        # Auto-fill run_id if user didn't provide it
        if not run_id:
            if "current_run_id" in sdata:
                run_id = sdata["current_run_id"]
                print(f"[DEBUG] Using stored run_id: {run_id}")
            else:
                parsed_response["confirmation"] = "needs_clarification"
                parsed_response["message"] = (
                    "We need a 'run_id' to log the metric, and none is stored. "
                    "Please provide an actual run_id."
                )
                return {"assistant_response": parsed_response}

        if not metric_key:
            parsed_response["confirmation"] = "needs_clarification"
            parsed_response["message"] = (
                "We need the metric name/key (e.g. 'accuracy')."
            )
        elif metric_value is None:
            parsed_response["confirmation"] = "needs_clarification"
            parsed_response["message"] = "We need a metric value (e.g. '0.95')."
        else:
            try:
                value_float = float(metric_value)
            except ValueError:
                parsed_response["confirmation"] = "needs_clarification"
                parsed_response["message"] = (
                    f"The provided metric value '{metric_value}' isn't a number."
                )
            else:
                success, msg = log_metric(run_id, metric_key, value_float, step)
                if success:
                    parsed_response["message"] = f"✅ {msg}"
                else:
                    parsed_response["confirmation"] = "needs_clarification"
                    parsed_response["message"] = f"❌ {msg}"

        # --------------- get_experiment_details ---------------
    elif intent == "get_experiment_details" and confirmation == "confirmed":
        experiment_id = entities.get("experiment_id")
        experiment_name = entities.get("experiment_name")

        print(
            f"[DEBUG] Processing get_experiment_details intent with entities: {entities}"
        )

        # Handle case where no identifier is provided
        if not experiment_id and not experiment_name:
            parsed_response["confirmation"] = "needs_clarification"
            parsed_response["message"] = (
                "Please provide an experiment name or ID to get details."
            )
            return {"assistant_response": parsed_response}

        # Try name-based lookup first if provided
        if experiment_name:
            print(f"[DEBUG] Looking up experiment ID for name: '{experiment_name}'")
            found_id = get_experiment_id_by_name(experiment_name)

            if found_id:
                print(f"[DEBUG] Resolved name '{experiment_name}' to ID: {found_id}")
                experiment_id = found_id
            else:
                print(
                    f"[DEBUG] Failed to find experiment with name: '{experiment_name}'"
                )

                # Try to list available experiments to help the user
                try:
                    list_url = f"{settings.MLFLOW_TRACKING_URI}/api/2.0/mlflow/experiments/list"
                    list_res = requests.get(list_url, timeout=10)

                    if list_res.ok:
                        experiments = list_res.json().get("experiments", [])
                        if experiments:
                            # Show first few experiment names
                            exp_names = [
                                f"'{exp.get('name')}'" for exp in experiments[:5]
                            ]
                            exp_list = ", ".join(exp_names)

                            if len(experiments) > 5:
                                exp_list += f", and {len(experiments) - 5} more"

                            parsed_response["confirmation"] = "needs_clarification"
                            parsed_response["message"] = (
                                f"❌ Experiment '{experiment_name}' not found. Available experiments include: {exp_list}"
                            )
                        else:
                            parsed_response["confirmation"] = "needs_clarification"
                            parsed_response["message"] = (
                                "❌ No experiments found in MLflow."
                            )
                    else:
                        parsed_response["confirmation"] = "needs_clarification"
                        parsed_response["message"] = (
                            f"❌ Failed to list available experiments. Status: {list_res.status_code}"
                        )
                except Exception as e:
                    parsed_response["confirmation"] = "needs_clarification"
                    parsed_response["message"] = (
                        f"❌ Error listing experiments: {str(e)}"
                    )

                return {"assistant_response": parsed_response}

        # At this point, we should have an experiment_id
        if not experiment_id:
            parsed_response["confirmation"] = "needs_clarification"
            parsed_response["message"] = (
                "❌ Could not determine experiment ID from the provided information."
            )
            return {"assistant_response": parsed_response}

        # Get the details using the ID
        print(f"[DEBUG] Getting details for experiment ID: {experiment_id}")
        success, msg, exp_details = get_experiment_by_id(experiment_id)

        if success and exp_details:
            name = exp_details.get("name", "Unknown")
            lifecycle_stage = exp_details.get("lifecycle_stage", "Unknown")
            artifact_location = exp_details.get("artifact_location", "Unknown")

            # Get creation time if available
            creation_time = exp_details.get("creation_time")
            time_str = "Unknown"
            if creation_time:
                time_str = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(int(creation_time) / 1000)
                )

            # Get run count for this experiment
            run_success, _, runs = list_runs(experiment_id)
            run_count = len(runs) if run_success else "Unknown"

            # Format the experiment details
            parsed_response["message"] = (
                f"📋 Experiment Details: {name}\n\n"
                f"• ID: {experiment_id}\n"
                f"• Created: {time_str}\n"
                f"• Status: {lifecycle_stage}\n"
                f"• Artifact Location: {artifact_location}\n"
                f"• Total Runs: {run_count}"
            )
        else:
            parsed_response["confirmation"] = "needs_clarification"
            parsed_response["message"] = f"❌ Error getting experiment details: {msg}"

    # --------------- list_runs ---------------
    elif intent == "list_runs" and confirmation == "confirmed":
        experiment_id = entities.get("experiment_id")
        experiment_name = entities.get("experiment_name")

        if not experiment_id and not experiment_name:
            parsed_response["confirmation"] = "needs_clarification"
            parsed_response["message"] = (
                "Please provide either an experiment ID or name to list runs for."
            )
            return {"assistant_response": parsed_response}

        # Resolve experiment ID if only name provided
        if not experiment_id and experiment_name:
            found_id = get_experiment_id_by_name(experiment_name)
            if not found_id:
                parsed_response["confirmation"] = "needs_clarification"
                parsed_response["message"] = (
                    f"No experiment found named '{experiment_name}'."
                )
                return {"assistant_response": parsed_response}
            experiment_id = found_id

        success, msg, runs = list_runs(experiment_id)

        if success and runs:
            # Get experiment name for context
            exp_name = "Unknown"
            exp_success, _, exp_details = get_experiment_by_id(experiment_id)
            if exp_success:
                exp_name = exp_details.get("name", "Unknown")

            # Prepare a formatted list of runs
            run_list = []
            for i, run in enumerate(runs[:20], 1):  # Show up to 20 runs
                run_info = run.get("info", {})
                run_id = run_info.get("run_id", "Unknown")
                run_name = run_info.get("run_name", "Unnamed run")
                status = run_info.get("status", "Unknown")

                # Get start time
                start_time = run_info.get("start_time")
                time_str = ""
                if start_time:
                    time_str = f", Started: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(start_time) / 1000))}"

                # Get metrics if available
                metrics = run.get("data", {}).get("metrics", {})
                metrics_str = ""
                if metrics:
                    # Format top 3 metrics
                    top_metrics = list(metrics.items())[:3]
                    metrics_str = ", ".join([f"{k}: {v}" for k, v in top_metrics])
                    metrics_str = f", Metrics: {metrics_str}"

                    # Indicate if there are more metrics
                    if len(metrics) > 3:
                        metrics_str += f" and {len(metrics) - 3} more"

                # Format the run info
                run_list.append(
                    f"{i}. {run_name} (ID: {run_id[:8]}...{run_id[-4:]}, Status: {status}{time_str}{metrics_str})"
                )

            # Join the run list with newlines
            formatted_list = "\n".join(run_list)

            # Add a note if there are more runs
            if len(runs) > 20:
                formatted_list += f"\n\n...and {len(runs) - 20} more runs."

            parsed_response["message"] = (
                f"📋 Found {len(runs)} runs for experiment '{exp_name}':\n\n{formatted_list}"
            )
        elif success:
            parsed_response["message"] = (
                f"No runs found for experiment ID {experiment_id}."
            )
        else:
            parsed_response["confirmation"] = "needs_clarification"
            parsed_response["message"] = f"❌ {msg}"

    # --------------- list_experiments ---------------
    elif intent == "list_experiments" and confirmation == "confirmed":
        success, msg, experiments = list_experiments()

        if success and experiments:
            # Prepare a formatted list of experiments
            exp_list = []
            for i, exp in enumerate(experiments[:20], 1):  # Show up to 20 experiments
                name = exp.get("name", "Unnamed")
                exp_id = exp.get("experiment_id", "Unknown")

                # Get creation time if available (might not be in all MLflow versions)
                creation_time = exp.get("creation_time")
                time_str = ""
                if creation_time:
                    time_str = f", Created: {time.strftime('%Y-%m-%d', time.localtime(int(creation_time) / 1000))}"

                # Get lifecycle stage
                lifecycle = exp.get("lifecycle_stage", "Unknown")

                # Format the experiment info
                exp_list.append(
                    f"{i}. {name} (ID: {exp_id}{time_str}, Status: {lifecycle})"
                )

            # Join the experiment list with newlines
            formatted_list = "\n".join(exp_list)

            # Add a note if there are more experiments
            if len(experiments) > 20:
                formatted_list += (
                    f"\n\n...and {len(experiments) - 20} more experiments."
                )

            parsed_response["message"] = (
                f"📋 Found {len(experiments)} experiments:\n\n{formatted_list}"
            )
        elif success:
            parsed_response["message"] = "No experiments found in MLflow."
        else:
            parsed_response["confirmation"] = "needs_clarification"
            parsed_response["message"] = f"❌ {msg}"

        # --------------- get_mlflow_summary ---------------
    elif intent == "get_mlflow_summary" and confirmation == "confirmed":
        summary = get_mlflow_summary_stats()

        if "error" in summary:
            parsed_response["confirmation"] = "needs_clarification"
            parsed_response["message"] = (
                f"❌ Error retrieving MLflow summary: {summary['error']}"
            )
        else:
            # Format a nice summary message
            parsed_response["message"] = (
                f"📊 MLflow Summary Statistics:\n\n"
                f"• Total Experiments: {summary['experiment_count']}\n"
                f"• Registered Models: {summary['registered_model_count']}\n"
                f"• Total Runs: {summary['total_runs']}\n"
                f"• Active Runs: {summary['active_runs']}\n"
                f"• Data as of: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(summary['timestamp']))}"
            )

    # --------------- get_model_versions ---------------
    elif intent == "get_model_versions" and confirmation == "confirmed":
        model_name = entities.get("model_name")

        # If there's no model_name but there's a message that appears to be an informational response
        if (
            not model_name
            and "message" in parsed_response
            and len(parsed_response["message"]) > 20
        ):
            # This is likely a general information response, just pass it through
            # (The message length check helps distinguish between actual answers and placeholder messages)
            print(
                f"[DEBUG] Passing through informational response: {parsed_response['message'][:50]}..."
            )
            # No modifications needed to parsed_response, just use the LLM's message
        elif not model_name:
            # No model name and no informational message, ask for clarification
            parsed_response["confirmation"] = "needs_clarification"
            parsed_response["message"] = (
                "Please provide a model name to get versions for."
            )
        else:
            # Normal flow when a model name is provided
            success, msg, versions = get_model_versions(model_name)

            if success and versions:
                # Format model versions into readable output
                versions_text = ""
                for v in versions:
                    version_num = v.get("version", "Unknown")
                    status = v.get("current_stage", "Unknown")
                    user = v.get("user_id", "Unknown")
                    created = time.strftime(
                        "%Y-%m-%d %H:%M:%S",
                        time.localtime(int(v.get("creation_timestamp", 0) / 1000)),
                    )
                    run_id = v.get("run_id", "Unknown")

                    versions_text += (
                        f"• Version {version_num} (Status: {status})\n"
                        f"  - Created by: {user}\n"
                        f"  - Created on: {created}\n"
                        f"  - Run ID: {run_id}\n"
                    )

                parsed_response["message"] = (
                    f"📋 Versions for model '{model_name}':\n\n{versions_text}"
                )
            elif success:
                parsed_response["message"] = (
                    f"No versions found for model '{model_name}'."
                )
            else:
                parsed_response["confirmation"] = "needs_clarification"
                parsed_response["message"] = f"❌ {msg}"

    # --------------- get_model_details ---------------
    elif intent == "get_model_details" and confirmation == "confirmed":
        model_name = entities.get("model_name")
        version = entities.get("version")

        if not model_name:
            parsed_response["confirmation"] = "needs_clarification"
            parsed_response["message"] = (
                "Please provide a model name to get details for."
            )
        else:
            success, msg, details = get_model_details(model_name, version)

            if success and details:
                version_num = details.get("version", "Unknown")
                status = details.get("current_stage", "Unknown")
                user = details.get("user_id", "Unknown")
                created = time.strftime(
                    "%Y-%m-%d %H:%M:%S",
                    time.localtime(int(details.get("creation_timestamp", 0) / 1000)),
                )
                run_id = details.get("run_id", "Unknown")
                source = details.get("source", "Unknown")

                # Get experiment name for this run
                exp_id = (
                    details.get("run", {})
                    .get("info", {})
                    .get("experiment_id", "Unknown")
                )
                exp_name = "Unknown"
                if exp_id != "Unknown":
                    exp_success, _, exp_details = get_experiment_by_id(exp_id)
                    if exp_success:
                        exp_name = exp_details.get("name", "Unknown")

                parsed_response["message"] = (
                    f"📦 Model: {model_name} (Version {version_num})\n\n"
                    f"• Status: {status}\n"
                    f"• Created by: {user}\n"
                    f"• Created on: {created}\n"
                    f"• Run ID: {run_id}\n"
                    f"• Experiment: {exp_name}\n"
                    f"• Artifact Location: {source}\n"
                )
            elif success:
                parsed_response["message"] = (
                    f"No details found for model '{model_name}'."
                )
            else:
                parsed_response["confirmation"] = "needs_clarification"
                parsed_response["message"] = f"❌ {msg}"

    # --------------- get_recent_models ---------------
    elif intent == "get_recent_models" and confirmation == "confirmed":
        limit = entities.get("limit", 5)

        # Validate limit is reasonable
        try:
            limit = int(limit)
            if limit <= 0:
                limit = 5
        except (ValueError, TypeError):
            limit = 5

        success, msg, recent_models = get_recently_updated_models(limit)

        if success and recent_models:
            models_text = ""
            for i, model in enumerate(recent_models, 1):
                name = model.get("name", "Unknown")
                last_updated = time.strftime(
                    "%Y-%m-%d %H:%M:%S",
                    time.localtime(int(model.get("last_updated_timestamp", 0) / 1000)),
                )

                # Get latest version
                version_success, _, versions = get_model_versions(name)
                latest_version = "Unknown"
                if version_success and versions:
                    sorted_versions = sorted(
                        versions, key=lambda v: int(v.get("version", 0)), reverse=True
                    )
                    if sorted_versions:
                        latest_version = sorted_versions[0].get("version", "Unknown")

                models_text += (
                    f"{i}. {name}\n"
                    f"   • Last Updated: {last_updated}\n"
                    f"   • Latest Version: {latest_version}\n"
                )

            parsed_response["message"] = (
                f"🔄 Top {len(recent_models)} Recently Updated Models:\n\n{models_text}"
            )
        elif success:
            parsed_response["message"] = "No registered models found in MLflow."
        else:
            parsed_response["confirmation"] = "needs_clarification"
            parsed_response["message"] = f"❌ {msg}"

    # --------------- batch_create_experiments ---------------
    elif intent == "batch_create_experiments" and confirmation == "confirmed":
        experiment_names = entities.get("experiment_names", [])

        if (
            not experiment_names
            or not isinstance(experiment_names, list)
            or len(experiment_names) == 0
        ):
            parsed_response["confirmation"] = "needs_clarification"
            parsed_response["message"] = (
                "Please provide a list of experiment names to create."
            )
        else:
            results = batch_create_experiments(experiment_names)

            # Count successful creations
            successful = sum(1 for r in results if r["success"])

            if successful == len(experiment_names):
                exp_ids = [r["result"] for r in results if r["success"]]
                exp_list = "\n".join(
                    [
                        f"• {name} (ID: {id})"
                        for name, id in zip(experiment_names, exp_ids)
                    ]
                )
                parsed_response["message"] = (
                    f"✅ Successfully created all {len(experiment_names)} experiments:\n\n{exp_list}"
                )
                # Store the experiment IDs for reference
                set_session_data(session_id, "batch_experiment_ids", exp_ids)
            elif successful > 0:
                # Create a list of successful and failed creations
                success_list = []
                failed_list = []

                for result in results:
                    name = result["experiment_name"]
                    if result["success"]:
                        success_list.append(f"• {name} (ID: {result['result']})")
                    else:
                        failed_list.append(f"• {name} (Error: {result['result']})")

                success_text = "\n".join(success_list)
                failed_text = "\n".join(failed_list)

                parsed_response["message"] = (
                    f"⚠️ Created {successful} out of {len(experiment_names)} experiments.\n\n"
                    f"Successful:\n{success_text}\n\n"
                    f"Failed:\n{failed_text}"
                )
            else:
                parsed_response["confirmation"] = "needs_clarification"
                parsed_response["message"] = "❌ Failed to create any experiments."

    # --------------- get_models_with_artifacts ---------------
    elif intent == "get_models_with_artifacts" and confirmation == "confirmed":
        experiment_id = entities.get("experiment_id")
        experiment_name = entities.get("experiment_name")

        if not experiment_id and not experiment_name:
            parsed_response["confirmation"] = "needs_clarification"
            parsed_response["message"] = (
                "Please provide either an experiment ID or name to find models."
            )
            return {"assistant_response": parsed_response}

        # Resolve experiment ID if only name provided
        if not experiment_id and experiment_name:
            found_id = get_experiment_id_by_name(experiment_name)
            if not found_id:
                parsed_response["confirmation"] = "needs_clarification"
                parsed_response["message"] = (
                    f"No experiment found named '{experiment_name}'."
                )
                return {"assistant_response": parsed_response}
            experiment_id = found_id

        success, msg, runs = get_runs_with_model_info(experiment_id)

        if success:
            # Filter runs with models
            runs_with_models = [
                r for r in runs if r.get("model_info", {}).get("has_model", False)
            ]

            if runs_with_models:
                runs_text = ""
                for i, run in enumerate(runs_with_models[:10], 1):
                    run_info = run.get("info", {})
                    run_id = run_info.get("run_id", "Unknown")
                    run_name = run_info.get("run_name", "Unnamed run")
                    status = run_info.get("status", "Unknown")
                    start_time = time.strftime(
                        "%Y-%m-%d %H:%M:%S",
                        time.localtime(int(run_info.get("start_time", 0) / 1000)),
                    )

                    artifact_paths = [
                        a.get("path", "Unknown")
                        for a in run.get("model_info", {}).get("model_artifacts", [])
                    ]
                    artifact_text = (
                        "\n      ".join(artifact_paths) or "No specific paths found"
                    )

                    runs_text += (
                        f"{i}. {run_name} (ID: {run_id[:8]}...)\n"
                        f"   • Status: {status}\n"
                        f"   • Started: {start_time}\n"
                        f"   • Model Artifacts:\n      {artifact_text}\n"
                    )

                if len(runs_with_models) > 10:
                    runs_text += (
                        f"\n...and {len(runs_with_models) - 10} more runs with models."
                    )

                parsed_response["message"] = (
                    f"🔍 Found {len(runs_with_models)} runs with models in experiment {experiment_id}:\n\n{runs_text}"
                )
            else:
                parsed_response["message"] = (
                    f"No runs with logged models found in experiment {experiment_id}."
                )
        else:
            parsed_response["confirmation"] = "needs_clarification"
            parsed_response["message"] = f"❌ {msg}"

        # --------------- get_recently_used_models ---------------
    elif intent == "get_recently_used_models" and confirmation == "confirmed":
        limit = entities.get("limit", 5)

        # Validate limit
        try:
            limit = int(limit)
            if limit <= 0:
                limit = 5
        except (ValueError, TypeError):
            limit = 5

        success, msg, recent_models = get_recently_used_models(limit)

        if success and recent_models:
            models_text = ""
            for i, model in enumerate(recent_models, 1):
                name = model.get("name", "Unknown")
                recent_runs = model.get("recent_runs", [])

                # Format timestamp of most recent use
                latest_timestamp = model.get("latest_timestamp", 0)
                latest_time = (
                    time.strftime(
                        "%Y-%m-%d %H:%M:%S",
                        time.localtime(int(latest_timestamp / 1000)),
                    )
                    if latest_timestamp
                    else "Unknown"
                )

                # Get versions used
                versions = set(
                    run.get("version") for run in recent_runs if run.get("version")
                )
                versions_text = ", ".join(sorted(versions)) if versions else "Unknown"

                models_text += (
                    f"{i}. {name}\n"
                    f"   • Last Used: {latest_time}\n"
                    f"   • Versions Used: {versions_text}\n"
                    f"   • Recent Usage Count: {len(recent_runs)}\n"
                )

            parsed_response["message"] = (
                f"🔄 Top {len(recent_models)} Recently Used Models:\n\n{models_text}"
            )
        elif success:
            parsed_response["message"] = "No recently used models found in MLflow."
        else:
            parsed_response["confirmation"] = "needs_clarification"
            parsed_response["message"] = f"❌ {msg}"

    # --------------- get_registered_models ---------------
    elif intent == "get_registered_models" and confirmation == "confirmed":
        success, msg, models = get_registered_models()

        if success and models:
            # Prepare a formatted list of models
            model_list = []
            for i, model in enumerate(models[:20], 1):  # Show up to 20 models
                name = model.get("name", "Unnamed")

                # Get latest version if available
                latest_version = "Unknown"
                version_success, _, versions = get_model_versions(name)
                if version_success and versions:
                    sorted_versions = sorted(
                        versions, key=lambda v: int(v.get("version", 0)), reverse=True
                    )
                    if sorted_versions:
                        latest_version = sorted_versions[0].get("version", "Unknown")

                # Get last updated timestamp
                last_updated = model.get("last_updated_timestamp")
                time_str = ""
                if last_updated:
                    time_str = f", Updated: {time.strftime('%Y-%m-%d', time.localtime(int(last_updated) / 1000))}"

                # Get stages if available
                stages = set()
                if version_success and versions:
                    for v in versions:
                        stage = v.get("current_stage")
                        if stage and stage != "None":
                            stages.add(stage)
                stages_str = ""
                if stages:
                    stages_str = f", Stages: {', '.join(sorted(stages))}"

                # Format the model info
                model_list.append(
                    f"{i}. {name} (Latest version: {latest_version}{time_str}{stages_str})"
                )

            # Join the model list with newlines
            formatted_list = "\n".join(model_list)

            # Add a note if there are more models
            if len(models) > 20:
                formatted_list += f"\n\n...and {len(models) - 20} more models."

            parsed_response["message"] = (
                f"📋 Found {len(models)} registered models:\n\n{formatted_list}"
            )
        elif success:
            parsed_response["message"] = "No registered models found in MLflow."
        else:
            parsed_response["confirmation"] = "needs_clarification"
            parsed_response["message"] = f"❌ {msg}"

        # --------------- batch_create_runs ---------------
    elif intent == "batch_create_runs" and confirmation == "confirmed":
        experiment_id = entities.get("experiment_id")
        experiment_name = entities.get("experiment_name")
        run_names = entities.get("run_names", [])

        if not run_names or not isinstance(run_names, list) or len(run_names) == 0:
            parsed_response["confirmation"] = "needs_clarification"
            parsed_response["message"] = "Please provide a list of run names to create."
            return {"assistant_response": parsed_response}

        # Resolve experiment ID if only name provided
        if not experiment_id and experiment_name:
            found_id = get_experiment_id_by_name(experiment_name)
            if not found_id:
                parsed_response["confirmation"] = "needs_clarification"
                parsed_response["message"] = (
                    f"No experiment found named '{experiment_name}'. Please create it first or provide an existing ID."
                )
                return {"assistant_response": parsed_response}
            experiment_id = found_id

        if not experiment_id:
            parsed_response["confirmation"] = "needs_clarification"
            parsed_response["message"] = (
                "Please provide either an experiment ID or name to create runs in."
            )
        else:
            # Get experiment name for context
            exp_name = "Unknown"
            exp_success, _, exp_details = get_experiment_by_id(experiment_id)
            if exp_success:
                exp_name = exp_details.get("name", "Unknown")

            results = batch_create_runs(experiment_id, run_names)

            # Count successful creations
            successful = sum(1 for r in results if r["success"])

            if successful == len(run_names):
                run_ids = [r["run_id"] for r in results if r["success"]]
                run_list = "\n".join(
                    [
                        f"• {name} (ID: {id[:8]}...{id[-4:]})"
                        for name, id in zip(run_names, run_ids)
                        if id
                    ]
                )
                parsed_response["message"] = (
                    f"✅ Successfully created all {len(run_names)} runs in experiment '{exp_name}':\n\n{run_list}"
                )
                # Store the last run ID for reference
                if run_ids:
                    set_session_data(session_id, "current_run_id", run_ids[-1])
                    set_session_data(session_id, "batch_run_ids", run_ids)
            elif successful > 0:
                # Create a list of successful and failed creations
                success_list = []
                failed_list = []

                for result in results:
                    name = result["run_name"]
                    if result["success"]:
                        run_id = result["run_id"]
                        success_list.append(
                            f"• {name} (ID: {run_id[:8]}...{run_id[-4:]})"
                        )
                    else:
                        failed_list.append(f"• {name} (Error: {result['message']})")

                success_text = "\n".join(success_list)
                failed_text = "\n".join(failed_list)

                parsed_response["message"] = (
                    f"⚠️ Created {successful} out of {len(run_names)} runs in experiment '{exp_name}'.\n\n"
                    f"Successful:\n{success_text}\n\n"
                    f"Failed:\n{failed_text}"
                )
            else:
                parsed_response["confirmation"] = "needs_clarification"
                parsed_response["message"] = (
                    f"❌ Failed to create any runs in experiment '{exp_name}'."
                )

    # Return the final response
    return {"assistant_response": parsed_response}
