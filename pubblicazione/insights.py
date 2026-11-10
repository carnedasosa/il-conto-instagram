#!/usr/bin/env python3
"""Legge i numeri dell'account Instagram e dei suoi post e li scrive in insights.json.

Non pubblica niente e non crea token: usa lo stesso IG_ACCESS_TOKEN della pubblicazione.
Il pannello social legge il file da qui, come calendario.json e pubblicati.json.

Cosa legge:
  - follower, seguiti, numero di post, like e commenti di ogni post: bastano i permessi
    che il token ha già (instagram_business_basic);
  - copertura, visualizzazioni, salvataggi, condivisioni e interazioni di ogni post:
    servono anche instagram_business_manage_insights. Se il token non li ha, il file
    lo dice ("insights": "non disponibili ...") e il resto viene scritto lo stesso.

Esce con errore SOLO se il token non vale più (codice 190): così il giro di Actions
diventa rosso e si vede subito, invece di accorgersene al primo post che non esce.
In quel caso nel file resta l'ultima lettura buona, più il campo "errore".
Ogni altro problema (rete, Instagram che non risponde) finisce nel log e il giro resta verde:
il pannello avvisa comunque se i numeri restano fermi troppo a lungo.

Il token non viene mai stampato: niente URL nei log, e dagli errori di Meta si tengono solo i codici.

Uso:
  python3 insights.py                    legge e scrive insights.json accanto a questo file
  python3 insights.py --ogni-ore 3       come sopra, ma solo se l'ultima lettura ha più di 3 ore
  python3 insights.py --prova            stampa cosa scriverebbe, senza scrivere
  python3 insights.py --env ../.env --uscita insights.json
                                         prende token e id dal file .env (per gli script sul PC)
"""
import argparse
import http.client
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

API = "https://graph.instagram.com/v27.0"
QUI = Path(__file__).resolve().parent
POST_MASSIMI = 60
# Valide sia per i post (FEED) sia per i reel (REELS): reference/instagram-media/insights, v27.0.
METRICHE = {
    "reach": "copertura",
    "views": "visualizzazioni",
    "saved": "salvataggi",
    "shares": "condivisioni",
    "total_interactions": "interazioni",
}
# Errori di permesso: il token vale, ma non può leggere gli insights.
CODICI_PERMESSO = {10, 200, 3}


class ErroreApi(Exception):
    def __init__(self, stato, codice, sotto, breve):
        super().__init__(breve)
        self.stato, self.codice, self.sotto = stato, codice, sotto


def chiedi(percorso, **campi):
    token = os.environ["IG_ACCESS_TOKEN"]
    campi["access_token"] = token
    url = f"{API}/{percorso}?{urllib.parse.urlencode(campi)}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=20) as r:
            return json.loads(r.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode(errors="replace")).get("error", {})
        except Exception:
            err = {}
        codice, sotto = err.get("code"), err.get("error_subcode")
        raise ErroreApi(e.code, codice, sotto, f"HTTP {e.code}, codice {codice}, sottocodice {sotto}") from None
    except (OSError, ValueError, http.client.HTTPException) as e:
        # Rete giù, connessione chiusa a metà, risposta che non è JSON. Il messaggio di urllib non contiene
        # l'URL, ma per sicurezza tolgo il token se ci fosse.
        testo = str(getattr(e, "reason", e)).replace(token, "[token]")[:150]
        raise ErroreApi(None, None, None, f"rete o risposta non valida: {type(e).__name__} {testo}") from None


def adesso():
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(d):
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def leggi_env(file):
    """Le righe CHIAVE=valore di un file .env (lo stesso formato di automazione/.env di Lino)."""
    valori = {}
    with open(file, encoding="utf-8-sig") as f:
        for riga in f:
            riga = riga.strip()
            if riga and not riga.startswith("#") and "=" in riga:
                k, v = riga.split("=", 1)
                valori[k.strip()] = v.strip().strip('"').strip("'")
    return valori


def leggi_post(user_id):
    campi = "id,permalink,timestamp,media_type,media_product_type,like_count,comments_count"
    pagina = chiedi(f"{user_id}/media", fields=campi, limit=50)
    media = list(pagina.get("data", []))
    # Si va avanti col cursore "after" (non con l'URL "next", che contiene il token).
    while len(media) < POST_MASSIMI and pagina.get("paging", {}).get("next"):
        dopo = pagina["paging"].get("cursors", {}).get("after")
        if not dopo:
            break
        pagina = chiedi(f"{user_id}/media", fields=campi, limit=50, after=dopo)
        media += pagina.get("data", [])
    out = []
    for m in media[:POST_MASSIMI]:
        out.append({
            "media_id": m["id"],
            "permalink": m.get("permalink"),
            "pubblicato_il": m.get("timestamp"),
            "tipo": m.get("media_product_type") or m.get("media_type"),
            # Se il proprietario nasconde like o commenti, Instagram non manda il campo.
            "like": m.get("like_count"),
            "commenti": m.get("comments_count"),
        })
    return out


def aggiungi_insights(post):
    """Aggiunge le metriche a ogni post. Ritorna lo stato da scrivere nel file."""
    letti, saltati = 0, 0
    for p in post:
        try:
            dati = chiedi(f"{p['media_id']}/insights", metric=",".join(METRICHE))
        except ErroreApi as e:
            if e.codice == 190:
                raise
            if e.codice in CODICI_PERMESSO:
                return f"non disponibili (codice {e.codice}): al token manca instagram_business_manage_insights"
            if e.stato is None:
                # Problema di rete: inutile insistere post per post (rischia di sforare il tempo del passo).
                return f"letti per {letti} post su {len(post)}, poi problema di rete"
            # Un post solo può non avere insights (per esempio se è uscito prima che il profilo diventasse professionale).
            saltati += 1
            if saltati >= 3 and letti == 0:
                return f"non disponibili ({e})"
            continue
        for voce in dati.get("data", []):
            nome = METRICHE.get(voce.get("name"))
            valori = voce.get("values") or [{}]
            if nome:
                p[nome] = valori[0].get("value")
        letti += 1
    return "ok" if saltati == 0 else f"ok, {saltati} post senza insights"


def main():
    a = argparse.ArgumentParser(description="Scrive insights.json con i numeri di Instagram.")
    a.add_argument("--uscita", default=str(QUI / "insights.json"))
    a.add_argument("--ogni-ore", type=float, default=0, help="salta se l'ultima lettura buona è più recente di così")
    a.add_argument("--env", help="file .env da cui prendere IG_ACCESS_TOKEN e IG_USER_ID")
    a.add_argument("--prova", action="store_true", help="non scrive il file")
    arg = a.parse_args()

    if arg.env:
        for k, v in leggi_env(arg.env).items():
            if k in ("IG_ACCESS_TOKEN", "IG_USER_ID"):
                os.environ.setdefault(k, v)
    if not os.environ.get("IG_ACCESS_TOKEN"):
        sys.exit("Manca IG_ACCESS_TOKEN")

    uscita = Path(arg.uscita)
    prima = {}
    if uscita.exists():
        try:
            prima = json.loads(uscita.read_text(encoding="utf-8"))
        except ValueError:
            prima = {}
    if arg.ogni_ore and prima.get("letto_il") and not prima.get("errore"):
        eta = adesso() - datetime.fromisoformat(prima["letto_il"].replace("Z", "+00:00"))
        if eta < timedelta(hours=arg.ogni_ore):
            print(f"Ultima lettura {int(eta.total_seconds() // 60)} minuti fa: niente da fare.")
            return 0

    try:
        io = chiedi("me", fields="user_id,username,followers_count,follows_count,media_count")
        if "data" in io:  # alcune risposte arrivano dentro una lista
            io = io["data"][0]
        user_id = os.environ.get("IG_USER_ID") or io["user_id"]
        post = leggi_post(user_id)
        stato_insights = aggiungi_insights(post)
    except ErroreApi as e:
        if e.codice != 190:
            print(f"Lettura non riuscita, riprovo al prossimo giro: {e}")
            return 0
        print(f"TOKEN NON VALIDO: {e}. Va rigenerato e rimesso nel segreto IG_ACCESS_TOKEN.")
        if not prima.get("errore") and not arg.prova:
            # Tengo l'ultima lettura buona e aggiungo l'errore: il pannello lo mostra come avviso.
            prima["errore"] = {"quando": iso(adesso()), "codice": 190, "sottocodice": e.sotto,
                               "messaggio": "token non valido: va rigenerato"}
            uscita.write_text(json.dumps(prima, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 1

    dati = {
        "versione": 1,
        "letto_il": iso(adesso()),
        "account": {
            "username": io.get("username"),
            "follower": io.get("followers_count"),
            "seguiti": io.get("follows_count"),
            "post": io.get("media_count"),
        },
        "insights": stato_insights,
        "post": post,
        "errore": None,
    }
    print(f"@{dati['account']['username']}: {dati['account']['follower']} follower, "
          f"{len(post)} post letti, insights: {stato_insights}")
    if arg.prova:
        print(json.dumps(dati, ensure_ascii=False, indent=2))
    else:
        uscita.write_text(json.dumps(dati, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


def principale():
    """Ogni errore inatteso finisce nel log e il giro resta verde: rosso solo per il token invalidato."""
    try:
        return main()
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        token = os.environ.get("IG_ACCESS_TOKEN") or "nessun-token"
        print(f"Numeri non letti per un errore inatteso, riprovo al prossimo giro: {type(e).__name__} {str(e).replace(token, '[token]')[:200]}")
        return 0


if __name__ == "__main__":
    sys.exit(principale())
