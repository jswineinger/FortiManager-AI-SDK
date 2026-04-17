# FortiManager Object Checksum — Skills

## How to Call

Use this tool when:
- Building change-detection loops ("alert me when policy package changes")
- Confirming a sibling change took effect before polling the full table
- Cheap "has anything changed?" check for idle monitoring
- Drift detection between two points in time — compare stored value vs current

**Example prompts:**
- "What's the current version of the default policy package?"
- "Give me the ADOM checksum for root"
- "Has the firewall address table in tenant A changed since I last looked?"

## Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `fmg_host` | string | Yes | — | FMG hostname/IP |
| `url` | string | Yes | — | Table URL (for chksum) or ADOM obj root (for devinfo) |
| `mode` | string | No | `chksum` | `chksum` (table version int) or `devinfo` (ADOM UUID) |

## Mode Differences

| Mode | Granularity | Returns | Use when |
|---|---|---|---|
| `chksum` | Per-table | Integer version (e.g. `"9"`) | You care about a specific table changing |
| `devinfo` | Per-ADOM object DB | UUID string | You want "did anything change in this ADOM?" |

## Interpreting Results

### chksum
```json
{
  "success": true,
  "url": "/pm/config/adom/root/pkg/howard-sdwan-spoke-1/firewall/policy",
  "mode": "chksum",
  "value": "9"
}
```
Compare `value` to the previously-stored version. If different, the table has been modified.

### devinfo
```json
{
  "success": true,
  "url": "/pm/config/adom/root/obj",
  "mode": "devinfo",
  "value": "cbc1e398-3a73-51f1-f323-0b237cb063de"
}
```
New UUID = something in the ADOM's object DB changed.

## Example — Change Detection Loop Pattern

```python
# Iteration 1
r = execute_certified_tool(
    canonical_id="org.ulysses.noc.fortimanager-object-checksum/1.0.0",
    parameters={"fmg_host": "192.168.215.17",
                "url": "/pm/config/adom/root/pkg/default/firewall/policy"})
baseline = r["value"]  # "9"

# ...time passes, some other process modifies policies...

r = execute_certified_tool(canonical_id="...", parameters={...})
if r["value"] != baseline:
    # Package changed; fetch full policy list to see what
    pass
```

## Error Handling

| Error | Meaning | Fix |
|---|---|---|
| `FMG {'code': -6, ...}` | Invalid URL | For devinfo, use `/pm/config/adom/{adom}/obj`; for chksum, a specific table URL |
| `Unexpected devinfo response` | Mode/URL mismatch | devinfo expects `.../obj` root; chksum expects a specific table |
| `Unexpected chksum response` | Same, inverse | Stick to the mode's recommended URL shape |

## Pairs With

- `fortimanager-policy-list` — after chksum reports a change, fetch the full table to see what
- `fortimanager-object-count` — quick sanity counts alongside version tracking
