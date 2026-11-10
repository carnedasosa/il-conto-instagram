# il-conto-instagram

Pubblicazione automatica su Instagram dei reel della serie documentaria «Il Conto». Stesso metodo di Wine Life e Spiegoni (GitHub Actions + Instagram API con login Instagram), con tre aggiunte: etichetta IA (`is_ai_generated`), primo commento con le fonti e unione automatica di calendario ed episodi.

**Per partire leggi `GUIDA.md`.** Qui solo la mappa.

```
pubblicazione/
  carica.py          unisce ../calendario.json e episodi/*/pubblicazione.json, copia video e copertina, salta gli episodi non pronti
  publish.py         pubblica i reel arrivati alla loro ora (--due), --post ID, --check, --commenta ID, --dry-run
  imposta_token.py   salva il token nei Secrets del repo, senza mostrarlo
  png2jpg.py         converte copertine PNG in JPEG
  calendario.json    il calendario di questo repo (lo scrive carica.py)
  caption.md         caption e primo commento di ogni reel (lo scrive carica.py)
  pubblicati.json    i reel già usciti (lo scrive il bot: niente esce due volte)
  video/  jpg/       i file che Instagram scarica da raw.githubusercontent.com
esempio/             dati FINTI per provare carica.py senza episodi veri
.github/workflows/pubblica.yml   il giro (cron ogni 30 minuti, in pratica ogni 4-8 ore; vedi GUIDA.md)
windows/giro.ps1     lanciato dalle attività di Windows: avvia il giro e avvisa con una finestra se fallisce
```

Prove senza token (dalla cartella `il-conto-instagram`, su Windows serve `-X utf8`):

```
python -X utf8 pubblicazione/carica.py --dry-run
python -X utf8 pubblicazione/carica.py --dry-run --calendario esempio/calendario.FINTO.json --radice esempio
python -X utf8 pubblicazione/publish.py --dry-run --due
```

Il repository GitHub **non esiste ancora**: finché non viene creato e finché non ci sono i Secrets, niente può pubblicare.
