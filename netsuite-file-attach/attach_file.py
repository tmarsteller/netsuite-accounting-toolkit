"""Upload a local file to the NetSuite File Cabinet and attach it to a record.

NetSuite's REST Record API has no File Cabinet support (GET /metadata-catalog/file
returns 404), so programmatic upload + attach requires a RESTlet. This script
calls the companion FileAttachRestlet (src/FileAttachRestlet.js) using OAuth 1.0
Token-Based Authentication (TBA) with HMAC-SHA256 signatures.

Configuration is via environment variables only (see .env.example; a .env file
next to this script is loaded automatically for any variables not already set):

    NS_ACCOUNT_ID         NetSuite account id, e.g. 1234567 or 1234567-sb1
    NS_CONSUMER_KEY       Integration record consumer key
    NS_CONSUMER_SECRET    Integration record consumer secret
    NS_TOKEN_ID           Access token id
    NS_TOKEN_SECRET       Access token secret
    NS_DEFAULT_FOLDER_ID  Optional fallback when --folder-id is omitted
    NS_SCRIPT_ID          Optional; defaults to customscript_file_attach
    NS_DEPLOY_ID          Optional; defaults to customdeploy_file_attach

Usage:
    python attach_file.py --file "C:/path/to/workpaper.xlsx" \
        --record-type journalentry --record-id 4242 \
        --folder-id 1234 --description "JE support workpaper"

Omit --record-type/--record-id to upload to the File Cabinet without attaching.
"""
from __future__ import annotations

import argparse
import base64
import os
import sys
from pathlib import Path

import requests
from requests_oauthlib import OAuth1

# RESTlet request payloads are capped around 10 MB and base64 inflates the raw
# bytes by ~33%, so cap the source file at 9 MB to stay safely under the limit.
MAX_BYTES = 9 * 1024 * 1024

REQUIRED_ENV = (
    "NS_ACCOUNT_ID",
    "NS_CONSUMER_KEY",
    "NS_CONSUMER_SECRET",
    "NS_TOKEN_ID",
    "NS_TOKEN_SECRET",
)


def _load_dotenv() -> None:
    """Load KEY=VALUE pairs from a .env beside this script (no dependency).

    Only sets variables that are not already in the environment, so real env
    vars always win over .env contents.
    """
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value


def _require_env() -> None:
    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        sys.exit(
            "Missing required environment variables: "
            + ", ".join(missing)
            + "\nCopy .env.example to .env and fill in your TBA credentials."
        )


def ns_auth() -> OAuth1:
    """OAuth 1.0 TBA signer for NetSuite.

    NetSuite requires HMAC-SHA256 (SHA1 is rejected) and a realm equal to the
    account id uppercased with hyphens replaced by underscores
    (e.g. account 1234567-sb1 -> realm 1234567_SB1).
    """
    account_id = os.environ["NS_ACCOUNT_ID"]
    return OAuth1(
        client_key=os.environ["NS_CONSUMER_KEY"],
        client_secret=os.environ["NS_CONSUMER_SECRET"],
        resource_owner_key=os.environ["NS_TOKEN_ID"],
        resource_owner_secret=os.environ["NS_TOKEN_SECRET"],
        signature_method="HMAC-SHA256",
        realm=account_id.upper().replace("-", "_"),
    )


def restlet_url(script_id: str, deploy_id: str) -> str:
    # Account-specific RESTlet domain uses the account id lowercased with
    # underscores replaced by hyphens (e.g. 1234567_SB1 -> 1234567-sb1).
    # String script ids work here — numeric internal ids are not required.
    account_id = os.environ["NS_ACCOUNT_ID"]
    subdomain = account_id.lower().replace("_", "-")
    return (
        f"https://{subdomain}.restlets.api.netsuite.com"
        f"/app/site/hosting/restlet.nl?script={script_id}&deploy={deploy_id}"
    )


def attach(path: Path, folder_id: int, record_type: str | None = None,
           record_id: int | None = None, description: str = "",
           script_id: str | None = None, deploy_id: str | None = None) -> dict:
    """Upload `path` to File Cabinet folder `folder_id`; optionally attach.

    Returns the RESTlet response dict, e.g. {"success": True, "fileId": 12345,
    "attached": True}. Raises on HTTP or RESTlet-reported errors.
    """
    script_id = script_id or os.environ.get("NS_SCRIPT_ID", "customscript_file_attach")
    deploy_id = deploy_id or os.environ.get("NS_DEPLOY_ID", "customdeploy_file_attach")

    data = path.read_bytes()
    if len(data) > MAX_BYTES:
        raise ValueError(
            f"{path.name} is {len(data):,} bytes; exceeds the {MAX_BYTES:,} byte "
            "limit (base64 inflation would push the request over the RESTlet cap)"
        )

    payload = {
        "filename": path.name,
        "contentBase64": base64.b64encode(data).decode(),
        "folderId": folder_id,
        "description": description,
    }
    if record_type and record_id:
        payload["recordType"] = record_type
        payload["recordId"] = record_id

    resp = requests.post(
        restlet_url(script_id, deploy_id),
        json=payload,
        auth=ns_auth(),
        headers={"Content-Type": "application/json"},
        timeout=120,
    )
    resp.raise_for_status()
    result = resp.json()
    if not result.get("success"):
        raise RuntimeError(f"RESTlet error: {result.get('error')}")
    return result


def main() -> None:
    _load_dotenv()
    _require_env()

    p = argparse.ArgumentParser(
        description="Upload a file to the NetSuite File Cabinet and optionally attach it to a record."
    )
    p.add_argument("--file", required=True, help="path to the local file to upload")
    p.add_argument("--folder-id", type=int, default=None,
                   help="File Cabinet folder internal id (falls back to NS_DEFAULT_FOLDER_ID)")
    p.add_argument("--record-type", default=None,
                   help="record type to attach to, e.g. journalentry, invoice, vendorbill")
    p.add_argument("--record-id", type=int, default=None,
                   help="internal id of the record to attach to")
    p.add_argument("--description", default="", help="File Cabinet file description")
    p.add_argument("--script-id", default=None,
                   help="RESTlet script id (default: customscript_file_attach)")
    p.add_argument("--deploy-id", default=None,
                   help="RESTlet deployment id (default: customdeploy_file_attach)")
    args = p.parse_args()

    folder_id = args.folder_id
    if folder_id is None:
        env_folder = os.environ.get("NS_DEFAULT_FOLDER_ID", "")
        if env_folder.isdigit():
            folder_id = int(env_folder)
    if folder_id is None:
        sys.exit("A folder id is required: pass --folder-id or set NS_DEFAULT_FOLDER_ID.")

    if bool(args.record_type) != bool(args.record_id):
        sys.exit("--record-type and --record-id must be provided together.")

    result = attach(Path(args.file), folder_id, args.record_type, args.record_id,
                    args.description, args.script_id, args.deploy_id)
    print(f"OK — fileId={result['fileId']} attached={result.get('attached')}")


if __name__ == "__main__":
    main()
