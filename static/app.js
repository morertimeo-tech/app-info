// Mémorise les sujets déjà consultés (sur cet appareil uniquement).
(function () {
  var KEY = "infos-lues-" + (document.body.dataset.date || "");
  var read = {};
  try { read = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { read = {}; }

  function save() {
    try {
      localStorage.setItem(KEY, JSON.stringify(read));
      // Nettoie les jours précédents
      for (var i = localStorage.length - 1; i >= 0; i--) {
        var k = localStorage.key(i);
        if (k && k.indexOf("infos-lues-") === 0 && k !== KEY) localStorage.removeItem(k);
      }
    } catch (e) { /* stockage indisponible : tant pis */ }
  }

  function mark(story) {
    if (!story || !story.id) return;
    story.classList.add("read");
    read[story.id] = 1;
    save();
  }

  document.querySelectorAll(".story").forEach(function (story) {
    if (read[story.id]) story.classList.add("read");
    var details = story.querySelector("details");
    if (details) details.addEventListener("toggle", function () { if (details.open) mark(story); });
    story.querySelectorAll(".links a").forEach(function (a) {
      a.addEventListener("click", function () { mark(story); });
    });
  });

  // Accueil : nombre de sujets non lus par catégorie
  document.querySelectorAll("[data-unread]").forEach(function (el) {
    var ids = el.dataset.unread ? el.dataset.unread.split(" ") : [];
    var left = ids.filter(function (id) { return !read[id]; }).length;
    if (ids.length && left === 0) el.textContent = "Tout lu ✓";
    else if (left < ids.length) el.textContent = left + " non lu" + (left > 1 ? "s" : "");
  });
})();
