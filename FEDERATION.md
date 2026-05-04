# Federation — How Multi-Hub Sync Works

ResKiosk supports **multi-hub federation**: multiple shelter Hubs running independently can discover each other and replicate data so that every Hub has a unified view of emergency alerts, kiosk registrations, and messages across the network.

---

## Architecture Overview

```
┌──────────────┐          pull /federation/changes          ┌──────────────┐
│   Hub A       │ ◄──────────────────────────────────────── │   Hub B       │
│  (SQLite DB)  │ ────────────────────────────────────────► │  (SQLite DB)  │
│               │          pull /federation/changes          │               │
│  ChangeLog    │                                           │  ChangeLog    │
│  HubPeer      │                                           │  HubPeer      │
│  Fed. Cursor  │                                           │  Fed. Cursor  │
└──────────────┘                                           └──────────────┘
```

Each Hub is **both a producer and consumer**. It logs its own changes and periodically pulls changes from every known peer.

---

## Key Components

| File | Role |
|---|---|
| `hub/core/change_tracker.py` | **Producer** — writes mutations to the `change_log` table |
| `hub/api/routes_federation.py` | **API** — exposes `GET /federation/changes` and `GET /federation/peers` |
| `hub/core/federation_worker.py` | **Consumer** — background thread that pulls and applies remote changes |
| `hub/db/schema.py` | **Schema** — defines `HubPeer`, `FederationCursor`, and `ChangeLog` tables |

---

## How Data Flows

### Step 1: Local Mutation → Change Log (Producer)

Whenever the Hub modifies data that should be shared, it calls `log_change()`:

```python
log_change(db, "emergency_alert", alert.id, "upsert", payload_dict)
```

This inserts a row into the `change_log` table with:
- **entity_type** — what kind of record changed (`emergency_alert`, `kiosk`, `hub_message`)
- **entity_key** — the record's local ID
- **op** — the operation (`upsert` or `delete`)
- **payload_json** — full JSON snapshot of the record
- **source_hub_id** — this Hub's ID (so peers know where it came from)

**Where `log_change()` is called:**

| Route | Entity Type | Trigger |
|---|---|---|
| `routes_emergency.py` | `emergency_alert` | Alert created, acknowledged, responding, or resolved |
| `routes_network.py` | `kiosk` | Kiosk heartbeat or new kiosk registration |
| `routes_messages.py` | `hub_message` | Message created, updated, or deleted |

### Step 2: Exposing the Feed (API)

The `GET /federation/changes?after_id=N&limit=100` endpoint returns all `change_log` rows with `id > N`, ordered ascending. Peers call this to ask **"what's new since I last checked?"**

Response shape:
```json
{
  "changes": [
    {
      "id": 42,
      "entity_type": "emergency_alert",
      "entity_key": "7",
      "op": "upsert",
      "payload": { "kiosk_id": "K-01", "status": "ACTIVE", ... },
      "source_hub_id": "1",
      "changed_at": 1740900000
    }
  ]
}
```

### Step 3: Pulling & Applying (Consumer)

The `FederationWorker` is a daemon thread started at boot (`hub/main.py`). Every **30 seconds** it:

1. Queries the `hub_peers` table for all peers with `status = "online"`
2. For each peer, reads the `federation_cursor` table to get `last_change_id`
3. Calls `GET {peer.base_url}/federation/changes?after_id={last_change_id}`
4. Applies each change locally using **upsert** logic
5. Advances the cursor to the highest `change_id` received

---

## Peer Discovery & Connectivity

### The `hub_peers` Table

Stores known neighboring Hubs:

| Column | Purpose |
|---|---|
| `peer_hub_id` | Unique ID of the remote Hub (primary key) |
| `peer_name` | Human-readable name |
| `base_url` | Full URL (e.g. `http://192.168.1.50:8001`) |
| `status` | `online` or `offline` — only online peers are synced |
| `last_seen` | Unix timestamp of last successful contact |
| `last_sync_at` | Unix timestamp of last completed sync cycle |
| `auth_shared_key` | Reserved for future authentication |

### The `federation_cursor` Table

Tracks sync progress per peer:

| Column | Purpose |
|---|---|
| `peer_hub_id` | Which peer this cursor belongs to |
| `last_change_id` | The highest `change_log.id` successfully applied from this peer |
| `last_synced_ts` | When the last sync happened |

This ensures the sync is **resumable** — if the Hub restarts, it picks up exactly where it left off.

---

## Data Mirroring Rules

### Emergency Alerts
- **Key:** `(hub_id, alert_id_local)` — each Hub's alerts are namespaced by its Hub ID
- **On insert:** Creates a new local row with the remote Hub's `hub_id`
- **On update:** Overwrites mutable fields (status, acknowledged_by, resolved, etc.)
- No remote alert will collide with local alerts since they have different `hub_id` values

### Kiosks
- **Key:** `(hub_id, kiosk_name)` — kiosks are namespaced by their home Hub
- **On insert:** Creates a new local kiosk record tagged with the remote Hub ID
- **On update:** Refreshes `status` and `last_seen`

### Hub Messages
- **Status:** Stubbed in v1 — `_apply_message()` is a no-op placeholder

---

## Consistency Model

| Property | Value |
|---|---|
| **Consistency** | Eventually consistent (30-second polling) |
| **Direction** | Bidirectional pull (each Hub pulls from every peer) |
| **Idempotency** | Safe to re-apply — upsert logic means duplicates are harmless |
| **Ordering** | Guaranteed per-peer via monotonic `change_log.id` cursor |
| **Conflict resolution** | Last-write-wins (latest pull overwrites) |
| **Failure handling** | Errors are logged; sync retries on the next 30-second cycle |

---

## Running Multiple Hubs on One Machine

For testing, you can run two Hub instances on different ports with separate databases:

```bash
# Hub A (default)
py -m hub.launcher

# Hub B (different port + database)
set HUB_PORT=8001
set HUB_DB_PATH=hub_b.db
py -m hub.launcher
```

Then register each Hub as a peer of the other via the `hub_peers` table or API.

---

## Diagram: Sync Lifecycle

```
  Hub A (local)                                   Hub B (remote peer)
  ─────────────                                   ──────────────────
       │                                                │
       │  1. Emergency alert created                    │
       │  → log_change("emergency_alert", ...)          │
       │  → row inserted into change_log                │
       │                                                │
       │                          ┌─────────────────────┤
       │                          │ 2. FederationWorker  │
       │                          │    wakes up (30s)    │
       │                          └──────────┬──────────┘
       │                                     │
       │  ◄── GET /federation/changes?after_id=41 ──────│
       │                                     │
       │  ──► { changes: [{id:42, ...}] } ──────────────│
       │                                     │
       │                          3. _apply_alert()      │
       │                          → upsert into local DB │
       │                          → advance cursor to 42 │
       │                                                │
```
