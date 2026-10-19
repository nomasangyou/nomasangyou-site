/* 株式会社野間産業 — サイト共通スクリプト（外部ライブラリなし） */
(function () {
  "use strict";

  var root = document.documentElement;
  var body = document.body;
  var each = function (list, fn) { Array.prototype.forEach.call(list, fn); };

  // PC表示（横並びのメニュー）になる画面幅。style.css の「960px」と必ず同じ値にする
  var NAV_BREAKPOINT = 960;
  var pcQuery = window.matchMedia ? window.matchMedia("(min-width: " + NAV_BREAKPOINT + "px)") : null;
  var isPC = function () { return !!(pcQuery && pcQuery.matches); };
  var onPCChange = function (fn) {
    if (!pcQuery) return;
    if (pcQuery.addEventListener) { pcQuery.addEventListener("change", fn); }
    else if (pcQuery.addListener) { pcQuery.addListener(fn); }
  };

  // 直前の操作がキーボードか、マウス・タッチかを覚えておく
  var usingKeyboard = false;
  var isNavKey = function (e) {
    return !(e.ctrlKey || e.altKey || e.metaKey) && ["Shift", "Control", "Alt", "Meta"].indexOf(e.key) < 0;
  };
  document.addEventListener("keydown", function (e) { if (isNavKey(e)) usingKeyboard = true; }, true);
  document.addEventListener("mousedown", function () { usingKeyboard = false; }, true);
  document.addEventListener("touchstart", function () { usingKeyboard = false; }, { capture: true, passive: true });

  /* ---------- スマートフォン用メニュー（960px未満：右上のボタン） ---------- */
  var toggle = document.querySelector(".nav-toggle");
  // メニューを開いている間は、裏にある部分（ロゴ・本文・お問い合わせ帯・フッターなど、
  // メニューボタンを含まないものすべて）へキーボード操作が移らないようにする
  var behind = [];
  if (toggle) {
    each(document.querySelectorAll("body > *, .site-top > *"), function (el) {
      if (!el.contains(toggle) && el.tagName !== "SCRIPT") behind.push(el);
    });
  }

  function setMenu(open) {
    if (!toggle) return;
    body.classList.toggle("nav-open", open);
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    each(behind, function (el) {
      if (open) { el.setAttribute("inert", ""); } else { el.removeAttribute("inert"); }
    });
  }

  if (toggle) {
    toggle.addEventListener("click", function () {
      setMenu(!body.classList.contains("nav-open"));
    });
  }

  /* ---------- 子メニュー ----------
     PC：ドロップダウン。∨ ボタンで開閉（同時に開くのは1つ）。マウスを乗せても開く（CSS）。
         フォーカスが外へ出る・外側をクリック・Esc で閉じる。
     スマホ：メニューの中の ＋ ボタンで開閉（初期状態は閉じる） */
  var subItems = document.querySelectorAll(".global-nav__item.has-sub");
  var hovered = function (item) { return item.matches && item.matches(":hover"); };

  function setSub(item, open) {
    item.classList.toggle("is-open", open);
    var btn = item.querySelector(".global-nav__expand");
    if (btn) btn.setAttribute("aria-expanded", open ? "true" : "false");
    // .is-dismissed（Esc でマウスオーバーの表示を消した印）はマウスが乗っている間だけ残す
    if (open || !hovered(item)) item.classList.remove("is-dismissed");
  }

  function closeSubs(except) {
    each(subItems, function (item) {
      if (item !== except && item.classList.contains("is-open")) setSub(item, false);
    });
  }

  each(subItems, function (item) {
    var btn = item.querySelector(".global-nav__expand");
    if (!btn) return;
    btn.addEventListener("click", function () {
      var open = !item.classList.contains("is-open");
      if (isPC()) closeSubs(item);
      setSub(item, open);
      // マウスを乗せたまま ∨ で閉じたときは、ホバーの表示も消す
      if (!open && isPC() && hovered(item)) item.classList.add("is-dismissed");
    });
    // マウスが離れたら、Esc で消した印を外す（次に乗せたときはまた開く）
    item.addEventListener("pointerleave", function () { item.classList.remove("is-dismissed"); });
    // PC：フォーカスが項目の外へ移ったら閉じる
    item.addEventListener("focusout", function (e) {
      if (isPC() && e.relatedTarget && !item.contains(e.relatedTarget)) setSub(item, false);
    });
  });

  // PC：ドロップダウンの外側をクリックしたら閉じる
  document.addEventListener("click", function (e) {
    if (isPC() && !(e.target.closest && e.target.closest(".global-nav__item.has-sub"))) closeSubs();
  });

  // Esc：スマホのメニューを閉じてボタンへ戻る／PCのドロップダウンを閉じて ∨ ボタンへ戻る
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape" && e.key !== "Esc") return;
    if (body.classList.contains("nav-open")) {
      setMenu(false);
      toggle.focus();
      return;
    }
    if (!isPC()) return;
    each(subItems, function (item) {
      var isHovered = hovered(item);
      if (!item.classList.contains("is-open") && !isHovered) return;
      var hadFocus = item.contains(document.activeElement);
      setSub(item, false);
      if (isHovered) item.classList.add("is-dismissed");
      var btn = item.querySelector(".global-nav__expand");
      if (hadFocus && btn) btn.focus();
    });
  });

  // PC表示とスマホ表示が切り替わったら、開いているメニューを閉じる
  onPCChange(function () { setMenu(false); closeSubs(); });

  // 「戻る」でキャッシュから表示し直したときは、開いたままのメニューを閉じる
  window.addEventListener("pageshow", function (e) {
    if (e.persisted) { setMenu(false); closeSubs(); }
  });

  /* ---------- ヘッダー：スクロールしたら影を付ける（.site-top.is-scrolled） ---------- */
  var siteTop = document.querySelector(".site-top");
  if (siteTop) {
    var onScroll = function () { siteTop.classList.toggle("is-scrolled", window.pageYOffset > 4); };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  /* ---------- スライドショー ---------- */
  each(document.querySelectorAll(".slideshow"), function (show) {
    var slides = show.querySelectorAll(".slideshow__slide");
    var thumbs = show.querySelectorAll(".slideshow__thumb");
    var delay = parseInt(show.getAttribute("data-autoplay"), 10) || 0;
    var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var index = 0;
    var timer = null;
    // マウスが乗っている・キーボードで操作中・拡大表示中は自動再生しない
    // （クリックやタップでボタンにフォーカスが残っても止めたままにしない）
    var pointerOver = false;
    var focused = false;
    var viewing = false;
    if (slides.length < 2) return;

    function go(n) {
      index = (n + slides.length) % slides.length;
      for (var i = 0; i < slides.length; i++) {
        slides[i].classList.toggle("is-active", i === index);
        slides[i].setAttribute("aria-hidden", i === index ? "false" : "true");
        slides[i].tabIndex = i === index ? 0 : -1;
        if (thumbs[i]) {
          thumbs[i].classList.toggle("is-active", i === index);
          thumbs[i].setAttribute("aria-current", i === index ? "true" : "false");
        }
      }
      // 写真の周りの余白に同じ写真をぼかして敷く（CSS の --slide-bg）。表示した写真にだけ設定する
      var active = slides[index];
      var img = active.querySelector("img");
      if (img && !active.style.getPropertyValue("--slide-bg")) {
        active.style.setProperty("--slide-bg", 'url("' + (img.currentSrc || img.src) + '")');
      }
    }

    function stop() {
      if (timer) { clearInterval(timer); timer = null; }
    }

    function start() {
      stop();
      if (!delay || reduce || pointerOver || focused || viewing || document.hidden) return;
      timer = setInterval(function () { go(index + 1); }, delay);
    }

    show.querySelector(".slideshow__prev").addEventListener("click", function () { go(index - 1); start(); });
    show.querySelector(".slideshow__next").addEventListener("click", function () { go(index + 1); start(); });
    each(thumbs, function (t, i) {
      t.addEventListener("click", function () { go(i); start(); });
    });
    show.addEventListener("pointerenter", function (e) {
      if (e.pointerType === "mouse") { pointerOver = true; stop(); }
    });
    show.addEventListener("pointerleave", function (e) {
      if (e.pointerType === "mouse") { pointerOver = false; start(); }
    });
    show.addEventListener("focusin", function () {
      focused = usingKeyboard;
      if (focused) { stop(); } else { start(); }
    });
    show.addEventListener("keydown", function (e) { if (isNavKey(e)) { focused = true; stop(); } });
    // マウス・タッチで操作したら、キーボード操作中の扱いを解除する
    show.addEventListener("mousedown", function () { focused = false; });
    show.addEventListener("touchstart", function () { focused = false; }, { passive: true });
    show.addEventListener("focusout", function (e) {
      if (!show.contains(e.relatedTarget)) { focused = false; start(); }
    });
    document.addEventListener("visibilitychange", start);
    document.addEventListener("lightbox:open", function () { viewing = true; stop(); });
    document.addEventListener("lightbox:close", function () { viewing = false; start(); });

    go(0);
    start();

    // ページの読み込みが終わったら、残りの写真とサムネイルを読み込む（style.css の .slideshow:not(.is-loaded)）
    var loaded = function () { show.classList.add("is-loaded"); };
    if (document.readyState === "complete") { loaded(); } else { window.addEventListener("load", loaded); }
  });

  /* ---------- 画像の拡大表示（ライトボックス） ---------- */
  var links = document.querySelectorAll("a[data-lightbox]");
  if (links.length && typeof HTMLDialogElement === "function") {
    var dialog = document.createElement("dialog");
    dialog.className = "lightbox";
    dialog.setAttribute("aria-label", "拡大画像");
    dialog.innerHTML =
      '<div class="lightbox__stage"><img alt=""></div>' +
      '<button type="button" class="lightbox__prev" aria-label="前へ"></button>' +
      '<button type="button" class="lightbox__next" aria-label="次へ"></button>' +
      '<button type="button" class="lightbox__close" aria-label="閉じる"></button>';
    body.appendChild(dialog);
    var stage = dialog.querySelector(".lightbox__stage");
    var img = dialog.querySelector("img");
    var prev = dialog.querySelector(".lightbox__prev");
    var next = dialog.querySelector(".lightbox__next");
    var group = [];
    var pos = 0;

    var show = function (n) {
      pos = (n + group.length) % group.length;
      img.src = group[pos].getAttribute("href");
      stage.scrollTop = 0;
    };

    each(links, function (a) {
      a.addEventListener("click", function (e) {
        e.preventDefault();
        var name = a.getAttribute("data-lightbox");
        group = Array.prototype.filter.call(links, function (x) { return x.getAttribute("data-lightbox") === name; });
        dialog.classList.toggle("lightbox--doc", a.hasAttribute("data-doc"));
        prev.hidden = next.hidden = group.length < 2;
        show(group.indexOf(a));
        var bar = window.innerWidth - root.clientWidth;
        if (bar > 0) root.style.paddingRight = bar + "px";
        root.classList.add("lightbox-open");
        document.dispatchEvent(new CustomEvent("lightbox:open"));
        dialog.showModal();
      });
    });

    prev.addEventListener("click", function () { show(pos - 1); });
    next.addEventListener("click", function () { show(pos + 1); });
    dialog.querySelector(".lightbox__close").addEventListener("click", function () { dialog.close(); });
    dialog.addEventListener("click", function (e) {
      if (e.target === dialog || e.target === stage) dialog.close();
    });
    dialog.addEventListener("keydown", function (e) {
      // 表などの文書画像：ボタンにフォーカスがあるときも、上下の矢印・PageUp/PageDown・Home/End で縦にスクロールする
      // （表示領域そのものにフォーカスがあるときは、ブラウザのスクロールに任せる）
      if (dialog.classList.contains("lightbox--doc") && e.target !== stage && !(e.altKey || e.ctrlKey || e.metaKey)) {
        var top = stage.scrollTop;
        var pageH = stage.clientHeight * 0.9;
        if (e.key === "ArrowDown" || e.key === "Down") { top += 40; }
        else if (e.key === "ArrowUp" || e.key === "Up") { top -= 40; }
        else if (e.key === "PageDown") { top += pageH; }
        else if (e.key === "PageUp") { top -= pageH; }
        else if (e.key === "Home") { top = 0; }
        else if (e.key === "End") { top = stage.scrollHeight; }
        else { top = null; }
        if (top !== null) {
          stage.scrollTop = top;
          e.preventDefault();
          return;
        }
      }
      if (group.length < 2) return;
      if (e.key === "ArrowLeft") show(pos - 1);
      if (e.key === "ArrowRight") show(pos + 1);
    });
    dialog.addEventListener("close", function () {
      img.removeAttribute("src");
      root.classList.remove("lightbox-open");
      root.style.paddingRight = "";
      document.dispatchEvent(new CustomEvent("lightbox:close"));
    });
  }

  /* ---------- コピーライトの年 ---------- */
  each(document.querySelectorAll(".js-year"), function (el) {
    var y = new Date().getFullYear();
    if (y > parseInt(el.textContent, 10)) el.textContent = String(y);
  });
})();
