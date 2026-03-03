# Legacy checks (footer / PDP OSM)

The **footer Klarna logo** and **PDP OSM** checks have been moved to `auditor/legacy_checks/`. They are **not run by default** so that the pipeline can focus on **platform/PSP detection** first, without triggering scroll/overlay logic.

## What is in legacy

- `auditor/legacy_checks/footer_klarna_logo.py` — FOOTER_KLARNA_LOGO (scroll to bottom, overlay clear, bring footer into view, template match).
- `auditor/legacy_checks/pdp_osm.py` — PDP_OSM (navigate to PDP, find Klarna OSM, green box overlay).

Code is **unchanged** and **runnable**; it is only excluded from the default pipeline.

## How to run legacy checks again

Set the environment variable:

```bash
export ENABLE_LEGACY_FOOTER_CHECKS=true
```

Then run the auditor as usual:

```bash
python3 -m auditor.run --merchant https://example.com --out-dir ./out/example
```

With the flag set, the run will:

1. Run **detection** (platform/PSP) as usual.
2. **Include** legacy checks (FOOTER_KLARNA_LOGO, PDP_OSM) in the pipeline.

## Default behavior (flag unset or false)

- Only **detection** runs (collect signals, fingerprint match, output `detection_summary` in the report).
- Legacy checks are **skipped** and listed in the report under `skipped_checks` with reason: `skipped: focus shifted to detection-only`.

## Rollback

To rely only on the old behavior (no detection, only footer/PDP):

1. Set `ENABLE_LEGACY_FOOTER_CHECKS=true`.
2. Optionally adjust the main entry so it does not run detection (or keep detection + legacy as above).
