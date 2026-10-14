/* 株式会社野間産業 — サイト共通スクリプト（外部ライブラリなし） */
(function () {
  "use strict";

  var root = document.documentElement;
  var body = document.body;
  var each = function (list, fn) { Array.prototype.forEach.call(list, fn); };

  // 直前の操作がキーボードか、マウス・タッチかを覚えておく
  var usingKeyboard = false;
  var isNavKey = function (e) {
    return !(e.ctrlKey || e.altKey || e.metaKey) && ["Shift", "Control", "Alt", "Meta"].indexOf(e.key) < 0;
  };
  document.addEventListener("keydown", function (e) { if (isNavKey(e)) usingKeyboard = true; }, true);
  document.addEventListener("mousedown", function () { usingKeyboard = false; }, true);
  document.addEventListener("touchstart", function () { usingKeyboard = false; }, { capture: true, passive: true });

  /* ---------- スマートフォン用メニュー ---------- */
  var toggle = document.querySelector(".nav-toggle");
  // メニューを開いている間は、裏にある本文へキーボード操作が移らないようにする
  var behind = document.querySelectorAll(".site-header, .site-body, .site-footer");

  function setMenu(open) {
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
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && body.classList.contains("nav-open")) {
        setMenu(false);
        toggle.focus();
      }
    });
    // 画面幅がPC表示に戻ったら閉じる
    var wide = window.matchMedia && window.matchMedia("(min-width: 768px)");
    var onWide = function (m) { if (m.matches) setMenu(false); };
    if (wide && wide.addEventListener) { wide.addEventListener("change", onWide); }
    else if (wide && wide.addListener) { wide.addListener(onWide); }
  }

  // 子メニューの開閉（初期状態は閉じる。現行サイトと同じ）
  each(document.querySelectorAll(".global-nav__expand"), function (btn) {
    var item = btn.parentNode;
    btn.addEventListener("click", function () {
      var open = item.classList.toggle("is-open");
      btn.setAttribute("aria-expanded", open ? "true" : "false");
    });
  });

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
    var hovered = false;
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
    }

    function stop() {
      if (timer) { clearInterval(timer); timer = null; }
    }

    function start() {
      stop();
      if (!delay || reduce || hovered || focused || viewing || document.hidden) return;
      timer = setInterval(function () { go(index + 1); }, delay);
    }

    show.querySelector(".slideshow__prev").addEventListener("click", function () { go(index - 1); start(); });
    show.querySelector(".slideshow__next").addEventListener("click", function () { go(index + 1); start(); });
    each(thumbs, function (t, i) {
      t.addEventListener("click", function () { go(i); start(); });
    });
    show.addEventListener("pointerenter", function (e) {
      if (e.pointerType === "mouse") { hovered = true; stop(); }
    });
    show.addEventListener("pointerleave", function (e) {
      if (e.pointerType === "mouse") { hovered = false; start(); }
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

    function show(n) {
      pos = (n + group.length) % group.length;
      img.src = group[pos].getAttribute("href");
      stage.scrollTop = 0;
    }

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
