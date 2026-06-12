# Deployment Guide

## Scripts
| Script ID | Type | Entry point | Deploy on | Effective context | Schedule |
|---|---|---|---|---|---|
| `customscript_rippling_aicje_name_ue` | User Event (SS2.1) | `beforeSubmit` (CREATE/EDIT) | Advanced Intercompany Journal Entry | Web services only (enforced in code) | n/a |
| `customscript_rippling_aicje_name_mr` | Map/Reduce (SS2.1) | getInputData/map/summarize | n/a | Scheduled | Daily |

## Script parameter
- `custscript_rippling_memo_prefix` — text, default `[Rippling]`. The line-memo hardening lock.

## Features
- Server SuiteScript (`SERVERSIDESCRIPTING`); OneWorld with Advanced Intercompany Journal Entries.

## Before you deploy
- **Edit the Map/Reduce recurrence start date** in `src/Objects/customscript_rippling_aicje_name_mr.xml`.
- Status enums differ by script type in SDF: the UE deployment uses `TESTING`/`RELEASED`; the
  Map/Reduce deployment uses `TESTING`/`SCHEDULED` (`RELEASED` is **not** a valid token for
  scheduled scripts and will fail server validation with "Invalid status reference key").

## Path A — SDF (preferred)
1. `suitecloud account:setup` → point at **SANDBOX** first.
2. `suitecloud project:validate` → fix anything it reports.
3. `suitecloud project:deploy` → deploys scripts + objects at status **TESTING**.
4. Run UAT (`docs/UAT_GUIDE.md`).
5. Re-point at **PRODUCTION**; set the UE deployment status to `RELEASED` and the M/R to
   `SCHEDULED` in the object XML; redeploy.

### ⚠ CRITICAL — confirm the Map/Reduce is actually scheduled
The backstop only works if the M/R deployment has a **daily recurrence**. After deploy, open the
M/R deployment in the UI and **verify a populated "Next Run" time** — if it's blank, the sweep
will never fire. (If `project:validate` rejects the recurrence schema in your account version,
set the daily schedule manually on the deployment: Schedule subtab → Daily.)

## Path B — UI (no-CLI fallback)
1. Upload the three `.js` files to the File Cabinet under `/SuiteScripts/rippling-aicje-name/`
   (keep the `lib/` subfolder).
2. Create a **User Event** Script record from the UE file; add the script parameter (default
   `[Rippling]`); deploy on **Advanced Intercompany Journal Entry**, status Testing, log level Audit.
3. Create a **Map/Reduce** Script record from the sweep file; create a **Scheduled** deployment (daily).
4. UAT, then set the UE deployment to **Released** in production.

## Roles / permissions
- The Map/Reduce run-as role needs **edit** on Advanced Intercompany Journal Entry. To enrich
  closed-but-unlocked periods (`allownonglchanges='T'`), it also needs **Allow Non-G/L Changes**.
  (Fully open periods need no special permission.)

## Error handling / notifications
- UE: **fail-open** — errors → `log.error`; enable *Notify Script Owner on Error* on the deployment.
- M/R: per-record errors surface in `summarize()`; enable owner notification.

## Operational notes
- **Integration token ownership:** if your Rippling integration's NetSuite token is owned by an
  individual user, entries post as that user and the token dies with their account — use a
  service account.
- **Segregation of duties:** the script acts as preparer (fills a non-posting field pre-approval);
  a human still reviews and approves every AICJE.

## Rollback
- Disable the deployment(s). To revert data, clear/reset `entity` on affected lines (non-posting;
  no GL effect).
