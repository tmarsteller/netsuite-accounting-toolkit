# netsuite-file-attach

Programmatic file upload + record attachment for NetSuite — a SuiteScript 2.1
RESTlet plus a standalone Python caller.

## The problem

NetSuite's REST Record API has **no File Cabinet support**. `GET
/services/rest/record/v1/metadata-catalog/file` returns 404 — there is no
`file` record in the REST catalog at all. If you need to upload a file and
attach it to a record (a journal entry, invoice, vendor bill, ...) from code,
your options are SOAP (SuiteTalk), the UI, or a RESTlet. This repo is the
RESTlet, with a ready-to-use client.

## What's in the repo

| Path | What it is |
|---|---|
| `src/FileAttachRestlet.js` | SuiteScript 2.1 RESTlet — creates a file in the File Cabinet via `N/file` and optionally attaches it via `N/record.attach` |
| `attach_file.py` | Standalone Python caller — signs requests with OAuth 1.0 TBA (HMAC-SHA256) |
| `requirements.txt` | Python dependencies (`requests`, `requests-oauthlib`) |
| `setup.bat` / `setup.ps1` | Windows one-click installer — checks/installs Python, installs dependencies, fills in `.env`, optionally installs the Claude Code skill |
| `setup.sh` | The same installer for macOS / Linux (`bash setup.sh`) |
| `.env.example` | Template for the five required credential env vars |
| `sdf-project/` | SuiteCloud (SDF) project that deploys the RESTlet — ready after `suitecloud account:setup` |
| `SKILL.md` | Claude Code skill definition — drop this folder into `~/.claude/skills/` and Claude can drive uploads end-to-end |

The copy of the RESTlet at `sdf-project/FileCabinet/SuiteScripts/` is identical
to `src/` — SDF requires the script inside the project's `FileCabinet` tree. If
you edit one, mirror the change in the other.

## Quick start

```bash
# 1. Deploy the RESTlet (see Deployment below)
cd sdf-project
suitecloud account:setup        # link your account (creates project.json)
suitecloud project:deploy

# 2. Configure credentials
cd ..
cp .env.example .env            # then fill in your TBA credentials

# 3. Upload + attach
pip install -r requirements.txt
python attach_file.py --file "C:/path/to/workpaper.xlsx" \
    --record-type journalentry --record-id 4242 \
    --folder-id 1234 --description "JE support workpaper"
```

Not comfortable with a terminal? See
[Setup for non-technical users](#setup-for-non-technical-users).

## Setup for non-technical users

You don't need to be a developer to use this. There are three parts: things
your NetSuite administrator does once, things you set up on your computer
once, and then day-to-day use (easiest through Claude Code).

### Part 1 — ask your NetSuite administrator (one-time)

Send your admin a link to this repo and ask for three things:

1. **Deploy the RESTlet** in your NetSuite account — the
   [Deployment](#deployment) section has step-by-step instructions for them
   (Path B needs no developer tools at all).
2. **Create credentials for you** — the
   [Authentication setup](#authentication-setup-tba) section walks them
   through it. You need five values back:
   account ID, consumer key, consumer secret, token ID, token secret.
   These are passwords — ask them to share via a password manager or other
   secure channel, **never plain email or chat**.
3. **The folder ID** — the internal ID of the File Cabinet folder where your
   uploads should land (they can see it under Documents > Files > File
   Cabinet).

### Part 2 — set up your computer (one-time, ~5 minutes)

A setup script does everything for you — no terminal knowledge needed.

1. **Download this repo:** click the green **Code** button at the top of the
   GitHub page → **Download ZIP** → extract it somewhere permanent, e.g. your
   Documents folder. (No git required.)
2. **Run the setup script:**
   - **Windows:** double-click **`setup.bat`**. If SmartScreen warns about an
     unrecognized app, click *More info* → *Run anyway* (both script files
     are short plain text — open them in Notepad if you want to see exactly
     what they do).
   - **macOS / Linux:** open Terminal, type `bash ` (with a trailing space),
     drag **`setup.sh`** onto the window, press Enter.
3. **Follow the prompts.** The script:
   - checks that Python 3 is installed (on Windows it offers to install it
     automatically; otherwise it opens the official download page),
   - installs the two Python packages the tool needs,
   - asks for the five credential values from Part 1 and saves them to a
     private `.env` file on your machine — they are never sent anywhere,
   - asks for your default folder ID so you never have to type it again,
   - offers to install the Claude Code skill (Part 3) for you.

   Safe to re-run any time — values you already entered are kept when you
   press Enter.
4. **Test it** with any small PDF or spreadsheet (the script prints this
   exact command when it finishes):

   ```
   python attach_file.py --file "test.pdf"
   ```

   You should see `OK — fileId=12345 attached=False`, and the file appears in
   the File Cabinet. If you get an error instead, the
   [Troubleshooting](#troubleshooting) table covers the common ones — `401`
   almost always means a typo in `.env` (re-run the setup script and re-paste
   the value).

### Part 3 — day-to-day use

You can keep running the command from step 6 (add
`--record-type journalentry --record-id <id>` to attach to a record), but the
easiest path for non-technical users is Claude Code: install it from
[claude.com/claude-code](https://claude.com/claude-code), follow
[Using with Claude Code](#using-with-claude-code) below, and from then on you
just ask in plain English — *"attach this month's workpaper to journal entry
4242"* — and Claude runs the script for you.

## Deployment

### Path A — SuiteCloud SDF CLI (recommended)

Prerequisites:

- Node.js 18+ and the CLI: `npm install -g @oracle/suitecloud-cli`
- **Java (JDK 17+) on PATH.** The CLI spawns a jar under the hood; without
  Java you get `spawn java ENOENT`.
- SuiteCloud Development Framework enabled in your account
  (Setup > Company > Enable Features > SuiteCloud > SuiteCloud Development Framework).

Deploy:

```bash
cd sdf-project
suitecloud account:setup     # browser-based auth; writes project.json (gitignored)
suitecloud project:validate  # optional sanity check
suitecloud project:deploy
```

This creates script `customscript_file_attach` with deployment
`customdeploy_file_attach` (Released, log level Audit).

Notes baked into this project so you don't rediscover them:

- `manifest.xml` and `deploy.xml` live at the **project root**, not in `src/`.
  The CLI errors out if they are anywhere else.
- The manifest declares `<feature required="true">SERVERSIDESCRIPTING</feature>`.
  RESTlet projects must declare it or validation fails.

### Path B — manual UI deployment

1. **Upload the script file:** Documents > Files > SuiteScripts > Add File →
   upload `src/FileAttachRestlet.js`.
2. **Create the script record:** Customization > Scripting > Scripts > New →
   pick the uploaded file. NetSuite detects the RESTlet type from the
   `@NScriptType` annotation. Set the ID to `_file_attach` (NetSuite prefixes
   it to `customscript_file_attach`).
3. **Deploy it:** on the script record, Deployments tab → New Deployment.
   Set ID `_file_attach` (becomes `customdeploy_file_attach`), Status
   **Released**, Log Level **Audit**, and choose the Audience (see Security).
4. Save. The deployment record shows the external RESTlet URL.

## Authentication setup (TBA)

The client signs every request with OAuth 1.0 Token-Based Authentication.
One-time setup in NetSuite:

1. **Enable features:** Setup > Company > Enable Features > SuiteCloud →
   check *Token-Based Authentication* (under Manage Authentication) and
   *Server SuiteScript*.
2. **Integration record:** Setup > Integration > Manage Integrations > New.
   Check *Token-Based Authentication*; uncheck the OAuth 2.0 and user
   credentials options. Save — the **consumer key/secret** are shown once.
3. **Role:** create (or pick) a role with the permissions listed under
   Security below, and assign it to the user who will own the token. The role
   needs *Log in using Access Tokens* (Setup tab).
4. **Access token:** Setup > Users/Roles > Access Tokens > New. Pick the
   integration, user, and role. Save — the **token id/secret** are shown once.
5. Put all five values in `.env` (copy `.env.example`).

Auth implementation details (already handled by `attach_file.py`, documented
for anyone porting the client):

- Signature method must be **HMAC-SHA256** — NetSuite rejects HMAC-SHA1.
- The OAuth `realm` is the account id **uppercased with `-` → `_`**
  (account `1234567-sb1` → realm `1234567_SB1`).
- The RESTlet domain is the account id **lowercased with `_` → `-`**:
  `https://1234567-sb1.restlets.api.netsuite.com`.
- RESTlet URLs accept **string script ids**
  (`script=customscript_file_attach&deploy=customdeploy_file_attach`) —
  you do not need the numeric internal ids.

## Usage

CLI:

```bash
# Upload and attach to a journal entry
python attach_file.py --file "C:/path/to/workpaper.xlsx" \
    --record-type journalentry --record-id 4242 \
    --folder-id 1234 --description "JE support workpaper"

# Upload only (no attachment)
python attach_file.py --file report.pdf --folder-id 1234
```

As a library:

```python
from pathlib import Path
from attach_file import attach

result = attach(Path("report.pdf"), folder_id=1234,
                record_type="invoice", record_id=4242)
print(result)  # {"success": True, "fileId": 12345, "attached": True}
```

Parameters:

- `--folder-id` is **required** (or set `NS_DEFAULT_FOLDER_ID`). There is no
  built-in default folder — find a folder's internal id under Documents >
  Files > File Cabinet.
- `--record-type` takes the REST/SuiteScript record type id: `journalentry`,
  `invoice`, `vendorbill`, `customrecord_*`, etc.
- Supported extensions: xlsx, xls, csv, pdf, txt, json, png, jpg/jpeg, zip,
  docx, doc. Extend `TYPE_BY_EXT` in the RESTlet for more.

## Security

- The RESTlet is `@NModuleScope SameAccount`, POST-only, and every request
  must carry a valid TBA signature — it is never anonymous, even with
  audience "All Roles".
- It writes files and creates attachments; it cannot read or return file
  contents.
- **Required role permissions** for the token's role:
  - *Documents and Files — Create* (Lists tab) to create File Cabinet files
  - Edit-level access to each record type you attach to (e.g. *Make Journal
    Entry* for journal entries)
  - *Log in using Access Tokens* (Setup tab)
- **Audience:** the shipped deployment uses "All Roles" for easy first
  deployment. For production, edit the deployment record (Audience tab) and
  restrict it to the dedicated integration role — then only tokens minted
  for that role can call it. In `sdf-project/Objects/customscript_file_attach.xml`
  that means replacing `<allroles>T</allroles>` with an explicit
  `<audslnsrole>` list referencing your role.

## Size limits

Keep request payloads under ~10 MB — base64 inflates file bytes by ~33%, so
the client caps source files at **9 MB** (`MAX_BYTES` in `attach_file.py`).
For larger files use SOAP, SFTP via `N/sftp`, or chunked custom handling.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `spawn java ENOENT` from `suitecloud` | Java isn't on PATH. Install a JDK and ensure `java -version` works in the same shell. |
| CLI: manifest/deploy file not found | `manifest.xml` / `deploy.xml` must be at the SDF project **root**, not inside `src/`. |
| Validation fails on the RESTlet object | Manifest is missing `<feature required="true">SERVERSIDESCRIPTING</feature>`. |
| `401 Unauthorized` / `INVALID_LOGIN_ATTEMPT` | Wrong realm (must be account id uppercased, `-` → `_`), wrong signature method (must be HMAC-SHA256), clock skew, or the role lacks *Log in using Access Tokens*. |
| `403 Forbidden` | Deployment audience doesn't include the token's role, or the deployment isn't Released. |
| `Unsupported file extension` | Add the extension to `TYPE_BY_EXT` in the RESTlet and redeploy. |
| Corrupted binary files in the File Cabinet | Binary types must be sent as **base64** in `contents` — never raw bytes or text. The client always base64-encodes. |
| Request rejected for size | Payload exceeded the ~10 MB RESTlet limit. Stay under the 9 MB source-file cap. |
| File uploads but attach fails | The role can create files but lacks edit permission on the target record type, or `recordType`/`recordId` is wrong. The file remains in the File Cabinet (the two steps are not transactional). |

## Using with Claude Code

This repo doubles as a [Claude Code](https://claude.com/claude-code) skill —
`SKILL.md` tells Claude when to trigger and how to run the script.

**Install:** the setup script (`setup.bat` / `setup.sh`) offers to do this
for you. Manually, copy (or symlink) this whole folder into your skills
directory:

- Windows: `%USERPROFILE%\.claude\skills\netsuite-file-attach\`
- macOS/Linux: `~/.claude/skills/netsuite-file-attach/`

For a single project instead, use `.claude/skills/netsuite-file-attach/`
inside that project. Keep your filled-in `.env` next to `attach_file.py` in
the skill folder — the script finds it automatically.

**Invoke:** start a new Claude Code session and just ask — no command to
memorize. The skill triggers on requests like:

- "attach this workbook to journal entry 4242"
- "upload report.pdf to the NetSuite File Cabinet"
- "add this support file to invoice 1234"

You can also invoke it explicitly with `/netsuite-file-attach`. Claude runs
`attach_file.py` for you, asks for a folder ID if one isn't configured,
enforces the size limit, and reports back the file ID. It is instructed to
stop and tell you what's missing (rather than guess) if credentials aren't
set up.

## Before you publish

If you forked or adapted this repo, **review it for leaks before making it
public**: account ids, script ids, folder ids, internal record ids, file
paths, and anything in `.env` or `sdf-project/project.json` (both gitignored
here by default). Run your own grep for your account id and company name.

## License

MIT — see [LICENSE](LICENSE).
