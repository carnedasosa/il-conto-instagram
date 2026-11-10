# Lancia un giro del workflow di Il Conto, ne aspetta l'esito e, se fallisce, apre una finestra di avviso.
# Lo usano le attività di Windows:
#   «Il Conto - pubblica reel»     -Modo pubblica  (12:35 e 13:05: pubblica il reel arrivato alla sua ora)
#   «Il Conto - controlla token»   -Modo token     (09:30: controlla solo il token, non pubblica)
# -Modo prova lancia un giro che fallisce apposta (un id che non esiste), senza toccare Instagram:
# serve solo a vedere la finestra di avviso.
param(
    [ValidateSet('pubblica', 'token', 'prova')]
    [string]$Modo = 'pubblica'
)

$repo = 'carnedasosa/il-conto-instagram'
$gh = 'C:\Program Files\GitHub CLI\gh.exe'
$log = Join-Path $env:LOCALAPPDATA 'il-conto-giro.log'

function Scrivi($testo) {
    Add-Content -Path $log -Value ("{0:yyyy-MM-dd HH:mm} [{1}] {2}" -f (Get-Date), $Modo, $testo) -Encoding UTF8
}

function Avvisa($testo, $url) {
    Add-Type -AssemblyName System.Windows.Forms
    $domanda = if ($url) { "`n`nApro il log su GitHub?" } else { '' }
    $bottoni = if ($url) { 'YesNo' } else { 'OK' }
    $r = [System.Windows.Forms.MessageBox]::Show($testo + $domanda, 'Il Conto', $bottoni, 'Warning', 'Button1', 'DefaultDesktopOnly')
    if ($url -and $r -eq 'Yes') { Start-Process $url }
}

$rigenera = "Se nel log c'è «Errore API 190» il token è stato invalidato. Per rigenerarlo:`n" +
    "developers.facebook.com → app «wine-life» → Casi d'uso → Personalizza → Configurazione dell'API con Instagram Login → Genera token accanto a da.allora.`n" +
    "Poi, nella cartella il-conto-instagram:`npython pubblicazione/imposta_token.py --profilo da.allora"

$extra = switch ($Modo) {
    'token' { @('-f', 'token=true') }
    'prova' { @('-f', 'post=prova-avviso-inesistente') }
    default { @() }
}

$inizio = [DateTimeOffset]::UtcNow.AddSeconds(-10)
& $gh workflow run pubblica.yml -R $repo @extra
if ($LASTEXITCODE -ne 0) {
    Scrivi 'non riesco a lanciare il workflow'
    Avvisa "Il Conto: non riesco a lanciare il giro su GitHub ($Modo).`n`nControlla la connessione e, in un terminale, «gh auth status»." $null
    exit 1
}

# Il giro appena lanciato: il primo workflow_dispatch partito dopo $inizio.
$run = $null
for ($i = 0; $i -lt 24 -and -not $run; $i++) {
    Start-Sleep -Seconds 5
    $lista = & $gh run list -R $repo -w pubblica.yml -e workflow_dispatch -L 10 --json databaseId,createdAt | ConvertFrom-Json
    $run = $lista | Where-Object { [DateTimeOffset]$_.createdAt -ge $inizio } |
        Sort-Object { [DateTimeOffset]$_.createdAt } | Select-Object -First 1
}
if (-not $run) {
    Scrivi 'giro lanciato ma non trovato dopo 2 minuti'
    Avvisa "Il Conto: ho lanciato il giro ($Modo) ma dopo 2 minuti non compare su GitHub.`n`nControlla la pagina Actions del repo." "https://github.com/$repo/actions"
    exit 1
}

$id = $run.databaseId
$url = "https://github.com/$repo/actions/runs/$id"
& $gh run watch $id -R $repo --interval 15 *> $null
$esito = (& $gh run view $id -R $repo --json conclusion --jq .conclusion).Trim()
Scrivi "giro ${id}: $esito"
if ($esito -eq 'success') { exit 0 }

$testo = switch ($Modo) {
    'token' { "Il Conto: il controllo del token è FALLITO ($esito).`n`nSe non lo sistemi prima delle 12:30, il reel di oggi non esce.`n`n$rigenera" }
    'prova' { "Il Conto: questa è una PROVA dell'avviso. Il giro è fallito apposta ($esito) e non ha toccato Instagram." }
    default { "Il Conto: il giro di pubblicazione è FALLITO ($esito). Il reel di oggi potrebbe non essere uscito.`n`n$rigenera`n`nDopo il token nuovo, per farlo uscire subito:`ngh workflow run pubblica.yml -R $repo" }
}
Avvisa $testo $url
exit 1
