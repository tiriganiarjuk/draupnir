# ATTENTION — the nornir readers return the gate contract

The nornir readers (`read_{json,yaml,toml,toon,xml,markdown}_validate_json`) were rebuilt and
redeployed to `~/ai/tools/lib`. `read(file_path, schema_name, schema_dir)` returns the same shape
every nornir gate returns:

```
{"ok": bool, "data": str | None, "error": {"type": str, "message": str} | None}
```

- `ok` true → `data` is the validated JSON string, on its way into `Model.model_validate_json`.
- `ok` false → `error.type` names the failure class, `error.message` is the educational text.

| `error.type` | Meaning |
|---|---|
| `read_error` | the file could not be read |
| `parse_error` | the file is not valid in its format |
| `conversion_error` | the converted JSON was invalid (an engine fault) |
| `schema_error` | the schema could not be loaded or compiled |
| `validation_error` | the data does not match the schema |
| `cache_error` | the validator cache failed (an engine fault) |

## What breaks here

This project's wrappers pass the reader's return value on as a `str`, so every read through them
fails until the wrappers are fixed:

- `src/draupnir/logic/impure/loader/ffi.py` — `gate_validate` (YAML)
- `src/draupnir/logic/impure/codegen_config/ffi.py` — `read_codegen_config` (TOML)

## The fix

Type the result at the wrapper: a frozen model of the contract in `structure/`, validated from
the reader's return, and the caller branches on `ok` and `error.type`. Decide per call site what
each `error.type` means for this project — hard failure, held back, reported.

Delete this file when the fix is in.
