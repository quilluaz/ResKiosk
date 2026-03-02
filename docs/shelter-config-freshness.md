# Shelter Config Freshness Policy

## Overview
ResKiosk now enforces a mandatory weekly review for Shelter Config data.

- Expiry window: `7 days`
- Scope: per section (not whole page)
- Enforced on: Console `Shelter Configuration` page load
- Behavior: blocking modal until admin takes action

## Sections Tracked

- `food_schedule`
- `sleeping_zones`
- `medical_station`
- `registration_steps`
- `announcements`
- `emergency_mode`

## Admin Flow

When an admin opens Shelter Config:

1. Console calls `GET /admin/evac/freshness`.
2. If any section is expired, a blocking modal appears.
3. Admin chooses:
   - `Confirm Selected Up-to-date`: resets freshness timer for selected sections only.
   - `Update Now`: closes modal so admin can edit values and save.

On save (`PUT /admin/evac`):

- Changed sections get fresh `reviewed_at`/`reviewed_by` stamps.
- Shelter config sync still updates evac-sourced KB articles.

## Freshness Metadata Storage

Stored in `evac_info.info_metadata` under `freshness`.

```json
{
  "subFields": {},
  "freshness": {
    "food_schedule": { "reviewed_at": 1700000000, "reviewed_by": "admin1@reskiosk.com" }
  }
}
```

## API

## `GET /admin/evac/freshness`
Returns computed freshness status:

- `freshness_days`
- `sections[]`:
  - `section`
  - `last_reviewed_at`
  - `reviewed_by`
  - `age_days`
  - `expires_at`
  - `is_expired`
- `expired_sections[]`

## `POST /admin/evac/freshness/confirm`
Body:

```json
{
  "sections": ["food_schedule", "announcements"],
  "note": null
}
```

Behavior:

- stamps selected sections with current timestamp and actor
- does not change shelter content
- does not bump KB version

## Actor Attribution

Freshness writes use request header `X-Admin-User` when available.  
Fallback actor value is `system`.

## Notes

- If a section has no freshness stamp, backend falls back to `evac_info.last_updated`.
- If no fallback is available, that section is treated as expired.
- Cloud integration is currently disabled and does not affect freshness logic.
  Freshness checks and enforcement remain fully local and available offline.
