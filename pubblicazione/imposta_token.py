#!/usr/bin/env python3
"""Salva il token Instagram nei secret del repo GitHub, senza mostrarlo a schermo.

Chiede il token (non si vede mentre lo incolli), legge user_id e username da
Instagram, poi imposta i secret IG_ACCESS_TOKEN e IG_USER_ID con la CLI `gh`.
Il token non viene scritto in nessun file.

Prima di salvare mostra @username e chiede conferma: il nome del profilo di
Il Conto non è fissato qui, così non si salva per sbaglio il token di un altro profilo
(@winee.life, @glispiegoni). Se passi il nome atteso con --profilo, lo script lo confronta.

Uso (dalla radice di il-conto-instagram, dopo aver creato il repo):
  python pubblicazione/imposta_token.py
  python pubblicazione/imposta_token.py --profilo nomedelprofilo
"""
import argparse
import getpass
import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

REPO = "carnedasosa/il-conto-instagram"
API = "https://graph.instagram.com/v23.0"
VIETATI = {"winee.life", "glispiegoni"}   # profili già automatizzati: qui non vanno mai

ap = argparse.ArgumentParser()
ap.add_argument("--profilo", help="nome atteso del profilo di Il Conto, senza @")
args = ap.parse_args()

token = getpass.getpass("Incolla il token e premi Invio (non si vede): ").strip()
if not token:
    sys.exit("Nessun token inserito.")

url = f"{API}/me?" + urllib.parse.urlencode({"fields": "user_id,username", "access_token": token})
try:
    with urllib.request.urlopen(url, timeout=30) as r:
        me = json.load(r)
except urllib.error.HTTPError as e:
    sys.exit(f"Instagram ha rifiutato il token ({e.code}). Rigeneralo e riprova.")

user_id, username = str(me["user_id"]), me.get("username", "?")
print(f"Token valido per @{username} (user_id {user_id}).")
if username.lower() in VIETATI:
    sys.exit(f"@{username} ha già la sua automazione: hai incollato il token sbagliato. Niente salvato.")
if args.profilo and username.lower() != args.profilo.lstrip("@").lower():
    sys.exit(f"Atteso @{args.profilo.lstrip('@')}, trovato @{username}. Niente salvato.")
if input(f"È il profilo di Il Conto? Salvo i secret su GitHub ({REPO})? [s/N] ").strip().lower() != "s":
    sys.exit("Annullato, niente salvato.")

for name, value in (("IG_ACCESS_TOKEN", token), ("IG_USER_ID", user_id)):
    subprocess.run(["gh", "secret", "set", name, "-R", REPO], input=value, text=True, check=True)
print("Fatto: IG_ACCESS_TOKEN e IG_USER_ID salvati nei secret del repo.")
