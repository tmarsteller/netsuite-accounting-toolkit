---
name: netsuite-developer
description: >
  Disciplined NetSuite development, querying, and administration with schema awareness and safety guardrails.
  Use this skill whenever the user mentions NetSuite, NS, SuiteScript, SuiteQL, SDF, NetSuite records,
  journal entries, JE, saved searches, REST Record API, custom records, custom fields, subsidiaries,
  posting periods, accounts, chart of accounts, GL, accounting periods, ERP, vendors, customers, items,
  transactions, or any NetSuite record types.
  Also trigger when the user references NS MCP tools (ns_runCustomSuiteQL, ns_getRecord, ns_createRecord,
  ns_updateRecord, ns_listAllReports, ns_runReport, ns_listSavedSearches, ns_runSavedSearch,
  ns_getRecordTypeMetadata, ns_getSuiteQLMetadata, ns_getSubsidiaries),
  or asks about ERP queries, accounting system integrations, or NetSuite configuration.
---

# NetSuite Developer Skill

## Purpose

This skill enforces disciplined, schema-aware, production-safe NetSuite development and usage.

It applies to:

- SuiteScript 2.1 development
- SuiteQL queries
- REST Record API usage
- NetSuite MCP connector operations (ns_runCustomSuiteQL, ns_getRecord, ns_createRecord, ns_updateRecord, etc.)
- Saved searches
- Integrations and CSV imports
- SuiteCloud Development Framework (SDF)
- Metadata-driven development via optional provider contract

This skill is adapted from the [netsuite-developer](https://github.com/joshOrigami/netsuite-developer) Codex skill by Joshua Meiri / Origami Precision, LLC (CC-BY-4.0).

---

# Accounting Safety Rules

Recommended defaults for any accounting team using this skill. Add your own
company-specific conventions (memo formats, task-number prefixes, default
subsidiaries, account mappings) in a companion file and reference it from here.

## Journal Entry Safety

- **NEVER create journal entries in approved or posted status.** All JEs must be created in Pending Approval state: `approved: false`, `approvalStatus: { id: "1" }`. No exceptions — a human reviews and approves in NetSuite.
- When using the NetSuite MCP connector (`ns_createRecord` for `journalentry`), always include these fields.
- **Always include a direct URL link in the response** after creating a JE. Format: `https://system.netsuite.com/app/accounting/transactions/journal.nl?id={recordId}` using the recordId returned from `ns_createRecord`.
- **Always reference JEs by their JE number (tranId), not the internal record ID.** After creating a JE, query `SELECT t.tranid FROM transaction t WHERE t.id = {recordId}` to get the JE number, and use that in all responses, file names, and supporting documents.

## NetSuite MCP Connector

You have access to the NetSuite MCP connector with these tools:

| Tool | Purpose |
|------|---------|
| `ns_runCustomSuiteQL` | Run SuiteQL queries (read-only analytics, reporting) |
| `ns_getRecord` | Fetch a single record by type and ID |
| `ns_createRecord` | Create a new record (use with caution) |
| `ns_updateRecord` | Update an existing record (use with caution) |
| `ns_getRecordTypeMetadata` | Get field/sublist metadata for a record type |
| `ns_getSubsidiaries` | List subsidiaries |
| `ns_getSuiteQLMetadata` | Get SuiteQL table/column metadata |
| `ns_listAllReports` | List available reports |
| `ns_runReport` | Run a financial or saved report |
| `ns_listSavedSearches` | List saved searches |
| `ns_runSavedSearch` | Execute a saved search |

### MCP Connector Best Practices

- **Use `ns_getRecordTypeMetadata` or `ns_getSuiteQLMetadata` before writing queries or creating records.** This is the equivalent of the metadata helper — use it to confirm field IDs, sublists, and column names rather than guessing.
- For read-only analysis, prefer `ns_runCustomSuiteQL` — it's fast and flexible.
- For record mutations (`ns_createRecord`, `ns_updateRecord`), confirm field names with metadata first and ask the user for confirmation before executing.
- When querying, respect all SuiteQL rules defined in this skill (no SELECT *, explicit WHERE, aliasing, NVL for JSON outputs, etc.).

---

# Core Operating Principles

1. Never assume schema.
2. Never swallow errors.
3. Never guess environment.
4. Never rely on undocumented behavior.
5. Never deploy without validation.

If metadata is available (via MCP connector or local files), use it.
If metadata is not available, ask before guessing.

---

# Governance & Performance Anti-Patterns

The following patterns are forbidden in NetSuite development. If a unique business case requires a deviation, flag it explicitly before generating code.

## 1. No Database Calls in Loops

Never place `record.load()`, `record.save()`, `record.submitFields()`, `search.run()`, or `query.run()` inside any loop structure. This creates quadratic governance consumption. Use collection-based processing or Map/Reduce instead.

If a small, fixed-limit loop is truly necessary, the code must include: `// @skip-gatekeeper: [Reasoning]`.

## 2. Prefer `submitFields` for Body Updates

If updating ONLY body fields (no sublists), use `N/record.submitFields` instead of a full `load` and `save` cycle. `submitFields` is ~10x faster and uses ~2 governance units vs 10+ for a full load.

## 3. No Unbounded Searches

Never use `search.run().each()` without an explicit exit strategy, `.getRange()`, or pagination. Unbounded searches pass in Sandbox with 10 records but crash in Production with 50,000.

## 4. SuiteQL Injection Prevention

Never use string concatenation to build SuiteQL queries with user-provided variables. Always use the `params` property in `query.runSuiteQL` to safely bind variables. When using `ns_runCustomSuiteQL` via MCP, parameterize where possible.

## 5. No Hardcoded Internal IDs

Never use numeric internal IDs (e.g., `id: 123`) for records, roles, or scripts in SuiteScript code. Internal IDs are environment-specific. Use Script Parameters or Script IDs (e.g., `custrecord_op_tier`).

Note: When using the MCP connector for one-off queries or record lookups, internal IDs from query results are acceptable — this rule applies to code that will be deployed across environments.

## 6. afterSubmit Safety Net

Every `afterSubmit` entry point must be wrapped in a root `try/catch` block. An unhandled error in `afterSubmit` can block the entire record from saving.

## 7. Frontend & Portal Security (Safe-Include Rule)

Any external JavaScript library loaded via CDN must include `integrity` and `crossorigin` attributes (Subresource Integrity) to prevent supply chain attacks.

---

# SuiteQL Rules

## When to Apply Full Discipline

A query is "non-trivial" if it:
- Joins tables
- Uses date filters
- Filters by subsidiary
- Uses createfrom lineage or systemnote
- Uses aggregation
- Is intended for reuse or reporting
- Impacts integration

## Required Output for Non-Trivial Queries

1. The SuiteQL query
2. A short QA test plan for the target environment

## Column Selection

- Never use `SELECT *`
- Always alias tables
- Prefer `BUILTIN.DF()` when only the display value is needed and it avoids an unnecessary join

## Null Handling

SuiteQL does not return null fields in JSON payloads. When output is consumed by JSON-based integrations or the MCP connector:

```sql
NVL(t.memo, 'n/a') AS memo,
NVL(t.createdfrom, 0) AS createdfrom
```

## Using the MCP Connector for SuiteQL

When using `ns_runCustomSuiteQL`:
- Start by using `ns_getSuiteQLMetadata` to confirm table and column names if you're unsure
- Apply all the same discipline: explicit columns, WHERE clause, aliasing, NVL for nulls
- For large result sets, use FETCH FIRST N ROWS ONLY or OFFSET/FETCH pagination
- Always explain the query to the user before running it against production data

---

# Metadata & Schema Discipline

## MCP-Based Metadata (Primary Method)

Use the NetSuite MCP connector tools for real-time metadata:

- `ns_getRecordTypeMetadata` — get fields, sublists, and field types for any record type
- `ns_getSuiteQLMetadata` — get table and column info for SuiteQL

This replaces the need for local metadata files in most cases.

## Local Metadata Provider (Optional)

If a `.netsuite-metadata/` folder exists in the project:

- Enumerate subfolders — each is an environment
- Do not assume SB, QA, PROD — accept any folder name
- Require explicit selection if multiple exist
- Use `tools/query_metadata.py` to query local metadata

The local metadata helper supports these commands:

```
python tools/query_metadata.py --env <ENV> list-records
python tools/query_metadata.py --env <ENV> get-record <record_key>
python tools/query_metadata.py --env <ENV> list-fields <record_key>
python tools/query_metadata.py --env <ENV> find-field <field_id>
python tools/query_metadata.py --env <ENV> suggest-suiteql <record_key> --fields <field1,field2>
```

## Schema-Dependent Logic Rule

Metadata must be consulted (via MCP or local helper) for ALL schema-dependent operations:

- SuiteQL generation
- SuiteScript record.load, record.create, record.submitFields
- record.setValue and getValue field usage
- Sublist access
- search.create column definitions
- REST field mappings
- Custom record and custom field usage

If metadata is available, do not assume a field exists, guess a sublist ID, invent a custom field ID, or infer a join path without confirmation.

If metadata is not available, explicitly ask the user before proceeding.

---

# Error Handling Discipline

Never swallow errors.

```javascript
// BAD - silent failure
try { ... } catch (e) { }

// GOOD - log and rethrow
try { ... } catch (e) {
   log.error({ title: 'Unexpected Error', details: e });
   throw e;
}
```

Rules:
- Always log errors
- Always preserve stack traces
- Scheduled and Map/Reduce scripts must log summary errors
- Integrations must surface errors upstream

---

# Logging Rules

- Use `log.audit` for business events
- Use `log.debug` only for temporary diagnostics
- Do not log sensitive data (SSNs, account numbers, passwords)
- In production, logging must not be excessive
- All unexpected errors must be reviewable

---

# Code Structure and Documentation

## Function Docstrings

Every function must include a JSDoc docstring covering:
- Purpose, inputs, outputs
- Governance considerations
- Side effects and assumptions

## Complex Logic Comments

Comments must explain WHY the logic exists, not restate the code.

---

# Script Deployment Discipline

When generating scripts, always specify:

1. Script Type
2. Execution Context
3. Deployment notes (status, audience, role)
4. Error notification guidance
5. Governance expectations

Deployment status discipline:
- **Testing**: Only script owner executes (SB/QA)
- **Released**: Available to permitted audience (PROD, after QA validation)
- Never promote directly to Released without documented QA validation

---

# Integration Discipline

For REST integrations:
- Validate required fields
- Handle 429 and 503 properly
- Respect rate limits
- Never expose raw NetSuite errors externally

CSV imports:
- Validate decimal separators, date format, encoding
- Confirm subsidiary context
- Validate multi-currency assumptions

---

# SDF Discipline

- Use SuiteScript 2.1
- Validate project before deploy
- Confirm `deploy.xml`
- Never assume local validation equals server validation
- Treat `deploy.xml` as source of truth

---

# Performance Guardrails

- Avoid N+1 search patterns
- Limit columns in queries
- Filter early
- Paginate large searches (`search.runPaged()`)
- Avoid loading entire datasets in memory
- Measure runtime for heavy operations
- Explicitly filter subsidiary when relevant

---

# Multi-Entity Safety

- Never assume single subsidiary
- Never assume base currency
- Never assume feature enablement
- Always check role context
- Always scope data intentionally

---

# Optional Feature Modules

This skill supports optional modules for specific NetSuite features. Read the relevant module from `references/modules/` when the feature is in scope:

| Feature | Module File | When to Read |
|---------|-------------|--------------|
| Multi-Book Accounting | `references/modules/multibook.md` | Any GL-impacting or posting-related work |
| Advanced Revenue Management | `references/modules/arm.md` | Revenue recognition, arrangements, plans |
| SuiteBilling | `references/modules/suitebilling.md` | Subscriptions, billing schedules, usage billing |
| SuiteTax | `references/modules/suitetax.md` | Tax calculation, tax details, tax overrides |
| Fiscal Calendars | `references/modules/fiscalcalendars.md` | Posting periods, fiscal year boundaries, 4-4-5 calendars |

If a `docs/modules/netsuite-features.json` file exists in the project, check it to determine which features are enabled per environment. If the feature is `true`, apply the module rules. If `false`, skip. If missing, treat as unknown and ask only if the current task touches that feature.

---

# Operational Documentation Requirements

For non-trivial development (scripts, integrations, SuiteQL reporting, SDF deployments), include:

1. **UAT Guide** — Environment, role, preconditions, step-by-step validation, edge cases, rollback
2. **Installation/Deployment Guide** — Script type, deployment ID, roles, permissions, features, error handling, rollback
3. **End User Guide** (if applicable) — What changed, who's affected, step-by-step usage

If the change is internal-only, explicitly state: "No end-user documentation required."

---

# Canonical References

When authoritative clarification is required, prefer official Oracle documentation:

- [SuiteScript Best Practices](https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/part_N3360914.html)
- [General Development Best Practices](https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/chapter_N3361037.html)
- [Optimizing SuiteScript Performance](https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_4460387617.html)
- [Logging Guidelines](https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_4430384449.html)
- [SuiteCloud CLI deploy/validate](https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_156044636320.html)
- [REST Record Service Guide](https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/chapter_1540810168.html)
- [SuiteQL Reference](https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_156257770590.html)

When in doubt, prefer these references over memory. Do not invent undocumented behavior.

---

# License & Attribution

Adapted from [netsuite-developer](https://github.com/joshOrigami/netsuite-developer) by Joshua Meiri, Origami Precision, LLC.
Original skill licensed under CC-BY-4.0. Python tooling under MIT.
