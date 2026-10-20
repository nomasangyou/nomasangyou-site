# 株式会社野間産業 Webサイト（www.nomasangyou.com）

旧サイト（ホームページ作成サービスで運用していたもの）を、ビルド不要の素の HTML / CSS / JavaScript に移したもの。GitHub Pages（main ブランチのルート）で公開する。
更新は「Claude Code に日本語で頼む」運用を想定している。このファイルの決まりを必ず守ること。

## 構成（URL ＝ フォルダ）

| URL | ファイル | 備考 |
|---|---|---|
| `/` | `index.html` | ホーム（ヒーロー・スライドショー・写真タイル） |
| `/会社概要-1/` | `会社概要-1/index.html` | 「-1」も含めて現行URLのまま。地図あり |
| `/機材センター/` | `機材センター/index.html` | 写真＋地図 |
| `/業務内容/` | `業務内容/index.html` | |
| `/業務内容/近年の施工実績/` | `業務内容/近年の施工実績/index.html` | スキャン画像（拡大表示あり） |
| `/業務内容/工事経歴/` | `業務内容/工事経歴/index.html` | 表＋スキャン画像 |
| `/業務内容/各種工法カタログ/` | `業務内容/各種工法カタログ/index.html` | カタログのカード（外部リンク） |
| `/関連企業/` | `関連企業/index.html` | 外部リンク |
| `/お問合せフォーム/` | `お問合せフォーム/index.html` | フォーム埋め込み枠 `#contact-form` |
| `/sitemap/` | `sitemap/index.html` | HTMLのサイトマップ |
| `/j/privacy/` | `j/privacy/index.html` | プライバシーポリシー |
| （存在しないURL） | `404.html` | GitHub Pages が自動で使う |

- `assets/css/style.css` … 全ページ共通のCSS（1ファイルだけ。先頭に目次。部品ごとに、その直後へ `@media` を書く）
- `assets/js/main.js` … 全ページ共通のJS（スマホメニュー・PCのドロップダウン・スクロール時のヘッダーの影・スライドショー・画像の拡大表示・コピーライト年）
- `assets/img/{common,home,company,equipment,services}/` … 画像
- `sitemap.xml` / `robots.txt` / `.nojekyll`（消さない） / `tools/check_site.py`（確認用。サイトには使わない）

ナビの階層：ホーム（子：会社概要・機材センター）／業務内容（子：近年の施工実績・工事経歴・各種工法カタログ）／関連企業／お問い合わせフォーム

## 絶対に守るルール

1. **URLを変えない。** フォルダ名・ファイル名を変えない、消さない。日本語のフォルダ名は Unicode NFC にする（macOS で作ったフォルダは NFD になることがあるので注意）。
2. **頼まれていない文章・数値・会社情報を変えない。** 誤字や古い表記に気づいたら、直さずに報告する。
3. **共通部分は全ページで揃える。** 各HTMLの `<!-- ===== 共通… ===== -->` コメントで始まる3つの部分（ヘッダー＋グローバルナビ、お問い合わせ帯、フッター）は全12ファイルで同じ内容。どれか1つを変えたら、残りもすべて同じように変える（違うのは下の「ページごとに変わる部分」だけ）。
4. **リンクと画像は相対パス。** `/` から始まるパスや `https://www.nomasangyou.com/…` をリンクに使わない（github.io のプレビューでも独自ドメインでも動くようにするため）。例外は `<link rel="canonical">`・OGP（`og:url` `og:image` など）・`sitemap.xml` で、これらは `https://www.nomasangyou.com/` の絶対URL。
5. **外部ライブラリ・CDN・Webフォントを使わない。** JSは `assets/js/main.js`、CSSは `assets/css/style.css` に書く。外部から読むのは Google マップの地図枠（キー不要の `maps.google.com/maps?q=…&output=embed`）と、お問い合わせフォームの埋め込み（下の手順）だけ。ほかの埋め込み（YouTube など）はオーナーの確認なしに増やさない。
6. **画像は最適化してから置く**（下の手順）。旧サイトのサービス（画像配信サーバーなど）への参照は作らない（`tools/check_site.py` が検出する）。
7. **独自ドメイン・DNS には触れない。** `CNAME` ファイルはオーナーの指示があるまで作らない。
8. **ビルドの仕組みを持ち込まない**（静的サイトジェネレーター、npm のビルド、Jekyll など）。
9. **セキュリティの指定（CSP）を消さない・ゆるめない。** 全ページの `<head>` の `<meta http-equiv="Content-Security-Policy" …>` は全12ファイルで同じ内容（下の「セキュリティの指定（CSP）」）。変えてよいのは「お問い合わせフォームを入れる」の `frame-src`／`form-action` と、ページ内スクリプトのハッシュだけ。

## ページの組み立て（上から順に）

```html
<body class="page-…">
<!-- ===== 共通ヘッダー（全ページ同じ。変更するときは全ページを揃える） ===== -->
<div class="site-top">  … 白いロゴ板 <header class="site-header"> と <nav class="global-nav">
<!-- ===== 共通ここまで ===== -->
<main class="site-main" id="main">
<!-- ===== ページ見出し帯（パンくず・見出し・サブメニュー。ページごとに変わる） ===== -->
<div class="page-hero"><div class="page-hero__inner"> パンくず／<h1 class="page-title">／サブメニュー </div></div>
<!-- ===== 見出し帯ここまで ===== -->
<div class="page-body"> 本文 </div>
</main>
<!-- ===== 共通お問い合わせ帯（全ページ同じ。旧サイドバーの内容） ===== -->
<aside class="site-contact"> … 写真・「ご相談はこちらから」・お問い合わせボタン・TEL・社名・住所
<!-- ===== 共通フッター（全ページ同じ） ===== -->
<footer class="site-footer"> … バッジ2つ・プライバシーポリシー｜サイトマップ・コピーライト
```

- ホームだけは見出し帯の代わりに `<section class="home-hero">`（h1 と紹介文）と `<div class="home-showcase">`（スライドショーと写真タイルのサブメニュー `nav.subnav.subnav--tiles`）。
- 本文の中の見出しは `<h2>`（クラスなしなら上に短い青線が付く）。h1 は見出し帯の1つだけ。
- 本文で使える部品（CSS の「6. 本文の枠と汎用部品」）：写真の後ろに青い板 `figure.photo-frame`、地図 `div.map-frame > iframe.map`、拡大できる画像 `a.zoomable[data-lightbox="グループ名"]`（表・スキャン画像は `data-doc` と `doc-sheet` を付け、`doc-panel` の台に置く）、横に長い表 `div.table-scroll`、ボタン `a.button`、言葉の途中で改行させないまとまり `span.nw`。

## ページごとに変わる部分（共通部分と見出し帯の中で）

- 相対パスの前置き：ルート直下 `index.html` は `""`、1階層（例 `会社概要-1/`）は `"../"`、2階層（例 `業務内容/工事経歴/`）は `"../../"`。ホームへのリンクはルートでは `./`。
- グローバルナビの現在位置：表示中のページの `<li class="global-nav__item …">` に `is-current` と `<a … aria-current="page">`。子ページを表示中は、親の項目に `is-parent`、子の `<li>` に `class="is-current"` と `aria-current="page"`。サイトマップ・プライバシーポリシー・404 ではどれにも付けない。
- 見出し帯（`<div class="page-hero">`）の中身：
  - パンくず（`<nav class="breadcrumb">`）：子ページだけに付ける（例：ホーム » 会社概要、業務内容 » 工事経歴）。最後の項目の `<a>` に `aria-current="page"`。
  - 見出し `<h1 class="page-title">`：そのページの見出し（本文にあった見出しを移したもの。見出しの無いページはナビの名前）。かっこ書きは `<span class="page-title__sub">` に入れる。狭い画面で1文字だけ次の行に残るときは、本文の見出しの中だけ `<wbr>` で区切りを入れてよい（ナビ・サブメニューの文字には入れない）。
  - サブメニュー（`<nav class="subnav subnav--tabs">`、タブ）：ホームの子ページ（会社概要・機材センター）では会社概要・機材センターを、業務内容系（業務内容と3つの子ページ）では3つの子ページを表示する。表示中のタブの `<li>` に `class="is-current"`、`<a>` に `aria-current="page"`。関連企業・お問い合わせ・サイトマップ・プライバシーポリシー・404 には付けない。
- `404.html` だけは `<base href="/">` を使い、パスはルートからの相対（`assets/…`、`業務内容/` など）で書く。github.io でプレビューするときはスクリプトが基準を `/nomasangyou-site/` に直す。**リポジトリ名を変えたら 404.html のこの文字列も変える**（スクリプトの中身が変わるので、全ページの CSP の script-src のハッシュも直す。値は `check_site.py` が表示する）。

## よくある作業の手順

### 文章を直す
対象ページの `<main>` の中だけを直す。会社情報（住所・電話など）がお問い合わせ帯・会社概要・お問い合わせページ・OGP の説明文など複数箇所にある場合は、頼まれた範囲を確認してから全箇所を揃える（電話番号と住所は全ページのお問い合わせ帯にもある）。

### 画像を追加・差し替える
1. 元画像の向きを直す（EXIF の回転情報を画素に反映し、EXIF は消す）。
2. 縮小する：写真は表示サイズの約2倍（本文幅いっぱいなら長辺1,600px程度）、文字の多いスキャン画像は長辺1,600〜2,400px。
3. 圧縮する：JPEG は品質80前後・プログレッシブ。PNG は必要なときだけ（透過など）、減色して軽くする。
4. ファイル名は半角英小文字・数字・ハイフン（例 `assets/img/services/history-6.jpg`）。
5. `<img>` には `width` と `height`（PC幅 1280px での表示サイズ。縦横比は元画像と同じ）、`alt`、2枚目以降は `loading="lazy"` を付ける。
6. CSS（`style.css`）から使っている画像もある（HTML を探しても見つからない）。差し替え・改名したら `style.css` の `url()` と切り取り位置も見直す（`url()` のリンク切れは `tools/check_site.py` が検出する）。
   - `common/header-bg.jpg`：見出し帯とホームのヒーローの写真（位置は場所ごとの `background-position`）
   - ホームのヒーロー：`.home-hero__slide--1〜3` が `header-bg.jpg`・`home/slide-04.jpg`・`slide-05.jpg` を CSS だけで7秒ごとに切り替える（写真を変えるときは `.home-hero__slide--N` の `url()` と `background-position` を直す。枚数を変えるなら HTML の `<span>` と `@keyframes hero-photo` の割合も直す）
   - `common/logo.png`：`.site-logo` が左右の余白を切り取っている（画像のピクセルで 左45・幅302・高さ179 の数値）
   - `common/side-photo.jpg`：お問い合わせ帯の写真（`object-fit` で切り取り。スマホは `object-position`）
   - `company/office.jpg` と `equipment/hatsukaichi-2.jpg`：ホームの写真タイル（`.subnav__tile--…` の `--tile-img`。会社概要・機材センターのページの写真と同じファイルなので、差し替えるとタイルも変わる）

Pillow を使う例：
```python
from PIL import Image, ImageOps
im = ImageOps.exif_transpose(Image.open("元画像.jpg"))
im.thumbnail((1600, 1600))
im.convert("RGB").save("assets/img/xxx/yyy.jpg", "JPEG", quality=80, optimize=True, progressive=True)
```

### ページを追加する
1. 同じ階層の既存ページをコピーして作る（共通部分・相対パスの深さをそのまま使える）。
2. `<title>`（「ページ名 - 株式会社野間産業」）、canonical、OGP、`<body class="page-…">`、見出し帯（パンくず・`h1.page-title`・サブメニュー）、`<div class="page-body">` の中の本文を書き換える。
3. 全ページのグローバルナビ（共通ヘッダーの中。子ページなら親の `global-nav__sub` に）、同じグループのページの見出し帯のサブメニュー、`sitemap/index.html`、`404.html` のサイトマップ、`sitemap.xml` に追加する。ホームの子ページなら、`index.html` の写真タイル（`nav.subnav--tiles`）にも `<li class="subnav__tile--xxx">` を足し、`style.css` に `.subnav__tile--xxx { --tile-img: url("../img/…"); }` を足す。
4. ナビ・タブの項目が増えると狭い画面の表示も変わるので、幅320px・390px・960px（メニューが横並びに変わる幅）で折り返しを確認する。

### お問い合わせフォームを入れる
`お問合せフォーム/index.html` の `<div class="form-embed" id="contact-form">` の中に、選んだサービスの埋め込みコード（iframe など）を入れる。中が空（コメントだけ）の間は表示されない（入れるとあいさつ文と連絡先の下に全幅で出る）。埋め込みの読み込み元（例 Google フォームなら `https://docs.google.com`）を全ページの CSP の `frame-src` に足す。iframe ではなく `<form action="https://…">` で送るサービスなら、全ページの CSP の `form-action 'none'` を `'self'` とその送信先に変える（例 `form-action 'self' https://ssgform.com`。`'self'` は送信後に自サイトのお礼ページへ戻す設定でも止められないように）。埋め込みコードに `<script>`・`<style>`・`style="…"`・`onload="…"` などが入っていたら、そのままでは止められるので、`main.js`／`style.css` に移せるか確かめる（移せないものはオーナーに相談）。足りないものは `check_site.py` が指摘する。入れたらプライバシーポリシーの記載（委託先・reCAPTCHA など）も見直す（オーナーの確認が必要）。

### セキュリティの指定（CSP）
各ページの `<head>`（viewport の次。`<base>` やスクリプトより前）にある `<meta http-equiv="Content-Security-Policy" …>` が、ページで動かしてよいものを決めている。万一ページに悪いスクリプトを差し込まれても動かないようにするためのもの。全12ファイルで同じ内容にする（`check_site.py` が確かめる）。
- 自サイトから読み込めるのはスクリプト（`main.js`）・CSS（`style.css`）・画像だけ（CSS の中の小さなアイコンの `data:` も可）。外部から読めるのは埋め込みの `frame-src`（いまは Google マップの `https://maps.google.com` と `https://www.google.com`）だけ。
- 動画・音声（`<video>` `<audio>`）、PDF などのページ内への埋め込み（`<iframe>` `<object>` `<embed>`）、Webフォント、`main.js` からの `fetch` は止められる。動画は YouTube などへのリンク、PDF は普通の `<a href>` リンクにする（ページに埋め込む必要があるならオーナーに確認する）。
- ページ内に直接書いたスクリプト（`<script>…</script>`。いまは全ページの `js` クラスの1行と、404.html の基準パスの1つ）は、中身のハッシュ（`'sha256-…'`）を `script-src` に載せたものだけ動く。中身を1文字でも変えたら全ページの CSP のハッシュも直し、古いハッシュは消す（正しい値は `check_site.py` が表示する）。新しい処理は `main.js` に書く（ページに `<script>…</script>` を増やさない）。
- HTML に `<style>`・`style="…"`・`onclick="…"` などを書かない（止められる）。見た目は `style.css`、動きは `main.js` に書く。
- 外部サイトへの普通のリンク（`<a href>`）は制限されない。
- GitHub Pages ではサーバー側の設定ができないため、他サイトの枠の中に表示されるのを防ぐ指定（`frame-ancestors`）は効かない。

### プライバシーポリシー
文面はオーナーの指示なく変えない。旧サイト前提の記述（Google アナリティクス、reCAPTCHA、ホスティング事業者のアクセス解析）が残っている。改訂するときはオーナーに案を見せてから。項目は `<section class="policy__section">` の中に見出し `<h2 class="policy__title">` と本文 `<div class="policy__text">`。

### コピーライトの年
フッターの `<span class="js-year">2026</span>` は、JSが表示時に今年の年へ自動で置き換える。HTML上の数字は年に1回くらい手で更新してもよい（全ページ同じ値にする）。

## 変更したら必ず確認する

```sh
python3 tools/check_site.py          # リンク切れ・h1と見出し帯・共通部分の不一致・ナビの現在位置・タブ・パンくず・写真タイル・canonical/og:url・セキュリティの指定（CSP）・外部ファイル（ルール5）・CSS の画像・NFC・旧サービスへの参照・サイトマップ（HTML と sitemap.xml）の漏れ・404 の基準パス・画面幅の区切り
python3 -m http.server 8000          # http://localhost:8000/ で表示を確認（PC幅とスマホ幅）
```
- 表示確認では、スマホ幅でメニューの開閉、PC幅でナビの ∨ ボタン（ドロップダウン）、トップのスライドショー、画像の拡大表示も触ってみる。
- `check_site.py` が OK を出してからコミットする。

## 表記の決まり

- 表示名は「お問い合わせ」に統一（URL の `/お問合せフォーム/` は変えない）。
- 工法名などのカタカナは全角（半角カナを使わない）。
- 色は CSS の `:root` に変数で定義してある。ほかの場所に色の値を直接書かない（半透明は `rgb(var(--c-ink-rgb) / .5)` の形）。文字と背景のコントラストは WCAG AA 以上にする。例外は CSS の「16. 強制カラー」の `CanvasText` などのシステムの色（Windows のコントラスト テーマで線やアイコンを見せるためのもの）。
  - 濃い面：`--c-ink` `#121519`（ヘッダー・見出し帯）、`--c-ink-2` `#1b1f25`（お問い合わせ帯・ドロップダウン）、`--c-ink-3` `#0b0d10`（フッター）。その上の文字は `--c-on-ink`（白）・`--c-on-ink-soft`・`--c-on-ink-muted`・`--c-on-ink-faint`。
  - 明るい面：文字 `--c-text` `#1d2127`、補足 `--c-text-muted` `#59626d`、背景 `--c-bg` `#ffffff`、薄いグレーの面 `--c-bg-alt` `#f1f3f5`、罫線 `--c-line` `#d8dde3`。
  - 青（ロゴの青）：`--c-blue` `#2884e9`（線・面・印。白地の小さい文字には使わない）、文字・ボタン用 `--c-blue-strong` `#1667c7`、ホバー `--c-blue-deep` `#0f53a6`、薄い青の面 `--c-blue-tint` `#e7f0fb`、濃い面の上の青（フォーカス枠）`--c-blue-light` `#6fb0ff`。
- 画面幅の区切り：**960px**（これ未満はメニューボタンの全面メニュー。`main.js` の `NAV_BREAKPOINT` と必ず同じ値）、768px（これ未満はスマホ・1列）、375px（これ未満はとても狭い画面）。部品によっては 1100px・600px も使う（CSS の目次に一覧）。「これ未満」は `@media (max-width: 959.98px)` のように .98 で書く（拡大率 125% などで画面幅が小数になっても、`min-width: 960px` とどちらか一方に必ず当たるように。`check_site.py` が確かめる）。
- 飾りの形は増やさない：ロゴ板の斜めの切り欠き、ホームのヒーローの斜めの下辺、写真の後ろにずらした青い板、見出しの上の短い青線。
