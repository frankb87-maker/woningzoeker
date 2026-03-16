import json
import re
import hashlib
from pathlib import Path
from datetime import datetime
from urllib.parse import quote_plus
import requests

# —————————————————————————

# Configuratie

# —————————————————————————

APP_TITLE = “Woningzoeker Frank Burrei”
VERSION   = “AI-radar v6.1”
MAX_HUUR  = 1600

CORE_PLACES = [“Beverwijk”, “Heemskerk”]
REGION_PLACES = [
“Uitgeest”, “Castricum”, “Assendelft”, “Velsen-Noord”, “Wijk aan Zee”,
“Zaandam”, “Driehuis”, “Santpoort-Noord”, “Velserbroek”, “Bakkum”,
“Heiloo”, “Limmen”, “Akersloot”, “Wormerveer”, “Krommenie”,
“Haarlem-Noord”, “IJmuiden”, “Heemstede”, “Bloemendaal”,
]

# —————————————————————————

# Directe bronnen — uitsluitend voor Radar

# Geen Google hier; Google is voorbehouden aan de Zoeken-tab.

# —————————————————————————

RADAR_SOURCES = [
# Grote landelijke platforms
{“name”: “Funda”,          “type”: “funda”,          “priority”: 1},
{“name”: “Pararius”,       “type”: “pararius”,        “priority”: 1},
{“name”: “Jaap”,           “type”: “jaap”,            “priority”: 1},
{“name”: “Huislijn”,       “type”: “huislijn”,        “priority”: 2},
{“name”: “Huurwoningen.nl”,“type”: “huurwoningen_nl”, “priority”: 2},
# Grote verhuurders met directe website
{“name”: “Vesteda”,        “type”: “vesteda”,         “priority”: 2},
{“name”: “Heimstaden”,     “type”: “heimstaden”,      “priority”: 2},
{“name”: “Holland2Stay”,   “type”: “holland2stay”,    “priority”: 3},
# Corporaties met directe website
{“name”: “Woonopmaat”,     “type”: “woonopmaat”,      “priority”: 2},
{“name”: “Kennemer Wonen”, “type”: “kennemerwonen”,   “priority”: 2},
{“name”: “Pré Wonen”,      “type”: “prewonen”,        “priority”: 2},
{“name”: “WoningNet”,      “type”: “woningnet”,       “priority”: 2},
{“name”: “Woonwaard”,      “type”: “woonwaard”,       “priority”: 3},
{“name”: “ZVH”,            “type”: “zvh”,             “priority”: 2},
]

# —————————————————————————

# Google-zoekopdrachten — uitsluitend voor de Zoeken-tab

# —————————————————————————

GOOGLE_QUERIES = [
{“name”: “Google 2 kamers”,       “priority”: 1, “focus”: “2 kamers”,
“query”: “2 kamer appartement huur {place} max {max_huur}”},
{“name”: “Google 3 kamers”,       “priority”: 2, “focus”: “3 kamers”,
“query”: “3 kamer appartement huur {place} max {max_huur}”},
{“name”: “Google kindvriendelijk”,“priority”: 2, “focus”: “kindvriendelijk”,
“query”: “kindvriendelijke huurwoning {place} max {max_huur}”},
{“name”: “Google gezinswoning”,   “priority”: 2, “focus”: “gezinswoning”,
“query”: “gezinswoning huur {place} max {max_huur}”},
]

GOOGLE_PORTALS = [
“Huurwoningen.nl”, “Huurstunt”, “Direct Wonen”, “Kamernet”,
“NederWoon”, “RentSlam”, “123Wonen”, “Rentola”, “Rentbird”,
]

GOOGLE_LANDLORDS = [
“Vesteda”, “MVGM”, “Rotsvast”, “Heimstaden”, “Holland2Stay”,
“Interhouse”, “HouseHunting”, “REBO”, “Altera”, “Bouwinvest”,
]

GOOGLE_CORPORATIONS = [
“Woonopmaat”, “Pré Wonen”, “Rochdale”, “Elan Wonen”, “WoningNet”,
“Eigen Haard”, “Ymere”, “Parteon”, “ZVH”, “Intermaris”,
“Kennemer Wonen”, “Woonzorg Nederland”, “Woonwaard”,
“de Alliantie”, “Stadgenoot”,
]

GOOGLE_AGENCIES = [
“Brantjes makelaars”, “Van Gulik makelaars”, “Teer makelaars”,
“Bert van Vulpen”, “Saen Garantiemakelaars”, “EV Wonen”,
“Kuijs Reinder Kakes”, “Hopman ERA”, “IJmond Makelaars”,
“Van Duin”, “PMA makelaars”,
]

# —————————————————————————

# Signaaldetectie helpers

# —————————————————————————

NOISE_TERMS = [
“just a moment”, “enable javascript”, “cookies to continue”,
“wat is mijn woning waard”, “veelgestelde vragen”,
“vind je verkoopmakelaar”, “nvm makelaar”, “koop jouw eerste huis”,
“cookie”, “privacy”, “voorwaarden”, “help”, “inloggen”,
“account aanmaken”, “contact opnemen”, “desk”,
“please click here”, “if you are not redirected”,
“google offered in”, “search the world”,
]

LISTING_TERMS = [
“huur”, “huurwoning”, “appartement”, “woning”, “studio”, “kamer”,
“slaapkamer”, “beschikbaar”, “per maand”, “woonoppervlakte”,
“m²”, “m2”, “te huur”, “direct beschikbaar”,
]

ADDRESS_HINTS = [
“straat”, “laan”, “weg”, “plein”, “hof”, “plantsoen”, “kade”, “gracht”,
]

# —————————————————————————

# URL-builders

# —————————————————————————

def google_url(query: str) -> str:
return “https://www.google.com/search?q=” + quote_plus(query)

def direct_url(source_type: str, place: str) -> str:
“”“Geeft een directe, werkende zoek-URL terug voor het opgegeven brontype en de opgegeven plaats.”””
p = place.lower().replace(” “, “-”)
p_enc = quote_plus(place.lower())

```
urls = {
    # Funda: werkt met slug in URL
    "funda":
        f"https://www.funda.nl/zoeken/huur?selected_area=%5B%22{p_enc}%22%5D&price=%22-{MAX_HUUR}%22",

    # Pararius: /{stad}/0-{max} — gebruik hyphenated slug
    "pararius":
        f"https://www.pararius.nl/huurwoningen/{p}/0-{MAX_HUUR}",

    # Jaap: directe huurzoekpagina per plaats
    "jaap":
        f"https://www.jaap.nl/huurhuizen/{p}",

    # Huislijn
    "huislijn":
        f"https://www.huislijn.nl/huurwoning/{p}",

    # Huurwoningen.nl — plaatspagina
    "huurwoningen_nl":
        f"https://www.huurwoningen.nl/in/{p}/",

    # Verhuurders — directe aanbodpagina's (geen plaatsfilter beschikbaar; zoek op regio)
    "vesteda":
        "https://www.vesteda.com/nl/woningaanbod/zoeken/?huurprijsmax=1600",
    "heimstaden":
        "https://www.heimstaden.com/nl/homes/",
    "holland2stay":
        "https://holland2stay.com/residences",

    # Corporaties — directe aanbodpagina's
    "woonopmaat":
        "https://www.woonopmaat.nl/woningaanbod/",
    "kennemerwonen":
        "https://www.kennemerwonen.nl/aanbod/",
    "prewonen":
        "https://www.prewonen.nl/woningaanbod/",
    "woningnet":
        "https://www.woningnet.nl/",
    "woonwaard":
        "https://www.woonwaard.nl/woningaanbod/",
    "zvh":
        "https://www.zvh.nl/aanbod/",
}

if source_type not in urls:
    raise ValueError(f"Onbekend brontype: {source_type}")
return urls[source_type]
```

# —————————————————————————

# Data-opbouw

# —————————————————————————

def add_row(rows, seen, bron, plaats, prioriteit, focus, url, tab=“both”):
key = (bron, plaats, url)
if key not in seen:
seen.add(key)
rows.append({
“bron”:      bron,
“plaats”:    plaats,
“prioriteit”: prioriteit,
“focus”:     focus,
“url”:       url,
“tab”:       tab,   # “radar” | “zoeken” | “both”
})

def build_data():
rows = []
seen = set()

```
# ---- Kerngemeenten ----
for place in CORE_PLACES:

    # Directe bronnen → Radar (en ook zichtbaar in Zoeken)
    for src in RADAR_SOURCES:
        add_row(rows, seen, src["name"], place, src["priority"],
                "huurwoningen", direct_url(src["type"], place), tab="radar")

    # Google-queries → alleen Zoeken
    for src in GOOGLE_QUERIES:
        add_row(rows, seen, src["name"], place, src["priority"], src["focus"],
                google_url(src["query"].format(place=place, max_huur=MAX_HUUR)), tab="zoeken")

    for name in GOOGLE_PORTALS:
        add_row(rows, seen, f"Google {name}", place, 3, "portal",
                google_url(f"{name} {place} huur"), tab="zoeken")
    for name in GOOGLE_LANDLORDS:
        add_row(rows, seen, f"Google {name}", place, 3, "verhuurder",
                google_url(f"{name} huurwoning {place}"), tab="zoeken")
    for name in GOOGLE_CORPORATIONS:
        add_row(rows, seen, f"Google {name}", place, 3, "corporatie",
                google_url(f"{name} huur {place}"), tab="zoeken")
    for name in GOOGLE_AGENCIES:
        add_row(rows, seen, f"Google {name}", place, 3, "makelaar",
                google_url(f"{name} huur {place}"), tab="zoeken")

# ---- Regiogemeenten ----
for place in REGION_PLACES:

    # Directe bronnen → Radar
    for src in RADAR_SOURCES:
        add_row(rows, seen, src["name"], place,
                max(2, src["priority"]), "regio-uitbreiding",
                direct_url(src["type"], place), tab="radar")

    # Google-queries → alleen Zoeken
    for src in GOOGLE_QUERIES:
        add_row(rows, seen, src["name"], place, max(2, src["priority"]), src["focus"],
                google_url(src["query"].format(place=place, max_huur=MAX_HUUR)), tab="zoeken")
    for name in GOOGLE_PORTALS[:5]:
        add_row(rows, seen, f"Google {name}", place, 3, "portal",
                google_url(f"{name} {place} huur"), tab="zoeken")
    for name in GOOGLE_AGENCIES[:5]:
        add_row(rows, seen, f"Google {name}", place, 3, "makelaar",
                google_url(f"{name} huur {place}"), tab="zoeken")

return rows
```

# —————————————————————————

# Signaaldetectie

# —————————————————————————

def load_json(path: Path, default):
if path.exists():
try:
return json.loads(path.read_text(encoding=“utf-8”))
except Exception:
return default
return default

def clean_html_text(html: str) -> str:
html = re.sub(r”<script.*?</script>”, “ “, html, flags=re.S | re.I)
html = re.sub(r”<style.*?</style>”,  “ “, html, flags=re.S | re.I)
html = re.sub(r”<[^>]+>”, “ “, html)
return re.sub(r”\s+”, “ “, html).strip()

def extract_title(html: str) -> str:
m = re.search(r”<title>(.*?)</title>”, html, flags=re.I | re.S)
if m:
return re.sub(r”\s+”, “ “, m.group(1)).strip()[:180]
return “”

def extract_signals(text: str, patterns: list) -> list:
found = []
for p in patterns:
found += re.findall(p, text, flags=re.I)
return list(dict.fromkeys(found))[:8]

def count_terms(text: str, terms: list) -> int:
lower = text.lower()
return sum(1 for t in terms if t in lower)

def extract_snippet(text: str) -> str:
m = re.search(
r”(.{0,80}(?:€\s?\d{3,5}|\d{2,3}\s?m²|\d+\s?kamer[s]?|huurwoning|appartement|te huur).{0,180})”,
text, flags=re.I,
)
return re.sub(r”\s+”, “ “, m.group(1)).strip()[:240] if m else “”

def fingerprint(title: str, text: str, prices: list, surfaces: list, rooms: list) -> str:
blob = “ | “.join([title[:180],
“ “.join(prices[:8]), “ “.join(surfaces[:8]),
“ “.join(rooms[:8]), text[:4000]])
return hashlib.sha256(blob.encode(“utf-8”, errors=“ignore”)).hexdigest()

def is_google_noise(text: str, title: str) -> bool:
blob = f”{title} {text}”.lower()
patterns = [
“google search”, “please click here”, “if you are not redirected”,
“images maps videos”, “news books”, “search the world’s information”,
“google offered in”, “redirected within a few seconds”,
]
return any(p in blob for p in patterns)

def signal_score(row: dict, title: str, text: str) -> dict:
prices   = extract_signals(text, [r”€\s?\d{3,5}”, r”eur\s?\d{3,5}”, r”\d{3,5}\s?euro”])
surfaces = extract_signals(text, [r”\d{2,3}\s?m²”, r”\d{2,3}\s?m2”])
rooms    = extract_signals(text, [r”\b\d+\s?kamer[s]?\b”, r”\b\d+\s?slaapkamer[s]?\b”])
noise_n  = count_terms(text, NOISE_TERMS)
list_n   = count_terms(text, LISTING_TERMS)
snippet  = extract_snippet(text)
google_n = is_google_noise(text, title)
lower    = text.lower()

```
score   = 0
reasons = []

if row["prioriteit"] == 1:   score += 22; reasons.append("prioriteit 1")
elif row["prioriteit"] == 2: score += 10; reasons.append("prioriteit 2")

if row["tab"] == "radar":    score += 20; reasons.append("directe bron")
if prices:                   score += 24; reasons.append("prijs gevonden")
if surfaces:                 score += 12; reasons.append("m² gevonden")
if rooms:                    score += 14; reasons.append("kamers gevonden")
if list_n >= 3:              score += 12; reasons.append("woning-taal")
if row["plaats"].lower() in lower: score += 6; reasons.append("plaats gevonden")
if snippet:                  score +=  8; reasons.append("listing-snippet")
if "huur" in lower and prices: score += 8; reasons.append("huur + prijs")
if prices and rooms and surfaces: score += 16; reasons.append("volledig profiel")
if any(h in lower for h in ADDRESS_HINTS): score += 6; reasons.append("adrespatroon")

if noise_n >= 1: score -= 18
if noise_n >= 2: score -= 18
if "enable javascript" in lower or "just a moment" in lower: score -= 35
if google_n:     score -= 70

score = max(0, min(score, 100))

if score >= 70:  label = "Waarschijnlijk nieuwe woning"
elif score >= 45: label = "Mogelijk nieuw aanbod"
else:            label = "Algemene update"

return {
    "score":       score,
    "label":       label,
    "reasons":     reasons[:4],
    "signals":     (prices + surfaces + rooms)[:5],
    "snippet":     snippet,
    "noise_count": noise_n,
    "google_noise": google_n,
}
```

def detect_changes(rows: list) -> list:
state_path = Path(“radar_state.json”)
prev       = load_json(state_path, {})
new_state  = {}
detections = []

```
headers    = {"User-Agent": "Mozilla/5.0"}
# Controleer alleen directe (Radar-)bronnen met prioriteit ≤ 2
candidates = [r for r in rows if r["tab"] == "radar" and r["prioriteit"] <= 2][:60]

for row in candidates:
    item_id = f'{row["bron"]}|{row["plaats"]}|{row["url"]}'
    status  = "ok"
    title   = ""
    text    = ""
    digest  = ""
    ai      = {"score": 0, "label": "Algemene update", "reasons": [],
               "signals": [], "snippet": "", "noise_count": 0, "google_noise": False}

    try:
        resp   = requests.get(row["url"], headers=headers, timeout=20, allow_redirects=True)
        status = str(resp.status_code)
        html   = resp.text[:150_000]
        title  = extract_title(html)
        text   = clean_html_text(html)[:25_000]
        prices   = extract_signals(text, [r"€\s?\d{3,5}", r"eur\s?\d{3,5}"])
        surfaces = extract_signals(text, [r"\d{2,3}\s?m²", r"\d{2,3}\s?m2"])
        rooms    = extract_signals(text, [r"\b\d+\s?kamer[s]?\b"])
        digest = fingerprint(title, text, prices, surfaces, rooms)
        ai     = signal_score(row, title, text)
    except Exception as e:
        status = "error"
        digest = hashlib.sha256(str(e).encode()).hexdigest()

    new_state[item_id] = {
        "digest":     digest,
        "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status":     status,
        "title":      title,
        **{k: row[k] for k in ("bron", "plaats", "url", "prioriteit", "focus")},
        "ai":         ai,
    }

    old = prev.get(item_id)
    change_type = None
    if not old:
        change_type = "nieuw gevolgd"
    elif old.get("digest") != digest:
        change_type = "pagina gewijzigd"

    if change_type:
        detections.append({
            "type":        change_type,
            "bron":        row["bron"],
            "plaats":      row["plaats"],
            "prioriteit":  row["prioriteit"],
            "focus":       row["focus"],
            "url":         row["url"],
            "status":      status,
            "title":       title or old.get("title", "") if old else title,
            "ai_score":    ai["score"],
            "ai_label":    ai["label"],
            "ai_reasons":  ai["reasons"],
            "signals":     ai["signals"],
            "snippet":     ai["snippet"],
            "noise_count": ai["noise_count"],
            "google_noise": ai["google_noise"],
        })

detections.sort(key=lambda x: x.get("ai_score", 0), reverse=True)

state_path.write_text(json.dumps(new_state, ensure_ascii=False, indent=2), encoding="utf-8")
Path("radar_feed.json").write_text(json.dumps(detections, ensure_ascii=False, indent=2), encoding="utf-8")
return detections
```

# —————————————————————————

# HTML-template

# —————————————————————————

def html_template(data_json: str, detections_json: str, generated_at: str) -> str:
row_count       = len(json.loads(data_json))
detection_count = len(json.loads(detections_json))

```
return f"""<!DOCTYPE html>
```

<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{APP_TITLE}</title>
<meta name="theme-color" content="#0f172a">
<style>
:root{{
  --bg:#f4f7fb;--shell:#fff;--card:#fff;--line:#e2e8f0;--text:#0f172a;--muted:#64748b;
  --brand:#0f172a;--blue:#2563eb;--shadow:0 10px 30px rgba(15,23,42,.08);
  --sh-bg:#ecfdf5;--sh-ln:#a7f3d0;--sh-tx:#065f46;
  --sm-bg:#fffbeb;--sm-ln:#fde68a;--sm-tx:#92400e;
  --sl-bg:#f8fafc;--sl-ln:#cbd5e1;--sl-tx:#334155;
}}
*{{box-sizing:border-box}}html,body{{margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;
  background:linear-gradient(180deg,#f8fafc 0%,#eef3f9 100%);color:var(--text)}}
.app-shell{{max-width:440px;margin:0 auto;min-height:100vh;background:var(--shell);
  position:relative;box-shadow:0 0 0 1px rgba(148,163,184,.08)}}
.safe{{padding:18px 16px 104px}}
.hero{{background:linear-gradient(135deg,#0f172a 0%,#1e293b 52%,#2563eb 100%);
  color:#fff;border-radius:28px;padding:24px 18px 18px;box-shadow:var(--shadow)}}
.hero h1{{margin:0 0 10px;font-size:26px;line-height:1.04;letter-spacing:-.02em}}
.hero p{{margin:0;font-size:14px;line-height:1.5;color:rgba(255,255,255,.92)}}
.hero-meta{{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}}
.hero-meta span{{background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.16);
  color:#fff;padding:8px 10px;border-radius:999px;font-size:12px}}
.grid-top{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:16px}}
.stat{{background:rgba(255,255,255,.96);color:var(--text);border-radius:18px;
  padding:14px 12px;min-height:82px}}
.stat strong{{display:block;font-size:23px;line-height:1.1;margin-bottom:6px}}
.stat span{{font-size:12px;color:var(--muted)}}
.section{{margin-top:18px}}
.section-head{{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}}
.section-head h2{{margin:0;font-size:22px;letter-spacing:-.02em}}
.section-head .subtle{{color:var(--muted);font-size:13px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:22px;
  padding:14px;box-shadow:0 8px 24px rgba(15,23,42,.04)}}
.notice{{background:#f8fafc;border:1px solid #dbe4ef;color:#334155;
  border-radius:18px;padding:12px;font-size:13px;line-height:1.5}}
.controls{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
.controls .full{{grid-column:1/-1}}
label{{display:block;font-size:12px;color:var(--muted);margin-bottom:6px}}
input,select,textarea{{width:100%;border:1px solid var(--line);border-radius:14px;
  padding:12px;font-size:15px;background:#fff;color:var(--text)}}
textarea{{min-height:150px;resize:vertical}}
.action-row{{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}}
button,.linkbtn{{border:none;appearance:none;background:var(--brand);color:#fff;
  border-radius:14px;padding:11px 13px;font-size:14px;text-decoration:none;
  cursor:pointer;display:inline-flex;align-items:center;justify-content:center}}
button.secondary,.linkbtn.secondary{{background:#eff6ff;color:#1d4ed8}}
button.ghost{{background:#fff;color:var(--text);border:1px solid var(--line)}}
.list{{display:grid;gap:12px}}
.item{{border-radius:22px;padding:14px;border:1px solid var(--line);
  background:#fff;box-shadow:0 6px 18px rgba(15,23,42,.04)}}
.item h3{{margin:0;font-size:18px;line-height:1.25;letter-spacing:-.01em}}
.meta{{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 12px}}
.meta span{{padding:6px 10px;border-radius:999px;font-size:12px;
  border:1px solid rgba(0,0,0,.04);background:#f8fafc}}
.p1{{background:#dcfce7}}.p2{{background:#dbeafe}}.p3{{background:#f1f5f9}}
.badge-new{{background:#dbeafe!important;color:#1d4ed8;border-color:#bfdbfe!important}}
.scorebar{{height:8px;border-radius:999px;background:#eef2f7;overflow:hidden;margin-top:8px}}
.scorebar>div{{height:100%;background:linear-gradient(90deg,#0f172a,#2563eb)}}
.panel{{display:none}}.panel.active{{display:block}}
.bottom-nav{{position:fixed;left:50%;transform:translateX(-50%);bottom:0;
  width:min(440px,100%);background:rgba(255,255,255,.96);backdrop-filter:blur(10px);
  border-top:1px solid var(--line);display:grid;grid-template-columns:repeat(5,1fr);
  padding:10px 8px calc(10px + env(safe-area-inset-bottom));z-index:20}}
.navbtn{{border:none;background:transparent;color:var(--muted);font-size:11px;
  display:flex;flex-direction:column;align-items:center;gap:5px;padding:6px 0;cursor:pointer}}
.navbtn .icon{{width:34px;height:34px;border-radius:12px;display:flex;
  align-items:center;justify-content:center;background:#f8fafc;font-size:17px}}
.navbtn.active{{color:#0f172a;font-weight:600}}.navbtn.active .icon{{background:#e2e8f0}}
.empty{{color:var(--muted);text-align:center;padding:18px}}
.sc{{border-radius:22px;padding:14px;border:1px solid var(--line)}}
.sc-h{{background:var(--sh-bg);border-color:var(--sh-ln);color:var(--sh-tx)}}
.sc-m{{background:var(--sm-bg);border-color:var(--sm-ln);color:var(--sm-tx)}}
.sc-l{{background:var(--sl-bg);border-color:var(--sl-ln);color:var(--sl-tx)}}
.sc-title{{margin:0 0 6px;font-size:18px;line-height:1.25}}
.sc-sub{{font-size:13px;opacity:.9;margin-bottom:10px}}
.badges{{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0 0}}
.badge{{display:inline-block;padding:6px 9px;border-radius:999px;font-size:12px;
  background:rgba(255,255,255,.7);border:1px solid rgba(0,0,0,.06)}}
.snippet{{margin-top:10px;font-size:13px;line-height:1.5;color:#334155}}
.best-grid{{display:grid;gap:12px}}
.pg{{display:grid;gap:10px}}
.pg .box{{border-radius:18px;padding:14px;line-height:1.5;border:1px solid var(--line)}}
.footer-note{{color:var(--muted);font-size:12px;text-align:center;margin-top:14px}}
.dbg{{color:#94a3b8;font-size:11px;margin-top:8px}}
</style>
</head>
<body>
<div class="app-shell">
  <div class="safe">
    <div class="hero">
      <h1>{APP_TITLE}</h1>
      <p>{VERSION} — Woningzoek-overzicht voor Beverwijk, Heemskerk en omgeving.
         De Radar gebruikt uitsluitend directe woningwebsites.
         Google-zoekopdrachten staan in de Zoeken-tab.</p>
      <div class="hero-meta">
        <span>{row_count} bronnen</span>
        <span>Update: {generated_at}</span>
        <span>{detection_count} signalen</span>
      </div>
      <div class="grid-top">
        <div class="stat"><strong id="totalCount">0</strong><span>bronnen</span></div>
        <div class="stat"><strong id="signalCount">0</strong><span>signalen</span></div>
        <div class="stat"><strong id="highCount">0</strong><span>sterk</span></div>
        <div class="stat"><strong id="unseenCount">0</strong><span>te bekijken</span></div>
      </div>
    </div>

```
<!-- ===== RADAR ===== -->
<div id="dashboard" class="panel section">
  <div class="section-head"><h2>Radar</h2><span class="subtle">directe bronnen</span></div>
  <div class="card">
    <div class="notice">
      De Radar controleert uitsluitend directe woningwebsites: Funda, Pararius, Jaap,
      Huislijn, Huurwoningen.nl, Vesteda, Heimstaden, corporaties en meer.
      Google wordt hier niet gebruikt.
    </div>
    <div class="action-row">
      <button id="markAllSeen">Alles gezien</button>
      <button class="ghost" id="resetRadar">Reset radar</button>
    </div>
    <div class="section-head" style="margin-top:16px">
      <h2 style="font-size:17px">Beste signalen</h2>
    </div>
    <div class="best-grid" id="bestList"></div>
    <div class="section-head" style="margin-top:16px">
      <h2 style="font-size:17px">Alle updates</h2>
    </div>
    <div class="list" id="detectionList"></div>
  </div>
</div>

<!-- ===== ZOEKEN ===== -->
<div id="zoeken" class="panel active section">
  <div class="section-head"><h2>Zoeken</h2><span class="subtle">start hier</span></div>
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
      <div>
        <label for="tabfilter">Brontype</label>
        <select id="tabfilter">
          <option value="all">Alles</option>
          <option value="radar">Directe bronnen</option>
          <option value="zoeken">Google-zoekopdrachten</option>
        </select>
      </div>
      <div>
        <label for="zoek">Zoeken</label>
        <input id="zoek" placeholder="Bijv. Funda, corporatie, 2 kamers">
      </div>
    </div>
    <div class="action-row">
      <button id="openBest">Open top-links</button>
      <button class="secondary" id="showFavs">Alleen favorieten</button>
      <button class="ghost" id="showAll">Toon alles</button>
    </div>
    <div class="list" id="list" style="margin-top:14px"></div>
  </div>
</div>

<!-- ===== FAVORIETEN ===== -->
<div id="favorieten" class="panel section">
  <div class="section-head"><h2>Favorieten</h2><span class="subtle">bewaard lokaal</span></div>
  <div class="card"><div class="list" id="favList"></div></div>
</div>

<!-- ===== FAMILIE ===== -->
<div id="familie" class="panel section">
  <div class="section-head"><h2>Familie</h2><span class="subtle">delen</span></div>
  <div class="card">
    <h3 style="margin-top:0">Bericht doorsturen</h3>
    <textarea id="familyText">Hoi! Zou je met me mee willen kijken naar een huurwoning?
```

Ik zoek in Beverwijk / Heemskerk en omgeving.
Belangrijk:

- maximaal €{MAX_HUUR} per maand
- liefst 2 of 3 kamers
- kindvriendelijke buurt

Als je iets ziet, stuur me dan meteen de link door. Dank je wel!</textarea>
<div class="action-row">
<button id="copyFamilyText">Kopieer bericht</button>
<button class="secondary" id="sharePage">Deel app</button>
</div>
</div>
</div>

```
<!-- ===== INFO ===== -->
<div id="prioriteiten" class="panel section">
  <div class="section-head"><h2>Info</h2><span class="subtle">uitleg</span></div>
  <div class="pg">
    <div class="box p1"><strong>Radar-tab</strong><br>
      Controleert uitsluitend directe woningwebsites (Funda, Pararius, Jaap,
      Huislijn, Huurwoningen.nl, Vesteda, Heimstaden, corporaties).
      Geen Google.</div>
    <div class="box p2"><strong>Zoeken-tab</strong><br>
      Alle bronnen inclusief Google-zoekopdrachten voor portals, makelaars
      en corporaties. Gebruik dit als startpunt.</div>
    <div class="box p3"><strong>Prioriteit 1</strong><br>
      Funda en Pararius in Beverwijk/Heemskerk — altijd als eerste.</div>
    <div class="box p3"><strong>Prioriteit 2</strong><br>
      Overige directe bronnen en regio-uitbreidingen.</div>
    <div class="box p3"><strong>Prioriteit 3</strong><br>
      Aanvullende portals, makelaars en corporaties.</div>
  </div>
  <div class="footer-note">{VERSION} · max. €{MAX_HUUR}/mnd</div>
</div>
```

  </div>

  <div class="bottom-nav">
    <button class="navbtn" data-tab="dashboard"><span class="icon">⌂</span><span>Radar</span></button>
    <button class="navbtn active" data-tab="zoeken"><span class="icon">⌕</span><span>Zoeken</span></button>
    <button class="navbtn" data-tab="favorieten"><span class="icon">★</span><span>Opslaan</span></button>
    <button class="navbtn" data-tab="familie"><span class="icon">⇪</span><span>Familie</span></button>
    <button class="navbtn" data-tab="prioriteiten"><span class="icon">◎</span><span>Info</span></button>
  </div>
</div>

<script>
const data = {json.dumps(json.loads(data_json), ensure_ascii=False)};
const detections = {json.dumps(json.loads(detections_json), ensure_ascii=False)};
const FAV_KEY  = "woningzoeker_v6_favs";
const SEEN_KEY = "woningzoeker_v6_seen";

const getFavs = () => JSON.parse(localStorage.getItem(FAV_KEY)  || "[]");
const setFavs = v => localStorage.setItem(FAV_KEY, JSON.stringify(v));
const getSeen = () => JSON.parse(localStorage.getItem(SEEN_KEY) || "[]");
const setSeen = v => localStorage.setItem(SEEN_KEY, JSON.stringify(v));

let onlyFavs = false;

function isNew(item) {{ return !getSeen().includes(item.url); }}

function sourceScore(item) {{
  let s = [0, 55, 25, 10][item.prioriteit] || 0;
  if (["Beverwijk","Heemskerk"].includes(item.plaats)) s += 20;
  if ((item.focus||"").includes("2 kamers")) s += 10;
  if (item.tab === "radar") s += 10;
  return Math.min(100, s);
}}

function itemHtml(item, isFav) {{
  const sc = sourceScore(item);
  const tab_badge = item.tab === "radar"
    ? '<span style="background:#ecfdf5;color:#065f46">Direct</span>'
    : '<span style="background:#eff6ff;color:#1d4ed8">Google</span>';
  return `
    <div class="item p${{item.prioriteit}}">
      <h3>${{item.bron}} — ${{item.plaats}}</h3>
      <div class="meta">
        <span>P${{item.prioriteit}}</span>
        <span>${{item.focus}}</span>
        ${{tab_badge}}
        ${{isNew(item) ? '<span class="badge-new">Te bekijken</span>' : '<span>Gezien</span>'}}
      </div>
      <div style="color:var(--muted);font-size:12px">Score ${{sc}}/100</div>
      <div class="scorebar"><div style="width:${{sc}}%"></div></div>
      <div class="action-row">
        <a class="linkbtn" href="${{item.url}}" target="_blank" rel="noopener">Open</a>
        <button class="secondary" data-fav="${{item.url}}">${{isFav?"Verwijder":"Bewaar"}}</button>
        <button class="ghost" data-seen="${{item.url}}">${{isNew(item)?"Gezien":"Al gezien"}}</button>
      </div>
    </div>`;
}}

function scClass(score) {{ return score>=70?"sc-h":score>=45?"sc-m":"sc-l"; }}

function detectionHtml(item) {{
  const badges = [...(item.ai_reasons||[]),...(item.signals||[])]
    .map(x=>`<span class="badge">${{x}}</span>`).join("");
  return `
    <div class="sc ${{scClass(item.ai_score||0)}}">
      <div class="sc-title">${{item.ai_label||item.type}}</div>
      <div class="sc-sub">${{item.bron}} · ${{item.plaats}} · score ${{item.ai_score||0}}</div>
      <div class="badges">${{badges}}</div>
      ${{item.snippet?`<div class="snippet">${{item.snippet}}</div>`:""}}
      <div class="action-row">
        <a class="linkbtn" href="${{item.url}}" target="_blank" rel="noopener">Open bron</a>
      </div>
      <div class="dbg">Focus: ${{item.focus}} · P${{item.prioriteit}}</div>
    </div>`;
}}

function renderBest() {{
  const el = document.getElementById("bestList");
  const best = detections.filter(x=>(x.ai_score||0)>=45&&!x.google_noise)
    .sort((a,b)=>(b.ai_score||0)-(a.ai_score||0)).slice(0,3);
  el.innerHTML = best.length ? best.map(detectionHtml).join("") :
    '<div class="empty">Nog geen sterke signalen vandaag.</div>';
}}

function renderDetections() {{
  const el = document.getElementById("detectionList");
  const items = detections.filter(x=>(x.ai_score||0)>=20&&!x.google_noise)
    .sort((a,b)=>(b.ai_score||0)-(a.ai_score||0));
  el.innerHTML = items.length ? items.map(detectionHtml).join("") :
    '<div class="empty">Nog geen bruikbare signalen.</div>';
}}

function bindButtons(root) {{
  root.querySelectorAll("[data-fav]").forEach(b=>b.onclick=()=>toggleFav(b.dataset.fav));
  root.querySelectorAll("[data-seen]").forEach(b=>b.onclick=()=>markSeen(b.dataset.seen));
}}

function filteredItems() {{
  const plaats    = document.getElementById("plaats").value;
  const prio      = document.getElementById("prio").value;
  const tabfilter = document.getElementById("tabfilter").value;
  const zoek      = document.getElementById("zoek").value.toLowerCase().trim();
  const favs      = getFavs();
  return data.filter(item => {{
    if (plaats    !== "all" && item.plaats !== plaats) return false;
    if (prio      !== "all" && String(item.prioriteit) !== prio) return false;
    if (tabfilter !== "all" && item.tab !== tabfilter) return false;
    if (zoek && !(`${{item.bron}} ${{item.focus}} ${{item.plaats}}`).toLowerCase().includes(zoek)) return false;
    if (onlyFavs && !favs.includes(item.url)) return false;
    return true;
  }}).sort((a,b)=>sourceScore(b)-sourceScore(a));
}}

function renderList() {{
  const el    = document.getElementById("list");
  const items = filteredItems();
  const favs  = getFavs();
  el.innerHTML = items.length ? items.map(i=>itemHtml(i, favs.includes(i.url))).join("") :
    '<div class="empty">Geen resultaten.</div>';
  bindButtons(el);
}}

function renderFavs() {{
  const el   = document.getElementById("favList");
  const favs = getFavs();
  const items = data.filter(i=>favs.includes(i.url)).sort((a,b)=>sourceScore(b)-sourceScore(a));
  el.innerHTML = items.length ? items.map(i=>itemHtml(i,true)).join("") :
    '<div class="empty">Nog geen favorieten.</div>';
  bindButtons(el);
}}

function renderStats() {{
  const clean = detections.filter(x=>(x.ai_score||0)>=20&&!x.google_noise);
  document.getElementById("totalCount").textContent  = data.length;
  document.getElementById("signalCount").textContent = clean.length;
  document.getElementById("highCount").textContent   = clean.filter(x=>(x.ai_score||0)>=70).length;
  document.getElementById("unseenCount").textContent = data.filter(isNew).length;
}}

function toggleFav(url) {{
  let f = getFavs();
  f = f.includes(url) ? f.filter(x=>x!==url) : [...f, url];
  setFavs(f); renderAll();
}}

function markSeen(url) {{
  const s = getSeen(); if(!s.includes(url)) s.push(url); setSeen(s); renderAll();
}}

function renderAll() {{
  renderBest(); renderDetections(); renderList(); renderFavs(); renderStats();
}}

function switchTab(tab) {{
  document.querySelectorAll(".panel").forEach(p=>p.classList.remove("active"));
  document.querySelectorAll(".navbtn").forEach(b=>b.classList.remove("active"));
  document.getElementById(tab).classList.add("active");
  document.querySelectorAll(`.navbtn[data-tab="${{tab}}"]`).forEach(b=>b.classList.add("active"));
  window.scrollTo({{top:0,behavior:"smooth"}});
}}

function populatePlaces() {{
  const sel = document.getElementById("plaats");
  [...new Set(data.map(x=>x.plaats))].sort().forEach(p=>{{
    const o=document.createElement("option"); o.value=p; o.textContent=p; sel.appendChild(o);
  }});
}}

document.querySelectorAll(".navbtn").forEach(b=>b.onclick=()=>switchTab(b.dataset.tab));
document.getElementById("plaats").onchange    = renderList;
document.getElementById("prio").onchange      = renderList;
document.getElementById("tabfilter").onchange = renderList;
document.getElementById("zoek").oninput       = renderList;
document.getElementById("showFavs").onclick   = ()=>{{ onlyFavs=true;  renderList(); }};
document.getElementById("showAll").onclick    = ()=>{{ onlyFavs=false; renderList(); }};
document.getElementById("openBest").onclick   = ()=>{{
  data.filter(x=>x.prioriteit===1&&x.tab==="radar")
    .sort((a,b)=>sourceScore(b)-sourceScore(a)).slice(0,10)
    .forEach((item,i)=>setTimeout(()=>window.open(item.url,"_blank"), i*220));
}};
document.getElementById("markAllSeen").onclick = ()=>{{ setSeen(data.map(x=>x.url)); renderAll(); }};
document.getElementById("resetRadar").onclick  = ()=>{{ localStorage.removeItem(SEEN_KEY); renderAll(); }};

const familyTextEl = document.getElementById("familyText");
document.getElementById("copyFamilyText").onclick = async ()=>{{
  try {{ await navigator.clipboard.writeText(familyTextEl.value); alert("Gekopieerd!"); }}
  catch {{ alert("Kopiëren mislukt."); }}
}};
document.getElementById("sharePage").onclick = async ()=>{{
  const d={{title:"{APP_TITLE}",text:"Woningzoeker",url:location.href}};
  if(navigator.share){{ try{{await navigator.share(d);}}catch{{}} }}
  else {{ try{{await navigator.clipboard.writeText(location.href); alert("Link gekopieerd.");}}catch{{}} }}
}};

populatePlaces();
renderAll();
switchTab("zoeken");
</script>

</body>
</html>"""

# —————————————————————————

# Entrypoint

# —————————————————————————

def build_app():
rows       = build_data()
detections = detect_changes(rows)
generated_at = datetime.now().strftime(”%Y-%m-%d %H:%M”)

```
html = html_template(
    json.dumps(rows,       ensure_ascii=False),
    json.dumps(detections, ensure_ascii=False),
    generated_at,
)
Path("index.html").write_text(html, encoding="utf-8")

radar_rows  = [r for r in rows if r["tab"] == "radar"]
google_rows = [r for r in rows if r["tab"] == "zoeken"]
print(f"Gegenereerd : index.html  ({VERSION})")
print(f"Totaal bronnen : {len(rows)}  "
      f"(radar: {len(radar_rows)}, zoeken/Google: {len(google_rows)})")
print(f"AI-signalen    : {len(detections)}")
```

if **name** == “**main**”:
build_app()
