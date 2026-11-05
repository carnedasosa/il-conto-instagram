#!/usr/bin/env python3
"""Prepara la pubblicazione di Il Conto: unisce il calendario e gli episodi pronti.

Legge
  <radice>/calendario.json                      (lo scrive la sessione "calendario")
  <radice>/episodi/<cartella>/pubblicazione.json (lo scrive la sessione di ogni episodio)
dove <radice> è la cartella del progetto (di default la cartella sopra il-conto-instagram/).

Formato di calendario.json (quello della sessione calendario):
  {"fuso_orario": "Europe/Rome",
   "post": [{"id": "001", "quando": "2026-11-09T20:00", "rubrica": "Il Conto",
             "video": "episodi/e01-.../render/e01-....mp4",       # relativo alla radice
             "copertina": "episodi/e01-.../render/copertina.jpg",
             "caption": "episodi/e01-.../pubblicazione.json"}]}   # percorso del json, oppure il testo
Accetta anche la chiave "episodi" al posto di "post" e una lista nuda.

Formato di pubblicazione.json (stanotte/REGOLE.md, sezione 11; i percorsi sono relativi alla cartella dell'episodio):
  {"id": "001", "cartella": "e01-...", "titolo": "...", "video": "render/e01-....mp4",
   "copertina": "render/copertina.jpg", "caption": "...", "primo_commento": "Fonti: ..."}

Per ogni episodio PRONTO (json valido, caption, video e copertina presenti, e voce nel calendario):
  - copia il video in pubblicazione/video/<cartella>.mp4 (con ffmpeg: video invariato, audio AAC 128 kbps,
    moov all'inizio; senza ffmpeg: copia semplice);
  - copia la copertina in pubblicazione/jpg/<cartella>-cover.jpg (converte se è un PNG);
  - scrive la voce in pubblicazione/calendario.json (id = cartella) e rigenera caption.md.
Gli episodi NON pronti vengono saltati e elencati con il motivo. Può essere rilanciato quante volte si vuole.
I reel già in pubblicati.json non si toccano.

Uso:
  python -X utf8 pubblicazione/carica.py --dry-run     # solo rapporto, non copia e non scrive nulla
  python -X utf8 pubblicazione/carica.py               # copia e scrive (poi: git add, commit, push)
  python -X utf8 pubblicazione/carica.py --ricomprimi  # come sopra, ma ricodifica il video: i render da 90 MB scendono a circa 40
  python -X utf8 pubblicazione/carica.py --calendario esempio/calendario.FINTO.json --radice esempio
"""
import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
VIDEO_OUT = HERE / "video"
JPG_OUT = HERE / "jpg"
CAL_OUT = HERE / "calendario.json"
CAP_OUT = HERE / "caption.md"
STATO = HERE / "pubblicati.json"

MAX_MB = 95            # raw.githubusercontent.com non serve file molto oltre i 100 MB
RIGA_IA = "Ricostruzione con immagini e voce generate da IA"
RICOMPRIMI = False     # --ricomprimi: ricodifica il video (H264, CRF 21, massimo 10 Mbps) invece di copiarlo


def carica_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def voci_calendario(cal):
    if isinstance(cal, list):
        return cal
    return cal.get("post") or cal.get("episodi") or []


def ffprobe(path):
    exe = shutil.which("ffprobe")
    if not exe:
        return None
    try:
        out = subprocess.run(
            [exe, "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height,avg_frame_rate:format=duration",
             "-of", "json", str(path)], capture_output=True, text=True, timeout=60, check=True).stdout
        return json.loads(out)
    except Exception:
        return None


def tipo_immagine(path):
    testa = Path(path).read_bytes()[:8]
    if testa.startswith(b"\xff\xd8"):
        return "jpg"
    if testa.startswith(b"\x89PNG"):
        return "png"
    return "?"


def controlla_episodio(voce, radice, avvisi):
    """Ritorna (episodio, None) se pronto, oppure (None, motivo)."""
    id_ = str(voce.get("id", "?"))
    cap = voce.get("caption", "")
    pj = None
    if isinstance(cap, str) and cap.strip().endswith(".json"):
        pj = radice / cap.strip()
    else:
        cand = sorted((radice / "episodi").glob("e*/pubblicazione.json"))
        for c in cand:
            try:
                if str(carica_json(c).get("id")) == id_:
                    pj = c
            except Exception:
                pass
    if pj is None or not pj.exists():
        return None, f"manca pubblicazione.json ({pj.relative_to(radice) if pj else 'nessuno trovato per id ' + id_})"
    try:
        p = carica_json(pj)
    except Exception as e:
        return None, f"pubblicazione.json non valido: {e}"
    ep_dir = pj.parent
    cartella = p.get("cartella") or ep_dir.name
    testo = (p.get("caption") or "").strip()
    if not testo:
        return None, "caption vuota in pubblicazione.json"
    if len(testo) > 2200:
        return None, f"caption di {len(testo)} caratteri (massimo 2200)"
    if testo.count("#") > 30:
        return None, "più di 30 hashtag"
    if RIGA_IA not in testo:
        avvisi.append(f"{cartella}: la caption non contiene la riga fissa «{RIGA_IA}…»")

    def trova(chiave_pj, chiave_cal):
        for base, rel in ((ep_dir, p.get(chiave_pj)), (radice, voce.get(chiave_cal))):
            if rel and (base / rel).exists():
                return base / rel
        return None

    video = trova("video", "video")
    if not video:
        return None, f"video non ancora pronto ({p.get('video') or voce.get('video') or 'percorso mancante'})"
    cover = trova("copertina", "copertina")
    if not cover:
        return None, f"copertina mancante ({p.get('copertina') or voce.get('copertina') or 'percorso mancante'})"
    if tipo_immagine(cover) == "?":
        return None, "la copertina non è né JPEG né PNG"

    mb = video.stat().st_size / 1e6
    if mb > MAX_MB and not RICOMPRIMI:
        avvisi.append(f"{cartella}: video di {mb:.0f} MB, oltre {MAX_MB} MB: GitHub rifiuta i file da 100 MiB in su e il repo cresce in fretta. "
                      "Usa --ricomprimi (video H264 a CRF 21, massimo 10 Mbps) oppure ridimensiona il render")
    elif mb > 50 and not RICOMPRIMI:
        avvisi.append(f"{cartella}: video di {mb:.0f} MB: GitHub avvisa sopra i 50 MB; con tutti gli episodi il repo supera 1 GB. Valuta --ricomprimi")
    info = ffprobe(video)
    if info:
        flussi = {s["codec_type"]: s for s in info.get("streams", []) if "codec_type" in s}
        durata = float(info.get("format", {}).get("duration", 0) or 0)
        v = flussi.get("video", {})
        if v.get("codec_name") not in ("h264", "hevc"):
            return None, f"codec video {v.get('codec_name')}: Instagram vuole H264 o HEVC"
        if not 3 <= durata <= 900:
            return None, f"durata {durata:.1f} s: i reel via API vanno da 3 s a 15 minuti"
        if "audio" not in flussi:
            avvisi.append(f"{cartella}: il video non ha audio")
        if (v.get("width"), v.get("height")) != (1080, 1920):
            avvisi.append(f"{cartella}: formato {v.get('width')}x{v.get('height')}, la serie è 1080x1920")
    else:
        avvisi.append(f"{cartella}: ffprobe non disponibile o video illeggibile, durata e codec non controllati")
    if not (p.get("primo_commento") or "").strip():
        avvisi.append(f"{cartella}: nessun primo_commento, ma la caption promette «Fonti nei commenti»")
    return {"id": id_, "cartella": cartella, "pj": pj, "p": p, "video": video, "cover": cover,
            "quando": voce.get("quando"), "rubrica": voce.get("rubrica", "Il Conto")}, None


def copia_video(src, dst, dry):
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        return "già aggiornato"
    if dry:
        return "da copiare"
    ff = shutil.which("ffmpeg")
    if ff:
        video = (["-c:v", "libx264", "-preset", "medium", "-crf", "21", "-maxrate", "10M", "-bufsize", "20M", "-pix_fmt", "yuv420p"]
                 if RICOMPRIMI else ["-c:v", "copy"])
        r = subprocess.run([ff, "-y", "-v", "error", "-i", str(src), "-map", "0:v:0", "-map", "0:a:0?", *video,
                            "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-movflags", "+faststart", str(dst)],
                           capture_output=True, text=True)
        if r.returncode == 0:
            return ("ricodificato con ffmpeg (H264 CRF 21, AAC 128 kbps, faststart)" if RICOMPRIMI
                    else "copiato con ffmpeg (AAC 128 kbps, faststart)")
        dst.unlink(missing_ok=True)
        print(f"   ffmpeg non è riuscito ({r.stderr.strip()[:200]}): copia semplice", file=sys.stderr)
    shutil.copy2(src, dst)
    return "copiato (copia semplice: controlla che il moov sia all'inizio e l'audio AAC)"


def copia_cover(src, dst, dry):
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        return "già aggiornata"
    if dry:
        return "da copiare"
    if tipo_immagine(src) == "png":
        from PIL import Image
        Image.open(src).convert("RGB").save(dst, "JPEG", quality=92, optimize=True, progressive=True)
        return "convertita da PNG"
    shutil.copy2(src, dst)
    return "copiata"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="solo rapporto: non copia e non scrive")
    ap.add_argument("--calendario", help="calendario.json da usare (default: <radice>/calendario.json)")
    ap.add_argument("--ricomprimi", action="store_true",
                    help="ricodifica i video (H264 CRF 21, massimo 10 Mbps): file molto più piccoli, qualità quasi uguale")
    ap.add_argument("--radice", help="cartella del progetto (default: la cartella sopra il-conto-instagram)")
    args = ap.parse_args()
    global RICOMPRIMI
    RICOMPRIMI = args.ricomprimi

    radice = Path(args.radice).resolve() if args.radice else REPO.parent
    cal_path = Path(args.calendario).resolve() if args.calendario else radice / "calendario.json"
    if not cal_path.exists():
        print(f"Il calendario {cal_path} non c'è ancora: niente da fare.")
        print("Per provare con l'esempio finto: --calendario esempio/calendario.FINTO.json --radice esempio")
        return
    cal = carica_json(cal_path)
    tz = ZoneInfo(cal.get("fuso_orario", "Europe/Rome")) if isinstance(cal, dict) else ZoneInfo("Europe/Rome")
    if "FINTO" in json.dumps(cal)[:400] or "FINTO" in cal_path.name:
        print("*** ATTENZIONE: calendario d'esempio FINTO. Non è il calendario vero. ***")
    pubblicati = carica_json(STATO) if STATO.exists() else {}
    esistente = {x["id"]: x for x in voci_calendario(carica_json(CAL_OUT))} if CAL_OUT.exists() else {}

    avvisi, pronti, saltati, gia = [], [], [], []
    visti = set()
    for voce in voci_calendario(cal):
        ep, motivo = controlla_episodio(voce, radice, avvisi)
        etichetta = Path(str(voce.get("caption", ""))).parent.name or str(voce.get("id"))
        if motivo:
            saltati.append((f"{voce.get('id')} {etichetta}", voce.get("quando"), motivo))
            continue
        visti.add(ep["cartella"])
        if ep["cartella"] in pubblicati:
            gia.append(ep["cartella"])
            continue
        pronti.append(ep)

    # Cartelle di episodio che nel calendario non compaiono.
    in_cal = {Path(str(v.get("caption", ""))).parent.name for v in voci_calendario(cal)}
    for d in sorted((radice / "episodi").glob("*")):
        if d.is_dir() and d.name not in in_cal:
            motivo = "senza pubblicazione.json" if not (d / "pubblicazione.json").exists() else "pronto ma non in calendario"
            saltati.append((d.name, None, f"fuori dal calendario, {motivo}"))

    print(f"\nRadice: {radice}\nCalendario: {cal_path}\n")
    if args.dry_run:
        print("(prova: non copio e non scrivo nulla)\n")
    adesso = datetime.now(tz)
    nuove = []
    for ep in sorted(pronti, key=lambda e: e["quando"] or ""):
        v_out = VIDEO_OUT / f"{ep['cartella']}.mp4"
        c_out = JPG_OUT / f"{ep['cartella']}-cover.jpg"
        if not args.dry_run:
            VIDEO_OUT.mkdir(exist_ok=True)
            JPG_OUT.mkdir(exist_ok=True)
        rv = copia_video(ep["video"], v_out, args.dry_run)
        rc = copia_cover(ep["cover"], c_out, args.dry_run)
        quando = ep["quando"]
        if quando and datetime.fromisoformat(quando).replace(tzinfo=tz) <= adesso:
            avvisi.append(f"{ep['cartella']}: l'ora {quando} è già passata, uscirebbe al primo giro dopo il push")
        print(f"PRONTO  {ep['cartella']:<24} {quando}  video: {rv}; copertina: {rc}")
        nuove.append({"id": ep["cartella"], "quando": quando, "rubrica": ep["rubrica"],
                      "video": f"{ep['cartella']}.mp4", "copertina": f"{ep['cartella']}-cover.jpg",
                      "caption": ep["p"]["caption"].strip(), "primo_commento": (ep["p"].get("primo_commento") or "").strip()})
    for c in gia:
        print(f"GIÀ USCITO  {c}: non lo tocco")
    for nome, quando, motivo in saltati:
        print(f"SALTATO {nome:<28} {quando or ''}  → {motivo}")
    for a in avvisi:
        print(f"AVVISO  {a}")
    print(f"\nRiassunto: {len(nuove)} pronti, {len(saltati)} saltati, {len(gia)} già usciti.")

    if args.dry_run:
        return
    # Tiene le voci dei reel già usciti, aggiunge/aggiorna quelle pronte. Quelle saltate non entrano.
    voci = {k: v for k, v in esistente.items() if k in pubblicati}
    for n in nuove:
        voci[n["id"]] = n
    out = {"fuso_orario": cal.get("fuso_orario", "Europe/Rome") if isinstance(cal, dict) else "Europe/Rome",
           "post": sorted(voci.values(), key=lambda x: x["quando"] or "")}
    CAL_OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    righe = ["# Il Conto: calendario e caption", "",
             "Generato da `pubblicazione/carica.py`: non modificarlo a mano, cambia l'episodio e rilancia.", "",
             "| Quando | Reel | Stato |", "|---|---|---|"]
    for x in out["post"]:
        righe.append(f"| {x['quando']} | {x['id']} | {'pubblicato' if x['id'] in pubblicati else 'in calendario'} |")
    for x in out["post"]:
        righe += ["", f"## {x['id']}", "", "```", x["caption"], "```"]
        if x.get("primo_commento"):
            righe += ["", "Primo commento:", "", "```", x["primo_commento"], "```"]
    CAP_OUT.write_text("\n".join(righe) + "\n", encoding="utf-8")
    print(f"Scritti {CAL_OUT.relative_to(REPO)} e {CAP_OUT.relative_to(REPO)}. Ora: git add, commit e push.")


if __name__ == "__main__":
    main()
