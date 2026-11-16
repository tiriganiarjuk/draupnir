# ATTENTION — the nornir readers return the gate contract

The nornir readers (`read_{json,yaml,toml,toon,xml,markdown}_validate_json`) were rebuilt and
redeployed to `~/ai/tools/lib`. `read(file_path, schema_name, schema_dir)` returns the same shape
every nornir gate returns:

```
{"ok": bool, "data": str | None, "error": {"type": str, "message": str} | None}
```

- `ok` true → `data` is the validated JSON string, on its way into `Model.model_validate_json`.
- `ok` false → `error.type` names the failure class, `error.message` is the educational text.

The failure classes are tabled in `~/ai/smidja/nornir/MUST_READ_BEFORE_BUILDING.md`
§ `error.type`, generated from the error registry.

## What breaks here

This project's wrappers pass the reader's return value on as a `str`, so every read through them
fails until the wrappers are fixed:

- `src/draupnir/logic/impure/loader/ffi.py` — `gate_validate` (YAML)
- `src/draupnir/logic/impure/codegen_config/ffi.py` — `read_codegen_config` (TOML)

## The fix

Type the result at the wrapper with the two-outcome model in `structure/`: a success model with
`ok: Literal[True]` and a refusal model with `ok: Literal[False]`, joined by
`Field(discriminator="ok")` — the form `~/ai/smidja/nornir/MUST_READ_BEFORE_BUILDING.md`
§ Calling one from Python shows, working in Galdr at
`~/ai/smidja/galdr/src/galdr/structure/model/gate_types.py`. The caller matches on the outcome's
type; a refusal carries `error.type` to branch on. Decide per call site what each `error.type`
means for this project — hard failure, held back, reported.

Delete this file when the fix is in.
