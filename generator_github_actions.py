import json
from pathlib import Path
from datetime import datetime
from urllib.parse import quote_plus

APP_TITLE = "Woningzoeker Frank Burrei"
MAX_HUUR = 1600

CORE_PLACES = ["Beverwijk", "Heemskerk"]
REGION_PLACES = [
    "Uitgeest", "Castricum", "Assendelft", "Velsen-Noord", "Wijk aan Zee",
    "Zaandam", "Driehuis", "Santpoort-Noord", "Velserbroek", "Bakkum",
    "Heiloo", "Limmen", "Akersloot", "Wormerveer", "Krommenie",
    "Haarlem-Noord", "IJmuiden", "Heemstede", "Bloemendaal"
]

DIRECT_SOURCES = [
    {"name": "Funda", "type": "funda", "priority": 1, "focus": "huurwoningen"},
    {"name": "Pararius", "type": "pararius", "priority": 1, "focus": "huurwoningen"},
]

GOOGLE_QUERIES = [
    {"name": "Google 2 kamers", "priority": 1, "focus": "2 kamers", "query": "2 kamer appartement huur {place} max {max_huur}"},
    {"name": "Google 3 kamers", "priority": 2, "focus": "3 kamers", "query": "3 kamer appartement huur {place} max {max_huur}"},
    {"name": "Google kindvriendelijk", "priority": 2, "focus": "kindvriendelijk", "query": "kindvriendelijke huurwoning {place} max {max_huur}"},
    {"name": "Google gezinswoning", "priority": 2, "focus": "gezinswoning", "query": "gezinswoning huur {place} max {max_huur}"},
    {"name": "Google appartement", "priority": 2, "focus": "appartement", "query": "appartement huur {place} max {max_huur}"},
    {"name": "Google huurwoning", "priority": 2, "focus": "huurwoning", "query": "huurwoning {place} max {max_huur}"},
]

PORTALS = [
    "Huurwoningen.nl", "Huurportaal", "Huurstunt", "Direct Wonen", "Kamernet",
    "NederWoon", "RentSlam", "HousingAnywhere", "123Wonen", "kamers.nl",
    "Rentola", "Rentbird", "Jaap huur", "Mansion.nl", "Wonen31", "ExpatRentals",
    "Pararius huur", "Funda huur", "Rental Apartments", "Huurteam", "Stekkies"
]

LANDLORDS = [
    "Vesteda", "MVGM", "Rotsvast", "Heimstaden", "Holland2Stay", "Interhouse",
    "HouseHunting", "REBO", "Altera", "Bouwinvest", "Newomij", "Amvest Living",
    "BPD Woningfonds", "Rockfield", "ACH Vastgoed", "Change=", "Brix", "Greystar",
    "The Fizz", "OurDomain"
]

CORPORATIONS = [
    "Woonopmaat", "Pré Wonen", "Rochdale", "Elan Wonen", "WoningNet",
    "Eigen Haard", "Ymere", "Parteon", "ZVH", "Intermaris", "Kennemer Wonen",
    "Woonzorg Nederland", "Wonen Zuid Kennemerland", "Lieven de Key", "De Key",
    "Wooncompagnie", "Woonwaard", "Woonservice", "de Alliantie", "Stadgenoot",
    "Omnia Wonen", "Thuisvester", "Portaal", "Lefier", "Vivare", "Laris",
    "Socius Wonen", "Rijnhart Wonen", "Velison Wonen", "Dudok Wonen"
]

AGENCIES = [
    "Brantjes makelaars", "Van Gulik makelaars", "Teer makelaars", "Bert van Vulpen",
    "Saen Garantiemakelaars", "EV Wonen", "Kuijs Reinder Kakes", "Hopman ERA",
    "Bakker Makelaardij", "KRK makelaars", "Mooijekind Vleut", "Vos Makelaardij",
    "IJmond Makelaars", "Van Duin", "Noordstad makelaars", "PMA makelaars",
    "Van der Borden", "De Best van Staveren", "Rikken Makelaardij", "Overspaern",
    "Hendriks makelaardij", "Bakker Schoon", "Puur Makelaars", "Magneet Makelaars"
]

EXTRA_REGION = [
    ("Makelaars IJmond", "makelaar", 3, "makelaar huurwoning IJmond"),
    ("Verhuurmakelaar IJmond", "makelaar", 3, "verhuurmakelaar IJmond"),
    ("Makelaars Noord-Holland huur", "makelaar", 3, "makelaar huurwoning Noord-Holland"),
    ("Middenhuur Noord-Holland", "corporatie", 3, "middenhuur Noord-Holland huurwoning"),
    ("Huurwoning 10 km Beverwijk", "straal 10 km", 2, "huurwoning Beverwijk 10 km max 1600"),
    ("Huurwoning 10 km Heemskerk", "straal 10 km", 2, "huurwoning Heemskerk 10 km max 1600"),
    ("Huurwoning IJmond gezin", "gezinswoning", 2, "gezinswoning huur IJmond max 1600"),
]

def google_url(query: str) -> str:
    return "https://www.google.com/search?q=" + quote_plus(query)

def direct_url(source_type: str, place: str) -> str:
    p = place.lower()
    if source_type == "funda":
        return f"https://www.funda.nl/zoeken/huur?selected_area=%5B%22{p}%22%5D&price=%22-1600%22"
    if source_type == "pararius":
        return f"https://www.pararius.nl/huurwoningen/{p}/0-{MAX_HUUR}"
    raise ValueError(source_type)

def add_row(rows, seen, bron, plaats, prioriteit, focus, url):
    key = (bron, plaats, url)
    if key not in seen:
        seen.add(key)
        rows.append({
            "bron": bron,
            "plaats": plaats,
            "prioriteit": prioriteit,
            "focus": focus,
            "url": url,
        })

def build_data():
    rows = []
    seen = set()

    for place in CORE_PLACES:
        for src in DIRECT_SOURCES:
            add_row(rows, seen, src["name"], place, src["priority"], src["focus"], direct_url(src["type"], place))
        for src in GOOGLE_QUERIES:
            add_row(rows, seen, src["name"], place, src["priority"], src["focus"], google_url(src["query"].format(place=place, max_huur=MAX_HUUR)))
        for name in PORTALS:
            add_row(rows, seen, f"Google {name}", place, 3, "portal", google_url(f"{name} {place} huur"))
        for name in LANDLORDS:
            add_row(rows, seen, f"Google {name}", place, 3, "verhuurder", google_url(f"{name} huurwoning {place}"))
        for name in CORPORATIONS:
            add_row(rows, seen, f"Google {name}", place, 3, "corporatie", google_url(f"{name} huur {place}"))
        for name in AGENCIES:
            add_row(rows, seen, f"Google {name}", place, 3, "makelaar", google_url(f"{name} huur {place}"))

    for place in REGION_PLACES:
        for src in DIRECT_SOURCES:
            add_row(rows, seen, src["name"], place, 2, "regio-uitbreiding", direct_url(src["type"], place))
        for src in GOOGLE_QUERIES:
            if src["priority"] <= 2:
                add_row(rows, seen, src["name"], place, max(2, src["priority"]), src["focus"], google_url(src["query"].format(place=place, max_huur=MAX_HUUR)))
        for name in PORTALS[:10]:
            add_row(rows, seen, f"Google {name}", place, 3, "portal", google_url(f"{name} {place} huur"))
        for name in AGENCIES[:10]:
            add_row(rows, seen, f"Google {name}", place, 3, "makelaar", google_url(f"{name} huur {place}"))

    for name, focus, priority, query in EXTRA_REGION:
        add_row(rows, seen, name, "Regio", priority, focus, google_url(query))

    return rows

def html_template(data_json: str, generated_at: str) -> str:
    template = """<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>__APP_TITLE__</title>
<meta name="theme-color" content="#0b57d0">
<style>
:root{
  --bg:#eef4ff; --bg2:#f8fbff; --card:#ffffff; --text:#132238; --muted:#68788f;
  --line:#d9e4f5; --brand:#0b57d0; --brand3:#eaf2ff; --green:#e9fff1; --greenLine:#a8e6c0;
  --blue:#eef4ff; --blueLine:#c7d9ff; --gray:#f6f7f9; --grayLine:#d9dde3; --orange:#fff4e6;
  --orangeLine:#f2c88e; --shadow:0 14px 42px rgba(13,39,89,.10);
}
*{box-sizing:border-box} html,body{margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;background:linear-gradient(180deg,var(--bg2) 0%, var(--bg) 100%);color:var(--text)}
.app-shell{max-width:430px;margin:0 auto;min-height:100vh;background:linear-gradient(180deg,#f8fbff 0%,#eef4ff 100%);position:relative}
.safe{padding:16px 16px 104px 16px}
.hero{background:linear-gradient(145deg,#0b57d0 0%, #2f74ef 42%, #72a8ff 100%);color:#fff;border-radius:30px;padding:24px 18px 18px;box-shadow:var(--shadow);overflow:hidden}
.hero h1{margin:0;font-size:28px;line-height:1.04}
.hero p{margin:10px 0 0;line-height:1.45;font-size:14px;max-width:320px;opacity:.96}
.hero-meta{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}
.hero-meta span{background:rgba(255,255,255,.16);border:1px solid rgba(255,255,255,.18);color:#fff;padding:8px 10px;border-radius:999px;font-size:12px}
.grid-top{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:14px}
.stat{background:rgba(255,255,255,.94);color:var(--text);border:1px solid rgba(255,255,255,.7);border-radius:18px;padding:13px}
.stat strong{display:block;font-size:24px;margin-bottom:4px}
.section{margin-top:16px}
.section-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
.section-head h2{margin:0;font-size:20px}
.subtle{color:var(--muted);font-size:13px}
.card{background:var(--card);border:1px solid var(--line);border-radius:22px;padding:14px;box-shadow:0 8px 24px rgba(14,30,66,.05)}
.controls{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.controls .full{grid-column:1 / -1}
label{display:block;font-size:12px;color:var(--muted);margin-bottom:6px}
input, select, textarea{width:100%;border:1px solid var(--line);border-radius:14px;padding:12px 12px;font-size:15px;background:#fff;color:var(--text)}
textarea{min-height:150px;resize:vertical}
.action-row{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}
button, .linkbtn{border:none;appearance:none;background:var(--brand);color:#fff;border-radius:14px;padding:11px 13px;font-size:14px;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;justify-content:center;gap:6px}
button.secondary, .linkbtn.secondary{background:var(--brand3);color:var(--brand)}
button.ghost{background:#f5f7fb;color:#1f2937;border:1px solid var(--line)}
.notice{background:#eef5ff;border:1px solid #c8d9ff;color:#1f4e98;border-radius:16px;padding:12px;font-size:13px;line-height:1.45}
.list{display:grid;gap:12px}
.item{border-radius:22px;padding:14px;border:1px solid var(--line);box-shadow:0 6px 18px rgba(15,23,42,.04)}
.item h3{margin:0;font-size:18px;line-height:1.2}
.meta{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 12px}
.meta span{padding:6px 10px;border-radius:999px;font-size:12px;border:1px solid rgba(0,0,0,.04);background:rgba(255,255,255,.8)}
.priority1{background:var(--green); border-color:var(--greenLine)} .priority2{background:var(--blue); border-color:var(--blueLine)} .priority3{background:var(--gray); border-color:var(--grayLine)}
.badge-new{background:var(--orange)!important;border-color:var(--orangeLine)!important}
.panel{display:none} .panel.active{display:block}
.bottom-nav{position:fixed;left:50%;transform:translateX(-50%);bottom:0;width:min(430px,100%);background:rgba(255,255,255,.94);backdrop-filter: blur(12px);border-top:1px solid var(--line);display:grid;grid-template-columns:repeat(5,1fr);padding:10px 8px calc(10px + env(safe-area-inset-bottom));z-index:10}
.navbtn{border:none;background:transparent;color:var(--muted);font-size:11px;display:flex;flex-direction:column;align-items:center;gap:5px;padding:6px 0;cursor:pointer}
.navbtn .icon{width:34px;height:34px;border-radius:12px;display:flex;align-items:center;justify-content:center;background:#f4f7fb;font-size:17px}
.navbtn.active{color:var(--brand);font-weight:600} .navbtn.active .icon{background:var(--brand3)}
.empty{color:var(--muted);text-align:center;padding:16px}
.scorebar{height:8px;border-radius:999px;background:rgba(255,255,255,.65);overflow:hidden;margin-top:8px;border:1px solid rgba(0,0,0,.04)}
.scorebar > div{height:100%;background:linear-gradient(90deg,#0b57d0,#69a2ff)}
.priority-guide{display:grid;gap:10px} .priority-guide .box{border-radius:18px;padding:14px;line-height:1.45}
.prio1{background:var(--green)} .prio2{background:var(--blue)} .prio3{background:var(--gray)}
.footer-note{color:var(--muted);font-size:12px;text-align:center;margin-top:14px}
</style>
</head>
<body>
<div class="app-shell">
  <div class="safe">
    <div class="hero">
      <h1>__APP_TITLE__</h1>
      <p>Woningzoek-overzicht voor Beverwijk, Heemskerk en omgeving. Deze app bundelt verschillende verhuurwebsites, makelaars en woningplatforms zodat je sneller woningen kunt vinden.</p>
      <div class="hero-meta">
        <span>__COUNT__ woningbronnen</span>
        <span>Genereerd: __GENERATED_AT__</span>
        <span>Max. €__MAX_HUUR__</span>
      </div>
      <div class="grid-top">
        <div class="stat"><strong id="totalCount">0</strong><span class="subtle">woningbronnen</span></div>
        <div class="stat"><strong id="newCount">0</strong><span class="subtle">nieuw</span></div>
      </div>
    </div>

    <div id="dashboard" class="panel active section">
      <div class="section-head"><h2>Radar</h2><span class="subtle">start hier</span></div>
      <div class="card">
        <div class="notice">Nieuwe bronnen worden gemarkeerd zodat je makkelijk ziet waar je nog kunt kijken.</div>
        <div class="action-row">
          <button id="markAllSeen">Alles gezien</button>
          <button class="ghost" id="resetRadar">Reset radar</button>
        </div>
        <div class="list" id="todayList" style="margin-top:12px"></div>
      </div>
    </div>

    <div id="zoeken" class="panel section">
      <div class="section-head"><h2>Zoeken</h2><span class="subtle">filter & open</span></div>
      <div class="card">
        <div class="controls">
          <div>
            <label for="plaats">Plaats</label>
            <select id="plaats"><option value="all">Alles</option></select>
          </div>
          <div>
            <label for="prio">Prioriteit</label>
            <select id="prio">
              <option value="all">Alles</option>
              <option value="1">Prioriteit 1</option>
              <option value="2">Prioriteit 2</option>
              <option value="3">Prioriteit 3</option>
            </select>
          </div>
          <div class="full">
            <label for="zoek">Zoeken</label>
            <input id="zoek" placeholder="Bijv. makelaar, corporatie, 2 kamers">
          </div>
        </div>
        <div class="action-row">
          <button id="openBest">Open beste links</button>
          <button class="secondary" id="showFavs">Alleen favorieten</button>
          <button class="ghost" id="showAll">Toon alles</button>
        </div>
        <div class="list" id="list" style="margin-top:14px"></div>
      </div>
    </div>

    <div id="favorieten" class="panel section">
      <div class="section-head"><h2>Favorieten</h2><span class="subtle">bewaard lokaal</span></div>
      <div class="card"><div class="list" id="favList"></div></div>
    </div>

    <div id="familie" class="panel section">
      <div class="section-head"><h2>Familie</h2><span class="subtle">delen</span></div>
      <div class="card">
        <h3 style="margin-top:0">Bericht om door te sturen</h3>
        <textarea id="familyText">Hoi! Zou je met me mee willen kijken naar een huurwoning?

Ik zoek in Beverwijk / Heemskerk en omgeving.
Belangrijk:
- maximaal €__MAX_HUUR__ huur
- liefst 2 of 3 kamers
- kindvriendelijke buurt

Als je iets ziet, stuur me dan meteen de link door. Dank je wel!</textarea>
        <div class="action-row">
          <button id="copyFamilyText">Kopieer bericht</button>
          <button class="secondary" id="sharePage">Deel app</button>
        </div>
      </div>
    </div>

    <div id="prioriteiten" class="panel section">
      <div class="section-head"><h2>Prioriteiten</h2><span class="subtle">betekenis</span></div>
      <div class="priority-guide">
        <div class="box prio1"><strong>Prioriteit 1</strong><br>Belangrijkste websites en sterkste zoekroutes.</div>
        <div class="box prio2"><strong>Prioriteit 2</strong><br>Regio-uitbreiding en extra kansrijke routes.</div>
        <div class="box prio3"><strong>Prioriteit 3</strong><br>Makelaars, portals, corporaties en aanvullende bronnen.</div>
      </div>
      <div class="footer-note">Overzicht van woningbronnen voor sneller zoeken.</div>
    </div>
  </div>

  <div class="bottom-nav">
    <button class="navbtn active" data-tab="dashboard"><span class="icon">⌂</span><span>Radar</span></button>
    <button class="navbtn" data-tab="zoeken"><span class="icon">⌕</span><span>Zoeken</span></button>
    <button class="navbtn" data-tab="favorieten"><span class="icon">★</span><span>Opslaan</span></button>
    <button class="navbtn" data-tab="familie"><span class="icon">⇪</span><span>Familie</span></button>
    <button class="navbtn" data-tab="prioriteiten"><span class="icon">◎</span><span>Info</span></button>
  </div>
</div>

<script>
const data = __DATA_JSON__;
const favKey = "woningzoeker_v4_favs_v1";
const seenKey = "woningzoeker_v4_seen_v1";
const getFavs = () => JSON.parse(localStorage.getItem(favKey) || "[]");
const setFavs = (favs) => localStorage.setItem(favKey, JSON.stringify(favs));
const getSeen = () => JSON.parse(localStorage.getItem(seenKey) || "[]");
const setSeen = (seen) => localStorage.setItem(seenKey, JSON.stringify(seen));

let onlyFavs = false;
const list = document.getElementById("list");
const favList = document.getElementById("favList");
const todayList = document.getElementById("todayList");

function populatePlaces() {
  const select = document.getElementById("plaats");
  [...new Set(data.map(x => x.plaats))].sort().forEach(place => {
    const opt = document.createElement("option");
    opt.value = place;
    opt.textContent = place;
    select.appendChild(opt);
  });
}

function isNew(item) { return !getSeen().includes(item.url); }

function score(item) {
  let s = 0;
  if (item.prioriteit === 1) s += 55;
  if (item.prioriteit === 2) s += 25;
  if (item.prioriteit === 3) s += 10;
  if (["Beverwijk", "Heemskerk"].includes(item.plaats)) s += 20;
  if ((item.focus || "").includes("2 kamers")) s += 10;
  if (item.bron === "Funda" || item.bron === "Pararius") s += 10;
  return Math.min(100, s);
}

function itemHtml(item, isFav) {
  const sc = score(item);
  const newBadge = isNew(item) ? '<span class="badge-new">Nieuw</span>' : '<span>Gezien</span>';
  return `
    <div class="item priority${item.prioriteit}">
      <h3>${item.bron} — ${item.plaats}</h3>
      <div class="meta">
        <span>Prioriteit ${item.prioriteit}</span>
        <span>${item.focus}</span>
        ${newBadge}
      </div>
      <div class="subtle">Matchscore ${sc}/100</div>
      <div class="scorebar"><div style="width:${sc}%"></div></div>
      <div class="action-row">
        <a class="linkbtn" href="${item.url}" target="_blank" rel="noopener">Open link</a>
        <button class="secondary" data-fav="${item.url}">${isFav ? "Verwijder favoriet" : "Bewaar favoriet"}</button>
        <button class="ghost" data-seen="${item.url}">${isNew(item) ? "Markeer als gezien" : "Al gezien"}</button>
      </div>
    </div>
  `;
}

function bindButtons(root) {
  root.querySelectorAll("[data-fav]").forEach(btn => btn.onclick = () => toggleFav(btn.dataset.fav));
  root.querySelectorAll("[data-seen]").forEach(btn => btn.onclick = () => markSeen(btn.dataset.seen));
}

function filteredItems() {
  const plaats = document.getElementById("plaats").value;
  const prio = document.getElementById("prio").value;
  const zoek = document.getElementById("zoek").value.toLowerCase().trim();
  const favs = getFavs();

  return data.filter(item => {
    if (plaats !== "all" && item.plaats !== plaats) return false;
    if (prio !== "all" && String(item.prioriteit) !== prio) return false;
    if (zoek && !(`${item.bron} ${item.focus} ${item.plaats}`.toLowerCase().includes(zoek))) return false;
    if (onlyFavs && !favs.includes(item.url)) return false;
    return true;
  }).sort((a, b) => score(b) - score(a));
}

function renderList() {
  const items = filteredItems();
  const favs = getFavs();
  list.innerHTML = items.length ? "" : '<div class="empty">Geen resultaten met deze filters.</div>';
  items.forEach(item => list.insertAdjacentHTML("beforeend", itemHtml(item, favs.includes(item.url))));
  bindButtons(list);
}

function renderFavs() {
  const favs = getFavs();
  const items = data.filter(item => favs.includes(item.url)).sort((a, b) => score(b) - score(a));
  favList.innerHTML = items.length ? "" : '<div class="empty">Nog geen favorieten opgeslagen.</div>';
  items.forEach(item => favList.insertAdjacentHTML("beforeend", itemHtml(item, true)));
  bindButtons(favList);
}

function renderToday() {
  const favs = getFavs();
  const items = data.filter(item => isNew(item)).sort((a, b) => score(b) - score(a)).slice(0, 20);
  todayList.innerHTML = items.length ? "" : '<div class="empty">Geen nieuwe items. Alles is al gezien.</div>';
  items.forEach(item => todayList.insertAdjacentHTML("beforeend", itemHtml(item, favs.includes(item.url))));
  bindButtons(todayList);
}

function renderStats() {
  document.getElementById("totalCount").textContent = data.length;
  document.getElementById("newCount").textContent = data.filter(isNew).length;
}

function toggleFav(url) {
  let favs = getFavs();
  if (favs.includes(url)) favs = favs.filter(x => x !== url);
  else favs.push(url);
  setFavs(favs);
  renderAll();
}

function markSeen(url) {
  let seen = getSeen();
  if (!seen.includes(url)) seen.push(url);
  setSeen(seen);
  renderAll();
}

function markAllSeen() { setSeen(data.map(x => x.url)); renderAll(); }
function resetRadar() { localStorage.removeItem(seenKey); renderAll(); }

function renderAll() {
  renderList();
  renderFavs();
  renderToday();
  renderStats();
}

function switchTab(tab) {
  document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".navbtn").forEach(b => b.classList.remove("active"));
  document.getElementById(tab).classList.add("active");
  document.querySelectorAll(`.navbtn[data-tab="${tab}"]`).forEach(b => b.classList.add("active"));
  window.scrollTo({top:0, behavior:"smooth"});
}

document.querySelectorAll(".navbtn").forEach(btn => btn.onclick = () => switchTab(btn.dataset.tab));
document.getElementById("plaats").onchange = renderList;
document.getElementById("prio").onchange = renderList;
document.getElementById("zoek").oninput = renderList;
document.getElementById("showFavs").onclick = () => { onlyFavs = true; renderList(); };
document.getElementById("showAll").onclick = () => { onlyFavs = false; renderList(); };
document.getElementById("openBest").onclick = () => {
  data.filter(x => x.prioriteit === 1).sort((a, b) => score(b) - score(a)).slice(0, 12).forEach((item, i) => setTimeout(() => window.open(item.url, "_blank"), i * 220));
};
document.getElementById("markAllSeen").onclick = markAllSeen;
document.getElementById("resetRadar").onclick = resetRadar;

const familyTextEl = document.getElementById("familyText");
async function copyText(text, msg) {
  try { await navigator.clipboard.writeText(text); alert(msg); }
  catch (e) { alert("Kopiëren lukte niet automatisch."); }
}
document.getElementById("copyFamilyText").onclick = () => copyText(familyTextEl.value, "Bericht gekopieerd.");
document.getElementById("sharePage").onclick = async () => {
  const shareData = { title: "Woningzoeker Frank Burrei", text: "Check deze woningzoek-app", url: location.href };
  if (navigator.share) { try { await navigator.share(shareData); } catch (e) {} }
  else { copyText(location.href, "Link gekopieerd."); }
};

populatePlaces();
renderAll();
</script>
</body>
</html>"""

    return (template
        .replace("__APP_TITLE__", APP_TITLE)
        .replace("__MAX_HUUR__", str(MAX_HUUR))
        .replace("__GENERATED_AT__", generated_at)
        .replace("__COUNT__", str(len(json.loads(data_json))))
        .replace("__DATA_JSON__", data_json))

def build_app():
    data = build_data()
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    html = html_template(json.dumps(data, ensure_ascii=False), generated_at)
    out = Path("index.html")
    out.write_text(html, encoding="utf-8")
    print(f"Gegenereerd: {out}")
    print(f"Aantal woningbronnen: {len(data)}")

if __name__ == "__main__":
    build_app()
