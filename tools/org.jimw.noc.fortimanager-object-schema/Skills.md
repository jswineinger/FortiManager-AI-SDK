# FortiManager Object Schema — Skills

## How to Call

Use this tool when:
- Partner AI is writing a new CRUD tool for an FMG resource and needs to know the field shape (no prior docs)
- User asks "what fields does a VIP object have?" or "what are the valid values for policy.action?"
- Deciding required vs optional fields before building a form
- Discovering which fields reference other tables (datasrc) — those must be supplied by the caller with no default possible

**This is the foundation of AI-authored tools.** Instead of hardcoding every FortiOS object type, partners' AIs introspect FMG itself.

**Example prompts:**
- "What fields does a firewall address have?"
- "Show me the schema for policy packages"
- "What are the valid values for policy.action?"
- "List all ADOM-level object tables I can manage"

## Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `fmg_host` | string | Yes | — | FMG hostname/IP |
| `url` | string | Yes | — | Leaf table URL or parent category URL |
| `summarize` | boolean | No | `true` | Flatten to AI-friendly field list (vs raw FMG tree) |
| `include_help` | boolean | No | `false` | Include FMG `help` strings (verbose) |

## URL Patterns

| URL | Returns |
|---|---|
| `/pm/config/adom/{adom}/obj/firewall/address` | Schema for one table |
| `/pm/config/adom/{adom}/obj` | All ADOM-level object tables (compact summary) |
| `/pm/config/adom/{adom}/pkg/{pkg}/firewall/policy` | Policy table schema |
| `/pm/config/device/{device}/global/system/global` | Device-level system schema |
| `/pm/config/device/{device}/vdom/{vdom}` | All tables in a device VDOM |

## Interpreting Results

### Summarized single-table (most common)

```json
{
  "success": true,
  "url": "/pm/config/adom/root/obj/firewall/address",
  "table_name": "firewall address",
  "alimit": 400000,
  "field_count": 46,
  "required_datasrc_fields": [
    {"name": "associated-interface",
     "refs": [{"category": "system interface", "mkey": "name"}]}
  ],
  "fields": [
    {"name": "allow-routing", "type": "uint32", "default": "disable",
     "options": {"disable": 0, "enable": 1}},
    {"name": "type", "type": "uint32", "default": "ipmask",
     "options": {"ipmask": 0, "iprange": 1, "fqdn": 2, ...}},
    {"name": "subnet", "type": "ip4addr-any", "default": "0.0.0.0 0.0.0.0"}
  ]
}
```

**Field object shape:**
- `name`: attribute name
- `type`: FMG primitive — `uint32`, `string`, `ip4addr`, `datasrc`, `list`, etc.
- `default`: value FMG uses when caller omits
- `options`: enum map (symbolic → int) when `type` is enumerated
- `max`: max size for strings/integers
- `datasrc_refs`: list of `{category, mkey}` for fields that reference other tables
- `excluded`: `true` if field is read-only / server-computed

### Parent category (e.g. `/pm/config/adom/root/obj`)

```json
{
  "success": true,
  "url": "/pm/config/adom/root/obj",
  "table_count": 85,
  "tables": [
    {"table_name": "firewall address", "alimit": 400000, "field_count": 46},
    {"table_name": "firewall addrgrp", "alimit": null, "field_count": 12},
    ...
  ]
}
```

## Example — Before Creating a VIP

**User:** "What do I need to create a VIP?"

**Tool call:**
```python
execute_certified_tool(
    canonical_id="org.ulysses.noc.fortimanager-object-schema/1.0.0",
    parameters={
        "fmg_host": "192.168.215.17",
        "url": "/pm/config/adom/root/obj/firewall/vip"
    }
)
```

Agent inspects `required_datasrc_fields` + `fields` with no default, then knows exactly what to pass.

## Error Handling

| Error | Meaning | Fix |
|---|---|---|
| `FMG {'code': -6, ...}` | Invalid URL | Table doesn't exist at that path; try parent category first |
| `FMG {'code': -3, ...}` | ADOM/package/device missing | Verify names |
| Empty `fields` | URL resolved but no schema | You hit a non-table URL (e.g. a single entity path) |

## Pairs With

- `fortimanager-field-datasrc` — for datasrc fields, fetch the VALID VALUES from the referenced tables
- `fortimanager-firewall-address-create` (or any CRUD tool) — use schema to validate inputs before calling
