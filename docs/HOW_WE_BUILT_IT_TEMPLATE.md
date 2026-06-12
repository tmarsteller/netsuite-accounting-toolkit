# How we built [AUTOMATION NAME] — a finance person's guide

*A reusable template for documenting a finance/accounting automation after you ship it. Replace
the bracketed prompts, delete the italic guidance, and keep the section structure — the structure
is the value. Written so a controller, auditor, or your successor can understand the what, why,
and how without reading code. Aim for 1–3 pages.*

---

## 1. The problem

*State the business problem in plain English. What was broken or manual? Who felt the pain, how
often, and what did it cost (hours, errors, audit risk)? One or two paragraphs.*

- **What was happening:** [e.g., "System X creates records with field Y blank…"]
- **Why it mattered:** [downstream process that breaks / manual effort / control gap]
- **Confirmed root cause:** [e.g., vendor confirmed the integration doesn't support the field —
  cite the ticket or email so nobody re-litigates this later]

## 2. What we built

*Describe the solution in one short paragraph per component — what it is and when it runs, not
how the code works.*

| Component | Type | What it does |
|---|---|---|
| [name] | [script / scheduled job / workflow] | [one sentence] |
| [name] | [backstop / monitor] | [one sentence] |

**The rule the automation applies:** [state the business rule precisely, in one sentence — this
is the sentence an auditor will quote]

### Design decisions that mattered (and why)

*This is the most valuable section. For each consequential choice, say what you decided and the
reason — especially decisions where the obvious option was wrong. Capture rejected options.*

| Decision | Why |
|---|---|
| [e.g., No hardcoded IDs / config read live at run time] | [what real-world change would have silently broken a hardcoded version] |
| [e.g., How the automation identifies its target records] | [why the durable signal was chosen over the obvious-but-fragile one] |
| [e.g., Fail-open vs. fail-closed on error] | [which business process must never be blocked, and what backstop recovers misses] |
| [e.g., Scope of what the automation may touch] | [what it can never modify — your auditability story] |
| [e.g., Segregation of duties] | [who still reviews/approves; the automation's role (preparer ≠ approver)] |
| [e.g., Independent review before deploy] | [who/what reviewed it, and what the review caught] |

## 3. The process

*Document the phases you actually ran and where the owner signed off. If you skipped a step
(e.g., sandbox), say so honestly and record why the risk was acceptable.*

1. **Scoping** — [what was in/out of scope; period; materiality]
2. **Requirements** — [source-of-truth data; the exact rule; tie-outs with tolerances]
3. **Methodology** — [options considered; what was chosen; why]
4. **Execution plan** — [ordered tasks; owners; rollback plan]
5. **Build** — [who built it; what decisions were escalated; review performed]
6. **Review & sign-off** — [deploy; verification performed; who was notified; monitoring set up]

**Deviations / accepted risks:** [e.g., "Deployed to production without sandbox UAT because the
failure mode is benign (fail-open + daily backstop); documented and accepted by OWNER on DATE."]

## 4. The toolchain — what actually had to be installed

*List every tool a successor needs, why it's needed, and the install command. This is the section
nobody writes down and everybody needs.*

| Tool | What it is | Why it's needed | Install |
|---|---|---|---|
| [tool] | [one-phrase description] | [why] | [command or link] |

**One-time setup steps:**

```bash
[command]   # [what it does, in plain English]
[command]   # [what it does]
```

[Time it actually took, prerequisites (roles/permissions), and the no-CLI/manual alternative if
one exists.]

## 5. Gotchas we hit (so you don't)

*Number them. Each one: the error or surprise, what it meant, and the fix. These save the next
person hours.*

1. **[Error message or surprise]** — [what it actually meant; the fix]
2. **[Silent failure mode]** — [how you'd ever notice; the verification step that catches it]
3. **[Dependency on a person]** — [e.g., tokens/credentials owned by an individual; what breaks
   when they leave; the service-account fix]

## 6. What it costs to run

*Ongoing cost in money, compute, and people-time. If it's zero, say why (e.g., runs inside the
platform license). Compare against the alternative you rejected if the difference is material.*

## 7. Where everything lives

- **Code:** [repo / folder / branch policy]
- **Documentation:** [this doc, UAT guide, deployment guide, decision log / workpaper]
- **Monitoring:** [logs to check; alerts; scheduled verifications; who gets notified]
- **Owner:** [current owner + backup — at least two humans must know this exists]

---

*[Closing attribution — who built it, who reviewed it, who owned the judgments. E.g.: "Built by
NAME with TOOLING; independently reviewed before deploy; a human signed off at every gate."]*
