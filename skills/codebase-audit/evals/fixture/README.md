# Sectionsvc

A small service that renders landing-page sections from structured payloads.

- `app/registry.py` — section builders and layout metadata
- `app/pipeline.py` — payload validation, serialization, caching
- `app/handlers.py` — request handlers
- `app/tasks.py` — background job execution
- `app/storage.py` — job persistence and report export
- `config.yaml` — runtime configuration
