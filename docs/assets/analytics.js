(function () {
  "use strict";
  var site = window.SITE || {};
  var id = (site.umamiWebsiteId || "").trim();
  if (!id) return;
  var src = (site.umamiScriptUrl || "https://cloud.umami.is/script.js").trim();
  if (document.querySelector('script[data-website-id="' + id + '"]')) return;
  var s = document.createElement("script");
  s.defer = true;
  s.src = src;
  s.setAttribute("data-website-id", id);
  document.head.appendChild(s);
})();
