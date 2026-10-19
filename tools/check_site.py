#!/usr/bin/env python3
"""サイトの整合性チェック（ビルドではない。変更後に実行して問題がないか確かめるだけ）

使い方:  python3 tools/check_site.py
標準ライブラリだけで動く。問題があれば一覧を出して終了コード1で終わる。
グローバルナビの親子関係（どのページがどのページの子か）は index.html のナビから読み取る。
"""
import html
import os
import posixpath
import re
import sys
import unicodedata
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://www.nomasangyou.com/"
# 旧サイトのサービス名。このファイル自体が全文検索に引っかからないよう、分割して書いている。
OLD_SERVICE = [("jim" + x).encode() for x in ("do", "cdn", "static")]
# グローバルナビの現在位置・タブ・パンくずを付けないページ
NO_CURRENT = {"sitemap/", "j/privacy/", "404.html"}
problems = []


def rel(p):
    return os.path.relpath(p, ROOT)


def read(r):
    return open(os.path.join(ROOT, r), encoding="utf-8").read()


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


def page_path(r):
    """ファイル（例 業務内容/工事経歴/index.html）→ サイト内のパス（例 業務内容/工事経歴/。ホームは ""）"""
    return r if r == "404.html" else r[: -len("index.html")]


def site_path(r, href):
    """ページ r に書かれたリンク href → サイト内のパス（ホームは ""）。404.html は <base href="/"> なのでルートから"""
    base = "" if r == "404.html" else posixpath.dirname(r)
    p = posixpath.normpath(posixpath.join(base, urllib.parse.unquote(html.unescape(href))))
    return "" if p == "." else p + "/"


def names(paths):
    return "、".join(p or "ホーム" for p in paths) or "なし"


# グローバルナビの親子関係：{親のパス: [子のパス, …]}（index.html のナビの並び順）
nav = between(read("index.html"), '<ul class="global-nav__list">', "<!-- ===== 共通ここまで")
GROUPS = {}
for m in re.finditer(r'<li class="global-nav__item[^"]*"><a href="([^"]*)"(.*?)(?=<li class="global-nav__item|\Z)', nav, re.S):
    GROUPS[site_path("index.html", m.group(1))] = [site_path("index.html", h) for h in re.findall(r'<a href="([^"]*)"', m.group(2))]
PARENT = {c: p for p, cs in GROUPS.items() for c in cs}
NAV_ORDER = [x for p, cs in GROUPS.items() for x in [p] + cs]
if not GROUPS:
    problems.append("index.html のグローバルナビ（global-nav__list）が読み取れない")

css = read("assets/css/style.css")

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
if not os.path.exists(os.path.join(ROOT, ".nojekyll")):
    problems.append(".nojekyll がない（消さない）")

shared = {}
for page in pages():
    s = open(page, encoding="utf-8").read()
    r = rel(page)
    is404 = r == "404.html"
    depth = 0 if is404 or r == "index.html" else r.count(os.sep)
    prefix = "../" * depth
    r = r.replace(os.sep, "/")
    me = page_path(r)
    body = s[s.find("<body"):]

    # 2. 必須要素。canonical と og:url はこのページ自身のURL（ページをコピーして作ったときの直し忘れ）
    for need in ("<title>", '<meta charset="utf-8">', 'name="viewport"', "assets/css/style.css", "assets/js/main.js"):
        if need not in s:
            problems.append(f"{r}: {need} がない")
    if not is404:
        canon = [urllib.parse.unquote(u) for u in re.findall(r'<link rel="canonical" href="([^"]*)"', s)]
        og = [urllib.parse.unquote(u) for u in re.findall(r'<meta property="og:url" content="([^"]*)"', s)]
        if canon != [SITE + me] or og != [SITE + me]:
            problems.append(f"{r}: canonical と og:url をこのページのURL（{SITE + me}）にする: canonical={canon} og:url={og}")

    # 3. 内部リンク・画像のリンク切れ（外部URL・#・mailto・tel は対象外）
    base_dir = ROOT if is404 else os.path.dirname(page)
    links = re.sub(r"<base\b[^>]*>", "", s)  # 404.html の基準パス指定はリンクではない
    for attr, _q, url in re.findall(r"""\b(href|src)=(["'])(.*?)\2""", links):
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

    # 自サイト内のリンク・画像は相対パスにする（canonical と OGP（<head> の中）だけは絶対URL）
    for url in re.findall(r"""\b(?:href|src)=["'](https?://(?:www\.)?nomasangyou\.com[^"']*)""", body):
        problems.append(f"{r}: 自サイトへのリンク・画像が絶対URLになっている（相対パスにする）: {url}")

    # 外部のライブラリ・フォント・埋め込みは使わない（ルール5。外部サイトへの <a> リンクと Google マップの地図枠は除く）
    for m in re.finditer(r"""<(\w+)\b[^>]*?\b(?:src|href)=["']((?:https?:)?//[^"']*)""", s):
        tag, url = m.group(1).lower(), m.group(2)
        if tag == "a" or (tag == "link" and 'rel="canonical"' in m.group(0)):
            continue
        if tag == "iframe" and url.startswith("https://maps.google.com/maps?") and "output=embed" in url:
            continue
        problems.append(f"{r}: 外部のライブラリ・フォント・埋め込みは使わない（ルール5）: <{tag}> {url[:80]}")
    for url in re.findall(r"""url\(\s*["']?((?:https?:)?//[^"')\s]*)""", s):
        problems.append(f"{r}: 外部のファイルを読まない（ルール5）: url({url[:80]})")

    # 4. 画像には width/height を付ける
    for tag in re.findall(r"<img\b[^>]*>", s):
        if "dialog" in tag:
            continue
        if 'width="' not in tag or 'height="' not in tag:
            problems.append(f"{r}: width/height のない画像: {tag[:80]}")

    # 見出し h1 はページに1つだけ（ページ見出し帯の .page-title、ホームはヒーローの見出し）
    h1_count = len(re.findall(r"<h1\b", s))
    if h1_count != 1:
        problems.append(f"{r}: <h1> が1つではない（{h1_count}個）")
    hero = between(s, '<div class="page-hero">', "<!-- ===== 見出し帯ここまで")
    if me and '<h1 class="page-title"' not in hero:
        problems.append(f'{r}: 見出し帯（<div class="page-hero"> … <!-- ===== 見出し帯ここまで ===== -->）の中に <h1 class="page-title"> がない')

    # 5. 共通部分（ヘッダーとグローバルナビ・お問い合わせ帯・フッター）が全ページで同じか
    blocks = {
        "ヘッダー・グローバルナビ": between(s, "<!-- ===== 共通ヘッダー", "<!-- ===== 共通ここまで ===== -->"),
        "お問い合わせ帯": between(s, '<aside class="site-contact"', "</aside>"),
        "フッター": between(s, '<footer class="site-footer">', "</footer>"),
    }
    for name, block in blocks.items():
        if not block:
            problems.append(f"{r}: 共通部分「{name}」が見つからない")
            continue
        shared.setdefault(name, {}).setdefault(normalize_shared(block, "" if is404 else prefix), []).append(r)

    # 6. ページごとに変わる部分：グローバルナビの現在位置・タブ・パンくず（CLAUDE.md「ページごとに変わる部分」）
    hdr = blocks["ヘッダー・グローバルナビ"]
    items = re.findall(r'<li(?: class="([^"]*)")?><a href="([^"]*)"( aria-current="page")?>', hdr)
    want = [] if me in NO_CURRENT else [me]
    cur_aria = [site_path(r, h) for c, h, a in items if a]
    cur_cls = [site_path(r, h) for c, h, a in items if "is-current" in c.split()]
    if cur_aria != want or cur_cls != want or hdr.count('aria-current="page"') != len(cur_aria):
        problems.append(f"{r}: グローバルナビの現在位置（li の is-current と a の aria-current=\"page\"）を {names(want)} にする"
                        f"（いま: is-current={names(cur_cls)}／aria-current={names(cur_aria)}）")
    want_parent = [PARENT[me]] if me in PARENT else []
    got_parent = [site_path(r, h) for c, h, a in items if "is-parent" in c.split()]
    if got_parent != want_parent:
        problems.append(f"{r}: グローバルナビの is-parent を {names(want_parent)} にする（いま: {names(got_parent)}）")

    tabs = between(hero, '<nav class="subnav subnav--tabs"', "</nav>")
    group = PARENT.get(me, me if me and GROUPS.get(me) else None)
    if group is not None:
        tab_items = re.findall(r'<li(?: class="([^"]*)")?><a href="([^"]*)"( aria-current="page")?>', tabs)
        got = [site_path(r, h) for c, h, a in tab_items]
        if got != GROUPS[group]:
            problems.append(f"{r}: 見出し帯のタブ（subnav--tabs）を {names(GROUPS[group])} の順にする（いま: {names(got)}）")
        want_tab = [me] if me in PARENT else []
        tab_aria = [site_path(r, h) for c, h, a in tab_items if a]
        tab_cls = [site_path(r, h) for c, h, a in tab_items if c == "is-current"]
        if tab_aria != want_tab or tab_cls != want_tab or tabs.count('aria-current="page"') != len(tab_aria):
            problems.append(f"{r}: 表示中のタブ（li の class=\"is-current\" と a の aria-current=\"page\"）を {names(want_tab)} にする"
                            f"（いま: is-current={names(tab_cls)}／aria-current={names(tab_aria)}）")
    elif tabs:
        problems.append(f"{r}: このページには見出し帯のタブ（subnav--tabs）を付けない")

    bc = between(hero, '<nav class="breadcrumb"', "</nav>")
    if me in PARENT:
        bc_items = re.findall(r'<a href="([^"]*)"( aria-current="page")?>', bc)
        if [site_path(r, h) for h, a in bc_items] != [PARENT[me], me] or [bool(a) for h, a in bc_items] != [False, True]:
            problems.append(f"{r}: パンくず（breadcrumb）を「{names([PARENT[me]])} » {names([me])}」にし、最後の項目の a に aria-current=\"page\" を付ける")
    elif bc:
        problems.append(f"{r}: パンくず（breadcrumb）は子ページだけに付ける")

    # ホームの写真タイル（subnav--tiles）：ホームの子ページすべてに1枚ずつ。写真は style.css の --tile-img
    if me == "":
        tiles = between(s, '<nav class="subnav subnav--tiles"', "</nav>")
        tile_items = re.findall(r'<li class="(subnav__tile--[\w-]+)"><a href="([^"]*)"', tiles)
        got = [site_path(r, h) for c, h in tile_items]
        if got != GROUPS.get("", []):
            problems.append(f"index.html: ホームの写真タイル（subnav--tiles）を {names(GROUPS.get('', []))} の順にする（いま: {names(got)}）")
        for c, h in tile_items:
            if not re.search(r"\." + re.escape(c) + r"\s*\{[^}]*--tile-img:", css):
                problems.append(f"index.html: 写真タイル {c} の写真が style.css にない（.{c} {{ --tile-img: url(\"../img/…\"); }} を足す）")

for name, variants in shared.items():
    if len(variants) > 1:
        groups = sorted(variants.values(), key=len, reverse=True)
        odd = [p for g in groups[1:] for p in g]
        problems.append(f"共通部分「{name}」が他のページと違う: {', '.join(odd)}")

# 7. サイトマップ（sitemap/index.html と 404.html の一覧）はグローバルナビと同じページを同じ順に
for r in ("sitemap/index.html", "404.html"):
    lst = between(read(r), '<ul class="sitemap">', "</main>")
    got = [site_path(r, h) for h in re.findall(r'<a href="([^"]*)"', lst)]
    if got != NAV_ORDER:
        missing = [p for p in NAV_ORDER if p not in got]
        extra = [p for p in got if p not in NAV_ORDER]
        problems.append(f"{r}: サイトマップの一覧がグローバルナビと違う（足りない: {names(missing)}／余分: {names(extra)}／順番も揃える）")

# sitemap.xml に全ページが載っているか（サイトマップ・プライバシー・404は対象外）
sm = open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8").read()
locs = {urllib.parse.unquote(u) for u in re.findall(r"<loc>(.*?)</loc>", sm)}
for page in pages():
    r = rel(page).replace(os.sep, "/")
    if r in ("404.html", "sitemap/index.html", "j/privacy/index.html"):
        continue
    url = SITE + r[: -len("index.html")]
    if url not in locs:
        problems.append(f"sitemap.xml に載っていない: {url}")

# 8. 404.html：<base href="/"> と、github.io でのプレビュー用の基準パス（リポジトリ名と同じ）
s404 = read("404.html")
if '<base href="/">' not in s404:
    problems.append('404.html: <base href="/"> がない（GitHub Pages の404ページでリンクと画像が切れる）')
m = re.search(r'var p="([^"]*)"', s404)
# リポジトリ名は .git/config の origin から読む（.git が無いときは現在の名前）
repo = "nomasangyou-site"
git_config = os.path.join(ROOT, ".git", "config")
if os.path.exists(git_config):
    u = re.search(r'\[remote "origin"\][^\[]*?\burl\s*=\s*(\S+)', open(git_config, encoding="utf-8").read())
    if u:
        repo = re.sub(r"\.git$", "", u.group(1).rstrip("/")).rsplit("/", 1)[-1]
if not m:
    problems.append('404.html: github.io 用の基準パスのスクリプト（var p="/リポジトリ名/"）がない')
elif m.group(1) != f"/{repo}/":
    problems.append(f'404.html: github.io 用の基準パス var p="{m.group(1)}" をリポジトリ名に合わせて "/{repo}/" にする')

# 9. style.css：画像は相対パスで、ファイルがあること。外部のフォント・ファイルは読まない（ルール5）
if re.search(r"@import\b", css):
    problems.append("style.css: @import は使わない（外部のライブラリ・フォントは使わない：ルール5。CSS は1ファイル）")
for url in re.findall(r"""url\(\s*["']?([^"')\s]+)""", css):
    if url.startswith("data:"):
        continue
    if re.match(r"^(?:[a-z][a-z0-9+.-]*:|//)", url, re.I):
        problems.append(f"style.css: 外部のファイルを読まない（ルール5）: url({url[:80]})")
    elif url.startswith("/"):
        problems.append(f"style.css: ルートから始まるパスは使わない（相対パスにする）: url({url})")
    elif not os.path.exists(os.path.join(ROOT, "assets", "css", urllib.parse.unquote(url.split("#")[0].split("?")[0]))):
        problems.append(f"style.css: CSS で使っている画像が見つからない: url({url})")

# 10. 画面幅の区切り：main.js の NAV_BREAKPOINT と CSS の 960px を揃える。
#     「未満」側（max-width）は .98 で書く（拡大率 125% などの小数の画面幅で、どちらにも当たらない隙間を作らない）
bad_max = sorted({v for q in re.findall(r"@media[^{]*", css) for v in re.findall(r"max-width:\s*([\d.]+)px", q) if not v.endswith(".98")}, key=float)
for v in bad_max:
    problems.append(f"style.css: @media の (max-width: {v}px) は (max-width: {int(float(v))}.98px) と書く")
bp = re.search(r"NAV_BREAKPOINT\s*=\s*(\d+)", read("assets/js/main.js"))
if not bp:
    problems.append("main.js: NAV_BREAKPOINT が見つからない")
else:
    n = int(bp.group(1))
    if f"(min-width: {n}px)" not in css or f"(max-width: {n - 1}.98px)" not in css:
        problems.append(f"main.js の NAV_BREAKPOINT（{n}）と style.css の区切り（min-width: {n}px／max-width: {n - 1}.98px）が合っていない")

if problems:
    print("問題が見つかりました:")
    for p in problems:
        print(" -", p)
    sys.exit(1)
print(f"OK: {sum(1 for _ in pages())} ページを確認しました（リンク切れ・h1と見出し帯・共通部分・ナビの現在位置・タブ・パンくず・"
      "写真タイル・canonical/og:url・外部ファイル（ルール5）・CSS の画像・NFC・旧サービスへの参照・サイトマップ（HTML と sitemap.xml）・"
      "404 の基準パス・画面幅の区切り）")
