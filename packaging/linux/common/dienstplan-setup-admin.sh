#!/usr/bin/env bash
set -euo pipefail

DATA_DIR="/var/lib/dienstplan/data"
BOOTSTRAP_FILE="${DATA_DIR}/bootstrap.env"

mkdir -p "${DATA_DIR}"

prompt_if_tty() {
  [ -t 0 ] && [ -t 1 ]
}

if ! prompt_if_tty; then
  echo "No interactive terminal detected. Skipping admin credential prompt."
  exit 0
fi

default_email="admin@fritzwinter.de"
read -r -p "Initiale Admin-E-Mail [${default_email}]: " admin_email
admin_email="${admin_email:-$default_email}"

while true; do
  read -r -s -p "Initiales Admin-Passwort (leer = automatisch generiert): " admin_password
  echo
  read -r -s -p "Passwort wiederholen: " admin_password_confirm
  echo
  if [ "${admin_password}" = "${admin_password_confirm}" ]; then
    break
  fi
  echo "Passwoerter stimmen nicht ueberein. Bitte erneut eingeben."
done

{
  echo "DIENSTPLAN_INITIAL_ADMIN_EMAIL=${admin_email}"
  if [ -n "${admin_password}" ]; then
    echo "DIENSTPLAN_INITIAL_ADMIN_PASSWORD=${admin_password}"
  fi
} > "${BOOTSTRAP_FILE}"

chmod 600 "${BOOTSTRAP_FILE}"
if id -u dienstplan >/dev/null 2>&1; then
  chown dienstplan:dienstplan "${BOOTSTRAP_FILE}"
fi

echo "Initiale Admin-Credentials gespeichert: ${BOOTSTRAP_FILE}"
echo "Die Datei wird beim ersten Start automatisch verarbeitet und danach geloescht."
