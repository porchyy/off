# Workspace Rules

## Zip and Handoff Cleanup
Before creating zip archives or delivering project files, always remove automatically generated build artifacts and dependency folders:
- `rm -rf frontend/node_modules frontend/dist`
- Remove any temporary test/pycache caches (`.pytest_cache`, `__pycache__`).
