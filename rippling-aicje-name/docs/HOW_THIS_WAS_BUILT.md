# How this was built — a finance person's guide

*A plain-English walkthrough of how an accountant (not a developer) shipped a production
NetSuite automation, what had to be installed, and what we learned along the way. Written for
controllers, accounting managers, and finance-systems folks considering something similar.*

---

## 1. The problem

Rippling's NetSuite integration books multi-subsidiary payroll as **Advanced Intercompany
Journal Entries** (AICJEs) — e.g., the parent company pays a foreign subsidiary's payroll, which
creates intercompany receivable/payable lines between the two entities.

The integration leaves the **line-level Name (entity) field blank** on those entries. Rippling
support confirmed the field isn't supported by their sync. If your intercompany elimination or
reconciliation process needs the counterparty's "representing entity" on those lines (most
OneWorld setups do), someone has to open every payroll journal and fill it in by hand. Forever.

## 2. What we built

Two small scripts that live **inside NetSuite** (no external servers, no ongoing cost):

- **A User Event script** — fires the instant Rippling creates the journal, and fills in the
  Name on each intercompany line *before the entry ever reaches a human approver*. Think of it
  as a rule that runs at the moment of record creation.
- **A daily "sweep" script** — a scheduled backstop that finds any Rippling journal still
  missing the Name (say, if the first script was ever down) and fixes it.

**The rule both scripts apply:** for each journal line that has a "due to/from subsidiary"
(NetSuite's marker for the intercompany counterparty) but no Name, set the Name to that
counterparty subsidiary's **representing entity** — looked up *live* from NetSuite's own
subsidiary table at run time.

### Design decisions that mattered (and why an accountant should care)

| Decision | Why |
|---|---|
| **No hardcoded account numbers or entity IDs.** The rule keys off NetSuite's structural intercompany markers, and the subsidiary→entity map is read live each run. | Our intercompany accounts had *just been renumbered*, and real entries used three different account numbers in one month. Anything hardcoded would have silently broken. |
| **Detect "this came from Rippling" by the creation channel, not the creator.** The scripts check that the entry arrived via web services (the channel integrations use) plus the `[Rippling]` memo prefix on the lines. | The "Created By" user looked like an obvious filter — until the data showed it had changed three times over two years (it's just whoever owns the integration's login token). Channel + memo is durable; people aren't. |
| **Fail-open.** If the script ever errors, the payroll entry still saves — un-fixed — and the daily sweep catches it later. | An automation that *blocks payroll posting* when it hiccups is far worse than the blank field it fixes. |
| **Classification-only.** The scripts touch one non-posting field. Debits, credits, amounts, FX, accounts, periods — untouchable by design, and verified untouched in testing. | Auditability. The change can't move the GL, so the risk profile is genuinely low. |
| **Segregation of duties preserved.** The script acts as a *preparer* (it fills a field pre-approval). A human still reviews and approves every journal. | The automation never approves anything. Preparer ≠ approver, same as ever. |
| **Independent code review before deploy.** The code was reviewed against Oracle's documentation *and* live system data by a reviewer who didn't write it. | The review caught a real bug: the daily sweep had no schedule attached — it would have deployed and then silently never run. |

## 3. The process (worth stealing)

We ran this like an accounting workpaper, not a hack session — six phases, each ending with an
explicit sign-off by the accountant who owns the judgment:

1. **Scoping** — what exactly is broken, for which entries, since when, and what's out of scope.
2. **Requirements** — source-of-truth data, the exact rule, and the tie-outs (e.g., "GL impact
   before vs. after must be identical, tolerance zero").
3. **Methodology** — 2–3 candidate approaches with trade-offs (real-time script vs. scheduled
   poller vs. external tool), pick one, document why.
4. **Execution plan** — ordered tasks, who does what, rollback plan.
5. **Build** — with every material choice (fail-open vs. fail-closed, detection key, etc.)
   surfaced as a decision for the owner, and an independent code review at the end.
6. **Review & sign-off** — deploy, verify in the UI, notify the team, schedule monitoring.

Every decision was logged with its rationale as it happened. When an auditor (or your successor)
asks "why does this script exist and why does it do X," the answer is written down.

One honest deviation: we deployed to production without a sandbox pass (a deliberate, documented
risk call — the failure mode is benign because of fail-open + the sweep). The "right" path is
sandbox first; the UAT guide in this repo is the checklist for it.

## 4. The toolchain — what actually had to be installed

This was the surprise for a non-developer. Getting code *into* NetSuite isn't drag-and-drop; the
clean way is Oracle's **SuiteCloud Development Framework (SDF)** — a command-line tool that
validates your project against your account and deploys it. Here's the full stack, in install
order:

| Tool | What it is | Why it's needed | Install |
|---|---|---|---|
| **Node.js** | A JavaScript runtime | The SuiteCloud CLI runs on it | `winget install OpenJS.NodeJS` (or nodejs.org) |
| **Oracle JDK 17 or 21** | Java | The CLI shells out to Java for validation/deploy. It refuses to run without it — this was our first error message. | `winget install Oracle.JDK.21` |
| **SuiteCloud CLI** | Oracle's official deploy tool (`suitecloud`) | Validates and deploys the project to your NetSuite account | `npm install -g @oracle/suitecloud-cli` |

Then, one-time, from the project folder:

```bash
suitecloud account:setup     # browser-based OAuth login to your NetSuite account
                             # you give the saved login a nickname ("auth ID")
suitecloud project:validate  # server-side check of every file and object
suitecloud project:deploy    # pushes scripts + deployment records into NetSuite
```

Total elapsed time from "never heard of SDF" to "deployed in production": about an hour,
including the errors below. A NetSuite **Administrator** role is required.

**The alternative** (no CLI at all): upload the `.js` files through the File Cabinet and create
the Script/Deployment records by hand in the UI. It works — the deployment guide documents it —
but the CLI path is repeatable, reviewable, and version-controlled.

## 5. Gotchas we hit (so you don't)

1. **"Java is not installed on this machine."** The SuiteCloud CLI needs Oracle JDK 17/21 even
   though it's a Node tool. Install the JDK, open a *new* terminal (the old one won't see it).
2. **Scheduled scripts have different status values than other scripts.** In the deployment
   config, a User Event goes live as `RELEASED`, but a scheduled Map/Reduce must be `SCHEDULED` —
   using `RELEASED` fails with "Invalid status reference key." (Found this the hard way, mid-deploy.)
3. **A scheduled script with no recurrence deploys fine and never runs.** Nothing warns you.
   After deploying, open the deployment record and confirm **"Next Run" shows a time**. Our
   code review caught this before it bit; it's now a mandatory step in the deploy guide.
4. **The deployment record needed a `title` field** that wasn't obvious from examples —
   server-side `project:validate` told us exactly what was missing. Lesson: always run
   `validate` before `deploy`; its error messages are genuinely helpful.
5. **Integration tokens are owned by people.** NetSuite integrations (like Rippling's)
   authenticate with a token owned by a specific user. When that person leaves and their account
   is deactivated, the token can die — and the integration stops syncing. Our own history showed
   the integration's "Created By" changing with each owner. **Put integration tokens on a
   service account**, not a person.
6. **Verify your assumptions against real records before writing code.** Almost every "obvious"
   filter we considered (creator, account numbers, a memo alone) was disproven by querying actual
   historical entries. The 20 minutes of read-only queries up front shaped the whole design.

## 6. What it costs to run

Nothing incremental. SuiteScript executes on NetSuite's servers under your existing license
(within governance limits this tool doesn't come near). There are no API calls, no external
runtime, no per-run fees — unlike an external bot or AI agent polling on a schedule, which would
cost money forever. The only real costs were one-time: the build, the review, and the deploy.

## 7. Where everything lives

- **This repo** — the scripts, the SDF project, a UAT checklist, and a deployment guide
  (including the no-CLI path).
- In your own company: keep the code in your team's version-controlled repo, deploy via SDF, and
  make sure at least two people know it exists — the script's owner *will* eventually change jobs.

---

*Built by an accountant with an AI pair-programmer doing the heavy lifting, an independent
automated code review before deploy, and a human sign-off at every gate. The combination is the
point: the accountant owned every judgment; the tools did the typing.*
