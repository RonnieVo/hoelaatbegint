/* hoelaatbegint.nl — countdowns en statussen die vanzelf meelopen met de tijd */
(function () {
  var DUR = { darts: 240, voetbal: 120, handbal: 100, f1: 120, hockey: 90, schaatsen: 240, veldrijden: 75 };

  function parts(ms) {
    var m = Math.floor(ms / 60000), d = Math.floor(m / 1440), h = Math.floor((m % 1440) / 60), mm = m % 60;
    if (d >= 2) return d + " dagen";
    if (d === 1) return "1 dag en " + h + " uur";
    if (h >= 1) return h + " uur " + mm + " min";
    return mm + " min";
  }
  function sameDay(a, b) {
    var f = function (x) { return x.toLocaleDateString("nl-NL", { timeZone: "Europe/Amsterdam" }); };
    return f(a) === f(b);
  }
  function tick() {
    var now = new Date();
    document.querySelectorAll("[data-start]").forEach(function (el) {
      var start = new Date(el.getAttribute("data-start"));
      var mins = DUR[el.getAttribute("data-sport")] || 120;
      var end = new Date(start.getTime() + mins * 60000);
      var cd = el.querySelector(".countdown"), badge = el.querySelector(".badge");
      if (now < start) {
        if (cd) cd.textContent = "nog " + parts(start - now);
        if (badge && sameDay(now, start)) { badge.className = "badge today"; badge.textContent = "Vandaag"; }
      } else if (now < end) {
        if (cd) cd.textContent = "is bezig";
        if (badge) { badge.className = "badge live"; badge.textContent = "Bezig"; }
      } else {
        if (cd) cd.textContent = "afgelopen";
        if (badge) { badge.className = "badge"; badge.textContent = "Afgelopen"; }
        el.classList.add("is-past");
      }
    });
    // datumblokken zonder tijd (bijv. "14 t/m 22 december") verbergen als ze voorbij zijn
    document.querySelectorAll("[data-end-date]").forEach(function (el) {
      var end = new Date(el.getAttribute("data-end-date") + "T23:59:59+01:00");
      if (now > end) el.classList.add("is-past");
    });
  }
  tick();
  setInterval(tick, 30000);

  // "Meer sporten" sluiten bij klik ernaast of Escape
  var more = document.querySelector("details.more");
  if (more) {
    document.addEventListener("click", function (e) { if (more.open && !more.contains(e.target)) more.open = false; });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") more.open = false; });
  }

  // Delen via WhatsApp / native share
  document.querySelectorAll("[data-share]").forEach(function (b) {
    b.addEventListener("click", function (e) {
      var text = b.getAttribute("data-share"), url = location.href;
      if (navigator.share) { e.preventDefault(); navigator.share({ text: text, url: url }).catch(function () {}); }
      else { b.href = "https://wa.me/?text=" + encodeURIComponent(text + " " + url); }
    });
  });

  // Pushmeldingen (OneSignal), alleen als het is ingesteld
  document.querySelectorAll("[data-push]").forEach(function (b) {
    if (!window.OneSignalDeferred) { b.hidden = true; return; }
    b.addEventListener("click", function () {
      window.OneSignalDeferred.push(function (OneSignal) {
        OneSignal.Notifications.requestPermission();
        OneSignal.User.addTag(b.getAttribute("data-push"), "1");
      });
    });
  });
})();
