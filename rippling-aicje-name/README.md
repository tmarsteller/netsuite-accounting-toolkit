# netsuite-rippling-aicje-name

**Auto-populate the line-level Name (entity) on NetSuite Advanced Intercompany Journal Entries
created by the Rippling payroll integration.**

## The problem

Rippling's NetSuite integration books multi-subsidiary payroll as **Advanced Intercompany Journal
Entries** (AICJEs) — e.g., the parent pays a foreign subsidiary's payroll, producing intercompany
receivable/payable lines. The integration **does not set the line-level Name (entity) field**
(confirmed by Rippling support: the field isn't supported by their sync), so every intercompany
line arrives blank.

If your consolidation / intercompany-elimination process keys off the counterparty's
**representing entity** on those lines, someone has to open every payroll AICJE and fill the Name
in by hand.

## The fix

Two small SuiteScript 2.1 scripts that do it automatically:

| Script | Type | What it does |
|---|---|---|
| `rippling_aicje_name_ue.js` | User Event (`beforeSubmit`) | Fires the instant Rippling creates the AICJE and fills the Name **before the entry reaches your approval queue**. Edits lines in place — no second save, no recursion. |
| `rippling_aicje_name_sweep_mr.js` | Map/Reduce (scheduled daily) | Backstop: finds any Rippling AICJE in an editable period that still has a blank Name and fixes it. |

**The rule:** for each line where `duetofromsubsidiary` is set and `entity` is empty, set
`entity = the counterparty subsidiary's representing customer` — read **live** from the
`subsidiary` table at run time. No hardcoded account numbers, subsidiaries, or entity IDs: rename
or renumber your intercompany accounts, add subsidiaries, and the script keeps working.

**Detection (how it knows an entry is Rippling's):**
1. Record type — deployed only on Advanced Intercompany Journal Entry;
2. Creation channel — `runtime.executionContext === WEBSERVICES` (Rippling posts via SOAP web
   services; manual UI entries and CSV imports are excluded automatically);
3. A line memo starting with `[Rippling]` (the prefix Rippling writes on every line; configurable
   via script parameter).

**Safety properties**
- **Classification-only:** never touches accounts, debits, credits, amounts, FX, memos, periods,
  or subsidiaries. Zero GL impact.
- **Fail-open:** if anything errors, the payroll entry still saves (un-enriched) and the daily
  sweep recovers it. Payroll posting is never blocked.
- **Idempotent:** re-running on an already-enriched entry is a no-op.
- **Never guesses:** if a counterparty subsidiary has no representing entity configured, the line
  is left blank and an error is logged — nothing is invented.
- Governance-clean: the subsidiary→entity map is fetched with one cached query (`N/cache`,
  5-minute TTL); no DB calls inside line loops; the sweep's input query is bounded.

## Requirements

- NetSuite **OneWorld** with **Advanced Intercompany Journal Entries** enabled
- **Representing customer/vendor** configured on each subsidiary that appears on payroll AICJEs
  (Setup > Company > Subsidiaries). This script uses `representingcustomer`; if your org
  deliberately splits AR/AP representing entities, adapt `buildSubsidiaryEntityMap()` in the lib.
- The Rippling → NetSuite integration posting AICJEs via SOAP web services with its standard
  `[Rippling]` line-memo prefix
- Server-side SuiteScript enabled; SDF (SuiteCloud CLI) for the scripted deploy path

## Install

```bash
npm i -g @oracle/suitecloud-cli      # requires Oracle JDK 17 or 21
suitecloud account:setup             # authenticate (browser OAuth)
suitecloud project:validate          # server-side validation
suitecloud project:deploy
```

Deploys at status **TESTING**. Run UAT (see `docs/UAT_GUIDE.md`), then set the User Event
deployment to **Released** and confirm the Map/Reduce deployment shows a populated **Next Run**
(daily). Full details, including a no-CLI manual path: `docs/DEPLOYMENT_GUIDE.md`.

New to SuiteScript/SDF, or a finance person wondering how this got built? Read
**[docs/HOW_THIS_WAS_BUILT.md](docs/HOW_THIS_WAS_BUILT.md)** — a plain-English walkthrough of the
problem, the design decisions, the full toolchain (Node + JDK + SuiteCloud CLI), and the gotchas.
Want to write the same doc for your own automation? Start from
**[docs/HOW_WE_BUILT_IT_TEMPLATE.md](docs/HOW_WE_BUILT_IT_TEMPLATE.md)**.

> ⚠️ Edit the Map/Reduce deployment's recurrence start date in
> `src/Objects/customscript_rippling_aicje_name_mr.xml` before deploying.

## Caveats

- **Test in sandbox first.** One behavior to verify in your account: that `duetofromsubsidiary`
  is readable in `beforeSubmit` on a web-services create. If it isn't, switch the UE entry point
  to `afterSubmit` + `record.load`/`save` (the shared lib is unchanged; it's idempotent). Even if
  the UE misses, the daily sweep self-heals — the failure mode is benign.
- The `[Rippling]` memo gate is record-scoped: once an entry qualifies, **all** of its
  intercompany lines are enriched. Rippling payroll AICJEs are single-purpose, so this is correct —
  but don't deploy on accounts where mixed-purpose web-services AICJEs exist without reviewing.
- Watch your integration token ownership: if the Rippling integration's NetSuite token is owned by
  an individual user, entries post as that user, and the token dies with their account. Use a
  service account.

## Not affiliated

This project is not affiliated with, endorsed by, or supported by Rippling or Oracle/NetSuite.
Use at your own risk; review and test before running against production financial data.

## License

MIT — see [LICENSE](LICENSE).
