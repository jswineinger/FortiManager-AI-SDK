# Playbook: SD-WAN Config Audit

## Goal

Read a device's full SD-WAN configuration from FMG and grade it against MSSP best-practice patterns from the SDWAN corpus. Identifies orphaned members, mis-numbered seq-nums, missing health-check coverage, services without SLA fallback, ADVPN gaps, and other config drift.

This is **read-only** — produces a report; does NOT modify the device.

## When to Run

- Quarterly audit per tenant
- After bulk template push (verify the push landed cleanly)
- Before scheduled maintenance (pre-change snapshot)
- Onboarding: validate a freshly-onboarded spoke matches the blueprint

## Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `fmg_host` | Yes | — | FortiManager IP/hostname |
| `adom` | No | `root` | ADOM containing the device |
| `device` | Yes | — | Managed device name |
| `vdom` | No | `root` | VDOM containing the SD-WAN config |

## Procedure

### Step 1 — Pull the full SD-WAN config

```python
sdwan = object-list({
    "fmg_host": fmg_host,
    "url": f"/pm/config/device/{device}/vdom/{vdom}/system/sdwan",
    "verbose": 1
})
cfg = sdwan["data"]   # dict with: zone[], members[], health-check[], service[], neighbor[]
```

Single call returns the entire SD-WAN configuration tree (verified live: 5 sub-tables, all in one response).

### Step 2 — Pull Fabric VPN config (if used alongside SD-WAN)

```python
fabric = object-list({
    "fmg_host": fmg_host,
    "url": f"/pm/config/device/{device}/global/system/fabric-vpn",
    "verbose": 1
})
overlays = object-list({
    "fmg_host": fmg_host,
    "url": f"/pm/config/device/{device}/global/system/fabric-vpn/overlays"
})
```

### Step 3 — Pull live health for cross-reference

```python
live = device-monitor-proxy({
    "fmg_host": fmg_host,
    "resource": "/api/v2/monitor/virtual-wan/health-check",
    "targets": [f"/adom/{adom}/device/{device}"]
})
```

### Step 4 — Apply audit checks

For each domain, score and emit findings:

#### Zones
- ✅ Has at least one non-default zone (i.e. not just `virtual-wan-link`)
- ✅ Each zone has at least one member
- ⚠️ Zones with `advpn-select=1` should have a non-empty `advpn-health-check`
- ❌ FAIL if any zone has 0 members

#### Members
- ✅ All `seq-num` values are unique
- ⚠️ Per-corpus convention: spoke seq-nums = `site_id × 100` + offset (100, 101 for dual hubs)
- ⚠️ Members with `source: 0.0.0.0` SHOULD use a loopback IP (corpus uses 172.16.0.X for site X)
- ❌ Members not assigned to any zone
- Cross-check vs live: each member should appear in `live.results[*][interface]`

#### Health checks
- ✅ At least one health check probes a hub loopback (per corpus: `HUB_Health` → 172.16.255.253)
- ✅ Each hub overlay member is referenced by at least one health-check
- ⚠️ Default_* checks (Default_DNS, Default_Office_365, etc.) — flag if any have empty `members` (orphan)
- ⚠️ SLA threshold of 0 ms latency = nonsensical, flag (saw `Public_SLA` with `latency-threshold: 5`)

#### Services (steering rules)
- ✅ Each service references a `health-check` for SLA mode (`mode=3`)
- ⚠️ Services with `priority-members` empty
- ⚠️ Services using ISDB (`internet-service=1`) should use `Public_SLA` or equivalent for fallback
- Per-corpus: rule IDs cascade — 1=DEFAULT, 2=VOICE, 3=BULK; flag if naming suggests collisions

#### Neighbor (ADVPN)
- ✅ If `zone[].advpn-select=1`, expect at least one `neighbor[]` entry
- ✅ `neighbor[].health-check` should match an existing `health-check[].name`
- ✅ `neighbor[].member` IDs should match seq-nums of overlay members

#### Cross-reference
- Every name referenced in `service[].health-check`, `service[].priority-members`, `service[].priority-zone` must exist in the corresponding table

### Step 5 — Synthesize verdict

```json
{
  "overall_grade": "B",   // A=clean, B=minor issues, C=structural issues, F=broken
  "device": "howard-sdwan-spoke-1",
  "vdom": "root",
  "summary_counts": {
    "zones": 2, "members": 3, "health_checks": 6, "services": 3, "neighbors": 1
  },
  "findings": [
    {"severity": "warn",  "domain": "members",       "detail": "wan member (seq=2) has source 0.0.0.0; corpus convention is to use a loopback IP for spoke identity"},
    {"severity": "info",  "domain": "health-checks", "detail": "5 of 6 health-checks (Default_*) have empty members list — orphaned/unused"},
    {"severity": "ok",    "domain": "advpn",         "detail": "SDWAN-HUB zone has advpn-select=1 + advpn-health-check=HUB_Health, neighbor 172.16.255.253 properly referenced"}
  ],
  "recommendations": [
    "Set wan member source to 172.16.0.2 to match SD-WAN spoke identity",
    "Either populate or delete Default_DNS/Default_Office_365/etc. health-checks if not used"
  ]
}
```

## Example AI Dialogue

**User:** "Audit the SD-WAN config on my spoke"

**AI:**
> Pulling SD-WAN config for howard-sdwan-spoke-1 (root VDOM).
>
> **Topology:** 2 zones (virtual-wan-link, SDWAN-HUB), 3 members (HUB1-VPN1 seq=100, wan seq=2, HUB2-VPN2 seq=101), 6 health-checks, 3 service rules, 1 ADVPN neighbor.
>
> **Grade: B** (1 minor issue, several info-level cleanup opportunities).
>
> **Findings:**
> - ⚠️ The `wan` member uses source `0.0.0.0` — corpus best practice is to use the spoke's loopback IP (172.16.0.X) so policy ordering is identity-based.
> - ℹ️ 5 of 6 health-checks (Default_DNS, Default_Office_365, etc.) have empty `members` lists — they're configured but not assigned. Consider deleting or populating.
> - ✅ ADVPN setup is clean — SDWAN-HUB zone has health-check tied to neighbor 172.16.255.253.
>
> **Recommended next:** want me to fix the wan source IP? I can use object-update.

## Tools Used

- `object-list` — pulls SD-WAN config + Fabric VPN config
- `device-monitor-proxy` — live health-check cross-reference

(NB: this playbook is **read-only**. Mutation playbooks `sdwan-spoke-onboard` and `sdwan-fix-drift` are separate.)

## Failure Modes

| Symptom | What to tell the user |
|---|---|
| `object-list` returns code -3 on `system/sdwan` | "SD-WAN not configured on this device. Use sdwan-spoke-onboard playbook to set it up." |
| All `members[*].zone` empty | "Members exist but unassigned to zones — config corrupt." |
| `live` response has interfaces not in `cfg.members` | "Drift detected — live device has additional SD-WAN members not in FMG. Run config sync." |
| `neighbor[].health-check` references missing health-check | "Broken reference. Either add the missing health-check or remove the neighbor entry." |

## Related Playbooks

- `sdwan-health-check.md` — runtime health (vs this playbook's config audit)
- `sdwan-spoke-onboard.md` — fix drift / build new spoke (mutation, planned)
