# UAT Guide (SANDBOX)

**Environment:** Sandbox. **Role:** Administrator (or the deployment's run-as role).
**Preconditions:** UE + Map/Reduce deployed to sandbox at status TESTING; every subsidiary that
appears on payroll AICJEs has a representing customer/vendor set (Setup > Company > Subsidiaries).

## A. Schema / context confirmation — DO FIRST
1. In the **Records Browser** (Advanced Intercompany Journal Entry → `line` sublist), confirm the
   internal field IDs used by the library: `entity`, `memo`, and the due-to/from subsidiary field
   (assumed **`duetofromsubsidiary`**). If any differ in your account version, update
   `lib/rippling_aicje_name_lib.js`.
2. Confirm **`duetofromsubsidiary` is readable in `beforeSubmit`** on a web-services create (test
   B1). If NetSuite only populates it on save in your account, switch the UE entry point to
   `afterSubmit` + `record.load`/`save` (the library logic is unchanged; it is idempotent).

## B. User Event tests
| # | Test | Expected |
|---|------|----------|
| B1 | Web-services create of a Rippling-shaped AICJE (intercompany lines: `duetofromsubsidiary` set, `entity` blank, `[Rippling]` line memos) | `entity` set to the counterparty's representing entity, pre-approval |
| B2 | Compare debit/credit/amount/FX before vs after B1 | Identical — zero GL impact |
| B3 | Cash / clearing lines (no `duetofromsubsidiary`) | `entity` stays blank |
| B4 | Create an AICJE in the **UI** with a `[Rippling]` memo | Unchanged (context ≠ WEBSERVICES) |
| B5 | A non-`[Rippling]` web-services or CSV-imported AICJE | Unchanged |
| B6 | Temporarily clear a subsidiary's representing entity; create an entry facing it | Line left blank + `log.error`; record still saves |
| B7 | Re-save an already-enriched entry | No change (idempotent) |
| B8 | Force an error (e.g. temporarily break a field id) | Record still saves; `log.error` written (fail-open) |

## C. Map/Reduce sweep tests
- C1: place 2 un-enriched Rippling-shaped AICJEs in an **open** period; run the M/R on demand →
  both enriched; GL unchanged.
- C2: confirm it ignores closed+locked periods and non-Rippling entries.
- C3: run the M/R against a **closed-but-unlocked** period (`allownonglchanges='T'`) with the
  run-as role → entry enriched, no error; confirm the load+save does not trip intercompany
  re-validation or FX errors.
- C4: confirm the M/R deployment shows a **populated "Next Run" time** (daily schedule active).

## Rollback
Clear/reset the `entity` field on affected lines (non-posting; no GL effect); disable the
deployment(s).
