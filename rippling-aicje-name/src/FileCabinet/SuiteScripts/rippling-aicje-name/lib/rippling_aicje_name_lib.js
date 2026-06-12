/**
 * @NApiVersion 2.1
 * @NModuleScope SameAccount
 *
 * rippling_aicje_name_lib.js — shared logic for the Rippling AICJE "Name" (entity) enrichment.
 *
 * Background: on a Rippling-created Advanced Intercompany Journal Entry, each intercompany line
 * carries a populated `duetofromsubsidiary` (the counterparty) but a BLANK `entity` (the Rippling
 * SOAP integration does not set it). For each such line, Name (entity) = the counterparty
 * subsidiary's representing entity.
 *
 * NOTE: this lib uses `representingcustomer`. In most accounts the representing customer and
 * representing vendor resolve to the same entity per subsidiary; if yours deliberately splits
 * them by AR/AP side, adapt buildSubsidiaryEntityMap() accordingly.
 *
 * Shared by the User Event (real-time, pre-approval) and the Map/Reduce backstop sweep.
 *
 * Governance: the subsidiary->entity map is fetched with ONE cached query; line processing is pure
 * in-memory (no DB calls in the loop).
 *
 * VERIFY IN SANDBOX (never guess schema): the line sublist field IDs below should be confirmed
 * against the NetSuite Records Browser for your account version before promoting to RELEASED.
 */
define(['N/query', 'N/cache'], function (query, cache) {

  var DEFAULT_MEMO_PREFIX = '[Rippling]';
  var SUBLIST = 'line';
  var FLD_ENTITY = 'entity';
  var FLD_MEMO = 'memo';
  var FLD_DUETOFROM = 'duetofromsubsidiary'; // VERIFY vs Records Browser

  /**
   * Build subsidiary(id) -> representing entity(id) map, live from the subsidiary table.
   * Cached 5 min (N/cache, 300s = documented TTL floor) so repeated calls (e.g. across Map/Reduce
   * keys) don't re-query.
   * Governance: a single SuiteQL query; never called inside a line loop.
   * @returns {Object<string, number>}
   */
  function buildSubsidiaryEntityMap() {
    var c = cache.getCache({ name: 'rippling_aicje_sub_entity_map', scope: cache.Scope.PRIVATE });
    var hit = c.get({ key: 'map', ttl: 300 });
    if (hit) { return JSON.parse(hit); }

    var map = {};
    var rows = query.runSuiteQL({
      query: "SELECT id, representingcustomer FROM subsidiary " +
             "WHERE isinactive = 'F' AND representingcustomer IS NOT NULL"
    }).asMappedResults();
    for (var i = 0; i < rows.length; i++) {
      map[String(rows[i].id)] = rows[i].representingcustomer;
    }
    c.put({ key: 'map', value: JSON.stringify(map), ttl: 300 });
    return map;
  }

  /**
   * True if at least one line memo starts with the Rippling prefix (hardening lock so the scripts
   * never touch a non-Rippling web-services AICJE).
   * @param {Record} rec
   * @param {string} [prefix]
   * @returns {boolean}
   */
  function hasRipplingMemo(rec, prefix) {
    prefix = prefix || DEFAULT_MEMO_PREFIX;
    var n = rec.getLineCount({ sublistId: SUBLIST });
    for (var i = 0; i < n; i++) {
      var m = rec.getSublistValue({ sublistId: SUBLIST, fieldId: FLD_MEMO, line: i });
      if (m && String(m).indexOf(prefix) === 0) { return true; }
    }
    return false;
  }

  /**
   * Enrich intercompany lines in place. For each line where duetofromsubsidiary is set and entity
   * is empty, set entity = map[counterparty]. Idempotent (skips already-set lines). Never guesses:
   * a counterparty with no representing entity is recorded in `skipped`, not written.
   * @param {Record} rec  new/loaded record (modified in place)
   * @param {Object} subEntityMap
   * @returns {{changed:number, skipped:Array<{line:number,dueToFrom:string}>}}
   */
  function enrichLines(rec, subEntityMap) {
    var out = { changed: 0, skipped: [] };
    var n = rec.getLineCount({ sublistId: SUBLIST });
    for (var i = 0; i < n; i++) {
      var due = rec.getSublistValue({ sublistId: SUBLIST, fieldId: FLD_DUETOFROM, line: i });
      if (!due) { continue; }                                                   // not an IC line
      if (rec.getSublistValue({ sublistId: SUBLIST, fieldId: FLD_ENTITY, line: i })) { continue; } // already set
      var rep = subEntityMap[String(due)];
      if (!rep) { out.skipped.push({ line: i, dueToFrom: String(due) }); continue; }
      rec.setSublistValue({ sublistId: SUBLIST, fieldId: FLD_ENTITY, line: i, value: rep });
      out.changed++;
    }
    return out;
  }

  return {
    DEFAULT_MEMO_PREFIX: DEFAULT_MEMO_PREFIX,
    buildSubsidiaryEntityMap: buildSubsidiaryEntityMap,
    hasRipplingMemo: hasRipplingMemo,
    enrichLines: enrichLines
  };
});
