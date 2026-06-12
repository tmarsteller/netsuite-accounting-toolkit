/**
 * @NApiVersion 2.1
 * @NScriptType UserEventScript
 * @NModuleScope SameAccount
 *
 * rippling_aicje_name_ue.js — Rippling AICJE "Name" (entity) enrichment, User Event.
 *
 * Deploy on : Advanced Intercompany Journal Entry.
 * Fires     : beforeSubmit (CREATE/EDIT). Edits the line entity IN PLACE — no second save, no recursion.
 * Gate      : web-services origin (Rippling SOAP integration) + a [Rippling] line memo.
 * Stance    : FAIL-OPEN — any error is logged and the record still saves un-enriched; the
 *             Map/Reduce sweep recovers it. Enrichment must NEVER block a payroll posting.
 *
 * See docs/DEPLOYMENT_GUIDE.md and docs/UAT_GUIDE.md.
 */
define(['N/runtime', 'N/log', '/SuiteScripts/rippling-aicje-name/lib/rippling_aicje_name_lib'],
function (runtime, log, lib) {

  /**
   * @param {Object} context
   * @param {Record} context.newRecord
   * @param {string} context.type
   */
  function beforeSubmit(context) {
    try {
      if (context.type !== context.UserEventType.CREATE &&
          context.type !== context.UserEventType.EDIT) {
        return;
      }

      // Gate 1 — only the SOAP integration channel. Manual UI (USERINTERFACE), CSV (CSVIMPORT),
      // and the backstop sweep (SCHEDULED/MAPREDUCE) are all excluded — which also means this
      // never re-fires on its own or the sweep's edits.
      if (runtime.executionContext !== runtime.ContextType.WEBSERVICES) { return; }

      var rec = context.newRecord;

      // Gate 2 — Rippling memo signature (hardening lock; configurable via script parameter).
      var prefix = runtime.getCurrentScript().getParameter({ name: 'custscript_rippling_memo_prefix' })
                   || lib.DEFAULT_MEMO_PREFIX;
      if (!lib.hasRipplingMemo(rec, prefix)) { return; }

      // One cached map fetch, then in-memory line enrichment (no DB calls in the loop).
      var res = lib.enrichLines(rec, lib.buildSubsidiaryEntityMap());

      if (res.changed > 0) {
        log.audit({
          title: 'Rippling AICJE Name enrichment',
          details: 'Entity set on ' + res.changed + ' intercompany line(s) pre-approval.'
        });
      }
      if (res.skipped.length > 0) {
        // A counterparty subsidiary has no representing entity — do NOT guess; flag for follow-up.
        log.error({
          title: 'Rippling AICJE Name enrichment — UNMAPPED counterparty (line left blank)',
          details: 'Skipped (lineIndex / dueToFromSubsidiary id): ' + JSON.stringify(res.skipped)
        });
      }
    } catch (e) {
      // FAIL-OPEN by design: never block the payroll AICJE from saving. The sweep will recover it.
      log.error({
        title: 'Rippling AICJE enrichment ERROR (fail-open; record still saved)',
        details: e
      });
    }
  }

  return { beforeSubmit: beforeSubmit };
});
