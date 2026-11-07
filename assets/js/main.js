// Repassa os parâmetros de campanha (utm_*, fbclid) da página para o checkout da Greenn
// e registra o clique no Pixel da Meta quando ele estiver ativo.
(function () {
  var params = new URLSearchParams(window.location.search);
  var keep = ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "fbclid"];
  var pass = new URLSearchParams();
  keep.forEach(function (k) { if (params.get(k)) pass.set(k, params.get(k)); });
  if (!pass.has("utm_source")) pass.set("utm_source", "site");

  document.querySelectorAll(".js-checkout").forEach(function (a) {
    var url = new URL(a.getAttribute("href"));
    pass.forEach(function (v, k) { url.searchParams.set(k, v); });
    if (a.dataset.cta) url.searchParams.set("utm_content", (pass.get("utm_content") ? pass.get("utm_content") + "_" : "") + a.dataset.cta);
    a.setAttribute("href", url.toString());
    a.addEventListener("click", function () {
      if (typeof window.fbq === "function") {
        window.fbq("track", "InitiateCheckout", { value: 99, currency: "BRL", content_name: "Diagnostico de Credito" });
      }
    });
  });

  document.querySelectorAll(".js-wa").forEach(function (a) {
    a.addEventListener("click", function () {
      if (typeof window.fbq === "function") window.fbq("track", "Contact", { content_name: "WhatsApp " + (a.dataset.cta || "") });
    });
  });

  // Barra de compra no celular: aparece depois que o topo sai da tela
  var bar = document.querySelector(".mobile-cta");
  var hero = document.querySelector(".hero");
  if (bar && hero && "IntersectionObserver" in window) {
    new IntersectionObserver(function (entries) {
      bar.classList.toggle("is-visible", !entries[0].isIntersecting);
    }, { threshold: 0 }).observe(hero);
  }
})();
