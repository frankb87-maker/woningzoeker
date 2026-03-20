import json
import re
import hashlib
from pathlib import Path
from datetime import datetime
from urllib.parse import quote_plus
import requests

APP_TITLE  = "Woningzoeker Frank Burrei"
VERSION    = "AI-radar v6.2"
MAX_HUUR   = 1600
MIN_KAMERS = 2

CORE_PLACES = ["Beverwijk", "Heemskerk"]
REGION_PLACES = [
    "Uitgeest", "Castricum", "Assendelft", "Velsen-Noord", "Wijk aan Zee",
    "Zaandam", "Driehuis", "Santpoort-Noord", "Velserbroek", "Bakkum",
    "Heiloo", "Limmen", "Akersloot", "Wormerveer", "Krommenie",
    "Haarlem-Noord", "IJmuiden", "Heemstede", "Bloemendaal",
]

RADAR_SOURCES = [
    # Prioriteit 1: platforms met volledige plaats + prijs + kamers filter
    {"name": "Funda",           "type": "funda",           "priority": 1},
    {"name": "Pararius",        "type": "pararius",        "priority": 1},
    {"name": "Jaap",            "type": "jaap",            "priority": 1},
    # Prioriteit 2: platforms met plaatsfilter in URL
    {"name": "Huislijn",        "type": "huislijn",        "priority": 2},
    {"name": "Huurwoningen.nl", "type": "huurwoningen_nl", "priority": 2},
    {"name": "Kamernet",        "type": "kamernet",        "priority": 2},
    {"name": "Vesteda",         "type": "vesteda",         "priority": 2},
    # Corporaties regio IJmond/Kennemerland
    {"name": "Woonopmaat",      "type": "woonopmaat",      "priority": 2},
    {"name": "Kennemer Wonen",  "type": "kennemerwonen",   "priority": 2},
    {"name": "Pre Wonen",       "type": "prewonen",        "priority": 2},
    {"name": "WoningNet",       "type": "woningnet",       "priority": 2},
    {"name": "ZVH",             "type": "zvh",             "priority": 2},
    {"name": "Woonwaard",       "type": "woonwaard",       "priority": 3},
]

# Landelijke verhuurders zonder plaatsfilter -> alleen via Google in Zoeken-tab
GOOGLE_LANDLORDS_DIRECT = [
    "Heimstaden", "Holland2Stay", "MVGM", "Rotsvast", "Interhouse",
]

GOOGLE_QUERIES = [
    {"name": "Google: 2-kamer appartement",  "priority": 1, "focus": "2 kamers",
     "query": "2 kamer appartement huur {place} max {max_huur} euro per maand"},
    {"name": "Google: 3-kamer appartement",  "priority": 1, "focus": "3 kamers",
     "query": "3 kamer appartement huur {place} max {max_huur} euro per maand"},
    {"name": "Google: gezinswoning huur",    "priority": 1, "focus": "gezinswoning",
     "query": "gezinswoning te huur {place} minimaal 2 slaapkamers max {max_huur} euro"},
    {"name": "Google: kindvriendelijk",      "priority": 2, "focus": "kindvriendelijk",
     "query": "kindvriendelijke huurwoning {place} 2 of 3 kamers max {max_huur}"},
    {"name": "Google: eengezinswoning tuin", "priority": 2, "focus": "eengezinswoning",
     "query": "eengezinswoning huur {place} max {max_huur} euro tuin"},
    {"name": "Google: nieuw aanbod",         "priority": 2, "focus": "nieuw aanbod",
     "query": "nieuw huurwoning aanbod {place} 2 kamers site:funda.nl OR site:pararius.nl"},
    {"name": "Google: studio of kamer",      "priority": 3, "focus": "studio/kamer",
     "query": "studio te huur {place} max {max_huur} euro beschikbaar"},
]

GOOGLE_PORTALS = [
    "Huurwoningen.nl", "Huurstunt", "Direct Wonen", "Kamernet",
    "NederWoon", "RentSlam", "123Wonen", "Rentola", "Rentbird", "HousingAnywhere",
]

GOOGLE_LANDLORDS = [
    "Vesteda", "MVGM", "Rotsvast", "Heimstaden", "Holland2Stay",
    "Interhouse", "HouseHunting", "REBO", "Altera", "Bouwinvest",
]

GOOGLE_CORPORATIONS = [
    "Woonopmaat", "Pre Wonen", "Rochdale", "Elan Wonen", "WoningNet",
    "Eigen Haard", "Ymere", "Parteon", "ZVH", "Intermaris",
    "Kennemer Wonen", "Woonzorg Nederland", "Woonwaard",
    "de Alliantie", "Stadgenoot",
]

GOOGLE_AGENCIES = [
    "Brantjes makelaars", "Van Gulik makelaars", "Teer makelaars",
    "Bert van Vulpen", "Saen Garantiemakelaars", "EV Wonen",
    "Kuijs Reinder Kakes", "Hopman ERA", "IJmond Makelaars",
    "Van Duin", "PMA makelaars",
]

NOISE_TERMS = [
    "just a moment", "enable javascript", "cookies to continue",
    "wat is mijn woning waard", "veelgestelde vragen",
    "vind je verkoopmakelaar", "nvm makelaar", "koop jouw eerste huis",
    "cookie", "privacy", "voorwaarden", "help", "inloggen",
    "account aanmaken", "contact opnemen",
    "please click here", "if you are not redirected",
    "google offered in", "search the world",
]

LISTING_TERMS = [
    "huur", "huurwoning", "appartement", "woning", "studio", "kamer",
    "slaapkamer", "beschikbaar", "per maand", "woonoppervlakte",
    "m2", "te huur", "direct beschikbaar",
]

ADDRESS_HINTS = [
    "straat", "laan", "weg", "plein", "hof", "plantsoen", "kade", "gracht",
]


def google_url(query: str) -> str:
    return "https://www.google.com/search?q=" + quote_plus(query)


def direct_url(source_type: str, place: str) -> str:
    p     = place.lower().replace(" ", "-")
    p_enc = quote_plus(place.lower())

    urls = {
        "funda":
            f"https://www.funda.nl/zoeken/huur?selected_area=%5B%22{p_enc}%22%5D"
            f"&price=%22-{MAX_HUUR}%22&rooms=%22{MIN_KAMERS}-%22",
        "pararius":
            f"https://www.pararius.nl/huurwoningen/{p}/0-{MAX_HUUR}/{MIN_KAMERS}-slaapkamers",
        "jaap":
            f"https://www.jaap.nl/huurhuizen/{p}?prijsvan=0&prijstot={MAX_HUUR}",
        "huislijn":
            f"https://www.huislijn.nl/huurwoning/{p}",
        "huurwoningen_nl":
            f"https://www.huurwoningen.nl/in/{p}/",
        "kamernet":
            f"https://www.kamernet.nl/huren/appartement-{p}?maxRent={MAX_HUUR}",
        "vesteda":
            f"https://www.vesteda.com/nl/woningaanbod/zoeken/?location={p_enc}&huurprijsmax={MAX_HUUR}&kamers={MIN_KAMERS}",
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


def add_row(rows, seen, bron, plaats, prioriteit, focus, url, tab="both"):
    key = (bron, plaats, url)
    if key not in seen:
        seen.add(key)
        rows.append({"bron": bron, "plaats": plaats, "prioriteit": prioriteit,
                     "focus": focus, "url": url, "tab": tab})


def build_data():
    rows = []
    seen = set()

    for place in CORE_PLACES:
        for src in RADAR_SOURCES:
            add_row(rows, seen, src["name"], place, src["priority"],
                    "huurwoningen", direct_url(src["type"], place), tab="radar")
        for src in GOOGLE_QUERIES:
            add_row(rows, seen, src["name"], place, src["priority"], src["focus"],
                    google_url(src["query"].format(place=place, max_huur=MAX_HUUR)), tab="zoeken")
        for name in GOOGLE_PORTALS:
            add_row(rows, seen, f"Google: {name}", place, 3, "portal",
                    google_url(f"{name} {place} huur minimaal 2 kamers"), tab="zoeken")
        for name in GOOGLE_LANDLORDS:
            add_row(rows, seen, f"Google: {name}", place, 3, "verhuurder",
                    google_url(f"{name} huurwoning {place} 2 kamers max {MAX_HUUR} euro"), tab="zoeken")
        for name in GOOGLE_LANDLORDS_DIRECT:
            add_row(rows, seen, f"Google: {name}", place, 2, "verhuurder",
                    google_url(f"{name} huurwoning {place} beschikbaar"), tab="zoeken")
        for name in GOOGLE_CORPORATIONS:
            add_row(rows, seen, f"Google: {name}", place, 3, "corporatie",
                    google_url(f"{name} huur {place} beschikbaar"), tab="zoeken")
        for name in GOOGLE_AGENCIES:
            add_row(rows, seen, f"Google: {name}", place, 3, "makelaar",
                    google_url(f"{name} huur {place} woning"), tab="zoeken")

    for place in REGION_PLACES:
        for src in RADAR_SOURCES:
            add_row(rows, seen, src["name"], place,
                    max(2, src["priority"]), "regio",
                    direct_url(src["type"], place), tab="radar")
        for src in GOOGLE_QUERIES[:4]:
            add_row(rows, seen, src["name"], place, max(2, src["priority"]), src["focus"],
                    google_url(src["query"].format(place=place, max_huur=MAX_HUUR)), tab="zoeken")
        for name in GOOGLE_PORTALS[:5]:
            add_row(rows, seen, f"Google: {name}", place, 3, "portal",
                    google_url(f"{name} {place} huur 2 kamers"), tab="zoeken")
        for name in GOOGLE_AGENCIES[:5]:
            add_row(rows, seen, f"Google: {name}", place, 3, "makelaar",
                    google_url(f"{name} huur {place}"), tab="zoeken")

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
    html = re.sub(r"<style.*?</style>",   " ", html, flags=re.S | re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", html).strip()


def extract_title(html: str) -> str:
    m = re.search(r"<title>(.*?)</title>", html, flags=re.I | re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip()[:180] if m else ""


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
        r"(.{0,80}(?:€\s?\d{3,5}|\d{2,3}\s?m2|\d+\s?kamer[s]?|huurwoning|appartement|te huur).{0,180})",
        text, flags=re.I)
    return re.sub(r"\s+", " ", m.group(1)).strip()[:240] if m else ""


def fingerprint(title, text, prices, surfaces, rooms):
    blob = " | ".join([title[:180], " ".join(prices[:8]), " ".join(surfaces[:8]),
                       " ".join(rooms[:8]), text[:4000]])
    return hashlib.sha256(blob.encode("utf-8", errors="ignore")).hexdigest()


def is_google_noise(text: str, title: str) -> bool:
    blob = f"{title} {text}".lower()
    return any(p in blob for p in [
        "google search", "please click here", "if you are not redirected",
        "images maps videos", "news books", "search the world",
        "google offered in", "redirected within a few seconds",
    ])


def signal_score(row: dict, title: str, text: str) -> dict:
    prices   = extract_signals(text, [r"€\s?\d{3,5}", r"eur\s?\d{3,5}", r"\d{3,5}\s?euro"])
    surfaces = extract_signals(text, [r"\d{2,3}\s?m2"])
    rooms    = extract_signals(text, [r"\b\d+\s?kamer[s]?\b", r"\b\d+\s?slaapkamer[s]?\b"])
    noise_n  = count_terms(text, NOISE_TERMS)
    list_n   = count_terms(text, LISTING_TERMS)
    snippet  = extract_snippet(text)
    gnoise   = is_google_noise(text, title)
    lower    = text.lower()

    score, reasons = 0, []
    if row["prioriteit"] == 1:   score += 22; reasons.append("prioriteit 1")
    elif row["prioriteit"] == 2: score += 10; reasons.append("prioriteit 2")
    if row["tab"] == "radar":    score += 20; reasons.append("directe bron")
    if prices:                   score += 24; reasons.append("prijs gevonden")
    if surfaces:                 score += 12; reasons.append("m2 gevonden")
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
    if gnoise: score -= 70
    score = max(0, min(score, 100))
    label = ("Waarschijnlijk nieuwe woning" if score >= 70
             else "Mogelijk nieuw aanbod" if score >= 45 else "Algemene update")
    return {"score": score, "label": label, "reasons": reasons[:4],
            "signals": (prices + surfaces + rooms)[:5], "snippet": snippet,
            "noise_count": noise_n, "google_noise": gnoise}


def detect_changes(rows: list) -> list:
    state_path = Path("radar_state.json")
    prev       = load_json(state_path, {})
    new_state, detections = {}, []
    headers    = {"User-Agent": "Mozilla/5.0"}
    candidates = [r for r in rows if r["tab"] == "radar" and r["prioriteit"] <= 2][:60]

    for row in candidates:
        item_id = f'{row["bron"]}|{row["plaats"]}|{row["url"]}'
        status, title, text, digest = "ok", "", "", ""
        ai = {"score": 0, "label": "Algemene update", "reasons": [],
              "signals": [], "snippet": "", "noise_count": 0, "google_noise": False}
        try:
            resp   = requests.get(row["url"], headers=headers, timeout=20, allow_redirects=True)
            status = str(resp.status_code)
            html   = resp.text[:150_000]
            title  = extract_title(html)
            text   = clean_html_text(html)[:25_000]
            prices   = extract_signals(text, [r"€\s?\d{3,5}", r"eur\s?\d{3,5}"])
            surfaces = extract_signals(text, [r"\d{2,3}\s?m2"])
            rooms    = extract_signals(text, [r"\b\d+\s?kamer[s]?\b"])
            digest = fingerprint(title, text, prices, surfaces, rooms)
            ai     = signal_score(row, title, text)
        except Exception as e:
            status = "error"
            digest = hashlib.sha256(str(e).encode()).hexdigest()

        new_state[item_id] = {
            "digest": digest, "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "status": status, "title": title,
            **{k: row[k] for k in ("bron", "plaats", "url", "prioriteit", "focus")}, "ai": ai}

        old = prev.get(item_id)
        change_type = (None if old and old.get("digest") == digest
                       else "nieuw gevolgd" if not old else "pagina gewijzigd")
        if change_type:
            detections.append({
                "type": change_type, "bron": row["bron"], "plaats": row["plaats"],
                "prioriteit": row["prioriteit"], "focus": row["focus"], "url": row["url"],
                "status": status, "title": title or (old.get("title", "") if old else ""),
                "ai_score": ai["score"], "ai_label": ai["label"], "ai_reasons": ai["reasons"],
                "signals": ai["signals"], "snippet": ai["snippet"],
                "noise_count": ai["noise_count"], "google_noise": ai["google_noise"]})

    detections.sort(key=lambda x: x.get("ai_score", 0), reverse=True)
    state_path.write_text(json.dumps(new_state, ensure_ascii=False, indent=2), encoding="utf-8")
    Path("radar_feed.json").write_text(json.dumps(detections, ensure_ascii=False, indent=2), encoding="utf-8")
    return detections


def html_template(data_json: str, detections_json: str, generated_at: str) -> str:
    rc = len(json.loads(data_json))
    dc = len(json.loads(detections_json))
    d  = json.dumps(json.loads(data_json), ensure_ascii=False)
    dt = json.dumps(json.loads(detections_json), ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{APP_TITLE}</title>
<meta name="theme-color" content="#0f172a">
<style>
:root{{--line:#e2e8f0;--text:#0f172a;--muted:#64748b;--card:#fff;
  --sh-bg:#ecfdf5;--sh-ln:#a7f3d0;--sh-tx:#065f46;
  --sm-bg:#fffbeb;--sm-ln:#fde68a;--sm-tx:#92400e;
  --sl-bg:#f8fafc;--sl-ln:#cbd5e1;--sl-tx:#334155;}}
*{{box-sizing:border-box}}html,body{{margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;
  background:linear-gradient(160deg,#f0f4f8,#e8eef6);color:var(--text)}}
.shell{{max-width:440px;margin:0 auto;min-height:100vh;background:#fff;
  box-shadow:0 0 0 1px rgba(148,163,184,.1),0 4px 24px rgba(15,23,42,.06)}}
.safe{{padding:18px 16px 110px}}
.hero{{background:linear-gradient(135deg,#0f172a 0%,#1e3a5f 55%,#1d4ed8 100%);
  color:#fff;border-radius:24px;padding:22px 18px 18px;box-shadow:0 12px 32px rgba(15,23,42,.18)}}
.hero-eye{{font-size:11px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;opacity:.7;margin-bottom:8px}}
.hero h1{{margin:0 0 8px;font-size:24px;font-weight:700;line-height:1.1;letter-spacing:-.02em}}
.hero-sub{{font-size:13px;line-height:1.55;color:rgba(255,255,255,.85);margin:0}}
.pills{{display:flex;gap:6px;flex-wrap:wrap;margin-top:14px}}
.pills span{{background:rgba(255,255,255,.13);border:1px solid rgba(255,255,255,.18);
  color:#fff;padding:5px 10px;border-radius:999px;font-size:11px;font-weight:500}}
.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:14px}}
.stat{{background:rgba(255,255,255,.97);color:var(--text);border-radius:16px;padding:12px 10px;text-align:center}}
.stat strong{{display:block;font-size:21px;font-weight:700;line-height:1.1;margin-bottom:4px}}
.stat span{{font-size:11px;color:var(--muted);font-weight:500}}
.section{{margin-top:16px}}
.sh{{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}}
.sh h2{{margin:0;font-size:20px;font-weight:700;letter-spacing:-.02em}}
.sh .sub{{color:var(--muted);font-size:12px;font-weight:500}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:20px;
  padding:14px;box-shadow:0 4px 16px rgba(15,23,42,.04)}}
.notice{{background:#f0f7ff;border:1px solid #bfdbfe;color:#1e3a5f;
  border-radius:14px;padding:12px;font-size:13px;line-height:1.55}}
.controls{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
.full{{grid-column:1/-1}}
label{{display:block;font-size:11px;font-weight:600;color:var(--muted);
  text-transform:uppercase;letter-spacing:.04em;margin-bottom:5px}}
input,select,textarea{{width:100%;border:1px solid var(--line);border-radius:12px;
  padding:11px 12px;font-size:14px;background:#fff;color:var(--text);-webkit-appearance:none}}
input:focus,select:focus{{outline:2px solid #2563eb;outline-offset:1px}}
textarea{{min-height:140px;resize:vertical;font-size:14px;line-height:1.5}}
.ar{{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}}
button,.btn{{border:none;appearance:none;cursor:pointer;border-radius:12px;
  padding:10px 14px;font-size:13px;font-weight:600;
  display:inline-flex;align-items:center;justify-content:center;
  text-decoration:none;transition:opacity .15s}}
button:active,.btn:active{{opacity:.8}}
.bp{{background:#0f172a;color:#fff}}
.bs{{background:#eff6ff;color:#1d4ed8}}
.bg{{background:#f8fafc;color:var(--text);border:1px solid var(--line)}}
.list{{display:grid;gap:10px}}
.item{{border-radius:18px;padding:14px;border:1px solid var(--line);
  background:#fff;box-shadow:0 3px 12px rgba(15,23,42,.04)}}
.ih{{display:flex;align-items:flex-start;justify-content:space-between;gap:8px}}
.item h3{{margin:0;font-size:16px;font-weight:700;line-height:1.3;letter-spacing:-.01em}}
.stb{{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;
  padding:3px 8px;border-radius:999px;white-space:nowrap;flex-shrink:0}}
.db{{background:#ecfdf5;color:#065f46}}
.gb{{background:#eff6ff;color:#1d4ed8}}
.meta{{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0 10px}}
.meta span{{padding:4px 9px;border-radius:999px;font-size:11px;font-weight:500;
  border:1px solid rgba(0,0,0,.05);background:#f8fafc}}
.bn{{background:#fef3c7!important;color:#92400e;border-color:#fde68a!important}}
.bsn{{background:#f1f5f9!important;color:#64748b}}
.sbar{{height:5px;border-radius:999px;background:#eef2f7;overflow:hidden;margin:6px 0 10px}}
.sbar>div{{height:100%;background:linear-gradient(90deg,#1d4ed8,#06b6d4);border-radius:999px}}
.p1{{border-left:3px solid #22c55e}}
.p2{{border-left:3px solid #3b82f6}}
.p3{{border-left:3px solid #e2e8f0}}
.panel{{display:none}}.panel.active{{display:block}}
.bnav{{position:fixed;left:50%;transform:translateX(-50%);bottom:0;
  width:min(440px,100%);background:rgba(255,255,255,.97);backdrop-filter:blur(12px);
  border-top:1px solid var(--line);display:grid;grid-template-columns:repeat(5,1fr);
  padding:8px 4px calc(8px + env(safe-area-inset-bottom));z-index:20;
  box-shadow:0 -4px 20px rgba(15,23,42,.06)}}
.nb{{border:none;background:transparent;color:var(--muted);font-size:10px;font-weight:500;
  display:flex;flex-direction:column;align-items:center;gap:4px;padding:5px 2px;cursor:pointer}}
.nb svg{{width:22px;height:22px;stroke:currentColor;fill:none;stroke-width:1.8;
  stroke-linecap:round;stroke-linejoin:round}}
.nb.active{{color:#0f172a;font-weight:700}}
.pip{{width:32px;height:32px;border-radius:10px;display:flex;align-items:center;justify-content:center}}
.nb.active .pip{{background:#e2e8f0}}
.sc{{border-radius:18px;padding:14px;border:1px solid var(--line)}}
.sc-h{{background:var(--sh-bg);border-color:var(--sh-ln);color:var(--sh-tx)}}
.sc-m{{background:var(--sm-bg);border-color:var(--sm-ln);color:var(--sm-tx)}}
.sc-l{{background:var(--sl-bg);border-color:var(--sl-ln);color:var(--sl-tx)}}
.sc-eye{{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;opacity:.8;margin-bottom:4px}}
.sc-title{{margin:0 0 4px;font-size:16px;font-weight:700;line-height:1.3}}
.sc-sub{{font-size:12px;opacity:.85;margin-bottom:8px}}
.badges{{display:flex;flex-wrap:wrap;gap:5px;margin:6px 0 0}}
.badge{{display:inline-block;padding:4px 8px;border-radius:999px;font-size:11px;font-weight:500;
  background:rgba(255,255,255,.7);border:1px solid rgba(0,0,0,.07)}}
.snippet{{margin-top:8px;font-size:12px;line-height:1.55;color:#334155;
  background:rgba(255,255,255,.6);border-radius:8px;padding:8px}}
.ig{{display:grid;gap:10px}}
.ib{{border-radius:16px;padding:14px;border:1px solid var(--line);line-height:1.55}}
.ib strong{{display:block;margin-bottom:4px;font-size:14px}}
.ib p{{margin:0;font-size:13px;color:#334155}}
.ib1{{background:#ecfdf5;border-color:#a7f3d0}}
.ib2{{background:#eff6ff;border-color:#bfdbfe}}
.ib3{{background:#f8fafc}}
.empty{{color:var(--muted);text-align:center;padding:24px 16px;font-size:13px}}
.fn{{color:var(--muted);font-size:11px;text-align:center;margin-top:12px}}
.div{{height:1px;background:var(--line);margin:14px 0}}
</style>
</head>
<body>
<div class="shell">
<div class="safe">

<div class="hero">
  <div class="hero-eye">{VERSION}</div>
  <h1>{APP_TITLE}</h1>
  <p class="hero-sub">Woningzoek-overzicht voor Beverwijk, Heemskerk en omgeving.
    Radar gebruikt uitsluitend directe bronnen. Google-zoekopdrachten staan in Zoeken.</p>
  <div class="pills">
    <span>{rc} bronnen</span>
    <span>max. &euro;{MAX_HUUR}/mnd</span>
    <span>min. {MIN_KAMERS} kamers</span>
    <span>Update: {generated_at}</span>
  </div>
  <div class="stats">
    <div class="stat"><strong id="totalCount">0</strong><span>bronnen</span></div>
    <div class="stat"><strong id="signalCount">0</strong><span>signalen</span></div>
    <div class="stat"><strong id="highCount">0</strong><span>sterk</span></div>
    <div class="stat"><strong id="unseenCount">0</strong><span>nieuw</span></div>
  </div>
</div>

<div id="dashboard" class="panel section">
  <div class="sh"><h2>Radar</h2><span class="sub">directe bronnen</span></div>
  <div class="card">
    <div class="notice">Controleert dagelijks: Funda, Pararius, Jaap, Huislijn, Kamernet,
      Vesteda, MVGM, Rotsvast, Interhouse, corporaties en meer. Geen Google.</div>
    <div class="ar">
      <button class="bp" id="markAllSeen">Alles als gezien markeren</button>
      <button class="bg" id="resetRadar">Reset</button>
    </div>
    <div class="div"></div>
    <div class="sh"><h2 style="font-size:16px">Beste signalen</h2></div>
    <div class="list" id="bestList"></div>
    <div class="div"></div>
    <div class="sh" style="margin-top:4px"><h2 style="font-size:16px">Alle updates</h2></div>
    <div class="list" id="detectionList"></div>
  </div>
</div>

<div id="zoeken" class="panel active section">
  <div class="sh"><h2>Zoeken</h2><span class="sub">start hier</span></div>
  <div class="card">
    <div class="controls">
      <div><label for="plaats">Plaats</label>
        <select id="plaats"><option value="all">Alle plaatsen</option></select></div>
      <div><label for="prio">Prioriteit</label>
        <select id="prio">
          <option value="all">Alle</option>
          <option value="1">Prioriteit 1</option>
          <option value="2">Prioriteit 2</option>
          <option value="3">Prioriteit 3</option>
        </select></div>
      <div><label for="tabfilter">Brontype</label>
        <select id="tabfilter">
          <option value="all">Alles</option>
          <option value="radar">Directe bronnen</option>
          <option value="zoeken">Google-zoekopdrachten</option>
        </select></div>
      <div class="full"><label for="zoek">Trefwoord</label>
        <input id="zoek" placeholder="Bijv. Funda, corporatie, makelaar, 2 kamers"></div>
    </div>
    <div class="ar">
      <button class="bp" id="openBest">Open top-links</button>
      <button class="bs" id="showFavs">Favorieten</button>
      <button class="bg" id="showAll">Toon alles</button>
    </div>
    <div class="list" id="list" style="margin-top:14px"></div>
  </div>
</div>

<div id="favorieten" class="panel section">
  <div class="sh"><h2>Opgeslagen</h2><span class="sub">lokaal bewaard</span></div>
  <div class="card"><div class="list" id="favList"></div></div>
</div>

<div id="familie" class="panel section">
  <div class="sh"><h2>Delen</h2><span class="sub">doorsturen</span></div>
  <div class="card">
    <label for="familyText">Bericht voor familie of vrienden</label>
    <textarea id="familyText">Hoi! Zou je met me mee willen kijken naar een huurwoning?

Ik zoek in Beverwijk / Heemskerk en omgeving.
Eisen:
- maximaal €{MAX_HUUR} per maand
- minimaal {MIN_KAMERS} kamers
- kindvriendelijke buurt

Als je iets ziet, stuur me dan meteen de link door. Alvast bedankt!</textarea>
    <div class="ar">
      <button class="bp" id="copyFamilyText">Kopieer bericht</button>
      <button class="bs" id="sharePage">Deel app</button>
    </div>
  </div>
</div>

<div id="prioriteiten" class="panel section">
  <div class="sh"><h2>Info</h2><span class="sub">uitleg</span></div>
  <div class="ig">
    <div class="ib ib1"><strong>Radar-tab</strong>
      <p>Controleert dagelijks directe woningwebsites: Funda, Pararius, Jaap, Huislijn,
      Kamernet, Vesteda, MVGM, Rotsvast, Interhouse en corporaties. Geen Google.</p></div>
    <div class="ib ib2"><strong>Zoeken-tab</strong>
      <p>Alle bronnen inclusief specifieke Google-zoekopdrachten op kamers, prijs en
      buurttype. Gebruik het Brontype-filter om te verfijnen.</p></div>
    <div class="ib ib3"><strong>Prioriteit 1</strong>
      <p>Funda, Pararius en Jaap in Beverwijk en Heemskerk. Altijd als eerste controleren.</p></div>
    <div class="ib ib3"><strong>Prioriteit 2</strong>
      <p>Overige directe platforms, verhuurders, corporaties en regiogemeenten.</p></div>
    <div class="ib ib3"><strong>Prioriteit 3</strong>
      <p>Extra portals, makelaars en corporaties buiten de kernregio.</p></div>
  </div>
  <div class="fn">{VERSION} &middot; max. &euro;{MAX_HUUR}/mnd &middot; min. {MIN_KAMERS} kamers</div>
</div>

</div>
<div class="bnav">
  <button class="nb" data-tab="dashboard">
    <div class="pip"><svg viewBox="0 0 24 24"><path d="M3 9.5L12 3l9 6.5V20a1 1 0 01-1 1H4a1 1 0 01-1-1V9.5z"/><path d="M9 21V12h6v9"/></svg></div><span>Radar</span></button>
  <button class="nb active" data-tab="zoeken">
    <div class="pip"><svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.35-4.35"/></svg></div><span>Zoeken</span></button>
  <button class="nb" data-tab="favorieten">
    <div class="pip"><svg viewBox="0 0 24 24"><path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z"/></svg></div><span>Opgeslagen</span></button>
  <button class="nb" data-tab="familie">
    <div class="pip"><svg viewBox="0 0 24 24"><path d="M4 12v8a2 2 0 002 2h12a2 2 0 002-2v-8"/><polyline points="16 6 12 2 8 6"/><line x1="12" y1="2" x2="12" y2="15"/></svg></div><span>Delen</span></button>
  <button class="nb" data-tab="prioriteiten">
    <div class="pip"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg></div><span>Info</span></button>
</div>
</div>

<script>
const data={d};
const detections={dt};
const FK="woningzoeker_v62_favs",SK="woningzoeker_v62_seen";
const gF=()=>JSON.parse(localStorage.getItem(FK)||"[]");
const sF=v=>localStorage.setItem(FK,JSON.stringify(v));
const gS=()=>JSON.parse(localStorage.getItem(SK)||"[]");
const sS=v=>localStorage.setItem(SK,JSON.stringify(v));
let onlyFavs=false;

function isNew(i){{return !gS().includes(i.url);}}
function sc(i){{
  let s=[0,55,25,10][i.prioriteit]||0;
  if(["Beverwijk","Heemskerk"].includes(i.plaats))s+=20;
  if((i.focus||"").match(/[23] kamers/))s+=8;
  if(i.tab==="radar")s+=12;
  return Math.min(100,s);
}}

function itemHtml(i,fav){{
  const tb=i.tab==="radar"?'<span class="stb db">Direct</span>':'<span class="stb gb">Google</span>';
  const nw=isNew(i)?'<span class="meta bn">Nieuw</span>':'<span class="meta bsn">Gezien</span>';
  return `<div class="item p${{i.prioriteit}}">
    <div class="ih"><h3>${{i.bron}}</h3>${{tb}}</div>
    <div class="meta"><span>${{i.plaats}}</span><span>P${{i.prioriteit}}</span><span>${{i.focus}}</span>${{nw}}</div>
    <div class="sbar"><div style="width:${{sc(i)}}%"></div></div>
    <div class="ar">
      <a class="btn bp" href="${{i.url}}" target="_blank" rel="noopener">Openen</a>
      <button class="btn bs" data-fav="${{i.url}}">${{fav?"Verwijder":"Bewaar"}}</button>
      <button class="btn bg" data-seen="${{i.url}}">${{isNew(i)?"Gezien":"Opnieuw"}}</button>
    </div></div>`;
}}

function scCl(s){{return s>=70?"sc-h":s>=45?"sc-m":"sc-l";}}
function detHtml(i){{
  const b=[...(i.ai_reasons||[]),...(i.signals||[])].map(x=>`<span class="badge">${{x}}</span>`).join("");
  return `<div class="sc ${{scCl(i.ai_score||0)}}">
    <div class="sc-eye">${{i.ai_label||i.type}}</div>
    <div class="sc-title">${{i.bron}} &mdash; ${{i.plaats}}</div>
    <div class="sc-sub">Score ${{i.ai_score||0}}/100 &middot; ${{i.focus}}</div>
    <div class="badges">${{b}}</div>
    ${{i.snippet?`<div class="snippet">${{i.snippet}}</div>`:""}}
    <div class="ar"><a class="btn bp" href="${{i.url}}" target="_blank" rel="noopener">Openen</a></div>
  </div>`;
}}

function renderBest(){{
  const el=document.getElementById("bestList");
  const best=detections.filter(x=>(x.ai_score||0)>=45&&!x.google_noise)
    .sort((a,b)=>(b.ai_score||0)-(a.ai_score||0)).slice(0,3);
  el.innerHTML=best.length?best.map(detHtml).join(""):'<div class="empty">Nog geen sterke signalen vandaag.</div>';
}}
function renderDetections(){{
  const el=document.getElementById("detectionList");
  const items=detections.filter(x=>(x.ai_score||0)>=20&&!x.google_noise)
    .sort((a,b)=>(b.ai_score||0)-(a.ai_score||0));
  el.innerHTML=items.length?items.map(detHtml).join(""):'<div class="empty">Nog geen bruikbare signalen.</div>';
}}
function bind(root){{
  root.querySelectorAll("[data-fav]").forEach(b=>b.onclick=()=>togFav(b.dataset.fav));
  root.querySelectorAll("[data-seen]").forEach(b=>b.onclick=()=>markSeen(b.dataset.seen));
}}
function filtered(){{
  const pl=document.getElementById("plaats").value;
  const pr=document.getElementById("prio").value;
  const tf=document.getElementById("tabfilter").value;
  const z=document.getElementById("zoek").value.toLowerCase().trim();
  const favs=gF();
  return data.filter(i=>{{
    if(pl!=="all"&&i.plaats!==pl)return false;
    if(pr!=="all"&&String(i.prioriteit)!==pr)return false;
    if(tf!=="all"&&i.tab!==tf)return false;
    if(z&&!`${{i.bron}} ${{i.focus}} ${{i.plaats}}`.toLowerCase().includes(z))return false;
    if(onlyFavs&&!favs.includes(i.url))return false;
    return true;
  }}).sort((a,b)=>sc(b)-sc(a));
}}
function renderList(){{
  const el=document.getElementById("list"),items=filtered(),favs=gF();
  el.innerHTML=items.length?items.map(i=>itemHtml(i,favs.includes(i.url))).join(""):'<div class="empty">Geen resultaten.</div>';
  bind(el);
}}
function renderFavs(){{
  const el=document.getElementById("favList"),favs=gF();
  const items=data.filter(i=>favs.includes(i.url)).sort((a,b)=>sc(b)-sc(a));
  el.innerHTML=items.length?items.map(i=>itemHtml(i,true)).join(""):'<div class="empty">Nog geen opgeslagen links.</div>';
  bind(el);
}}
function renderStats(){{
  const cl=detections.filter(x=>(x.ai_score||0)>=20&&!x.google_noise);
  document.getElementById("totalCount").textContent=data.length;
  document.getElementById("signalCount").textContent=cl.length;
  document.getElementById("highCount").textContent=cl.filter(x=>(x.ai_score||0)>=70).length;
  document.getElementById("unseenCount").textContent=data.filter(isNew).length;
}}
function togFav(url){{let f=gF();f=f.includes(url)?f.filter(x=>x!==url):[...f,url];sF(f);renderAll();}}
function markSeen(url){{const s=gS();if(!s.includes(url))s.push(url);sS(s);renderAll();}}
function renderAll(){{renderBest();renderDetections();renderList();renderFavs();renderStats();}}
function switchTab(tab){{
  document.querySelectorAll(".panel").forEach(p=>p.classList.remove("active"));
  document.querySelectorAll(".nb").forEach(b=>b.classList.remove("active"));
  document.getElementById(tab).classList.add("active");
  document.querySelectorAll(`.nb[data-tab="${{tab}}"]`).forEach(b=>b.classList.add("active"));
  window.scrollTo({{top:0,behavior:"smooth"}});
}}
function populatePlaces(){{
  const sel=document.getElementById("plaats");
  [...new Set(data.map(x=>x.plaats))].sort().forEach(p=>{{
    const o=document.createElement("option");o.value=p;o.textContent=p;sel.appendChild(o);
  }});
}}
document.querySelectorAll(".nb").forEach(b=>b.onclick=()=>switchTab(b.dataset.tab));
document.getElementById("plaats").onchange=renderList;
document.getElementById("prio").onchange=renderList;
document.getElementById("tabfilter").onchange=renderList;
document.getElementById("zoek").oninput=renderList;
document.getElementById("showFavs").onclick=()=>{{onlyFavs=true;renderList();}};
document.getElementById("showAll").onclick=()=>{{onlyFavs=false;renderList();}};
document.getElementById("openBest").onclick=()=>{{
  data.filter(x=>x.prioriteit===1&&x.tab==="radar")
    .sort((a,b)=>sc(b)-sc(a)).slice(0,10)
    .forEach((i,n)=>setTimeout(()=>window.open(i.url,"_blank"),n*220));
}};
document.getElementById("markAllSeen").onclick=()=>{{sS(data.map(x=>x.url));renderAll();}};
document.getElementById("resetRadar").onclick=()=>{{localStorage.removeItem(SK);renderAll();}};
const ft=document.getElementById("familyText");
document.getElementById("copyFamilyText").onclick=async()=>{{
  try{{await navigator.clipboard.writeText(ft.value);alert("Bericht gekopieerd.");}}
  catch{{alert("Kopiëren mislukt.");}}
}};
document.getElementById("sharePage").onclick=async()=>{{
  const d={{title:"{APP_TITLE}",text:"Woningzoeker",url:location.href}};
  if(navigator.share){{try{{await navigator.share(d);}}catch{{}}}}
  else{{try{{await navigator.clipboard.writeText(location.href);alert("Link gekopieerd.");}}catch{{}}}}
}};
populatePlaces();
renderAll();
switchTab("zoeken");
</script>
</body>
</html>"""


def build_app():
    rows         = build_data()
    detections   = detect_changes(rows)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    html = html_template(
        json.dumps(rows,       ensure_ascii=False),
        json.dumps(detections, ensure_ascii=False),
        generated_at,
    )
    Path("index.html").write_text(html, encoding="utf-8")
    radar_rows  = [r for r in rows if r["tab"] == "radar"]
    google_rows = [r for r in rows if r["tab"] == "zoeken"]
    print(f"Gegenereerd  : index.html  ({VERSION})")
    print(f"Totaal bronnen : {len(rows)}  (radar: {len(radar_rows)}, zoeken/Google: {len(google_rows)})")
    print(f"AI-signalen    : {len(detections)}")


if __name__ == "__main__":
    build_app()
