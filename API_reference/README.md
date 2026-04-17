# API Reference — Intake Rules

This folder is the **canonical source of truth** for FortiManager API documentation used by tool authors (human or AI).

## Structure

```
API_reference/
├── README.md      ← you are here (the rules)
├── raw/           ← raw Swagger / FNDN dumps, one file per endpoint
└── index.json     ← machine-readable: endpoint → raw file map
```

## Drop Rule (for humans)

When pasting docs from FNDN / Swagger / Ansible / curl, follow this naming:

```
raw/<path-with-dashes>.md     e.g. raw/dvmdb-adom.md
                                    raw/dvmdb-script-execute.md
                                    raw/pm-config-firewall-address.md
                                    raw/task-task.md
```

Rules:
- One file per endpoint.
- Lowercase, dashes for `/`, drop leading slash.
- Paste whatever format the source gave you (markdown, JSON snippet, plain text). **Don't hand-edit.** Raw = as-received.
- After dropping, update `index.json` (or ask the AI to do it).

## AI Rule (when building a tool)

Before you touch `execute()`, read in this order:

1. `docs/FNDN-API-Reference.md` — high-level endpoint map (fast orientation)
2. `API_reference/index.json` — find which raw file documents your endpoint
3. `API_reference/raw/<that-file>.md` — authoritative field names, param shapes, response schemas

If `raw/` has no matching file for your endpoint, **STOP** and ask the human to dump it. Do not guess field names.

## index.json Format

```json
{
  "endpoints": {
    "/dvmdb/adom": {"raw_file": "dvmdb-adom.md", "verbs": ["get"]},
    "/dvmdb/script/execute": {"raw_file": "dvmdb-script-execute.md", "verbs": ["exec"]},
    "/task/task/{taskid}": {"raw_file": "task-task.md", "verbs": ["get"]}
  },
  "last_updated": "2026-04-17"
}
```

Maintained by whoever drops a new raw file.
