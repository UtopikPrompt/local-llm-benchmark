---
title: Engine Management API
status: Proposed
date: 2026-09-16
authors: [AI Assistant]
---

# ADR 0008: Engine Management API

## Status

**Proposed**

## Context

The system architecture relies on various external components and internal modules, collectively referred to as 'Engines' (e.g., `openai_compat`, `local_llm`). The current process for adding or modifying an engine definition is ad-hoc, relying on manual code updates and UI placeholders. To achieve robust maintainability, a formal, centralized API contract is required for managing the metadata of these engine definitions.

## Decision

A dedicated RESTful API (`/api/engines`) must be established to handle the full lifecycle management (CRUD) of engine definitions. These definitions must be persisted in the primary data store (SQLite) and must include schema validation for all inputs.

## Consequences

### 🚀 Good
1. **Decoupling:** The UI and core services become decoupled from the physical implementation details of the engine definition.
2. **Maintainability:** Adding, editing, or retiring an engine type requires only API calls and database updates, not code deployment.
3. **Consistency:** A single source of truth for engine metadata is established.

### ⚠️ Bad
1. **Complexity:** Introducing an entire service layer dedicated to metadata management increases the initial boilerplate.
2. **Dependency:** All modules now have a dependency on the Engine Management API endpoint.

## Engine Data Schema

Every engine definition must adhere to the following schema:

| Field | Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| `engine_id` | String | **Primary Key, Unique** | The unique, immutable identifier for the engine (e.g., `local_llm`). |
| `engine_name` | String | Required | A human-readable display name. |
| `engine_type` | Enum | Required | Categorization (e.g., `LLM_PROVIDER`, `LOCAL_BENCHMARKER`, `EXTERNAL_API`). |
| `config_params` | JSON | Optional | Key-value parameters required by the engine (e.g., API keys, model parameters). |
| `is_active` | Boolean | Default `True` | Controls if the engine should be visible in the UI and available for selection. |

## API Endpoints

The backend service must implement the following endpoints:

1. **GET /api/engines:**
    *   **Function:** Read all engine definitions.
    *   **Response:** A paginated list of engine objects matching the data schema.

2. **GET /api/engines/{engine_id}:**
    *   **Function:** Retrieve the metadata for a single engine.

3. **POST /api/engines:**
    *   **Function:** Create a new engine definition.
    *   **Body:** Must contain at least `engine_name`, `engine_type`, and a unique `engine_id` (validated against existing records).

4. **PUT /api/engines/{engine_id}:**
    *   **Function:** Update existing engine metadata (e.g., change name, update parameters).
    *   **Body:** Must contain the fields to be updated.

5. **DELETE /api/engines/{engine_id}:**
    *   **Function:** Decommission an engine definition. Should optionally soft-delete (set `is_active=False`) before hard deletion.

## Action Items

1. Implement the Engine Management Service layer to fulfill the API contract.
2. Update the `docs/adr/README.md` index table to include this new ADR.