"""note（https://note.com/tartarosjapan）の記事から column.html を作る。

動かし方（site/ の中で）:  python3 tools/update_column.py
外の部品は使わない（Python だけで動く）。
"""
import html
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

NOTE_USER = "tartarosjapan"
ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (tartarosjapan.com column updater)"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def text_of(s, n=90):
    t = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    t = re.sub(r"\s+", " ", t).strip()
    return t[:n] + ("…" if len(t) > n else "")


def from_api():
    """note の一覧（全部）。公式の約束ではない窓口なので、だめなら RSS に切り替える。"""
    items, page = [], 1
    while page <= 30:
        d = json.loads(get(f"https://note.com/api/v2/creators/{NOTE_USER}/contents?kind=note&page={page}"))["data"]
        for c in d["contents"]:
            if c.get("status") not in (None, "published"):
                continue
            items.append({
                "title": c["name"],
                "url": c.get("noteUrl") or f"https://note.com/{NOTE_USER}/n/{c['key']}",
                "img": c.get("eyecatch") or "",
                "date": datetime.fromisoformat(c["publishAt"]).strftime("%Y.%m.%d"),
                "text": text_of(c.get("body") or c.get("description") or ""),
            })
        if d.get("isLastPage"):
            break
        page += 1
    return items


def from_rss():
    root = ET.fromstring(get(f"https://note.com/{NOTE_USER}/rss"))
    ns = {"media": "http://search.yahoo.com/mrss/"}
    items = []
    for it in root.find("channel").findall("item"):
        th = it.find("media:thumbnail", ns)
        items.append({
            "title": it.findtext("title"),
            "url": it.findtext("link"),
            "img": (th.text or "").strip() if th is not None else "",
            "date": parsedate_to_datetime(it.findtext("pubDate")).strftime("%Y.%m.%d"),
            "text": text_of(it.findtext("description")),
        })
    return items


def main():
    try:
        items = from_api()
    except Exception as e:  # noqa: BLE001
        print("API が使えないので RSS を使う:", e)
        items = from_rss()
    if not items:
        raise SystemExit("記事が取れなかった（column.html は変えない）")
    items.sort(key=lambda x: x["date"], reverse=True)

    cards = []
    for it in items:
        img = (f'<img src="{html.escape(it["img"])}" alt="" loading="lazy">' if it["img"]
               else '<span class="noimg"></span>')
        cards.append(
            f'<a class="card" href="{html.escape(it["url"])}" target="_blank" rel="noopener">{img}'
            f'<span class="card-date">{it["date"]}</span>'
            f'<span class="card-title">{html.escape(it["title"])}</span>'
            f'<span class="card-text">{html.escape(it["text"])}</span></a>')
    body = ('<h1 class="page-title">COLUMN</h1>'
            '<p class="lead">note で書いているコラムです。押すと note の記事が開きます。<br>'
            'Columns on <a href="https://note.com/tartarosjapan" target="_blank" rel="noopener">note</a>.</p>'
            '<div class="cards">' + "".join(cards) + "</div>")

    # 見出し・メニュー・足元は index.html から借りる
    tpl = (ROOT / "index.html").read_text(encoding="utf-8")
    page = re.sub(r'<main class="content">.*?</main>',
                  lambda m: f'<main class="content">\n{body}\n</main>', tpl, flags=re.S)
    page = re.sub(r"<title>.*?</title>", "<title>COLUMN - KEI HINOTANI</title>", page)
    page = re.sub(r'<meta property="og:title" content="[^"]*">',
                  '<meta property="og:title" content="COLUMN - KEI HINOTANI">', page)
    page = re.sub(r'<meta name="description" content="[^"]*">',
                  '<meta name="description" content="TARTAROS / KEI HINOTANI のコラム（note）">', page)
    page = re.sub(r'<meta property="og:image"[^>]*>\n?', "", page)
    page = page.replace(' class="current"', "")
    page = page.replace('<a href="/column.html">', '<a href="/column.html" class="current">')
    (ROOT / "column.html").write_text(page, encoding="utf-8")
    print(f"column.html: {len(items)} 件")


if __name__ == "__main__":
    main()
