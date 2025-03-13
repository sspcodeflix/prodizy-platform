import streamlit as st
import requests
import os
import time
import traceback
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Prodizy Platform - Intelligent Data-Aware AI Platform",
    page_icon="💬",
    layout="wide",
)

API_PORT = os.getenv("API_PORT", "5003")
BACKEND_API_URL = os.getenv("BACKEND_API_URL")
if not BACKEND_API_URL:
    BACKEND_API_URL = f"http://127.0.0.1:{API_PORT}/"

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
DEFAULT_PROVIDER = os.getenv("DEFAULT_LLM_PROVIDER", "openai")
DEFAULT_MODEL = os.getenv("DEFAULT_LLM_MODEL", "gpt-4o")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))

# Check if running on localhost, is required to disable invitation generation on deployment servers
is_localhost = "localhost" in BACKEND_API_URL or "127.0.0.1" in BACKEND_API_URL

# Initialize session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "backend_status" not in st.session_state:
    st.session_state.backend_status = None
if "mlflow_status" not in st.session_state:
    st.session_state.mlflow_status = None
if "is_processing" not in st.session_state:
    st.session_state.is_processing = False
if "current_message" not in st.session_state:
    st.session_state.current_message = None
if "session_started" not in st.session_state:
    st.session_state.session_started = False
if "llm_providers" not in st.session_state:
    st.session_state.llm_providers = []
if "selected_provider" not in st.session_state:
    st.session_state.selected_provider = DEFAULT_PROVIDER
if "provider_models" not in st.session_state:
    st.session_state.provider_models = {}
if "selected_model" not in st.session_state:
    st.session_state.selected_model = DEFAULT_MODEL
if "invitation_code" not in st.session_state:
    st.session_state.invitation_code = ""
if "invitation_valid" not in st.session_state:
    st.session_state.invitation_valid = False
if "remaining_requests" not in st.session_state:
    st.session_state.remaining_requests = 0
if "max_requests" not in st.session_state:
    st.session_state.max_requests = 0
# Add LLM status state
if "llm_status" not in st.session_state:
    st.session_state.llm_status = None


def check_backend_connection():
    try:
        response = requests.get(f"{BACKEND_API_URL}docs", timeout=5)
        if response.status_code < 400:
            return True
        return False
    except requests.RequestException:
        return False


def check_mlflow_connection():
    try:
        response = requests.get(f"{MLFLOW_TRACKING_URI}/health", timeout=5)
        if response.status_code < 400:
            return True
        return False
    except requests.RequestException:
        return False


def validate_invitation_code(code, session_id="streamlit-session"):
    try:
        payload = {"code": code, "session_id": session_id}
        response = requests.post(
            f"{BACKEND_API_URL}invitation/validate", json=payload, timeout=5
        )
        if response.ok:
            data = response.json()
            if data.get("valid", False):
                st.session_state.remaining_requests = data.get("remaining_requests", 0)
                st.session_state.max_requests = data.get("max_requests", 0)
                return True, data.get("message", "Valid invitation code")
            else:
                return False, data.get("message", "Invalid invitation code")
        return False, "Server error validating invitation code"
    except requests.RequestException as e:
        return False, f"Error: {str(e)}"


def get_providers():
    try:
        response = requests.get(f"{BACKEND_API_URL}chat/providers", timeout=5)
        if response.ok:
            data = response.json()
            return data.get("providers", [])
        return []
    except requests.RequestException:
        return []


def get_provider_models(provider_id, invitation_code):
    try:
        payload = {"provider_id": provider_id, "invitation_code": invitation_code}
        response = requests.post(
            f"{BACKEND_API_URL}chat/provider-models", json=payload, timeout=10
        )
        if response.ok:
            data = response.json()
            return data.get("models", [])
        return []
    except requests.RequestException:
        return []


def chat_with_bot(query, provider_id, model_id, invitation_code):
    payload = {
        "session_id": "streamlit-session",
        "query": query,
        "invitation_code": invitation_code,
        "cached_intent": {"llm_provider_id": provider_id, "llm_model_id": model_id},
    }

    headers = {"Content-Type": "application/json"}

    try:
        start_time = time.time()
        response = requests.post(
            f"{BACKEND_API_URL}chat/mlflow",
            json=payload,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        elapsed_time = time.time() - start_time

        if elapsed_time > 5:
            st.info(f"Request took {elapsed_time:.2f} seconds to complete")

        response.raise_for_status()

        response_json = response.json()
        assistant_response = response_json.get("assistant_response", {})

        st.session_state.remaining_requests -= 1

        return assistant_response
    except requests.exceptions.Timeout:
        return {
            "intent": "error",
            "confirmation": "needs_clarification",
            "message": f"❌ Request timed out after {REQUEST_TIMEOUT} seconds. The backend or MLflow server might be unresponsive.",
        }
    except requests.exceptions.ConnectionError:
        return {
            "intent": "error",
            "confirmation": "needs_clarification",
            "message": f"❌ Connection error: Could not connect to the backend at {BACKEND_API_URL}. Please check if the backend is running.",
        }
    except requests.RequestException as e:
        return {
            "intent": "error",
            "confirmation": "needs_clarification",
            "message": f"❌ Request error: {str(e)}",
        }
    except Exception as e:
        error_details = traceback.format_exc()
        return {
            "intent": "error",
            "confirmation": "needs_clarification",
            "message": f"❌ Unexpected error: {str(e)}\n\nDetails: {error_details}",
        }


# Generate a development invitation code
def generate_dev_invitation():
    try:
        response = requests.post(f"{BACKEND_API_URL}invitation/create", timeout=5)
        if response.ok:
            data = response.json()
            return data.get("code", "Error generating code")
        return "Error generating code"
    except requests.RequestException:
        return "Error connecting to backend"


# Check LLM status
def check_llm_status():
    try:
        response = requests.get(f"{BACKEND_API_URL}llm/status", timeout=10)
        if response.ok:
            return response.json()
        return {"providers": {}}
    except Exception as e:
        return {"providers": {}, "error": str(e)}


if st.session_state.backend_status is None:
    st.session_state.backend_status = check_backend_connection()

if st.session_state.mlflow_status is None:
    st.session_state.mlflow_status = check_mlflow_connection()

if not st.session_state.backend_status:
    st.error(f"⚠️ Cannot connect to backend at {BACKEND_API_URL}")
    st.info("""
    Possible causes:
    - Backend service is not running
    - BACKEND_API_URL configuration is incorrect
    - Network/firewall issues
    """)

if not st.session_state.mlflow_status:
    st.error(f"⚠️ Cannot connect to MLflow server at {MLFLOW_TRACKING_URI}")
    st.info("""
    Possible causes:
    - MLflow server is not running
    - MLFLOW_TRACKING_URI configuration is incorrect
    - Network/firewall issues
    """)

if st.session_state.backend_status and len(st.session_state.llm_providers) == 0:
    st.session_state.llm_providers = get_providers()

with st.sidebar:
    with st.container():
        st.subheader("🖥️ Server Status")

        col1, col2 = st.columns(2)

        with col1:
            if st.session_state.backend_status:
                st.success("Backend: ✅")
            else:
                st.error("Backend: ❌")

        with col2:
            if st.session_state.mlflow_status:
                st.success("MLflow: ✅")
            else:
                st.error("MLflow: ❌")

        # Add LLM Status Section
        if st.session_state.backend_status:
            st.markdown("##### LLM Providers")

            # Fetch LLM status if not already available
            if st.session_state.llm_status is None:
                with st.spinner("Checking LLM providers..."):
                    st.session_state.llm_status = check_llm_status()

            # Display LLM provider statuses
            llm_providers = st.session_state.llm_status.get("providers", {})

            if llm_providers:
                # Create a 2-column grid layout for LLM providers
                provider_names = list(llm_providers.keys())
                rows = (len(provider_names) + 1) // 2

                for i in range(rows):
                    cols = st.columns(2)

                    for j in range(2):
                        idx = i * 2 + j
                        if idx < len(provider_names):
                            provider = provider_names[idx]
                            provider_info = llm_providers[provider]

                            # Determine status
                            is_available = provider_info.get("status") == "available"

                            with cols[j]:
                                if is_available:
                                    st.success(f"{provider.title()}: ✅")
                                else:
                                    st.error(f"{provider.title()}: ❌")
            else:
                st.info("No LLM provider information available")

        with st.expander("Server Details"):
            st.code(
                f"Backend URL: {BACKEND_API_URL}\nMLflow URI: {MLFLOW_TRACKING_URI}"
            )
            col1, col2 = st.columns(2)

            with col1:
                if st.button(
                    "Refresh Status", use_container_width=True, type="primary"
                ):
                    st.session_state.backend_status = check_backend_connection()
                    st.session_state.mlflow_status = check_mlflow_connection()
                    if st.session_state.backend_status:
                        st.session_state.llm_providers = get_providers()
                    st.session_state.llm_status = None  # Reset to trigger refresh
                    st.rerun()

    if st.session_state.session_started:
        with st.container():
            st.subheader("🤖 LLM Configuration")

            st.info(f"**Provider:** {st.session_state.selected_provider}")
            st.info(f"**Model:** {st.session_state.selected_model}")

            if st.button("Change Model"):
                st.session_state.session_started = False
                st.rerun()

    if st.session_state.session_started:
        with st.container():
            st.subheader("📊 Session Limits")

            progress = (
                st.session_state.remaining_requests / st.session_state.max_requests
            )
            st.progress(progress)
            st.write(
                f"Remaining requests: {st.session_state.remaining_requests}/{st.session_state.max_requests}"
            )

            code = st.session_state.invitation_code
            masked_code = (
                code[:2] + "*" * (len(code) - 4) + code[-2:]
                if len(code) > 4
                else "****"
            )
            st.write(f"Invitation code: {masked_code}")

    with st.container():
        st.subheader("⚙️ Session Actions")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Clear Chat"):
                st.session_state.chat_history = []
                st.session_state.current_message = None
                st.session_state.is_processing = False
                st.rerun()

        with col2:
            if st.session_state.session_started:
                if st.button("End Session", type="primary", use_container_width=True):
                    st.session_state.session_started = False
                    st.session_state.invitation_valid = False
                    st.session_state.chat_history = []
                    st.session_state.current_message = None
                    st.session_state.is_processing = False
                    st.rerun()

if not st.session_state.invitation_valid:
    st.title("🔑 Prodizy - Intelligent Data-Aware AI Platform")

    with st.container():
        st.markdown("""
        ## Welcome to Prodizy Platform(Alpha) - Invitation Required
        
        This service requires an invitation code to access. Each invitation code:
        - Is valid for a single chat session
        - Has a limited number of requests (typically 10)
        - Expires after a certain period
        
        If you don't have an invitation code, please email **hey@prodizyplatform.in** 
                    to request one.
        """)

        # Add "Get Invitation Code" button for localhost only
        if is_localhost and st.session_state.backend_status:
            if st.button("Get Invitation Code"):
                invitation = generate_dev_invitation()
                st.info(f"Development Invitation Code: **{invitation}**")
                st.info(
                    "This code is for development purposes only and will expire soon."
                )

        invitation_code = st.text_input("Enter your invitation code", type="password")

        if st.button("Validate Invitation"):
            if invitation_code:
                valid, message = validate_invitation_code(invitation_code)
                if valid:
                    st.success(message)
                    st.session_state.invitation_code = invitation_code
                    st.session_state.invitation_valid = True
                    st.rerun()
                else:
                    st.error(message)
            else:
                st.error("Please enter an invitation code")

elif not st.session_state.session_started:
    st.title("🤖 Prodizy Platform - Model Selection")
    st.write("Select an LLM provider and model to start a chat session with MLflow.")

    with st.container():
        st.markdown("### Choose your LLM Provider")

        provider_options = [p["name"] for p in st.session_state.llm_providers]
        provider_ids = [p["id"] for p in st.session_state.llm_providers]

        if provider_options:
            default_idx = 0
            if DEFAULT_PROVIDER in provider_ids:
                default_idx = provider_ids.index(DEFAULT_PROVIDER)

            selected_provider_name = st.selectbox(
                "LLM Provider", options=provider_options, index=default_idx
            )

            provider_idx = provider_options.index(selected_provider_name)
            selected_provider_id = provider_ids[provider_idx]

            st.session_state.selected_provider = selected_provider_id

            with st.spinner("Fetching available models..."):
                models = get_provider_models(
                    selected_provider_id, st.session_state.invitation_code
                )
                provider_cache_key = selected_provider_id
                st.session_state.provider_models[provider_cache_key] = models

            models = st.session_state.provider_models.get(provider_cache_key, [])

            if models:
                st.markdown("### Select a Model")

                model_cols = st.columns(min(3, len(models)))

                for i, model in enumerate(models):
                    with model_cols[i % len(model_cols)]:
                        model_id = model["id"]
                        model_name = model["name"]
                        model_desc = model.get("description", "")

                        st.markdown(f"#### {model_name}")
                        st.write(model_desc)
                        st.write(f"Max tokens: {model.get('max_tokens', 'Unknown')}")

                        if st.button(f"Select {model_name}", key=f"model_{model_id}"):
                            st.session_state.selected_model = model_id
                            st.session_state.session_started = True
                            st.rerun()
            else:
                st.warning(
                    "No models available for this provider or your invitation code may "
                    "be invalid."
                )
                if st.button("Retry Loading Models"):
                    st.rerun()
        else:
            st.error("No LLM providers available. Please check the backend connection.")
            if st.button("Retry Loading Providers"):
                st.session_state.llm_providers = get_providers()
                st.rerun()

else:
    st.title("💬 Prodizy Platform - MLflow Chat")

    if st.session_state.remaining_requests <= 2:
        st.warning(
            f"⚠️ You have only {st.session_state.remaining_requests} requests remaining\
                  in this session."
        )

    chat_container = st.container()

    with chat_container:
        for speaker, message in st.session_state.chat_history:
            if speaker == "You":
                st.chat_message("user").write(message)
            else:
                st.chat_message("assistant").write(message)

        if st.session_state.is_processing and st.session_state.current_message:
            st.chat_message("user").write(st.session_state.current_message)
            with st.chat_message("assistant"):
                st.write("Processing your request...")
                with st.spinner():
                    pass

    chat_disabled = (
        st.session_state.is_processing
        or not st.session_state.backend_status
        or not st.session_state.mlflow_status
        or st.session_state.remaining_requests <= 0
    )

    if chat_disabled and not st.session_state.is_processing:
        if st.session_state.remaining_requests <= 0:
            st.error(
                "You have used all your available requests. \
                    Please contact hey@prodizyplatform.in for a new invitation code."
            )
        else:
            st.warning(
                "Chat input is disabled because one or more required services are not \
                    connected. Please check the service status in the sidebar."
            )

    prompt = st.chat_input("Ask something about MLflow", disabled=chat_disabled)
    if prompt and not st.session_state.is_processing:
        st.session_state.current_message = prompt
        st.session_state.is_processing = True

        st.rerun()

    if st.session_state.is_processing and st.session_state.current_message:
        assistant_data = chat_with_bot(
            st.session_state.current_message,
            st.session_state.selected_provider,
            st.session_state.selected_model,
            st.session_state.invitation_code,
        )

        assistant_message = assistant_data.get("message")
        if not assistant_message:
            assistant_message = str(assistant_data)

        st.session_state.chat_history.append(("You", st.session_state.current_message))
        st.session_state.chat_history.append(("Bot", assistant_message))

        st.session_state.is_processing = False
        st.session_state.current_message = None

        st.rerun()
