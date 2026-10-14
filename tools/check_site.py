#!/usr/bin/env python3
"""サイトの整合性チェック（ビルドではない。変更後に実行して問題がないか確かめるだけ）

使い方:  python3 tools/check_site.py
標準ライブラリだけで動く。問題があれば一覧を出して終了コード1で終わる。
"""
import html
import os
import re
import sys
import unicodedata
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://www.nomasangyou.com/"
# 旧サイトのサービス名。このファイル自体が全文検索に引っかからないよう、分割して書いている。
OLD_SERVICE = [("jim" + x).encode() for x in ("do", "cdn", "static")]
problems = []


def rel(p):
    return os.path.relpath(p, ROOT)


def pages():
    for d, dirs, files in os.walk(ROOT):
        dirs[:] = [x for x in dirs if not x.startswith(".") and x != "tools"]
        for f in files:
            if f.endswith(".html"):
                yield os.path.join(d, f)


def between(s, start, end):
    i = s.find(start)
    j = s.find(end, i)
    return s[i:j] if i >= 0 and j >= 0 else ""


def normalize_shared(block, prefix):
    """相対パスの深さと「現在のページ」の印を取り除き、全ページで比較できる形にする。"""
    if prefix:
        block = block.replace('="' + prefix, '="')
    block = re.sub(r' aria-current="page"', "", block)
    block = re.sub(r"\s?\bis-(?:current|parent)\b", "", block)
    block = re.sub(r' class=""', "", block)
    block = block.replace('href="./"', 'href=""')
    return block


# 1. ファイル名はNFC、旧サイトのサービスへの参照なし
for d, dirs, files in os.walk(ROOT):
    dirs[:] = [x for x in dirs if x != ".git"]
    for name in dirs + files:
        if not unicodedata.is_normalized("NFC", name):
            problems.append(f"ファイル名がNFCではない: {rel(os.path.join(d, name))}")
        path = os.path.join(d, name)
        if os.path.isfile(path):
            data = open(path, "rb").read().lower()
            if any(h in data for h in OLD_SERVICE):
                problems.append(f"旧サイトのサービス（画像配信など）への参照がある: {rel(path)}")

shared = {}
for page in pages():
    s = open(page, encoding="utf-8").read()
    r = rel(page)
    is404 = r == "404.html"
    depth = 0 if is404 or r == "index.html" else r.count(os.sep)
    prefix = "../" * depth

    # 2. 必須要素
    for need in ("<title>", '<meta charset="utf-8">', 'name="viewport"', "assets/css/style.css", "assets/js/main.js"):
        if need not in s:
            problems.append(f"{r}: {need} がない")
    if not is404 and '<link rel="canonical"' not in s:
        problems.append(f"{r}: canonical がない")

    # 3. 内部リンク・画像のリンク切れ（外部URL・#・mailto・tel は対象外）
    base_dir = ROOT if is404 else os.path.dirname(page)
    body = re.sub(r"<base\b[^>]*>", "", s)  # 404.html の基準パス指定はリンクではない
    for attr, url in re.findall(r'\b(href|src)="([^"]+)"', body):
        url = html.unescape(url)
        if re.match(r"^(https?:|mailto:|tel:|#|data:)", url):
            continue
        if url.startswith("/"):
            problems.append(f"{r}: ルートから始まるパスは使わない（相対パスにする）: {url}")
            continue
        target = os.path.normpath(os.path.join(base_dir, urllib.parse.unquote(url.split("#")[0].split("?")[0])))
        if url.endswith("/") or url in ("./", ""):
            target = os.path.join(target, "index.html")
        if not os.path.exists(target):
            problems.append(f"{r}: リンク切れ {attr}={url}")

    # 自サイト内のリンクは相対パスにする（canonical と OGP だけは絶対URL）
    for url in re.findall(r'<a\b[^>]*\bhref="(https?://(?:www\.)?nomasangyou\.com[^"]*)"', s):
        problems.append(f"{r}: 自サイトへのリンクが絶対URLになっている（相対パスにする）: {url}")

    # 4. 画像には width/height を付ける
    for tag in re.findall(r"<img\b[^>]*>", s):
        if "dialog" in tag:
            continue
        if 'width="' not in tag or 'height="' not in tag:
            problems.append(f"{r}: width/height のない画像: {tag[:80]}")

    # 5. 共通部分（ヘッダー・ナビの項目・サイドバー・フッター）が全ページで同じか
    blocks = {
        "ヘッダー": between(s, '<header class="site-header">', "</header>"),
        "グローバルナビ": between(s, '<nav class="global-nav"', "</nav>"),
        "サイドバー": between(s, '<div class="sidebar-box">', "</aside>"),
        "フッター": between(s, '<footer class="site-footer">', "</footer>"),
    }
    for name, block in blocks.items():
        if not block:
            problems.append(f"{r}: 共通部分「{name}」が見つからない")
            continue
        shared.setdefault(name, {}).setdefault(normalize_shared(block, "" if is404 else prefix), []).append(r)

for name, variants in shared.items():
    if len(variants) > 1:
        groups = sorted(variants.values(), key=len, reverse=True)
        odd = [p for g in groups[1:] for p in g]
        problems.append(f"共通部分「{name}」が他のページと違う: {', '.join(odd)}")

# 6. sitemap.xml に全ページが載っているか（サイトマップ・プライバシー・404は対象外）
sm = open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8").read()
locs = {urllib.parse.unquote(u) for u in re.findall(r"<loc>(.*?)</loc>", sm)}
for page in pages():
    r = rel(page).replace(os.sep, "/")
    if r in ("404.html", "sitemap/index.html", "j/privacy/index.html"):
        continue
    url = SITE + r[: -len("index.html")]
    if url not in locs:
        problems.append(f"sitemap.xml に載っていない: {url}")

if problems:
    print("問題が見つかりました:")
    for p in problems:
        print(" -", p)
    sys.exit(1)
print(f"OK: {sum(1 for _ in pages())} ページを確認しました（リンク切れ・共通部分・NFC・旧サービスへの参照・sitemap.xml）")
