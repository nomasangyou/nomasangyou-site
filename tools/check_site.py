#!/usr/bin/env python3
"""サイトの整合性チェック（ビルドではない。変更後に実行して問題がないか確かめるだけ）

使い方:  python3 tools/check_site.py
標準ライブラリだけで動く。問題があれば一覧を出して終了コード1で終わる。
グローバルナビの親子関係（どのページがどのページの子か）は index.html のナビから読み取る。
"""
import base64
import hashlib
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
# セキュリティの指定（CSP）。全ページの <head> に同じものを1つ置く（基準は index.html）
CSP_RE = re.compile(r'<meta http-equiv="Content-Security-Policy" content="([^"]*)">')
# 決まった形（ゆるめない）。変えてよいのは frame-src と form-action（お問い合わせフォームを入れるとき）と、
# script-src のハッシュ（ページ内の2つのスクリプトの中身を変えたとき）だけ
CSP_FIXED = {"default-src": ["'none'"], "style-src": ["'self'"], "img-src": ["'self'", "data:"], "base-uri": ["'self'"]}
CSP_DIRECTIVES = set(CSP_FIXED) | {"script-src", "frame-src", "form-action"}
ORIGIN_RE = re.compile(r"https://[a-z0-9.-]+(?::\d+)?(?:/[^\s;,']*)?")
HASH_RE = re.compile(r"'sha256-[A-Za-z0-9+/]{43}='")
# ページ内に書いてよいスクリプトは2つだけ（全ページの js クラスの1行と、404.html の基準パス。下の known で見分ける）
# 埋め込み（iframe）を置いてよいもの（ルール5）：Google マップの地図枠と、お問い合わせフォームの埋め込み枠の中
CONTACT_PAGE = "お問合せフォーム/index.html"


def parse_csp(csp):
    """CSP を {指定の種類: [値, …]} にする（同じ種類が2回あるときは None を入れて知らせる）"""
    out = {}
    for part in csp.split(";"):
        words = part.split()
        if words:
            out[words[0]] = None if words[0] in out else words[1:]
    return out


def csp_sources(csp, directive):
    """CSP の指定（例 frame-src）に並んでいる値の一覧"""
    return parse_csp(csp).get(directive) or []


def frame_allowed(url):
    """iframe の URL が CSP の frame-src に載っている読み込み元に当たるか（読み込み元だけ、または読み込み元＋パスの前方一致）"""
    for entry in FRAME_SRC:
        origin = re.match(r"https://[^/]+", entry).group(0)
        if entry == origin and re.match(r"https://[^/]+", url).group(0) == origin:
            return True
        if entry != origin and url.startswith(entry):
            return True
    return False


def script_hash(text):
    return "'sha256-" + base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode() + "'"


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

_csp_index = CSP_RE.findall(read("index.html"))
CSP = _csp_index[0] if len(_csp_index) == 1 else ""
if not CSP:
    problems.append("index.html: セキュリティの指定 <meta http-equiv=\"Content-Security-Policy\" …> が1つではない")
if CSP:
    pol = parse_csp(CSP)
    if set(pol) != CSP_DIRECTIVES or None in pol.values():
        problems.append(f"index.html: セキュリティの指定（CSP）の種類は {', '.join(sorted(CSP_DIRECTIVES))} を1つずつ"
                        f"（足りない: {', '.join(sorted(CSP_DIRECTIVES - set(pol))) or 'なし'}／余分・重複: {', '.join(sorted(k for k in pol if k not in CSP_DIRECTIVES or pol[k] is None)) or 'なし'}）")
    for k, want in CSP_FIXED.items():
        if pol.get(k) is not None and k in pol and sorted(pol[k]) != sorted(want):
            problems.append(f"index.html: CSP の {k} は {' '.join(want)} のまま（ゆるめない）。いま: {' '.join(pol[k])}")
    ss = pol.get("script-src") or []
    if not ss or ss[0] != "'self'" or not all(HASH_RE.fullmatch(v) for v in ss[1:]):
        problems.append(f"index.html: CSP の script-src は 'self' とページ内スクリプトのハッシュ（'sha256-…'）だけ（'unsafe-inline'・外部のURL・* は使わない）。いま: {' '.join(ss)}")
    fs = pol.get("frame-src") or []
    if not all(ORIGIN_RE.fullmatch(v) for v in fs):
        problems.append(f"index.html: CSP の frame-src には https://… の読み込み元だけを書く（* や https: だけ、'self' は使わない）。いま: {' '.join(fs)}")
    fa = pol.get("form-action") or []
    if fa != ["'none'"] and not (fa and all(v == "'self'" or ORIGIN_RE.fullmatch(v) for v in fa) and any(ORIGIN_RE.fullmatch(v) for v in fa)):
        problems.append(f"index.html: CSP の form-action は 'none'（フォームなし）か、'self' とフォームの送信先 https://… だけ。いま: {' '.join(fa)}")
FRAME_SRC = [u for u in csp_sources(CSP, "frame-src") if ORIGIN_RE.fullmatch(u)]
inline_hashes = set()

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

    # セキュリティの指定（CSP）：全ページ同じものを、<base> とスクリプトより前に1つ。
    # ページ内に直接書いたスクリプトは、その中身のハッシュが script-src に載っているものだけ動く
    csps = CSP_RE.findall(s)
    if len(csps) != 1 or csps[0] != CSP:
        problems.append(f"{r}: セキュリティの指定（CSP）の <meta> を index.html と同じものにして1つだけ置く")
    elif re.search(r"<(script|base)\b", s[: s.find("Content-Security-Policy")]):
        problems.append(f"{r}: セキュリティの指定（CSP）の <meta> は <base> と <script> より前に置く")
    for attrs, code in re.findall(r"<script\b([^>]*)>(.*?)</script>", s, re.S):
        if re.search(r"\bsrc\s*=", attrs) or re.search(r"""type=["']application/ld\+json["']""", attrs):
            continue
        # 決まった2つ（js クラスの1行・404 の基準パス）は、中身を書き換えてもハッシュを直せば動く。それ以外は増やさない
        known = (len(code) < 120 and "document.documentElement" in code and "js" in code) or (is404 and 'document.querySelector("base")' in code)
        if attrs.strip() or not known:
            problems.append(f"{r}: ページに直接スクリプトを書かない（セキュリティの指定で止められる。main.js に書く）: <script{attrs}>{code.strip()[:50]}…")
            continue
        inline_hashes.add(script_hash(code))
        if CSP and script_hash(code) not in csp_sources(CSP, "script-src"):
            problems.append(f"{r}: ページ内のスクリプトの中身が変わったので止められる。全ページの CSP の script-src のハッシュを {script_hash(code)} に直す"
                            f"（古いハッシュは消す）: <script>{code[:50]}…")
    if re.search(r"<style\b", s):
        problems.append(f"{r}: <style> は使わない（セキュリティの指定で止められる。style.css に書く）")
    if re.search(r"<(video|audio|source|track|object|embed)\b", s):
        problems.append(f"{r}: 動画・音声・PDF などの埋め込み（<video> <audio> <object> <embed>）はセキュリティの指定で止められる"
                        "（動画は YouTube などへのリンク、PDF は普通のリンクにする。ページに埋め込む必要があればオーナーに確認）")
    if re.search(r"""\son[a-z]+\s*=\s*["']""", body):
        problems.append(f"{r}: onclick= などの属性にスクリプトを書かない（セキュリティの指定で止められる。main.js に書く）")
    if re.search(r"""\sstyle\s*=\s*["']""", body):
        problems.append(f"{r}: style= 属性は使わない（セキュリティの指定で止められる。style.css に書く）")
    # 埋め込み（iframe）：ルール5で置いてよいのは Google マップの地図枠と、お問い合わせフォームの埋め込み枠の中だけ
    form_at = s.find('id="contact-form"') if r == CONTACT_PAGE else -1
    for m in re.finditer(r"""<iframe\b[^>]*?\bsrc=["']([^"']*)""", s):
        url = html.unescape(m.group(1))
        is_map = (url.startswith("https://maps.google.com/maps?") and "output=embed" in url) or url.startswith("https://www.google.com/maps/embed")
        in_form = form_at >= 0 and m.start() > form_at
        if not url.startswith("https://") or not (is_map or in_form):
            problems.append(f"{r}: ルール5：埋め込み（iframe）はオーナーの確認なしに増やさない（Google マップとお問い合わせフォームだけ）: {url[:80]}")
        elif not frame_allowed(url):
            problems.append(f"{r}: 埋め込み（iframe）{url[:60]} がセキュリティの指定で止められる。全ページの CSP の frame-src に"
                            f" {re.match(r'https://[^/]+', url).group(0)} を足す")
    for m in re.finditer(r"<form\b([^>]*)>", s):
        action = re.search(r"""\baction=["']([^"']*)""", m.group(1))
        url = action.group(1) if action else ""
        if not url.startswith("https://"):
            problems.append(f"{r}: フォームの送信先は https://… の外部サービスだけ（自サイト・mailto: などはセキュリティの指定で止められる）: action={url or '（なし）'}")
        elif re.match(r"https://[^/]+", url).group(0) not in csp_sources(CSP, "form-action"):
            o = re.match(r"https://[^/]+", url).group(0)
            problems.append(f"{r}: フォームの送信先 {o} がセキュリティの指定で止められる。全ページの CSP の form-action を 'self' {o} にする"
                            "（'self' は送信後に自サイトのお礼ページへ戻る設定のため）")

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
        if tag == "iframe":
            continue  # 埋め込みは上の「ルール5：埋め込み」で確かめている
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

# CSP の script-src に、どのページでも使われていないハッシュが残っていないか
for h in csp_sources(CSP, "script-src")[1:]:
    if HASH_RE.fullmatch(h) and h not in inline_hashes:
        problems.append(f"使われていないハッシュ {h} を全ページの CSP の script-src から消す")

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
      "写真タイル・canonical/og:url・セキュリティの指定（CSP）・外部ファイル（ルール5）・CSS の画像・NFC・旧サービスへの参照・サイトマップ（HTML と sitemap.xml）・"
      "404 の基準パス・画面幅の区切り）")
