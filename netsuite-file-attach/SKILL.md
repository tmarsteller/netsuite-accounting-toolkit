---
name: netsuite-file-attach
description: Upload a local file to the NetSuite File Cabinet and optionally attach it to a record (journal entry, invoice, vendor bill, or any record type) via the File Attach RESTlet. Use whenever the user says "attach file to NetSuite record", "attach this file to the JE", "upload a file to NetSuite", "add this workpaper to the journal entry", "put this file in the File Cabinet", "attach support to invoice", or any request to programmatically add a file to a NetSuite record. NetSuite's REST Record API cannot do this — file upload requires this RESTlet.
---

# NetSuite File Attach

Upload a local file to the NetSuite File Cabinet and optionally attach it to a
record, using `attach_file.py` in this skill's directory.

## Prerequisites (one-time, by the account admin)

1. The File Attach RESTlet is deployed in the target NetSuite account
   (script `customscript_file_attach`, deployment `customdeploy_file_attach`).
   See README.md in this directory for both deployment paths.
2. TBA credentials exist in the environment or in a `.env` file next to
   `attach_file.py`: `NS_ACCOUNT_ID`, `NS_CONSUMER_KEY`, `NS_CONSUMER_SECRET`,
   `NS_TOKEN_ID`, `NS_TOKEN_SECRET` (template: `.env.example`).
3. Python dependencies installed: `pip install -r requirements.txt`
   (requests, requests-oauthlib).

If credentials are missing, stop and tell the user which variables are unset —
never guess or fabricate credentials.

## How to run

```bash
python attach_file.py --file "<local path>" \
    --record-type <recordtype> --record-id <internal id> \
    --folder-id <File Cabinet folder internal id> \
    --description "<short description>"
```

- `--folder-id` is required unless `NS_DEFAULT_FOLDER_ID` is set. If neither is
  available, ask the user which File Cabinet folder to use (they can find a
  folder's internal id under Documents > Files > File Cabinet).
- `--record-type` and `--record-id` are optional as a pair — omit both to
  upload without attaching. Use SuiteScript/REST record type ids:
  `journalentry`, `invoice`, `vendorbill`, `customrecord_*`, etc.
- Success output looks like: `OK — fileId=12345 attached=True`. Report the
  file id back to the user.

## Constraints and failure handling

- **Size:** files must be under 9 MB (base64 inflation vs. the ~10 MB RESTlet
  payload cap). The script enforces this; if a file is too big, tell the user
  instead of trying to work around it.
- **Extensions:** xlsx, xls, csv, pdf, txt, json, png, jpg/jpeg, zip, docx,
  doc. Anything else returns `Unsupported file extension` — extending the map
  requires editing and redeploying the RESTlet.
- **401 errors:** bad credentials, wrong realm, or the role lacks "Log in
  using Access Tokens". Point the user to the Troubleshooting table in
  README.md; do not retry repeatedly.
- **403 errors:** the deployment audience doesn't include the token's role.
- **Attach fails after upload:** the file is still in the File Cabinet (the
  two steps are not transactional). Report the fileId and the attach error
  rather than re-uploading.
- Never print or log the values of the `NS_*` secret variables.
