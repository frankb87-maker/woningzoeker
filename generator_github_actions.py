import json
import re
import hashlib
from pathlib import Path
from datetime import datetime
from urllib.parse import quote_plus
import requests

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
]

PORTALS = [
    "Huurwoningen.nl", "Huurportaal", "Huurstunt", "Direct Wonen", "Kamernet",
    "NederWoon", "RentSlam", "HousingAnywhere", "123Wonen", "kamers.nl",
    "Rentola", "Rentbird", "Jaap huur"
]

LANDLORDS = [
    "Vesteda", "MVGM", "Rotsvast", "Heimstaden", "Holland2Stay", "Interhouse",
    "HouseHunting", "REBO", "Altera", "Bouwinvest"
]

CORPORATIONS = [
    "Woonopmaat", "Pré Wonen", "Rochdale", "Elan Wonen", "WoningNet",
    "Eigen Haard", "Ymere", "Parteon", "ZVH", "Intermaris", "Kennemer Wonen",
    "Woonzorg Nederland", "Woonwaard", "de Alliantie", "Stadgenoot"
]

AGENCIES = [
    "Brantjes makelaars", "Van Gulik makelaars", "Teer makelaars", "Bert van Vulpen",
    "Saen Garantiemakelaars", "EV Wonen", "Kuijs Reinder Kakes", "Hopman ERA",
    "KRK makelaars", "IJmond Makelaars", "Van Duin", "PMA makelaars"
]

NOISE_TERMS = [
    "just a moment",
    "enable javascript",
    "cookies to continue",
    "wat is mijn woning waard",
    "veelgestelde vragen",
    "vind je verkoopmakelaar",
    "nvm makelaar",
    "makelaars funda desk",
    "koop jouw eerste huis",
    "cookie",
    "privacy",
    "voorwaarden",
    "help",
    "inloggen",
    "account aanmaken",
    "contact opnemen",
    "desk",
    "google search",
    "please click here",
    "if you are not redirected",
    "images maps videos",
    "news books",
    "search the world's information",
    "google offered in",
    "all images maps videos",
]

LISTING_TERMS = [
    "huur",
    "huurwoning",
    "appartement",
    "woning",
    "studio",
    "kamer",
    "slaapkamer",
    "beschikbaar",
    "per maand",
    "woonoppervlakte",
    "m²",
    "m2",
    "te huur",
    "direct beschikbaar",
]

ADDRESS_HINTS = [
    "straat", "laan", "weg", "plein", "hof", "plantsoen", "kade", "gracht"
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
            add_row(rows, seen, src["name"], place, max(2, src["priority"]), src["focus"], google_url(src["query"].format(place=place, max_huur=MAX_HUUR)))
        for name in PORTALS[:6]:
            add_row(rows, seen, f"Google {name}", place, 3, "portal", google_url(f"{name} {place} huur"))
        for name in AGENCIES[:6]:
            add_row(rows, seen, f"Google {name}", place, 3, "makelaar", google_url(f"{name} huur {place}"))

    return rows


def load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def clean_html_text(html: str) -> str:
    html = re.sub(r"<script.*?</script>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    html = re.sub(r"\s+", " ", html)
    return html.strip()


def extract_title(html: str) -> str:
    m = re.search(r"<title>(.*?)</title>", html, flags=re.I | re.S)
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()[:180]
    return ""


def extract_price_signals(text: str):
    patterns = [r"€\s?\d{3,5}", r"eur\s?\d{3,5}", r"\d{3,5}\s?euro"]
    found = []
    for p in patterns:
        found += re.findall(p, text, flags=re.I)
    return list(dict.fromkeys(found))[:8]


def extract_surface_signals(text: str):
    patterns = [r"\d{2,3}\s?m²", r"\d{2,3}\s?m2"]
    found = []
    for p in patterns:
        found += re.findall(p, text, flags=re.I)
    return list(dict.fromkeys(found))[:8]


def extract_room_signals(text: str):
    patterns = [r"\b\d+\s?kamer[s]?\b", r"\b\d+\s?slaapkamer[s]?\b"]
    found = []
    for p in patterns:
        found += re.findall(p, text, flags=re.I)
    return list(dict.fromkeys(found))[:8]


def count_noise_terms(text: str):
    lower = text.lower()
    return sum(1 for term in NOISE_TERMS if term in lower)


def count_listing_terms(text: str):
    lower = text.lower()
    return sum(1 for term in LISTING_TERMS if term in lower)


def has_address_hint(text: str):
    lower = text.lower()
    return any(h in lower for h in ADDRESS_HINTS)


def looks_like_google_noise(text: str, title: str, bron: str):
    blob = f"{title} {text}".lower()

    strong_patterns = [
        "google search",
        "please click here",
        "if you are not redirected",
        "images maps videos",
        "news books",
        "search the world's information",
        "google offered in",
        "all images maps videos",
    ]

    if any(p in blob for p in strong_patterns):
        return True

    if bron.lower().startswith("google") and count_noise_terms(blob) >= 2 and "€" not in blob:
        return True

    return False


def extract_listing_like_snippet(text: str):
    m = re.search(
        r"(.{0,80}(?:€\s?\d{3,5}|eur\s?\d{3,5}|\d{2,3}\s?m²|\d+\s?kamer[s]?|huurwoning|appartement|woning|te huur).{0,180})",
        text,
        flags=re.I
    )
    if m:
        snippet = re.sub(r"\s+", " ", m.group(1)).strip()
        return snippet[:240]
    return ""


def listing_signal_score(row, title: str, text: str):
    score = 0
    reasons = []

    lower = text.lower()
    title_lower = title.lower()

    prices = extract_price_signals(text)
    surfaces = extract_surface_signals(text)
    rooms = extract_room_signals(text)
    noise_count = count_noise_terms(text)
    listing_count = count_listing_terms(text)
    snippet = extract_listing_like_snippet(text)
    google_noise = looks_like_google_noise(text, title, row["bron"])

    if row["prioriteit"] == 1:
        score += 22
        reasons.append("prioriteit 1")
    elif row["prioriteit"] == 2:
        score += 10
        reasons.append("prioriteit 2")

    if row["bron"] in ["Funda", "Pararius"]:
        score += 20
        reasons.append("sterke bron")
    elif row["bron"].lower().startswith("google"):
        score -= 8

    if prices:
        score += 24
        reasons.append("prijs gevonden")

    if surfaces:
        score += 12
        reasons.append("m² gevonden")

    if rooms:
        score += 14
        reasons.append("kamers gevonden")

    if listing_count >= 3:
        score += 12
        reasons.append("woning-taal")

    if row["plaats"].lower() in lower or row["plaats"].lower() in title_lower:
        score += 6
        reasons.append("plaats gevonden")

    if snippet:
        score += 8
        reasons.append("listing-snippet")

    if "huur" in lower and prices:
        score += 8
        reasons.append("huur + prijs")

    if prices and rooms and surfaces:
        score += 16
        reasons.append("volledig profiel")

    if has_address_hint(text):
        score += 6
        reasons.append("adresachtig patroon")

    if noise_count >= 1:
        score -= 18
    if noise_count >= 2:
        score -= 18

    if "enable javascript" in lower or "just a moment" in lower:
        score -= 35

    if "wat is mijn woning waard" in lower or "veelgestelde vragen" in lower:
        score -= 30

    if google_noise:
        score -= 45

    if row["bron"].lower().startswith("google") and not prices and not rooms and not surfaces:
        score -= 20

    score = max(0, min(score, 100))

    if score >= 70:
        label = "Waarschijnlijk nieuwe woning"
    elif score >= 45:
        label = "Mogelijk nieuw aanbod"
    else:
        label = "Algemene update"

    sample_bits = []
    sample_bits.extend(prices[:2])
    sample_bits.extend(surfaces[:2])
    sample_bits.extend(rooms[:2])

    return {
        "score": score,
        "label": label,
        "reasons": reasons[:4],
        "signals": sample_bits[:5],
        "snippet": snippet,
        "noise_count": noise_count,
        "google_noise": google_noise
    }


def fingerprint_relevant_content(title: str, text: str):
    prices = extract_price_signals(text)
    surfaces = extract_surface_signals(text)
    rooms = extract_room_signals(text)
    compact = " | ".join([
        title[:180],
        " ".join(prices[:8]),
        " ".join(surfaces[:8]),
        " ".join(rooms[:8]),
        text[:4000]
    ])
    return hashlib.sha256(compact.encode("utf-8", errors="ignore")).hexdigest()


def detect_changes(rows):
    state_path = Path("radar_state.json")
    prev = load_json(state_path, {})
    new_state = {}
    detections = []

    headers = {"User-Agent": "Mozilla/5.0"}
    candidates = [r for r in rows if r["prioriteit"] <= 2][:60]

    for row in candidates:
        item_id = f'{row["bron"]}|{row["plaats"]}|{row["url"]}'
        status = "ok"
        title = ""
        text = ""
        digest = ""
        ai = {
            "score": 0,
            "label": "Algemene update",
            "reasons": [],
            "signals": [],
            "snippet": "",
            "noise_count": 0,
            "google_noise": False
        }

        try:
            resp = requests.get(row["url"], headers=headers, timeout=20, allow_redirects=True)
            status = str(resp.status_code)
            html = resp.text[:150000]
            title = extract_title(html)
            text = clean_html_text(html)[:25000]
            digest = fingerprint_relevant_content(title, text)
            ai = listing_signal_score(row, title, text)
        except Exception as e:
            status = "error"
            digest = hashlib.sha256(str(e).encode("utf-8")).hexdigest()

        new_state[item_id] = {
            "digest": digest,
            "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "status": status,
            "title": title,
            "bron": row["bron"],
            "plaats": row["plaats"],
            "url": row["url"],
            "prioriteit": row["prioriteit"],
            "focus": row["focus"],
            "ai": ai,
        }

        old = prev.get(item_id)

        if not old:
            detections.append({
                "type": "nieuw gevolgd",
                "bron": row["bron"],
                "plaats": row["plaats"],
                "prioriteit": row["prioriteit"],
                "focus": row["focus"],
                "url": row["url"],
                "status": status,
                "title": title,
                "ai_score": ai["score"],
                "ai_label": ai["label"],
                "ai_reasons": ai["reasons"],
                "signals": ai["signals"],
                "snippet": ai["snippet"],
                "noise_count": ai["noise_count"],
                "google_noise": ai["google_noise"],
            })
        elif old.get("digest") != digest:
            detections.append({
                "type": "pagina gewijzigd",
                "bron": row["bron"],
                "plaats": row["plaats"],
                "prioriteit": row["prioriteit"],
                "focus": row["focus"],
                "url": row["url"],
                "status": status,
                "title": title or old.get("title", ""),
                "ai_score": ai["score"],
                "ai_label": ai["label"],
                "ai_reasons": ai["reasons"],
                "signals": ai["signals"],
                "snippet": ai["snippet"],
                "noise_count": ai["noise_count"],
                "google_noise": ai["google_noise"],
            })

    detections.sort(key=lambda x: x.get("ai_score", 0), reverse=True)

    state_path.write_text(json.dumps(new_state, ensure_ascii=False, indent=2), encoding="utf-8")
    Path("radar_feed.json").write_text(json.dumps(detections, ensure_ascii=False, indent=2), encoding="utf-8")
    return detections


def html_template(data_json: str, detections_json: str, generated_at: str) -> str:
    template = """<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>__APP_TITLE__</title>
<meta name="theme-color" content="#0f172a">
<style>
:root{
  --bg:#f4f7fb; --shell:#ffffff; --card:#ffffff; --line:#e2e8f0; --text:#0f172a; --muted:#64748b;
  --brand:#0f172a; --blue:#2563eb; --shadow:0 10px 30px rgba(15,23,42,.08);
  --signal-high-bg:#ecfdf5; --signal-high-line:#a7f3d0; --signal-high-text:#065f46;
  --signal-mid-bg:#fffbeb; --signal-mid-line:#fde68a; --signal-mid-text:#92400e;
  --signal-low-bg:#f8fafc; --signal-low-line:#cbd5e1; --signal-low-text:#334155;
  --prio1:#dcfce7; --prio2:#dbeafe; --prio3:#f1f5f9;
}
*{box-sizing:border-box} html,body{margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;background:linear-gradient(180deg,#f8fafc 0%,#eef3f9 100%);color:var(--text)}
.app-shell{max-width:440px;margin:0 auto;min-height:100vh;background:var(--shell);position:relative;box-shadow:0 0 0 1px rgba(148,163,184,.08)}
.safe{padding:18px 16px 104px}
.hero{background:linear-gradient(135deg,#0f172a 0%, #1e293b 52%, #2563eb 100%);color:#fff;border-radius:28px;padding:24px 18px 18px;box-shadow:var(--shadow)}
.hero h1{margin:0 0 10px;font-size:26px;line-height:1.04;letter-spacing:-.02em}
.hero p{margin:0;font-size:14px;line-height:1.5;color:rgba(255,255,255,.92)}
.hero-meta{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}
.hero-meta span{background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.16);color:#fff;padding:8px 10px;border-radius:999px;font-size:12px}
.grid-top{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:16px}
.stat{background:rgba(255,255,255,.96);color:var(--text);border-radius:18px;padding:14px 12px;min-height:82px}
.stat strong{display:block;font-size:23px;line-height:1.1;margin-bottom:6px}
.stat span{font-size:12px;color:var(--muted)}
.section{margin-top:18px}
.section-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}
.section-head h2{margin:0;font-size:22px;letter-spacing:-.02em}
.section-head .subtle{color:var(--muted);font-size:13px}
.card{background:var(--card);border:1px solid var(--line);border-radius:22px;padding:14px;box-shadow:0 8px 24px rgba(15,23,42,.04)}
.notice{background:#f8fafc;border:1px solid #dbe4ef;color:#334155;border-radius:18px;padding:12px;font-size:13px;line-height:1.5}
.controls{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.controls .full{grid-column:1/-1}
label{display:block;font-size:12px;color:var(--muted);margin-bottom:6px}
input, select, textarea{width:100%;border:1px solid var(--line);border-radius:14px;padding:12px;font-size:15px;background:#fff;color:var(--text)}
textarea{min-height:150px;resize:vertical}
.action-row{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}
button, .linkbtn{border:none;appearance:none;background:var(--brand);color:#fff;border-radius:14px;padding:11px 13px;font-size:14px;text-decoration:none;cursor:pointer;display:inline-flex;align-items:center;justify-content:center}
button.secondary, .linkbtn.secondary{background:#eff6ff;color:#1d4ed8}
button.ghost{background:#fff;color:var(--text);border:1px solid var(--line)}
.list{display:grid;gap:12px}
.item{border-radius:22px;padding:14px;border:1px solid var(--line);background:#fff;box-shadow:0 6px 18px rgba(15,23,42,.04)}
.item h3{margin:0;font-size:18px;line-height:1.25;letter-spacing:-.01em}
.meta{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 12px}
.meta span{padding:6px 10px;border-radius:999px;font-size:12px;border:1px solid rgba(0,0,0,.04);background:#f8fafc}
.priority1{background:var(--prio1)} .priority2{background:var(--prio2)} .priority3{background:var(--prio3)}
.badge-new{background:#dbeafe !important;color:#1d4ed8;border-color:#bfdbfe !important}
.scorebar{height:8px;border-radius:999px;background:#eef2f7;overflow:hidden;margin-top:8px}
.scorebar > div{height:100%;background:linear-gradient(90deg,#0f172a,#2563eb)}
.panel{display:none}.panel.active{display:block}
.bottom-nav{position:fixed;left:50%;transform:translateX(-50%);bottom:0;width:min(440px,100%);background:rgba(255,255,255,.96);backdrop-filter:blur(10px);border-top:1px solid var(--line);display:grid;grid-template-columns:repeat(5,1fr);padding:10px 8px calc(10px + env(safe-area-inset-bottom));z-index:20}
.navbtn{border:none;background:transparent;color:var(--muted);font-size:11px;display:flex;flex-direction:column;align-items:center;gap:5px;padding:6px 0;cursor:pointer}
.navbtn .icon{width:34px;height:34px;border-radius:12px;display:flex;align-items:center;justify-content:center;background:#f8fafc;font-size:17px}
.navbtn.active{color:#0f172a;font-weight:600}.navbtn.active .icon{background:#e2e8f0}
.empty{color:var(--muted);text-align:center;padding:18px}
.signal-card{border-radius:22px;padding:14px;border:1px solid var(--line)}
.signal-high{background:var(--signal-high-bg);border-color:var(--signal-high-line);color:var(--signal-high-text)}
.signal-mid{background:var(--signal-mid-bg);border-color:var(--signal-mid-line);color:var(--signal-mid-text)}
.signal-low{background:var(--signal-low-bg);border-color:var(--signal-low-line);color:var(--signal-low-text)}
.signal-title{margin:0 0 6px;font-size:18px;line-height:1.25;letter-spacing:-.01em}
.signal-sub{font-size:13px;opacity:.9;margin-bottom:10px}
.badges{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0 0}
.badge{display:inline-block;padding:6px 9px;border-radius:999px;font-size:12px;background:rgba(255,255,255,.7);border:1px solid rgba(0,0,0,.06)}
.snippet{margin-top:10px;font-size:13px;line-height:1.5;color:#334155}
.best-grid{display:grid;gap:12px}
.priority-guide{display:grid;gap:10px}
.priority-guide .box{border-radius:18px;padding:14px;line-height:1.5;border:1px solid var(--line)}
.prio1{background:#ecfdf5}.prio2{background:#eff6ff}.prio3{background:#f8fafc}
.footer-note{color:var(--muted);font-size:12px;text-align:center;margin-top:14px}
.debug{color:#94a3b8;font-size:11px;margin-top:8px}
</style>
</head>
<body>
<div class="app-shell">
  <div class="safe">
    <div class="hero">
      <h1>__APP_TITLE__</h1>
      <p>Professioneel woningzoek-overzicht voor Beverwijk, Heemskerk en omgeving. Deze radar bundelt verhuurwebsites, makelaars en woningplatforms en markeert de meest kansrijke updates.</p>
      <div class="hero-meta">
        <span>__COUNT__ bronnen</span>
        <span>Laatste update: __GENERATED_AT__</span>
        <span>__DETECTION_COUNT__ signalen</span>
      </div>
      <div class="grid-top">
        <div class="stat"><strong id="totalCount">0</strong><span>bronnen</span></div>
        <div class="stat"><strong id="signalCount">0</strong><span>signalen</span></div>
        <div class="stat"><strong id="highCount">0</strong><span>sterk</span></div>
        <div class="stat"><strong id="unseenCount">0</strong><span>te bekijken</span></div>
      </div>
    </div>

    <div id="dashboard" class="panel section">
      <div class="section-head"><h2>Beste signalen vandaag</h2><span class="subtle">eerst checken</span></div>
      <div class="card">
        <div class="best-grid" id="bestList"></div>
      </div>

      <div class="section">
        <div class="section-head"><h2>Radar</h2><span class="subtle">alle updates</span></div>
        <div class="card">
          <div class="notice">De radar probeert onderscheid te maken tussen waarschijnlijk nieuwe woning, mogelijk nieuw aanbod en algemene updates. Google-ruis wordt zoveel mogelijk uitgefilterd.</div>
          <div class="action-row">
            <button id="markAllSeen">Alles gezien</button>
            <button class="ghost" id="resetRadar">Reset radar</button>
          </div>
          <div class="list" id="detectionList" style="margin-top:12px"></div>
        </div>
      </div>
    </div>

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
        <div class="box prio1"><strong>Prioriteit 1</strong><br>Belangrijkste websites en sterkste zoekroutes. Hier begin je altijd.</div>
        <div class="box prio2"><strong>Prioriteit 2</strong><br>Goede uitbreidingsroutes in de regio en aanvullende zoekkansen.</div>
        <div class="box prio3"><strong>Prioriteit 3</strong><br>Aanvullende bronnen zoals portals, makelaars en corporaties.</div>
      </div>
      <div class="footer-note">De radar rangschikt signalen automatisch op relevantie.</div>
    </div>
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
const data = __DATA_JSON__;
const detections = __DETECTIONS_JSON__;
const favKey = "woningzoeker_ai_radar_v5_favs";
const seenKey = "woningzoeker_ai_radar_v5_seen";

const getFavs = () => JSON.parse(localStorage.getItem(favKey) || "[]");
const setFavs = (favs) => localStorage.setItem(favKey, JSON.stringify(favs));
const getSeen = () => JSON.parse(localStorage.getItem(seenKey) || "[]");
const setSeen = (seen) => localStorage.setItem(seenKey, JSON.stringify(seen));

let onlyFavs = false;

const list = document.getElementById("list");
const favList = document.getElementById("favList");
const detectionList = document.getElementById("detectionList");
const bestList = document.getElementById("bestList");

function populatePlaces() {
  const select = document.getElementById("plaats");
  [...new Set(data.map(x => x.plaats))].sort().forEach(place => {
    const opt = document.createElement("option");
    opt.value = place;
    opt.textContent = place;
    select.appendChild(opt);
  });
}

function isNew(item) {
  return !getSeen().includes(item.url);
}

function sourceScore(item) {
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
  const sc = sourceScore(item);
  const newBadge = isNew(item) ? '<span class="badge-new">Te bekijken</span>' : '<span>Gezien</span>';

  return `
    <div class="item priority${item.prioriteit}">
      <h3>${item.bron} — ${item.plaats}</h3>
      <div class="meta">
        <span>Prioriteit ${item.prioriteit}</span>
        <span>${item.focus}</span>
        ${newBadge}
      </div>
      <div class="subtle">Bronscore ${sc}/100</div>
      <div class="scorebar"><div style="width:${sc}%"></div></div>
      <div class="action-row">
        <a class="linkbtn" href="${item.url}" target="_blank" rel="noopener">Open link</a>
        <button class="secondary" data-fav="${item.url}">${isFav ? "Verwijder favoriet" : "Bewaar favoriet"}</button>
        <button class="ghost" data-seen="${item.url}">${isNew(item) ? "Markeer als gezien" : "Al gezien"}</button>
      </div>
    </div>
  `;
}

function signalClass(score) {
  if (score >= 70) return "signal-high";
  if (score >= 45) return "signal-mid";
  return "signal-low";
}

function signalBadges(item) {
  const reasons = (item.ai_reasons || []).map(x => `<span class="badge">${x}</span>`).join("");
  const signals = (item.signals || []).map(x => `<span class="badge">${x}</span>`).join("");
  return reasons + signals;
}

function detectionHtml(item) {
  return `
    <div class="signal-card ${signalClass(item.ai_score || 0)}">
      <div class="signal-title">${item.ai_label || item.type}</div>
      <div class="signal-sub">${item.bron} · ${item.plaats} · score ${item.ai_score || 0}</div>
      <div class="badges">${signalBadges(item)}</div>
      ${item.snippet ? `<div class="snippet">${item.snippet}</div>` : ""}
      <div class="action-row">
        <a class="linkbtn" href="${item.url}" target="_blank" rel="noopener">Open bron</a>
      </div>
      <div class="debug">Focus: ${item.focus} · Prioriteit ${item.prioriteit}</div>
    </div>
  `;
}

function renderBestSignals() {
  const best = [...detections]
    .filter(x => (x.ai_score || 0) >= 45 && !x.google_noise)
    .sort((a,b) => (b.ai_score || 0) - (a.ai_score || 0))
    .slice(0, 3);

  bestList.innerHTML = best.length ? "" : '<div class="empty">Nog geen sterke signalen vandaag.</div>';
  best.forEach(item => bestList.insertAdjacentHTML("beforeend", detectionHtml(item)));
}

function renderDetections() {
  const clean = [...detections]
    .filter(x => (x.ai_score || 0) >= 20 && !x.google_noise)
    .sort((a,b) => (b.ai_score || 0) - (a.ai_score || 0));

  detectionList.innerHTML = clean.length ? "" : '<div class="empty">Nog geen bruikbare signalen beschikbaar.</div>';
  clean.forEach(item => detectionList.insertAdjacentHTML("beforeend", detectionHtml(item)));
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
  }).sort((a, b) => sourceScore(b) - sourceScore(a));
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
  const items = data.filter(item => favs.includes(item.url)).sort((a, b) => sourceScore(b) - sourceScore(a));
  favList.innerHTML = items.length ? "" : '<div class="empty">Nog geen favorieten opgeslagen.</div>';
  items.forEach(item => favList.insertAdjacentHTML("beforeend", itemHtml(item, true)));
  bindButtons(favList);
}

function renderStats() {
  const clean = detections.filter(x => (x.ai_score || 0) >= 20 && !x.google_noise);
  document.getElementById("totalCount").textContent = data.length;
  document.getElementById("signalCount").textContent = clean.length;
  document.getElementById("highCount").textContent = clean.filter(x => (x.ai_score || 0) >= 70).length;
  document.getElementById("unseenCount").textContent = data.filter(isNew).length;
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

function markAllSeen() {
  setSeen(data.map(x => x.url));
  renderAll();
}

function resetRadar() {
  localStorage.removeItem(seenKey);
  renderAll();
}

function renderAll() {
  renderBestSignals();
  renderList();
  renderFavs();
  renderDetections();
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
  data.filter(x => x.prioriteit === 1).sort((a, b) => sourceScore(b) - sourceScore(a)).slice(0, 12).forEach((item, i) => setTimeout(() => window.open(item.url, "_blank"), i * 220));
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
  const shareData = { title: "Woningzoeker Frank Burrei", text: "Check deze woningzoeker", url: location.href };
  if (navigator.share) { try { await navigator.share(shareData); } catch (e) {} }
  else { copyText(location.href, "Link gekopieerd."); }
};

populatePlaces();
renderAll();
switchTab("zoeken");
</script>
</body>
</html>
"""

    return (template
        .replace("__APP_TITLE__", APP_TITLE)
        .replace("__MAX_HUUR__", str(MAX_HUUR))
        .replace("__GENERATED_AT__", generated_at)
        .replace("__COUNT__", str(len(json.loads(data_json))))
        .replace("__DETECTION_COUNT__", str(len(json.loads(detections_json))))
        .replace("__DATA_JSON__", data_json)
        .replace("__DETECTIONS_JSON__", detections_json))


def build_app():
    rows = build_data()
    detections = detect_changes(rows)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    html = html_template(
        json.dumps(rows, ensure_ascii=False),
        json.dumps(detections, ensure_ascii=False),
        generated_at
    )
    Path("index.html").write_text(html, encoding="utf-8")
    print("Gegenereerd: index.html")
    print(f"Aantal woningbronnen: {len(rows)}")
    print(f"Aantal AI-signalen: {len(detections)}")


if __name__ == "__main__":
    build_app()
