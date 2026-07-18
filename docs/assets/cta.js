(function () {
  "use strict";
  var site = window.SITE || {};
  var noteUrl = (site.noteUrl || "").trim();
  var hasNote = /^https?:\/\//i.test(noteUrl);

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function buildCta(options) {
    options = options || {};
    var box = el("aside", "cta-box");
    box.appendChild(el("p", "cta-kicker", options.kicker || "続きと毎日更新はこちら"));
    box.appendChild(
      el(
        "h2",
        "cta-title",
        options.title || "調査の時短マガジン（有料）"
      )
    );
    box.appendChild(
      el(
        "p",
        "cta-body",
        options.body ||
          "無料ではTop5要約と企業カルテ全文。有料ではTop20全文・順位の前日差分・深掘り更新を配信します。"
      )
    );

    var actions = el("div", "cta-actions");
    if (hasNote) {
      var paid = el("a", "btn btn-primary", site.notePaidLabel || "有料マガジンを見る");
      paid.href = noteUrl;
      paid.target = "_blank";
      paid.rel = "noopener noreferrer";
      actions.appendChild(paid);
    } else {
      var pending = el(
        "span",
        "btn btn-pending",
        "note準備中（開設後にここから登録できます）"
      );
      actions.appendChild(pending);
    }
    var pricing = el("a", "btn btn-ghost", "無料と有料の違い");
    pricing.href = options.pricingHref || "pricing.html";
    actions.appendChild(pricing);
    box.appendChild(actions);

    box.appendChild(el("p", "cta-fine", site.contactNote || ""));
    return box;
  }

  function mount() {
    var slots = document.querySelectorAll("[data-cta]");
    if (!slots.length) {
      var main = document.querySelector("main.wrap");
      if (!main) return;
      var footer = main.querySelector(".footer");
      var box = buildCta({
        pricingHref: (main.dataset.ctaPricing || "pricing.html"),
      });
      if (footer) main.insertBefore(box, footer);
      else main.appendChild(box);
      return;
    }
    slots.forEach(function (slot) {
      slot.replaceWith(
        buildCta({
          kicker: slot.getAttribute("data-cta-kicker"),
          title: slot.getAttribute("data-cta-title"),
          body: slot.getAttribute("data-cta-body"),
          pricingHref: slot.getAttribute("data-cta-pricing") || "pricing.html",
        })
      );
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();
