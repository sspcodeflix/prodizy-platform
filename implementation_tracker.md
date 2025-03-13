# Prodizy Platform Component Implementation Status

| Architecture Component | Current Implementation                        | Notes                                                |
| ---------------------- | --------------------------------------------- | ---------------------------------------------------- |
| Streamlit UI           | `app.py`                                      | Complete implementation of the frontend              |
| Core Engine            | `main.py`                                     | FastAPI backend application entry point              |
| AuthN                  | Part of `invitation_router.py`                | Basic authentication via invitation codes            |
| Session Store          | `session_store.py`                            | In-memory implementation                             |
| Invitation Store       | `invitation.py`                               | Complete implementation                              |
| LLM Connector Bridge   | `mlflow_router.py`                            | Currently only for MLflow                            |
| Decision System        | Logic in `mlflow_router.py`                   | Embedded in the router rather than a separate module |
| Connector Registry     | Not fully implemented                         | Basic patterns exist in LLM providers                |
| Schema Store           | Not implemented                               | Future enhancement                                   |
| Schema Discovery       | Not implemented                               | Future enhancement                                   |
| Connectors             | `mlflow_service.py`                           | Only MLflow connector implemented                    |
| LLM Service            | `llm_service.py` and provider implementations | Complete multi-provider implementation               |
| RAG Engine             | Not implemented                               | Future enhancement                                   |
| Knowledge Cache        | Not implemented                               | Future enhancement                                   |
| Vector DB              | Not implemented                               | Future enhancement                                   |
