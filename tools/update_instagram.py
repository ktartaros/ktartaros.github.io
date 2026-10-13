"""Instagram（@keihinotani）の投稿のうち、#keihinotaninews が付いたものを NEWS に載せる。

- news.html の <!--IG--> と <!--/IG--> の間に、カードを入れ直す
- 投稿ごとに news/ig-<id>.html を作る（写真と本文。Instagram へのリンク付き）
- 写真は uploads/ig/ に保存する（Instagram の写真の住所は、時間がたつと使えなくなるため）

鍵は環境変数 IG_TOKEN（GitHub では Secrets に入れてある）。
動かし方（site/ の中で）:  IG_TOKEN=... python3 tools/update_instagram.py
"""
import html
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

TAG = os.environ.get("IG_TAG", "#keihinotaninews")
API = "https://graph.instagram.com/v23.0/"
ROOT = Path(__file__).resolve().parent.parent
JST = timezone(timedelta(hours=9))


def get(url, **q):
    if q:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(q)
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def save_image(url, name):
    dst = ROOT / "uploads" / "ig" / name
    if not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=60) as r:
            dst.write_bytes(r.read())
    return f"/uploads/ig/{name}"


def fetch_posts(token):
    fields = "id,caption,media_type,media_url,thumbnail_url,permalink,timestamp"
    d = get(API + "me/media", fields=fields, limit=100, access_token=token)
    posts, pages = [], 0
    while True:
        posts += d.get("data", [])
        pages += 1
        nxt = d.get("paging", {}).get("next")
        if not nxt or pages >= 3:
            break
        d = get(nxt)
    out = []
    for p in posts:
        if TAG.lower() not in (p.get("caption") or "").lower():
            continue
        imgs = []
        if p["media_type"] == "CAROUSEL_ALBUM":
            kids = get(API + p["id"] + "/children", fields="id,media_type,media_url,thumbnail_url",
                       access_token=token).get("data", [])
        else:
            kids = [p]
        for i, k in enumerate(kids):
            src = k.get("thumbnail_url") if k["media_type"] == "VIDEO" else k.get("media_url")
            if src:
                imgs.append(save_image(src, f"{p['id']}_{i}.jpg"))
        out.append({**p, "imgs": imgs})
    return out


def page_from_template(title, body, current):
    tpl = (ROOT / "index.html").read_text(encoding="utf-8")
    page = re.sub(r'<main class="content">.*?</main>',
                  lambda m: f'<main class="content">\n{body}\n</main>', tpl, flags=re.S)
    t = html.escape(f"{title} - KEI HINOTANI")
    page = re.sub(r"<title>.*?</title>", f"<title>{t}</title>", page)
    page = re.sub(r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{t}">', page)
    page = re.sub(r'<meta property="og:image"[^>]*>\n?', "", page)
    page = page.replace(' class="current"', "")
    return page.replace(f'<a href="{current}">', f'<a href="{current}" class="current">')


def caption_html(cap):
    cap = re.sub(re.escape(TAG), "", cap, flags=re.I).strip()
    esc = html.escape(cap)
    esc = re.sub(r"(https?://[^\s<]+)", r'<a href="\1" target="_blank" rel="noopener">\1</a>', esc)
    return esc.replace("\n", "<br>")


def main():
    token = os.environ.get("IG_TOKEN") or Path.home().joinpath(".config/tartaros/ig_token").read_text().strip()
    posts = fetch_posts(token)
    cards = []
    for p in posts:
        dt = datetime.fromisoformat(p["timestamp"].replace("+0000", "+00:00")).astimezone(JST)
        cap = p.get("caption") or ""
        first = re.sub(re.escape(TAG), "", cap, flags=re.I).strip().split("\n")[0]
        title = first[:60] or "Instagram"
        figs = "".join(f'<figure><a href="{s}" class="lb"><img src="{s}" alt="" loading="lazy"></a></figure>'
                       for s in p["imgs"])
        body = (f'<article class="post"><p class="post-date">{dt:%Y.%m.%d}</p>'
                f'<h1 class="post-title">{html.escape(title)}</h1>'
                f'<div class="gallery" style="--cols:{min(3, max(1, len(p["imgs"])))}">{figs}</div>'
                f'<div class="paragraph">{caption_html(cap)}</div>'
                f'<p><a class="button" href="{html.escape(p["permalink"])}" target="_blank" rel="noopener">Instagram で見る</a></p>'
                f'<p class="back"><a href="/news.html">← NEWS 一覧へ</a></p></article>')
        (ROOT / "news" / f"ig-{p['id']}.html").write_text(page_from_template(title, body, "/news.html"), encoding="utf-8")
        thumb = (f'<img src="{p["imgs"][0]}" alt="" loading="lazy">' if p["imgs"] else '<span class="noimg"></span>')
        cards.append(f'<a class="card" href="/news/ig-{p["id"]}">{thumb}'
                     f'<span class="card-date">{dt:%Y.%m.%d}</span>'
                     f'<span class="card-title">{html.escape(title)}</span></a>')
    news = ROOT / "news.html"
    s = news.read_text(encoding="utf-8")
    s = re.sub(r"<!--IG-->.*?<!--/IG-->", lambda m: "<!--IG-->" + "".join(cards) + "<!--/IG-->", s, flags=re.S)
    news.write_text(s, encoding="utf-8")
    print(f"NEWS（Instagram {TAG}）: {len(cards)} 件")


if __name__ == "__main__":
    main()
