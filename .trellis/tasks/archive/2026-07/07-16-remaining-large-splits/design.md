# Design

Reuse `_split_module_package.py` and `_split_js_file.py`.

## openapi.py

| Module | Symbols |
|--------|---------|
| builders | _envelope_ref … _operation helpers |
| schemas | _schemas |
| paths | _paths |
| contract | get_external_api_openapi_contract |

Keep `from outlook_web.services.external_api.openapi import get_external_api_openapi_contract` working via `openapi/__init__.py` or replace file with package `openapi/`.

**Note:** Python cannot have both `openapi.py` and `openapi/` — convert to package, update imports if any use submodule paths.

## Frontend packages

Same pattern: globals + domain modules + `_load_order` + `_function_order`.
