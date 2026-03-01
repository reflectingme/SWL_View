# Known Issues Log

This file tracks known bugs/limitations that are not yet resolved.

## Open Issues

1. Thetis mode forcing is inconsistent (AM may not apply, or VAC may toggle)
- Status: Open
- First seen: 2026-03-01
- Area: TCI / Tune mode handling
- Symptoms:
  - Clicking a station tunes frequency correctly.
  - In some Thetis builds, mode does not reliably switch to AM.
  - In some cases, forcing mode may toggle VAC off.
- Notes:
  - Tried multiple command variants (`modulation:0,0,<mode>`, `modulation:0,<mode>`, `mode:0,0,<mode>`).
  - Current implementation for Thetis uses modulation-only variants to reduce side effects.
  - Pending confirmation from Thetis developer on preferred/official mode command behavior for latest build.

## Resolved Issues

1. Send Spot: Thetis spot text did not consistently appear
- Status: Resolved
- First seen: 2026-02-28
- Resolved: 2026-02-28
- Area: TCI / Spot integration
- Resolution summary:
  - Updated spot command to Thetis-observed format:
    - `SPOT:{CALL},{MODE},{FREQ_HZ},20381,[json]{...};`
  - Kept tune command flow unchanged.
