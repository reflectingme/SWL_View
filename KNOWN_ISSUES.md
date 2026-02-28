# Known Issues Log

This file tracks known bugs/limitations that are not yet resolved.

## Open Issues

- None currently logged.

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
