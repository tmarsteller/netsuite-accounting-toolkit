/**
 * @NApiVersion 2.1
 * @NScriptType MapReduceScript
 * @NModuleScope SameAccount
 *
 * rippling_aicje_name_sweep_mr.js — Rippling AICJE "Name" enrichment, backstop sweep.
 *
 * Defense-in-depth for the User Event. Finds Rippling AICJEs (source=webServices + [Rippling] memo)
 * that still have an intercompany line with no entity, in an EDITABLE period, and enriches them via
 * the shared library. Runs in SCHEDULED/MAPREDUCE context, so the UE's web-services gate does NOT
 * re-fire on these saves. Schedule: daily (set on the deployment).
 *
 * See docs/DEPLOYMENT_GUIDE.md and docs/UAT_GUIDE.md.
 */
define(['N/query', 'N/record', 'N/log', '/SuiteScripts/rippling-aicje-name/lib/rippling_aicje_name_lib'],
function (query, record, log, lib) {

  /**
   * Candidate Rippling AICJE ids: web-services origin + [Rippling] memo + >=1 IC line missing entity,
   * in an editable period. "Editable" = not all-locked AND (open OR allows non-G/L changes). The
   * run-as role must hold "Allow Non-G/L Changes" for the closed-but-unlocked case (see
   * DEPLOYMENT_GUIDE). Bounded result set -> returned as an array; one map() per id.
   * @returns {number[]}
   */
  function getInputData() {
    var sql =
      "SELECT t.id AS id FROM transaction t " +
      "JOIN accountingperiod ap ON ap.id = t.postingperiod " +
      "WHERE t.recordtype = 'advintercompanyjournalentry' AND t.source = 'webServices' " +
      "  AND ap.alllocked = 'F' AND (ap.closed = 'F' OR ap.allownonglchanges = 'T') " +
      "  AND EXISTS (SELECT 1 FROM transactionline ic WHERE ic.transaction = t.id " +
      "              AND ic.duetofromsubsidiary IS NOT NULL AND ic.entity IS NULL) " +
      "  AND EXISTS (SELECT 1 FROM transactionline rm WHERE rm.transaction = t.id " +
      "              AND rm.memo LIKE '[Rippling]%')";
    var ids = [];
    var rows = query.runSuiteQL({ query: sql }).asMappedResults();
    for (var i = 0; i < rows.length; i++) { ids.push(rows[i].id); }
    return ids;
  }

  /**
   * Enrich one AICJE. The sub->entity map is N/cache-backed in the library, so repeated calls across
   * map() keys hit cache rather than re-querying (no DB call in a loop).
   */
  function map(context) {
    var id = JSON.parse(context.value);
    try {
      var rec = record.load({ type: record.Type.ADV_INTER_COMPANY_JOURNAL_ENTRY, id: id, isDynamic: false });
      var res = lib.enrichLines(rec, lib.buildSubsidiaryEntityMap());
      if (res.changed > 0) {
        rec.save({ enableSourcing: false, ignoreMandatoryFields: true });
        log.audit({ title: 'Sweep enriched AICJE', details: 'id=' + id + ' lines=' + res.changed });
      }
      if (res.skipped.length > 0) {
        log.error({ title: 'Sweep — UNMAPPED counterparty (left blank)', details: 'id=' + id + ' ' + JSON.stringify(res.skipped) });
      }
    } catch (e) {
      log.error({ title: 'Sweep map error', details: 'id=' + id + ' | ' + e });
      throw e; // surface per-record errors in summarize(); never swallow
    }
  }

  function summarize(summary) {
    summary.mapSummary.errors.iterator().each(function (key, err) {
      log.error({ title: 'Sweep error (key ' + key + ')', details: err });
      return true;
    });
    log.audit({ title: 'Rippling AICJE sweep complete', details: 'keys processed: ' + summary.mapSummary.keys });
  }

  return { getInputData: getInputData, map: map, summarize: summarize };
});
