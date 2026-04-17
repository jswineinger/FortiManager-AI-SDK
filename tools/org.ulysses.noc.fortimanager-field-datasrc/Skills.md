# FortiManager Field Datasrc — Skills

## How to Call

Use this tool when:
- About to create/update an object with a cross-table reference and need to know what values FMG will accept
- AI is authoring `policy-create` and needs "what are the valid address names for `srcaddr`?"
- Partner AI is building a UI/form — show the user a dropdown of valid values per field
- Pre-flight validation — verify a name exists before sending it in a CRUD call

**Example prompts:**
- "What can I use for `srcaddr` in the howard-sdwan-spoke-1 policy package?"
- "What are the valid `member` values for address groups in root ADOM?"
- "Show me what `service` objects exist that I can use in policies"

## Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `fmg_host` | string | Yes | — | FMG hostname/IP |
| `url` | string | Yes | — | The table URL whose field you are asking about |
| `attr` | string | Yes | — | The field name within that table (e.g. `srcaddr`, `member`, `service`) |
| `max_per_category` | integer | No | `50` | Cap on returned items per source-table category |

## Why This Tool Exists

Many FMG fields are **datasrc references** — they hold names of objects from other tables. For example, `policy.srcaddr` accepts the name of any `firewall address` OR `firewall addrgrp`. There's no default — the caller MUST pick a valid name. This tool answers "what names are valid right now in this ADOM?"

Consult `fortimanager-object-schema` first to see which fields are `type: datasrc` and what their `refs` point to.

## Interpreting Results

```json
{
  "success": true,
  "url": "/pm/config/adom/root/pkg/howard-sdwan-spoke-1/firewall/policy",
  "attr": "srcaddr",
  "category_count": 2,
  "categories": [
    {
      "category": "firewall address",
      "total": 22,
      "items": [
        {"name": "RFC1918-10"},
        {"name": "RFC1918-172"},
        {"name": "all"}
      ]
    },
    {
      "category": "firewall addrgrp",
      "total": 3,
      "items": [
        {"name": "internal-groups"}
      ]
    }
  ]
}
```

**Field meanings:**
- `category`: the source table (e.g. `firewall address`)
- `total`: full count across categories (FMG-reported)
- `items[].name`: the valid name to pass back in subsequent CRUD calls

## Example — Build Policy Safely

```python
# Step 1: Ask what srcaddr can reference
src_options = execute_certified_tool(
    canonical_id="org.ulysses.noc.fortimanager-field-datasrc/1.0.0",
    parameters={
        "fmg_host": "192.168.215.17",
        "url": "/pm/config/adom/root/pkg/howard-sdwan-spoke-1/firewall/policy",
        "attr": "srcaddr"
    }
)
# Extract valid names
valid_src = [i["name"] for cat in src_options["categories"] for i in cat["items"]]

# Step 2: Create policy using a confirmed-valid name
execute_certified_tool(
    canonical_id="org.ulysses.noc.fortimanager-policy-create/1.0.0",
    parameters={
        "srcaddr": ["all" if "all" in valid_src else valid_src[0]],
        ...
    }
)
```

## Common Target Fields

| Table | Field | Returns refs to |
|---|---|---|
| `.../firewall/policy` | `srcaddr` / `dstaddr` | firewall address + addrgrp |
| `.../firewall/policy` | `srcintf` / `dstintf` | dynamic interfaces |
| `.../firewall/policy` | `service` | firewall service/custom + group |
| `.../firewall/policy` | `schedule` | firewall schedule/onetime + recurring |
| `.../firewall/addrgrp` | `member` | firewall address + addrgrp |
| `.../firewall/service/group` | `member` | firewall service/custom |

## Error Handling

| Error | Meaning | Fix |
|---|---|---|
| `Missing required parameter: attr` | Forgot `attr` | Supply the field name |
| `FMG {'code': -6, ...}` | Bad URL or attr name | Verify field exists via `fortimanager-object-schema` |
| `Unexpected datasrc shape` | FMG returned non-dict | Usually means `attr` isn't a datasrc field; check schema |

## Pairs With

- `fortimanager-object-schema` — discover WHICH fields are datasrc before querying
- `fortimanager-firewall-address-create` — create missing address if valid list doesn't have what you need
- `fortimanager-policy-create` — use returned names as confirmed-valid refs
