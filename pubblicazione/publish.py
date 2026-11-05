#!/usr/bin/env python3
"""Pubblica i reel di Il Conto su Instagram leggendo calendario.json.

Stesso metodo di Wine Life e Spiegoni, con due aggiunte per questa serie:
  - il reel esce con l'etichetta IA di Instagram (is_ai_generated=true);
  - dopo la pubblicazione scrive il primo commento con le fonti ("primo_commento").

Usa la Instagram API con login Instagram (graph.instagram.com): serve un account
Professional (Creator o Business), niente Pagina Facebook.

Variabili d'ambiente (non servono con --dry-run):
  IG_USER_ID       id dell'account Instagram (lo salva imposta_token.py)
  IG_ACCESS_TOKEN  token di lunga durata con instagram_business_content_publish
                   e, per il primo commento, instagram_business_manage_comments
  IMAGE_BASE_URL   URL pubblico di jpg/, es. https://raw.githubusercontent.com/<utente>/<repo>/main/pubblicazione/jpg
  VIDEO_BASE_URL   URL pubblico di video/

Esempi:
  python3 publish.py --dry-run --due                 # cosa uscirebbe adesso, senza toccare Instagram
  python3 publish.py --dry-run --post e01-wanna-marchi
  python3 publish.py --due                           # pubblica i reel arrivati alla loro ora
  python3 publish.py --check --post ID               # prepara il reel su Instagram ma NON lo pubblica
  python3 publish.py --commenta ID                   # riprova il primo commento di un reel già uscito
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

API = "https://graph.instagram.com/v23.0"
HERE = Path(__file__).resolve().parent
CALENDARIO = HERE / "calendario.json"
STATO = HERE / "pubblicati.json"
TENTATIVI_COMMENTO = 5
PAUSA_COMMENTO = 10


class ApiError(Exception):
    """Errore dell'API. str(e) va nei log; e.breve (solo codici, niente testo di Meta) va in pubblicati.json."""
    def __init__(self, msg, breve):
        super().__init__(msg)
        self.breve = breve


def call(method, path, **params):
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    if method == "GET":
        req = urllib.request.Request(f"{url}?{data.decode()}")
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        # Il token non compare mai: l'URL non viene stampato e dal corpo della risposta tengo solo i campi utili.
        corpo = e.read().decode(errors="replace")
        try:
            err = json.loads(corpo).get("error", {})
            dettaglio = (f"tipo={err.get('type')} codice={err.get('code')} sub={err.get('error_subcode')} "
                         f"messaggio={str(err.get('message', ''))[:200]}")
            breve = f"errore API {e.code}, codice {err.get('code')}"
        except Exception:
            dettaglio, breve = "corpo non leggibile", f"errore API {e.code}"
        token = os.environ.get("IG_ACCESS_TOKEN", "")
        if token:
            dettaglio = dettaglio.replace(token, "[token]")
        raise ApiError(f"Errore API {e.code} su {path}: {dettaglio}", breve)


def call_or_exit(method, path, **params):
    try:
        return call(method, path, **params)
    except ApiError as e:
        sys.exit(str(e))


def wait_ready(container_id, tries=90, pause=10):
    # Instagram scarica e valida il video in modo asincrono (qualche minuto).
    for _ in range(tries):
        info = call_or_exit("GET", container_id, fields="status_code,status")
        status = info["status_code"]
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            sys.exit(f"Container {container_id} in stato {status}: {info.get('status', '')}")
        time.sleep(pause)
    sys.exit(f"Container {container_id} non pronto dopo {tries * pause} secondi")


def pubblica_commento(media_id, testo):
    """Scrive il primo commento. Non interrompe mai il programma: ritorna (id, errore)."""
    ultimo = ""
    for n in range(1, TENTATIVI_COMMENTO + 1):
        try:
            r = call("POST", f"{media_id}/comments", message=testo)
            return r["id"], None
        except ApiError as e:
            ultimo = e.breve
            print(f"   commento: tentativo {n}/{TENTATIVI_COMMENTO} non riuscito")
            if n < TENTATIVI_COMMENTO:
                time.sleep(PAUSA_COMMENTO)
    return None, ultimo


def publish(post, dry_run, check=False):
    """Crea il container del reel e lo pubblica. Ritorna (media_id, container) o None."""
    user = os.environ.get("IG_USER_ID", "<IG_USER_ID>")
    base = os.environ.get("IMAGE_BASE_URL", "<IMAGE_BASE_URL>").rstrip("/")
    video = os.environ.get("VIDEO_BASE_URL", "<VIDEO_BASE_URL>").rstrip("/") + "/" + post["video"]
    cover = f"{base}/{post['copertina']}"
    print(f"→ {post['id']} (reel, etichetta IA)")
    if dry_run:
        print(f"   {video}")
        print(f"   {cover}")
        print("   caption: " + post["caption"].splitlines()[0])
        print("   etichetta IA: is_ai_generated=true")
        pc = post.get("primo_commento")
        print("   primo commento: " + (pc.splitlines()[0][:100] if pc else "(nessuno)"))
        return None
    container = call_or_exit(
        "POST", f"{user}/media", media_type="REELS", video_url=video, cover_url=cover,
        share_to_feed="true", caption=post["caption"], is_ai_generated="true")["id"]
    wait_ready(container)
    if check:
        # Instagram ha scaricato e accettato il video: senza media_publish il container scade da solo.
        print(f"   verifica ok: container {container} pronto, NON pubblicato")
        return None
    media_id = call_or_exit("POST", f"{user}/media_publish", creation_id=container)["id"]
    print(f"   pubblicato, media id {media_id}")
    return media_id


def salva(done):
    STATO.write_text(json.dumps(done, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--due", action="store_true", help="pubblica i reel la cui ora è passata")
    p.add_argument("--post", help="pubblica subito il reel con questo id")
    p.add_argument("--commenta", metavar="ID", help="riprova il primo commento di un reel già pubblicato")
    p.add_argument("--dry-run", action="store_true", help="non chiama Instagram e non legge token")
    p.add_argument("--check", action="store_true", help="con --post: prepara il reel su Instagram senza pubblicarlo")
    args = p.parse_args()
    if not (args.due or args.post or args.commenta):
        p.error("serve --due, --post ID oppure --commenta ID")
    if args.check and not args.post:
        p.error("--check va usato con --post ID")

    cal = json.loads(CALENDARIO.read_text(encoding="utf-8"))
    tz = ZoneInfo(cal["fuso_orario"])
    done = json.loads(STATO.read_text(encoding="utf-8")) if STATO.exists() else {}
    now = datetime.now(tz)

    if args.commenta:
        post = next((x for x in cal["post"] if x["id"] == args.commenta), None)
        if not post or args.commenta not in done:
            sys.exit(f"{args.commenta}: non è in calendario o non risulta pubblicato")
        if not post.get("primo_commento"):
            sys.exit(f"{args.commenta}: nessun primo_commento in calendario")
        if args.dry_run:
            print(f"→ {args.commenta}: scriverei il commento: " + post["primo_commento"].splitlines()[0][:100])
            return
        if not os.environ.get("IG_ACCESS_TOKEN"):
            sys.exit("Manca la variabile IG_ACCESS_TOKEN")
        cid, err = pubblica_commento(done[args.commenta]["media_id"], post["primo_commento"])
        done[args.commenta]["commento"] = cid if cid else f"NON PUBBLICATO: {err}"
        salva(done)
        print("   commento pubblicato" if cid else f"   commento non pubblicato: {err}")
        return

    if args.post:
        todo = [x for x in cal["post"] if x["id"] == args.post]
        if not todo:
            sys.exit(f"Nessun post con id {args.post}")
        if args.post in done:
            sys.exit(f"{args.post} è già stato pubblicato il {done[args.post]['pubblicato']}")
    else:
        todo = [x for x in cal["post"]
                if x["id"] not in done
                and datetime.fromisoformat(x["quando"]).replace(tzinfo=tz) <= now]
        # Uno per giro: se il cron è rimasto fermo, i reel arretrati escono distanziati.
        todo = todo[:1]
    if not todo:
        print("Niente da pubblicare adesso.")
        return
    if not args.dry_run:
        for var in ("IG_USER_ID", "IG_ACCESS_TOKEN", "IMAGE_BASE_URL", "VIDEO_BASE_URL"):
            if not os.environ.get(var):
                sys.exit(f"Manca la variabile {var}")

    for post in todo:
        if post["id"] in done and not args.post:
            continue
        media_id = publish(post, args.dry_run, args.check)
        if not media_id:
            continue
        # Prima lo stato, poi il commento: se il commento fallisce il reel non deve uscire due volte.
        voce = {"media_id": media_id, "pubblicato": datetime.now(tz).isoformat(timespec="minutes")}
        done[post["id"]] = voce
        salva(done)
        if post.get("primo_commento"):
            cid, err = pubblica_commento(media_id, post["primo_commento"])
            voce["commento"] = cid if cid else f"NON PUBBLICATO: {err}"
            print("   primo commento pubblicato" if cid else f"   ATTENZIONE, primo commento non pubblicato: {err}")
            salva(done)


if __name__ == "__main__":
    main()
