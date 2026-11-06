# Il Conto: pubblicazione automatica su Instagram. Guida per Alessio

Preparata il 5 novembre 2026, di notte, solo in locale. **Non è stato creato nessun repository, non è stato pubblicato nulla, non è stata fatta nessuna chiamata a Instagram, nessun token è stato toccato.** Questa cartella è una copia dei metodi di Wine Life e Spiegoni, con tre aggiunte per questa serie: etichetta IA, primo commento con le fonti, unione automatica di calendario ed episodi.

## In cima: i blocchi

**Nessun blocco vero.** Le tre domande che avevi posto, con la risposta letta sulla documentazione ufficiale di Meta:

| Domanda | Risposta | Da fare |
|---|---|---|
| Etichetta IA via API | **Si può.** Il parametro `is_ai_generated=true` alla creazione del reel applica l'etichetta «Info IA». | Niente. `publish.py` lo manda già. Va controllato sul primo reel. |
| Primo commento con le fonti | **Si può, ma serve un permesso in più:** `instagram_business_manage_comments`. Va aggiunto all'app Meta **prima** di generare il token di Il Conto. | Un passo in più nel pannello Meta (punto 3 qui sotto). |
| `cover_url`, durata, limiti | `cover_url` si può usare e prevale sul fotogramma. Il reel va da 3 secondi a 15 minuti. Un reel al giorno è lontanissimo dai limiti. | Niente. |

Se qualcosa di queste tre cose non funzionasse alla prova reale, il reel esce comunque e la caption porta già la riga fissa «Ricostruzione con immagini e voce generate da IA» (la mette l'episodio). Il commento si può scrivere a mano o ritentare dal workflow (vedi «Se il commento non esce»).

## Cosa è già pronto (non devi fare niente)

- `pubblicazione/publish.py`: pubblica i reel arrivati alla loro ora, un reel per giro, con etichetta IA e primo commento.
- `pubblicazione/carica.py`: unisce `calendario.json` della cartella principale con i `pubblicazione.json` degli episodi, copia video e copertina e **salta con un motivo gli episodi non pronti**. Si può rilanciare quante volte vuoi.
- `pubblicazione/imposta_token.py`: salva il token nei Secrets di GitHub senza mostrarlo.
- `.github/workflows/pubblica.yml`: ogni 30 minuti (minuti 7 e 37) controlla il calendario. Un giro alla volta, lo stato lo salva il bot.
- `esempio/`: dati FINTI per provare tutto senza episodi veri.
- Non c'è nessun video né nessuna copertina nella cartella: arrivano quando gli episodi sono pronti.

Prove fatte stanotte, tutte senza token (risultati in `stanotte/stato/automazione.md`).

## Cosa devi fare tu, in ordine

### 1. Il profilo (a mano, nell'app Instagram)

1. Scegli il nome. Nella cartella principale (`regole-verificate.md`) due nomi controllati sono `@da.allora` e `@andostorto`: la ricerca dice «pagina non disponibile», ma **non vuol dire che siano liberi**, lo sai solo provando. `@daallora` esiste già.
2. Crea l'account (o usa uno nuovo) e imposta il nome in **Profilo → Modifica profilo → Nome** e **Nome utente**.
3. Passa a professionale: **Impostazioni e attività → Tipo di account e strumenti → Passa a un account professionale → Creator** (va bene anche Business). Senza account professionale l'API non funziona. Non serve una Pagina Facebook.
4. Non scrivere il nome del profilo nelle immagini generate prima di averlo registrato (regola della serie).

### 2. Tester nell'app Meta «wine-life»

È la stessa app che usano Wine Life e Spiegoni, in modalità sviluppo. Stessi passi di Spiegoni:

1. Vai su developers.facebook.com → **app «wine-life»** → **Casi d'uso** → **Personalizza** → **Configurazione dell'API con Instagram Login**.
2. Nel riquadro «2. Genera i token d'accesso» clicca **Aggiungi account** ed entra con il profilo di Il Conto.
3. Nell'app Instagram del profilo di Il Conto accetta l'invito: **Impostazioni → App e siti web → Inviti tester**.

**Se l'invito non compare** (successo il 5 novembre con `@da.allora`, invitato prima che il profilo fosse professionale):
- Non esiste una pagina ufficiale di Meta che spieghi perché. La pagina dei ruoli dell'app non nomina l'«Instagram Tester» e non dice che tipo di account serve. Quello che segue è un tentativo, non una regola documentata.
- Nel pannello dell'app, scheda **Ruoli**, controlla che l'invito sia di tipo **Instagram Tester** (non «Tester» generico: è un ruolo diverso, che si accetta da Facebook) e che il nome sia scritto esattamente `da.allora`. Se risulta «in sospeso», rimuovilo e **reinvialo adesso** che il profilo è professionale.
- Prova anche la versione web: instagram.com/accounts/manage_access/ (indicata da guide di terzi, non confermata da Meta), con il profilo di Il Conto aperto.
- L'invito non va accettato da Facebook: quello è per gli «Authorized App Tester».

### 3. Aggiungi il permesso dei commenti (prima di generare il token)

Nello stesso caso d'uso, nella scheda dei permessi (il nome in italiano può variare, cerca «Autorizzazioni e funzioni»), aggiungi **`instagram_business_manage_comments`** accanto a `instagram_business_basic` e `instagram_business_content_publish`. È lo stesso permesso che Meta indica per i commenti con Instagram Login.

Non rigenerare i token di Wine Life e Spiegoni: non serve, hanno già i loro.

### 4. Genera il token e salvalo senza mostrarlo

1. Torna al riquadro «2. Genera i token d'accesso» e clicca **Genera token** accanto al profilo di Il Conto. Copialo. **Non incollarlo in chat e non scriverlo in nessun file.**
2. Dopo aver creato il repository (punto 5), da terminale, nella cartella `il-conto-instagram`:

```bash
python pubblicazione/imposta_token.py --profilo NOMEDELPROFILO
```

Lo script chiede il token senza mostrarlo, legge da Instagram il nome del profilo, **rifiuta @winee.life e @glispiegoni** (i profili già automatizzati) e ti chiede conferma prima di salvare `IG_ACCESS_TOKEN` e `IG_USER_ID` nei Secrets del repo.

### 5. Il repository su GitHub: NON ancora creato

Il repository deve essere **pubblico**, perché Instagram scarica video e copertine da `raw.githubusercontent.com`. Quando decidi di partire, dalla cartella `il-conto-instagram`:

```bash
gh repo create carnedasosa/il-conto-instagram --public --source=. --push
```

**Attenzione:** con il repo pubblico un video è visibile a chiunque sul web appena è nel repo, **prima** dell'ora in calendario. Per questo `carica.py` va lanciato solo per gli episodi che vuoi davvero far uscire, e il push va fatto poco prima. Quanto in anticipo conviene fare il push è una tua scelta.

### 6. Verifica finale prima di partire (non pubblica niente)

Quando c'è almeno un episodio pronto e il token è nei Secrets:

```bash
gh workflow run pubblica.yml -R carnedasosa/il-conto-instagram -f post=ID_EPISODIO -f verifica=true
```

Instagram scarica il video da GitHub, lo elabora e risponde `FINISHED`, ma non lo pubblica. Da rifare se cambia il token o il formato dei video. **Non prova il commento né l'etichetta IA:** quelle due cose si vedono solo sul primo reel vero.

### 7. Sul primo reel che esce

1. Apri il reel nell'app: deve mostrare **«Info IA»** (etichetta IA). Se non c'è, dillo: la voce di Meta del 22 giugno 2026 non nomina i Reels, parla in generale del Content Publishing. In quel caso si può aggiungere l'etichetta a mano dall'app.
2. Sotto il reel deve esserci il **primo commento con le fonti**. Se non c'è, guarda «Se il commento non esce».
3. Il commento **non si può fissare via API** (nessun endpoint documentato). Fissalo a mano se vuoi.

## Come tenere ferma l'automazione

L'automazione non parte da sola finché una di queste tre cose è vera. Basta una:

- **Il repository non esiste.** È la situazione di stanotte.
- **I Secrets non sono impostati.** Senza `IG_ACCESS_TOKEN` e `IG_USER_ID` `publish.py` si ferma con «Manca la variabile» e non pubblica.
- **Il workflow è spento** (con il repo già creato):

```bash
gh workflow disable pubblica.yml -R carnedasosa/il-conto-instagram
```

Per riaccenderlo: `gh workflow enable pubblica.yml -R carnedasosa/il-conto-instagram`.

Un reel che non vuoi far uscire: non lanciare `carica.py` per quell'episodio, oppure togli la voce da `pubblicazione/calendario.json` prima del push. I reel già in `pubblicati.json` non escono mai due volte.

## Il flusso per ogni episodio (dopo il primo avvio)

1. L'episodio è finito: `pubblicazione.json` accanto al render, voce in `calendario.json`.
2. Prova a secco, non scrive nulla:

```bash
python -X utf8 pubblicazione/carica.py --dry-run
```

3. Se il rapporto va bene (PRONTO), copia davvero. Con `--ricomprimi` i video scendono a circa un terzo (vedi «Dimensione sul repo»):

```bash
python -X utf8 pubblicazione/carica.py --ricomprimi
```

4. `git pull`, `git add`, commit e push. Da qui il reel esce da solo all'ora in calendario, di solito pochi minuti dopo le 20:05 grazie all'attività di Windows (vedi «Riserva su Windows»).
5. Controllo di cosa uscirebbe adesso, senza toccare Instagram: `python -X utf8 pubblicazione/publish.py --dry-run --due`.

Su Windows serve sempre `python -X utf8`.

## Se il commento non esce

Il reel è già pubblicato e registrato in `pubblicati.json` **prima** di scrivere il commento: se il commento fallisce non può mai uscire due volte il reel. Il commento fa 5 tentativi a 10 secondi; se falliscono, in `pubblicati.json` compare `"commento": "NON PUBBLICATO: …"` e l'azione GitHub mostra un avviso.

Per ritentare dal workflow, **senza tenere il token sul PC**:

```bash
gh workflow run pubblica.yml -R carnedasosa/il-conto-instagram -f commenta=ID_EPISODIO
```

Il testo da incollare a mano, se serve, sta in `pubblicazione/caption.md`.

La causa più probabile è il permesso `instagram_business_manage_comments` mancante nel token: nel log si vede un errore di permessi. Si risolve riaggiungendolo (punto 3) e rigenerando il token (punto 4).

## Le tre risposte, con le fonti

Tutto letto il 5 novembre 2026 sulle pagine ufficiali di Meta. Dove le pagine si contraddicono o tacciono, lo dico.

### Etichetta IA via API

- Fonte: [changelog Instagram Platform](https://developers.facebook.com/documentation/instagram-platform/changelog.md), voce del **22 giugno 2026** «AI Info Label»: il Content Publishing API supporta l'auto-dichiarazione di contenuto generato con IA al momento della pubblicazione; si imposta `is_ai_generated=true` quando si crea il container. Vale per Instagram API con Facebook Login **e** con Instagram Login.
- Conferma nella [guida alla pubblicazione](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/content-publishing): `is_ai_generated`, `true|false`, opzionale.
- Si può rileggere con `GET /{ig-media-id}?fields=is_ai_generated`.
- **Non verificato:** la voce del changelog non dice esplicitamente «Reels». Per questo il primo reel va guardato nell'app.

### Primo commento con le fonti

- Fonte: [riferimento IG Media Comments](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-media/comments) e [guida moderazione commenti con Instagram Login](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/comment-moderation).
- Endpoint documentato: `POST /{ig-media-id}/comments?message=…`. Risposta: l'id del commento.
- Permessi con Instagram Login: `instagram_business_basic` e **`instagram_business_manage_comments`**.
- Il proprio account basta: «Standard Access» è quello che serve per account che possiedi o gestisci ([guida alla pubblicazione](https://developers.facebook.com/documentation/instagram-platform/content-publishing.md)). Le pagine dei commenti non nominano modalità sviluppo né tester: **che funzioni in modalità sviluppo senza App Review è dedotto, non scritto.**
- **Incoerenza nella documentazione:** l'esempio del POST usa l'host `graph.facebook.com`; per Instagram Login la tabella dei requisiti indica `graph.instagram.com`, che è quello che usa `publish.py`. La prova reale lo dirà.
- **Non documentato:** lunghezza massima del commento, numero di link, limite di frequenza. **Nessun endpoint per fissare il commento.**
- Il testo è in `primo_commento` di `pubblicazione.json`, è nel `calendario.json` del repo e **finisce nel repo pubblico**: non metterci niente di riservato.

### `cover_url`, durata e limiti

- Fonte: [guida alla pubblicazione](https://developers.facebook.com/documentation/instagram-platform/content-publishing.md) e [riferimento di `/media`](https://developers.facebook.com/documentation/instagram-platform/instagram-graph-api/reference/ig-user/media).
- **`cover_url`:** immagine pubblica, JPEG, massimo 8 MB. Se ci sono sia `cover_url` sia `thumb_offset`, «usiamo `cover_url` e ignoriamo `thumb_offset`». Per questo le copertine devono essere JPEG (non PNG): `carica.py` converte da solo.
- **Reel:** da 3 secondi a 15 minuti; massimo 300 MB; MP4 o MOV con il `moov` all'inizio; video H264 o HEVC; audio AAC fino a 48 kHz e 128 kbps; da 23 a 60 fps; larghezza massima 1920 px; formato consigliato 9:16 (la serie è 1080x1920).
- **Caption:** massimo 2200 caratteri, 30 hashtag, 20 tag. Il testo alternativo (`alt_text`) **non è supportato** per i Reels.
- **Limiti di pubblicazione:** la guida dice 100 post pubblicati via API in 24 ore mobili e 400 container creabili. Un'altra frase della stessa guida (sezione caroselli) dice 50 post, e `content_publishing_limit` riporta una quota di 50. **Le pagine si contraddicono**, ma con un reel al giorno, anche con il recupero degli arretrati (uno per giro), siamo comunque lontanissimi da qualsiasi dei due numeri.
- **Dimensione sul repo: attenzione.** I render veri pesano tanto: e01 è 96 MB (40 s, circa 19 Mbps) ed e02 84 MB. GitHub rifiuta i file da 100 MiB in su e avvisa sopra i 50 MB; con 8 episodi da 90 MB il repo supera 1 GB. `carica.py` lo segnala come AVVISO. La soluzione è `--ricomprimi`: ricodifica in H264 (CRF 21, massimo 10 Mbps). Provato stanotte su e01 ed e02 **in una copia fuori dal repo**: 96 → 31 MB e 84 → 27 MB, stessa durata, 1080x1920, 30 fps, AAC 128 kbps, `moov` all'inizio; un fotogramma confrontato a occhio sembra identico, ma **il video intero non l'ho riguardato**. Decidi tu se ti sta bene la qualità: senza il flag il video resta quello del render (solo l'audio diventa AAC 128 kbps).
- **Attesa:** l'elaborazione è asincrona, Meta consiglia di controllare una volta al minuto per non più di 5 minuti; `publish.py` controlla ogni 10 secondi per un massimo di 15 minuti, come Wine Life e Spiegoni.

## Rinnovo del token

Il token dura **60 giorni**. Appena generato, segnati la scadenza (data di generazione + 60 giorni) e rigeneralo dal pannello qualche giorno prima: rigenera il token e rilancia `imposta_token.py`. Meta può anche invalidarlo prima, con errore 190 (è successo a Spiegoni il 4 novembre): se la pubblicazione fallisce con «Errore API 190», rigeneralo.

## Riserva su Windows (attiva dal 6 novembre 2026)

**Il cron di GitHub da solo non basta.** È impostato ogni 30 minuti, ma misurato il 6 novembre gira ogni 4-8 ore, sia qui sia su Spiegoni: senza riserva un reel delle 20:00 può uscire a notte fonda.

L'attività **«Il Conto - pubblica reel»** lancia il workflow ogni giorno alle **20:05 e alle 20:35**. È senza input, quindi pubblica solo ciò che è già arrivato alla sua ora, e `pubblicati.json` impedisce che un reel esca due volte.

- **Il PC deve essere acceso e con la tua sessione aperta** alle 20:05. Se non lo è, l'attività parte appena rientri, e nel frattempo resta solo il cron.
- **Se cambi l'ora dei reel** nel calendario, cambia anche l'ora dell'attività.
- **Per toglierla:**

```powershell
Unregister-ScheduledTask -TaskName "Il Conto - pubblica reel"
```

## Regole da non dimenticare

- **Il token** non va mai in chat, nei file o nei commit. Solo nei Secrets di GitHub, tramite `imposta_token.py`.
- **Commit** con l'email noreply di GitHub (`170640320+carnedasosa@users.noreply.github.com`), già impostata in questa copia.
- **Chiedere prima di:** pubblicare subito un reel (`-f post=ID` senza `verifica`), cancellare un reel dal calendario, cambiare l'ora di un reel già in calendario.
- **Altri due profili:** `@winee.life` e `@glispiegoni` hanno le loro automazioni. Questa cartella non le tocca.
