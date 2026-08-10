#requires -Version 5.1
<#
  Lokales Studien-Update fuer das Versorgungsforschung-Portal (Windows PowerShell).

  Ablauf:
    1. PubMed E-utilities: neueste Treffer zu "health services research" (nach Datum).
    2. Claude-API: 6 relevante Studien mit konkreten Ergebnissen auswaehlen und auf
       Deutsch zusammenfassen (strukturierte JSON-Ausgabe).
    3. Nur den Marker-Block (SNAP_DATE + STUDIES) in index.html ersetzen (inkl. Zeitstempel).
    4. Bei Aenderung: git add/commit/push -> GitHub Pages veroeffentlicht automatisch.

  Voraussetzung: Umgebungsvariable ANTHROPIC_API_KEY (Anthropic-API-Key).
  Modell ueber Umgebungsvariable MODEL aenderbar (Standard: claude-haiku-4-5).

  Aufruf (aus beliebigem Verzeichnis):
    powershell -NoProfile -ExecutionPolicy Bypass -File "<Repo>\scripts\update-studies.ps1"
#>

$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# --- Konfiguration --------------------------------------------------------
$RepoRoot = Split-Path -Parent $PSScriptRoot          # scripts/ -> Repo-Wurzel
$Index    = Join-Path $RepoRoot 'index.html'
$Model    = if ([string]::IsNullOrWhiteSpace($env:MODEL)) { 'claude-haiku-4-5' } else { $env:MODEL }
$ApiKey   = $env:ANTHROPIC_API_KEY
$Term     = '"health services research"'
$START    = '// === STUDIES-BLOCK-START (wird woechentlich vom Cloud-Agenten ersetzt) ==='
$END      = '// === STUDIES-BLOCK-ENDE ==='

if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    throw "ANTHROPIC_API_KEY ist nicht gesetzt. Bitte als Umgebungsvariable hinterlegen."
}

# --- Hilfsfunktionen ------------------------------------------------------
function ConvertTo-JsString([string]$s) {
    if ($null -eq $s) { return '""' }
    $s = $s -replace '\\', '\\'
    $s = $s -replace '"',  '\"'
    $s = $s -replace "`r", ''
    $s = $s -replace "`n", '\n'
    $s = $s -replace "`t", '\t'
    return '"' + $s + '"'
}

# --- 1) PubMed: neueste PMIDs --------------------------------------------
$es = Invoke-RestMethod -Method Get -Uri 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi' `
        -Body @{ db = 'pubmed'; term = $Term; sort = 'date'; retmax = '25'; retmode = 'json' }
$ids = @($es.esearchresult.idlist)
if ($ids.Count -eq 0) { throw "esearch lieferte keine PMIDs." }

# --- 2) PubMed: Abstracts als Text ---------------------------------------
$abstracts = Invoke-RestMethod -Method Get -Uri 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi' `
        -Body @{ db = 'pubmed'; id = ($ids -join ','); rettype = 'abstract'; retmode = 'text' }
$abstracts = [string]$abstracts

# --- 3) Claude-API: Auswahl + deutsche Zusammenfassungen -----------------
$schema = @{
    type = 'object'; additionalProperties = $false; required = @('studies')
    properties = @{
        studies = @{
            type = 'array'
            items = @{
                type = 'object'; additionalProperties = $false
                required = @('journal', 'year', 'pmid', 'title', 'sum', 'result')
                properties = @{
                    journal = @{ type = 'string' }; year = @{ type = 'string' }; pmid = @{ type = 'string' }
                    title   = @{ type = 'string' }; sum  = @{ type = 'string' }; result = @{ type = 'string' }
                }
            }
        }
    }
}

$system = 'Du bist Fachredakteur fuer Versorgungsforschung / Health Services Research. Aus einer Liste von PubMed-Abstracts waehlst du die relevantesten aktuellen Studien aus und fasst sie praezise auf Deutsch zusammen.'

$user = @"
Unten stehen aktuelle PubMed-Abstracts (nach Datum sortiert).

Waehle GENAU 6 Studien aus, die (a) fuer Versorgungsforschung / Health Services Research
relevant sind UND (b) im Abstract KONKRETE quantitative Ergebnisse nennen
(Prozentwerte, Odds/Hazard Ratios, p-Werte, Fallzahlen). Ueberspringe Studien ohne
Abstract oder ohne konkrete Ergebnisse. Achte auf thematische Vielfalt; die neuesten zuerst.

Fuer jede Studie:
- journal: Journalname (Originalsprache)
- year: Erscheinungsjahr, z. B. "2026"
- pmid: die PubMed-ID
- title: praegnanter deutscher Titel
- sum: 1 Satz auf Deutsch, was die Studie untersucht hat
- result: Deutsch, die konkreten Zahlen/Befunde + ein kurzer Einordnungssatz. Deutsches Zahlenformat mit Komma (z. B. 0,63).

Gib ausschliesslich das geforderte JSON zurueck.

=== ABSTRACTS ===
$abstracts
"@

$payload = @{
    model         = $Model
    max_tokens    = 8000
    system        = $system
    messages      = @(@{ role = 'user'; content = $user })
    output_config = @{ format = @{ type = 'json_schema'; schema = $schema } }
} | ConvertTo-Json -Depth 40

$headers = @{ 'x-api-key' = $ApiKey; 'anthropic-version' = '2023-06-01' }

try {
    $resp = Invoke-RestMethod -Method Post -Uri 'https://api.anthropic.com/v1/messages' `
                -Headers $headers -ContentType 'application/json' `
                -Body ([System.Text.Encoding]::UTF8.GetBytes($payload))
}
catch {
    $detail = $_.Exception.Message
    try {
        $stream = $_.Exception.Response.GetResponseStream()
        $detail = (New-Object System.IO.StreamReader($stream)).ReadToEnd()
    } catch {}
    throw "Claude-API-Fehler: $detail"
}

$txt = ($resp.content | Where-Object { $_.type -eq 'text' } | Select-Object -First 1).text
if ([string]::IsNullOrWhiteSpace($txt)) { throw "Keine Textantwort vom Modell erhalten." }
$studies = @(($txt | ConvertFrom-Json).studies)
if ($studies.Count -lt 5 -or $studies.Count -gt 7) {
    throw "Unerwartete Studienanzahl: $($studies.Count)"
}

# --- 4) Marker-Block bauen -----------------------------------------------
$months = @{ 1 = 'Jan.'; 2 = 'Feb.'; 3 = 'März'; 4 = 'Apr.'; 5 = 'Mai'; 6 = 'Juni';
             7 = 'Juli'; 8 = 'Aug.'; 9 = 'Sept.'; 10 = 'Okt.'; 11 = 'Nov.'; 12 = 'Dez.' }
$now  = Get-Date   # lokale Zeit = Berliner Zeit auf diesem Rechner
$snap = '{0}. {1} {2}, {3:00}:{4:00} Uhr' -f $now.Day, $months[$now.Month], $now.Year, $now.Hour, $now.Minute

$items = foreach ($s in $studies) {
    "  {`n" +
    "    journal:$(ConvertTo-JsString $s.journal), year:$(ConvertTo-JsString $s.year), pmid:$(ConvertTo-JsString $s.pmid),`n" +
    "    title:$(ConvertTo-JsString $s.title),`n" +
    "    sum:$(ConvertTo-JsString $s.sum),`n" +
    "    result:$(ConvertTo-JsString $s.result)`n" +
    "  }"
}

$block = @(
    $START,
    "const SNAP_DATE = $(ConvertTo-JsString $snap);",
    'const STUDIES = [',
    (($items -join ",`n") + ','),
    '];',
    $END
) -join "`n"

# --- 5) index.html aktualisieren -----------------------------------------
$html = [System.IO.File]::ReadAllText($Index, [System.Text.Encoding]::UTF8) -replace "`r", ''
$re = [regex]::new([regex]::Escape($START) + '.*?' + [regex]::Escape($END),
                   [System.Text.RegularExpressions.RegexOptions]::Singleline)
if (-not $re.IsMatch($html)) { throw "Marker-Block nicht in index.html gefunden." }

$new = $re.Replace($html, { param($m) $block }, 1)
if ($new -eq $html) {
    Write-Host "Inhalt unveraendert."
    return
}
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($Index, $new, $utf8NoBom)
Write-Host "index.html aktualisiert: $($studies.Count) Studien ($snap)."

# --- 6) Committen & pushen -----------------------------------------------
Push-Location $RepoRoot
try {
    if (git status --porcelain -- index.html) {
        git add index.html
        git -c user.name='VF-Portal Bot' -c user.email='stegmaier@m-vf.de' `
            commit -m "Studien-Update $($now.ToString('dd.MM.yyyy'))" | Out-Null
        git push
        Write-Host "Committet & gepusht."
    } else {
        Write-Host "Keine Git-Aenderung."
    }
}
finally { Pop-Location }
