# Capabilities — What This SDK Can Do

**AI: read this file at session start. When the user asks "what can you do?" or describes an operational problem, map their language to the capabilities below and propose 1-3 concrete options.** Don't dump the full list at once — pick what fits the user's context.

This is the **outcome-oriented** index. For the primitives themselves, see `tools/`.
For executable step-by-step workflows, see `playbooks/`.

---

## 🟢 Discovery & Audit

Outcomes you can deliver today:

| Capability | Tools used | Playbook |
|---|---|---|
| **Enumerate tenant inventory** — every ADOM, device, package, address, policy | `adom-list`, `device-list`, `policy-package-list`, `firewall-address-list`, `object-list`, `object-count` | — |
| **Count anything** — "how many policies does tenant X have?" | `object-count` | — |
| **Schema introspection** — "what fields does a VIP object have?" | `object-schema` | — |
| **Reference discovery** — "what are valid values for policy.srcaddr?" | `field-datasrc` | — |
| **Policy review with readable names** | `object-list` with `expand_datasrc` | — |
| **Security posture audit** — orphans, overly-permissive rules, unused objects | `object-list`, `object-count`, `policy-list`, `device-monitor-proxy` | `security-posture-audit.md` |

---

## 🟡 Authoring (Build)

| Capability | Tools used | Playbook |
|---|---|---|
| **Create any firewall object** — address, VIP, addrgrp, service, schedule, wildcard-fqdn | `object-schema` → `object-create` | — |
| **Author a firewall policy end-to-end** — addresses, services, policy | `firewall-address-create`, `object-create`, `policy-create` | — |
| **Build a CLI script library** | `script-create` | — |
| **Define MSSP variable templates** — per-site LAN_SUBNET, HOSTNAME, BGP_LOOPBACK, etc. | `metadata-create`, `metadata-set-device` | `tenant-onboarding.md` |
| **Onboard SD-WAN spoke** — full config from site_id + loopback + hubs | `object-create` × N + `device-settings-install` | `sdwan-spoke-onboard.md` |

---

## 🟠 Change (Modify / Remove)

| Capability | Tools used | Playbook |
|---|---|---|
| **Edit any object** — change color, comment, status, subnet | `object-update` | — |
| **Atomically manage group members** — add/remove/clear | `object-member-update` | — |
| **Delete anything safely** — with idempotent mode | `object-delete` | — |
| **Override per-device variable values** | `metadata-set-device` | — |
| **Audit what values a device will see at install** | `metadata-get-device` | — |

---

## 🔴 Execute (Push / Run)

| Capability | Tools used | Playbook |
|---|---|---|
| **Install a policy package to live FortiGates** | `policy-package-install` + `task-status` | `tenant-onboarding.md` |
| **Push device-scope settings only** (DNS, SNMP, interfaces) | `device-settings-install` + `task-status` | — |
| **Run a CLI script against live devices** | `script-run` (exec + poll + log) | — |
| **Any long-running FMG operation with task tracking** | `task-status` | — |

---

## 🔵 Monitor (Live + Historical)

| Capability | Tools used | Playbook |
|---|---|---|
| **Live FortiGate state via FMG broker** — interfaces, sessions, CPU, routes, BGP, IPsec — no per-device credentials needed | `device-monitor-proxy` | — |
| **SD-WAN health snapshot** — live + historical trend in one call | `device-monitor-proxy` + `sdwan-history` | `sdwan-health-check.md` |
| **SD-WAN config audit** — grade tenant SD-WAN against best practices | `object-list` + `device-monitor-proxy` | `sdwan-config-audit.md` |
| **Change detection** — "did the policy package change since I last looked?" | `object-checksum` | `mssp-change-detection.md` |
| **Device reachability + sync status** | `device-list` (conn_status + conf_status) | — |

---

## 🧭 How the AI Should Use This Index

**When the user asks "what can you do?":**
- Pick 3 capabilities most likely to match their role (MSSP analyst, network engineer, security auditor)
- Describe each in ONE sentence using their language (not tool names)
- Offer to run one

**When the user describes a problem:**
- Match it to a capability row above
- If a playbook exists, mention it by name and offer to execute step-by-step
- If no playbook exists, propose the tool sequence inline

**Example: user says "my SD-WAN feels sluggish":**
> I can check that two ways: live state right now (link status, per-member health), and a trend for the last hour (latency/jitter/packet loss). Want me to run the SD-WAN health playbook?

**Example: user says "I need to onboard a new branch tomorrow":**
> I have a tenant onboarding playbook that handles the template variables per-device plus the policy install. Want me to walk you through it?

---

## What This SDK CANNOT Do (Yet)

Be honest with the user — set expectations:

- **No FortiAnalyzer (FAZ) direct queries** — use FMG's event log proxies or log forwarding instead
- **No FortiSOC / FortiSIEM correlation** — out of scope for FMG SDK
- **No zero-touch provisioning (ZTP)** lifecycle — that lives in FortiZTP, separate SDK
- **No mTLS client-cert auth** — token + session auth only
- **No direct FortiWAN / SD-WAN Orchestrator API** — separate cookie-authenticated API, not yet wrapped

If partner needs any of the above, point them at the matching product's own API.

---

## Index of Playbooks

See `playbooks/` folder:

| Status | Playbook | Outcome |
|---|---|---|
| Built | `sdwan-health-check.md` | Live + historical SD-WAN health snapshot |
| Built | `sdwan-config-audit.md` | Read-only SD-WAN config grade (zones, members, health-checks, services, neighbors) vs MSSP best practices |
| Built | `sdwan-spoke-onboard.md` | Build SD-WAN config on a spoke from scratch — zones, members, health-checks, ADVPN neighbor — with dry-run + rollback |
| Planned | `tenant-onboarding.md` | Device blueprint + metadata + policy install |
| Planned | `security-posture-audit.md` | Policy hygiene + live hit stats |
| Planned | `mssp-change-detection.md` | Version/checksum drift loop for drift alerts |

(More coming — suggest one if you hit a gap.)
