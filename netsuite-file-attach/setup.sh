#!/usr/bin/env bash
# setup.sh — one-time setup for netsuite-file-attach (macOS / Linux)
#
# What this script does (and nothing else):
#   1. Checks that Python 3 is installed
#   2. Installs the Python dependencies from requirements.txt
#   3. Creates .env from .env.example and prompts you for your credentials
#   4. Optionally installs this folder as a Claude Code skill
#
# It never sends your credentials anywhere — they are only written to the
# local .env file. Run it again any time; existing values are kept unless
# you type new ones.
#
# Run it with:  bash setup.sh

set -u
cd "$(dirname "$0")"

step() { printf '\n== %s ==\n' "$1"; }
ok()   { printf '   %s\n' "$1"; }

echo "netsuite-file-attach setup"
echo "This sets up the Python client. The RESTlet itself must be deployed"
echo "in NetSuite by your administrator first (see README, Part 1)."

# ---------------------------------------------------------------- 1. Python
step "Checking for Python 3"
PY=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        if "$candidate" --version 2>&1 | grep -q "Python 3\."; then
            PY="$candidate"
            ok "Found $("$candidate" --version 2>&1)"
            break
        fi
    fi
done
if [ -z "$PY" ]; then
    echo "   Python 3 was not found."
    if [ "$(uname)" = "Darwin" ]; then
        echo "   Install it from https://www.python.org/downloads/ then re-run:"
        echo "       bash setup.sh"
        command -v open >/dev/null 2>&1 && open "https://www.python.org/downloads/"
    else
        echo "   Install it with your package manager, e.g.:"
        echo "       sudo apt install python3 python3-pip    (Debian/Ubuntu)"
        echo "       sudo dnf install python3 python3-pip    (Fedora)"
        echo "   then re-run:  bash setup.sh"
    fi
    exit 1
fi

# ---------------------------------------------------------- 2. Dependencies
step "Installing Python dependencies (requests, requests-oauthlib)"
# Newer systems mark Python "externally managed"; fall back accordingly.
"$PY" -m pip install --disable-pip-version-check -r requirements.txt 2>/dev/null \
  || "$PY" -m pip install --disable-pip-version-check --user -r requirements.txt 2>/dev/null \
  || "$PY" -m pip install --disable-pip-version-check --user --break-system-packages -r requirements.txt \
  || { echo "   pip install failed - see the messages above."; exit 1; }
ok "Dependencies installed."

# ------------------------------------------------------------- 3. .env file
step "Setting up your credentials (.env)"
if [ ! -f .env ]; then
    cp .env.example .env
    ok "Created .env from the template."
fi

get_env() {  # key -> current value (empty if unset)
    grep "^[[:space:]]*$1=" .env 2>/dev/null | head -1 | cut -d= -f2- | tr -d '[:space:]'
}

set_env() {  # key value
    if grep -q "^[[:space:]]*$1=" .env; then
        awk -v k="$1" -v v="$2" 'BEGIN{FS=OFS="="} $1==k {print k"="v; next} {print}' .env > .env.tmp \
            && mv .env.tmp .env
    else
        printf '%s=%s\n' "$1" "$2" >> .env
    fi
}

ask_env() {  # key label optional_note
    current="$(get_env "$1")"
    if [ -n "$current" ]; then
        printf '   %s (already set - press Enter to keep): ' "$2"
    elif [ -n "${3:-}" ]; then
        printf '   %s (%s - press Enter to skip): ' "$2" "$3"
    else
        printf '   %s: ' "$2"
    fi
    IFS= read -r entry
    entry="$(printf '%s' "$entry" | tr -d '[:space:]')"
    [ -n "$entry" ] && set_env "$1" "$entry"
}

echo "   Paste the five values from your NetSuite administrator."
echo "   (They are saved only to the local .env file in this folder.)"
ask_env NS_ACCOUNT_ID      "Account ID (e.g. 1234567 or 1234567-sb1)" ""
ask_env NS_CONSUMER_KEY    "Consumer key"    ""
ask_env NS_CONSUMER_SECRET "Consumer secret" ""
ask_env NS_TOKEN_ID        "Token ID"        ""
ask_env NS_TOKEN_SECRET    "Token secret"    ""
ask_env NS_DEFAULT_FOLDER_ID "Default File Cabinet folder ID" "optional but recommended"

missing=""
for key in NS_ACCOUNT_ID NS_CONSUMER_KEY NS_CONSUMER_SECRET NS_TOKEN_ID NS_TOKEN_SECRET; do
    [ -z "$(get_env "$key")" ] && missing="$missing $key"
done
if [ -n "$missing" ]; then
    echo "   Still missing:$missing - run 'bash setup.sh' again when you have them."
else
    ok "All five credentials are set."
fi

# ----------------------------------------------- 4. Claude Code skill (opt.)
step "Claude Code skill (optional)"
echo "   If you use Claude Code, this lets you just ask in plain English,"
echo "   e.g. \"attach this workbook to journal entry 4242\"."
printf '   Install as a Claude Code skill? (y/N): '
IFS= read -r answer
case "$answer" in
    [Yy]*)
        dest="$HOME/.claude/skills/netsuite-file-attach"
        mkdir -p "$dest"
        (tar --exclude .git -cf - .) | (cd "$dest" && tar -xf -)
        ok "Skill installed to $dest"
        ;;
esac

# ------------------------------------------------------------------ Summary
step "Done"
if [ -z "$missing" ]; then
    echo "   Try it with any small PDF or spreadsheet:"
    if [ -n "$(get_env NS_DEFAULT_FOLDER_ID)" ]; then
        echo "     $PY attach_file.py --file \"test.pdf\""
    else
        echo "     $PY attach_file.py --file \"test.pdf\" --folder-id <folder id>"
    fi
    echo "   Expected output:  OK - fileId=12345 attached=False"
fi
echo "   Reminder: the RESTlet must be deployed in NetSuite (README, Part 1)"
echo "   before uploads will work."
exit 0
