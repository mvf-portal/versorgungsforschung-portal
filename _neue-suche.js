// ---- Suche ---------------------------------------------------------------
// Grundsatz: Es passiert nichts, bevor der Nutzer absendet. Frueher schrieb
// die Seite die Links schon beim Tippen um - unsichtbar, ohne Rueckmeldung.
// Jetzt gilt das Muster gaengiger Suchmaschinen: eingeben, Enter, Ergebnis.
const input     = document.getElementById('q');
const goBtn     = document.getElementById('go');
const resultBar = document.getElementById('resultBar');
const boolHint  = document.getElementById('boolHint');
let   gesucht   = '';        // zuletzt abgeschickter Begriff

const OPERATOR = /(^|\s)(AND|OR|NOT)(\s|$)/;

function basisUrl(tpl){
  return tpl.split('?')[0].split('/%s')[0];
}

// Links auf den Begriff einstellen - oder zurueck auf die Startseiten.
function verdrahte(term){
  const enc = encodeURIComponent(term);
  cardIndex.forEach(c=>{
    c.el.href = (c.type === 'live' && term) ? c.tpl.replace('%s', enc)
              : (c.type === 'live')         ? basisUrl(c.tpl)
              :                               c.tpl;
  });
}

function suchen(){
  const term = input.value.trim();
  if(!term){ input.focus(); return; }
  gesucht = term;
  verdrahte(term);
  document.body.classList.add('gesucht');

  const sichtbar = cardIndex.filter(c=>!c.el.classList.contains('aus'));
  const live     = sichtbar.filter(c=>c.type==='live').length;
  const portale  = sichtbar.filter(c=>c.type==='portal').length;
  const lizenz   = sichtbar.filter(c=>c.type==='lic').length;

  resultBar.innerHTML =
    '<b>&bdquo;' + htmlEsc(term) + '&ldquo;</b> ist in <b>' + live + '</b> Datenbanken vorbereitet &mdash; '
    + 'ein Klick &ouml;ffnet die Trefferliste in einem neuen Tab.'
    + '<span class="rb-zusatz">Dazu ' + portale + ' Portale, in denen der Begriff nach dem &Ouml;ffnen '
    + 'einzugeben ist, und ' + lizenz + ' Datenbanken mit Lizenzpflicht.</span>';
  resultBar.hidden = false;

  // Sichtbar hinunterspringen: sonst bliebe die Wirkung im Kopfbereich verborgen.
  const ziel = document.querySelector('.cat:not(.aus)');
  if(ziel) ziel.scrollIntoView({behavior:'smooth', block:'start'});
  aktualisiereChips(term);
}

function zuruecksetzen(){
  gesucht = '';
  input.value = '';
  verdrahte('');
  document.body.classList.remove('gesucht');
  resultBar.hidden = true;
  boolHint.hidden = true;
  aktualisiereChips('');
  input.focus();
}

function aktualisiereChips(term){
  document.querySelectorAll('.chip').forEach(ch=>{
    ch.setAttribute('aria-pressed',
      ch.dataset.term.toLowerCase() === term.toLowerCase() ? 'true' : 'false');
  });
}

// Operatoren-Hinweis: nur wenn welche getippt werden, und mit den echten
// Zahlen. b:1 = geprueft, wertet aus. b:0 = geprueft, wertet nicht aus.
// Fehlendes Merkmal = ungeprueft und wird NICHT als "kann es" gezaehlt.
function pruefeOperatoren(){
  if(!OPERATOR.test(input.value)){ boolHint.hidden = true; return; }
  const live  = DB.filter(x=>x.t === 'live');
  const ja    = live.filter(x=>x.b === 1).length;
  const nein  = live.filter(x=>x.b === 0).length;
  const offen = live.length - ja - nein;
  boolHint.innerHTML =
    '<b>AND, OR und NOT</b> werden von <b>' + ja + '</b> der ' + live.length
    + ' Live-Suchen nachweislich ausgewertet; sie tragen das Zeichen '
    + '<b>AND/OR</b>. ' + nein + ' werten sie nachweislich nicht aus und suchen die '
    + 'W&ouml;rter einfach mit, bei ' + offen + ' ist es ungepr&uuml;ft.';
  boolHint.hidden = false;
}

input.addEventListener('input', ()=>{
  pruefeOperatoren();
  goBtn.disabled = !input.value.trim();
});
input.addEventListener('keydown', e=>{
  if(e.key === 'Enter'){ e.preventDefault(); suchen(); }
});
goBtn.addEventListener('click', suchen);
document.getElementById('clear').addEventListener('click', zuruecksetzen);

// ---- Schnellwahl ----
const chipsBox = document.getElementById('chips');
CHIPS.forEach(t=>{
  const b = document.createElement('button');
  b.type = 'button'; b.className = 'chip'; b.textContent = t; b.dataset.term = t;
  // Ein Chip ist eine fertige Suche - er sendet direkt ab.
  b.addEventListener('click', ()=>{ input.value = t; pruefeOperatoren(); suchen(); });
  chipsBox.appendChild(b);
});

// ---- Filter --------------------------------------------------------------
const FILTER = { zugang:'alle', suchart:'alle', bool:'alle', rubrik:new Set() };

// Rubrik-Chips aus CATS aufbauen, damit beides nie auseinanderlaeuft.
const rubrikBox = document.getElementById('filterRubrik');
CATS.forEach(cat=>{
  const b = document.createElement('button');
  b.type = 'button'; b.className = 'fchip'; b.dataset.wert = cat.id;
  b.textContent = cat.name; b.setAttribute('aria-pressed','false');
  rubrikBox.appendChild(b);
});

function passt(x){
  if(FILTER.zugang === 'frei'   && x.t === 'lic') return false;
  if(FILTER.zugang === 'lizenz' && x.t !== 'lic') return false;
  if(FILTER.suchart === 'live'   && x.t !== 'live')   return false;
  if(FILTER.suchart === 'portal' && x.t !== 'portal') return false;
  if(FILTER.bool === 'ja' && x.b !== 1) return false;
  if(FILTER.rubrik.size && !FILTER.rubrik.has(x.c)) return false;
  return true;
}

function filtern(){
  let sichtbar = 0;
  cardIndex.forEach(c=>{
    const ok = passt(c.eintrag);
    c.el.classList.toggle('aus', !ok);
    if(ok) sichtbar++;
  });
  // Rubriken ohne sichtbare Kachel ganz ausblenden - samt Sprungmarke.
  CATS.forEach(cat=>{
    const sek = document.getElementById(cat.id);
    if(!sek) return;
    const drin = cardIndex.filter(c=>c.eintrag.c === cat.id && !c.el.classList.contains('aus'));
    sek.classList.toggle('aus', drin.length === 0);
    const nav = document.querySelector('.jump a[href="#' + cat.id + '"]');
    if(nav) nav.classList.toggle('aus', drin.length === 0);
    const z = sek.querySelector('.cat-count');
    if(z) z.textContent = drin.length + ' Datenbanken';
  });

  const aktiv = (FILTER.zugang !== 'alle') + (FILTER.suchart !== 'alle')
              + (FILTER.bool !== 'alle') + (FILTER.rubrik.size ? 1 : 0);
  const badge = document.getElementById('filterBadge');
  badge.textContent = aktiv; badge.hidden = !aktiv;
  document.getElementById('dbCount').textContent = sichtbar;
  if(gesucht) suchen();   // Rueckmeldung an die neue Auswahl anpassen
}

document.querySelectorAll('.filter-group').forEach(gruppe=>{
  const name = gruppe.dataset.gruppe;
  gruppe.addEventListener('click', e=>{
    const b = e.target.closest('.fchip');
    if(!b) return;
    if(name === 'rubrik'){
      const an = b.getAttribute('aria-pressed') === 'true';
      b.setAttribute('aria-pressed', an ? 'false' : 'true');
      if(an) FILTER.rubrik.delete(b.dataset.wert); else FILTER.rubrik.add(b.dataset.wert);
    } else {
      FILTER[name] = b.dataset.wert;
      gruppe.querySelectorAll('.fchip').forEach(x=>
        x.setAttribute('aria-pressed', x === b ? 'true' : 'false'));
    }
    filtern();
  });
});

// ---- Anfangszustand: nichts ist gesucht, Links zeigen auf die Startseiten.
verdrahte('');
filtern();
goBtn.disabled = !input.value.trim();
