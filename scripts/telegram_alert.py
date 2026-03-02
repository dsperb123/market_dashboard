#!/usr/bin/env python3
"""
Daily alert — market headlines from MarketWatch + Seeking Alpha,
plus tickers from Indices, Sel Sectors and Industries with daily move > +1%.
No external dependencies required.
"""

import json
import os
import sys
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
THRESHOLD        = 1.0
ALERT_GROUPS     = ["Indices", "Sel Sectors", "Industries"]
MAX_HEADLINES    = 4  # per source

NAMES = {
    # Indices
    "QQQE":"Direxion Nasdaq-100 EW ETF","MGK":"Vanguard Mega Cap Growth ETF",
    "QQQ":"Invesco Nasdaq-100 ETF","IBIT":"iShares Bitcoin Trust","RSP":"Invesco S&P 500 EW ETF",
    "MDY":"SPDR S&P MidCap 400 ETF","IWM":"iShares Russell 2000 ETF","TLT":"iShares 20+ Year Treasury ETF",
    "SPY":"SPDR S&P 500 ETF","ETHA":"iShares Ethereum Trust","DIA":"SPDR Dow Jones ETF",
    # Sel Sectors
    "XLK":"SPDR Technology Select Sector ETF","XLI":"SPDR Industrials Select Sector ETF",
    "XLC":"SPDR Communication Services ETF","XLF":"SPDR Financials Select Sector ETF",
    "XLU":"SPDR Utilities Select Sector ETF","XLY":"SPDR Consumer Discretionary ETF",
    "XLRE":"SPDR Real Estate Select Sector ETF","XLP":"SPDR Consumer Staples ETF",
    "XLB":"SPDR Materials Select Sector ETF","XLE":"SPDR Energy Select Sector ETF",
    "XLV":"SPDR Health Care Select Sector ETF",
    # Industries
    "TAN":"Invesco Solar ETF","KCE":"SPDR S&P Capital Markets ETF","IBUY":"Amplify Online Retail ETF",
    "JETS":"US Global Jets ETF","IBB":"iShares Biotech ETF","SMH":"VanEck Semiconductor ETF",
    "CIBR":"First Trust Cybersecurity ETF","UTES":"Virtus Reaves Utilities ETF","ROBO":"Robo Global Robotics ETF",
    "IGV":"iShares Software ETF","WCLD":"WisdomTree Cloud Computing ETF","ITA":"iShares Aerospace & Defense ETF",
    "PAVE":"Global X Infrastructure ETF","BLOK":"Amplify Blockchain ETF","AIQ":"Global X AI ETF",
    "IYZ":"iShares US Telecommunications ETF","PEJ":"Invesco Leisure & Entertainment ETF",
    "FDN":"First Trust Internet ETF","KBE":"SPDR S&P Bank ETF","UNG":"US Natural Gas Fund",
    "BOAT":"SonicShares Global Shipping ETF","KWEB":"KraneShares China Internet ETF",
    "KRE":"SPDR S&P Regional Banking ETF","XRT":"SPDR S&P Retail ETF",
    "IHI":"iShares Medical Devices ETF","DRIV":"Global X Autonomous & EV ETF","MSOS":"AdvisorShares US Cannabis ETF",
    "SOCL":"Global X Social Media ETF","ARKF":"ARK Fintech Innovation ETF","SLX":"VanEck Steel ETF",
    "ARKK":"ARK Innovation ETF","XTN":"SPDR S&P Transportation ETF","XME":"SPDR S&P Metals & Mining ETF",
    "KIE":"SPDR S&P Insurance ETF","GLD":"SPDR Gold Shares","GDX":"VanEck Gold Miners ETF",
    "IPAY":"ETFMG Prime Mobile Payments ETF","XOP":"SPDR Oil & Gas E&P ETF","VNQ":"Vanguard Real Estate ETF",
    "EATZ":"AdvisorShares Restaurant ETF","DBA":"Invesco DB Agriculture Fund",
    "ICLN":"iShares Clean Energy ETF","SILJ":"ETFMG Junior Silver Miners ETF",
    "LIT":"Global X Lithium & Battery ETF","SLV":"iShares Silver Trust",
    "XHB":"SPDR Homebuilders ETF","PBJ":"Invesco Food & Beverage ETF","USO":"US Oil Fund",
    "DBC":"Invesco DB Commodity Fund","FCG":"First Trust Natural Gas ETF","XBI":"SPDR Biotech ETF",
    "ARKG":"ARK Genomic Revolution ETF","CPER":"US Copper Index Fund","XES":"SPDR Oil & Gas Equipment ETF",
    "OIH":"VanEck Oil Services ETF","PPH":"VanEck Pharmaceutical ETF","FNGS":"MicroSectors FANG+ ETF",
    "URA":"Global X Uranium ETF","WGMI":"Valkyrie Bitcoin Miners ETF","REMX":"VanEck Rare Earth ETF",
    "SCHH":"Schwab US REIT ETF","REZ":"iShares Residential Real Estate ETF",
    "GXC":"SPDR S&P China ETF","XHE":"SPDR S&P Health Care Equipment ETF",
}

RSS_FEEDS = [
    ("MarketWatch", "https://feeds.content.dowjones.io/public/rss/mw_marketpulse"),
    ("Seeking Alpha", "https://seekingalpha.com/market_currents.xml"),
]


def fetch_headlines(name, url):
    """Fetch headlines from an RSS feed."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            xml_data = resp.read()
        root = ET.fromstring(xml_data)
        headlines = []
        for item in root.findall(".//item"):
            title = item.findtext("title")
            if title:
                headlines.append(title.strip())
            if len(headlines) >= MAX_HEADLINES:
                break
        return headlines
    except Exception as e:
        print(f"Could not fetch {name} headlines: {e}")
        return []


def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: TELEGRAM_TOKEN or TELEGRAM_CHAT_ID not set.", file=sys.stderr)
        sys.exit(1)
    url  = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id":    TELEGRAM_CHAT_ID,
        "text":       message,
        "parse_mode": "HTML",
    }).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read())
        if not result.get("ok"):
            print(f"Telegram error: {result}", file=sys.stderr)
            sys.exit(1)


def main():
    try:
        with open("data/snapshot.json") as f:
            snapshot = json.load(f)
    except FileNotFoundError:
        print("ERROR: data/snapshot.json not found.", file=sys.stderr)
        sys.exit(1)

    now_str = datetime.now(timezone.utc).strftime("%d %b %Y")
    all_groups = snapshot.get("groups", {})

    lines = [f"📊 <b>Morning Market Brief — {now_str}</b>"]

    # ── Headlines ─────────────────────────────────────────
    for feed_name, feed_url in RSS_FEEDS:
        headlines = fetch_headlines(feed_name, feed_url)
        if headlines:
            lines.append(f"\n<b>── {feed_name} ──</b>")
            for h in headlines:
                lines.append(f"• {h}")

    # ── Movers ────────────────────────────────────────────
    total = 0
    mover_lines = []

    for group_name in ALERT_GROUPS:
        rows = all_groups.get(group_name, [])
        movers = [r for r in rows if r.get("daily") is not None and r["daily"] >= THRESHOLD]
        movers.sort(key=lambda r: r["daily"], reverse=True)

        if movers:
            mover_lines.append(f"\n<i>{group_name}</i>")
            for r in movers:
                ticker = r.get("ticker", "?")
                name   = NAMES.get(ticker, ticker)
                daily  = r["daily"]
                grade  = r.get("abc", "?")
                mover_lines.append(f"<b>{ticker}</b> [{grade}]  +{daily:.2f}%  —  {name}")
            total += len(movers)

    lines.append(f"\n<b>── Movers &gt;+{THRESHOLD}% ──</b>")
    if total == 0:
        lines.append(f"No tickers moved more than +{THRESHOLD}% yesterday.")
    else:
        lines.extend(mover_lines)
        lines.append(f"\n<i>{total} ticker(s) above +{THRESHOLD}%</i>")

    message = "\n".join(lines)
    print(message)
    send_telegram(message)
    print("✓ Alert sent.")


if __name__ == "__main__":
    main()
