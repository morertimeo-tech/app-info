/* Infos du jour — app mobile (une seule page, sans rechargement). */
(function () {
  "use strict";

  var DATA = JSON.parse(document.getElementById("data").textContent);
  var CATS = DATA.categories;
  var view = document.getElementById("view");
  var navbar = document.getElementById("navbar");
  var navTitle = document.getElementById("navbar-title");
  var sheet = document.getElementById("sheet");
  var sheetBody = document.getElementById("sheet-body");
  var backdrop = document.getElementById("backdrop");

  /* ---------------- Outils ---------------- */
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function plural(n, word) { return n + " " + word + (n > 1 ? "s" : ""); }
  function catById(id) { for (var i = 0; i < CATS.length; i++) if (CATS[i].id === id) return CATS[i]; return null; }
  function findStory(id) {
    for (var i = 0; i < CATS.length; i++)
      for (var j = 0; j < CATS[i].stories.length; j++)
        if (CATS[i].stories[j].id === id) return { cat: CATS[i], story: CATS[i].stories[j] };
    var saved = store.saved()[id];
    return saved ? { cat: saved.cat, story: saved.story, archived: true } : null;
  }
  function pct(v, d) {
    if (v == null) return "—";
    var s = (v >= 0 ? "+" : "−") + Math.abs(v).toFixed(d == null ? 2 : d).replace(".", ",");
    return s + " %";
  }
  function hue(str) { var h = 0; for (var i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) % 360; return h; }
  function avatar(source) {
    var letter = source.replace(/^(le|la|les|l')\s*/i, "").charAt(0).toUpperCase() || "?";
    return '<span class="av" style="background:hsl(' + hue(source) + ' 55% 46%)">' + esc(letter) + "</span>";
  }
  function icon(name) {
    var p = {
      chev: '<path d="m9 18 6-6-6-6"/>',
      close: '<path d="M18 6 6 18M6 6l12 12"/>',
      share: '<path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><path d="m16 6-4-4-4 4M12 2v13"/>',
      bookmark: '<path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"/>',
      ext: '<path d="M15 3h6v6M10 14 21 3M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
      moon: '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
      chart: '<path d="M22 7 13.5 15.5 8.5 10.5 2 17"/><path d="M16 7h6v6"/>'
    }[name];
    return '<svg viewBox="0 0 24 24" aria-hidden="true">' + p + "</svg>";
  }
  function sparkline(values, cls) {
    if (!values || values.length < 2) return "";
    var lo = Math.min.apply(null, values), hi = Math.max.apply(null, values), span = hi - lo || 1;
    var pts = values.map(function (v, i) {
      return (i * 100 / (values.length - 1)).toFixed(1) + "," + (26 - (v - lo) / span * 23).toFixed(1);
    });
    return '<svg class="spark ' + cls + '" viewBox="0 0 100 28" preserveAspectRatio="none" aria-hidden="true">' +
      '<polyline points="' + pts.join(" ") + '" stroke-width="2" vector-effect="non-scaling-stroke"/></svg>';
  }
  function trendClass(v) { return v == null ? "na" : v >= 0 ? "up" : "down"; }

  var toastTimer;
  function toast(msg) {
    var t = document.getElementById("toast");
    t.textContent = msg; t.classList.add("show");
    clearTimeout(toastTimer); toastTimer = setTimeout(function () { t.classList.remove("show"); }, 1800);
  }
  function haptic() { try { if (navigator.vibrate) navigator.vibrate(8); } catch (e) {} }

  /* ---------------- Stockage local (lus, enregistrés, préférences) ---------------- */
  var store = (function () {
    function get(k, d) { try { var v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } }
    function set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
    var readKey = "infos:lus:" + DATA.date;
    try { // nettoie les jours précédents
      for (var i = localStorage.length - 1; i >= 0; i--) {
        var k = localStorage.key(i);
        if (k && k.indexOf("infos:lus:") === 0 && k !== readKey) localStorage.removeItem(k);
      }
    } catch (e) {}
    var read = get(readKey, {});
    return {
      isRead: function (id) { return !!read[id]; },
      markRead: function (id) { if (!read[id]) { read[id] = 1; set(readKey, read); } },
      saved: function () { return get("infos:enregistres", {}); },
      isSaved: function (id) { return !!get("infos:enregistres", {})[id]; },
      toggleSaved: function (cat, story) {
        var all = get("infos:enregistres", {});
        if (all[story.id]) delete all[story.id];
        else all[story.id] = { at: Date.now(), date: DATA.date, story: story,
          cat: { id: cat.id, title: cat.title, short: cat.short, emoji: cat.emoji, color: cat.color } };
        var keys = Object.keys(all).sort(function (a, b) { return all[b].at - all[a].at; });
        keys.slice(100).forEach(function (k) { delete all[k]; }); // 100 max
        set("infos:enregistres", all);
        return !!all[story.id];
      },
      pref: function (k, d) { return get("infos:pref:" + k, d); },
      setPref: function (k, v) { set("infos:pref:" + k, v); }
    };
  })();

  function unreadCount(cat) {
    return cat.stories.filter(function (s) { return !store.isRead(s.id); }).length;
  }
  function totalRead() {
    var n = 0; CATS.forEach(function (c) { c.stories.forEach(function (s) { if (store.isRead(s.id)) n++; }); }); return n;
  }

  /* ---------------- Composants ---------------- */
  function storyCard(cat, s, i) {
    var read = store.isRead(s.id), saved = store.isSaved(s.id);
    var srcs = s.sources.slice(0, 3).map(avatar).join("");
    return '<button class="card tap' + (read ? " read" : "") + '" style="--c:' + cat.color + '" data-story="' + esc(s.id) + '">' +
      '<div class="top"><span class="num">' + (i + 1) + '</span><span>' + esc(s.time) + "</span>" +
      (read ? "" : '<span class="new">Nouveau</span>') + "</div>" +
      "<h3>" + esc(s.title) + "</h3><p>" + esc(s.summary) + "</p>" +
      '<div class="foot"><span class="avatars">' + srcs + '</span><span class="src">' +
      esc(s.sources.join(" · ")) + "</span>" + (saved ? icon("bookmark").replace("<svg", '<svg class="on"') : "") +
      "</div></button>";
  }
  function storyRow(cat, s, i) {
    return '<button class="row tap' + (store.isRead(s.id) ? " read" : "") + '" style="--c:' + cat.color + '" data-story="' + esc(s.id) + '">' +
      '<span class="num">' + (i + 1) + '</span><span class="main"><span class="t">' + esc(s.title) + '</span>' +
      '<span class="s">' + esc(plural(s.sources.length, "source")) + " · " + esc(s.time) + "</span></span>" +
      '<span class="dot"></span></button>';
  }
  function emptyState(ic, title, text) {
    return '<div class="empty"><div class="icon">' + icon(ic) + "</div><h3>" + esc(title) + "</h3><p>" + esc(text) + "</p></div>";
  }

  /* ---------------- Vues ---------------- */
  function viewToday() {
    var total = DATA.stats.stories, done = totalRead();
    var C = 2 * Math.PI * 22, ratio = total ? done / total : 0;
    var html = '<div class="large-title"><div class="eyebrow">' + esc(DATA.dateLong) + "</div><h1>" + esc(DATA.greeting) + " 👋</h1></div>";

    html += '<section class="brief"><div class="brief-top"><div><h2>Ton brief du jour</h2><p>' +
      esc(total ? "L'essentiel des dernières 24h en " + DATA.readingMinutes + " min" : "Rien de neuf pour l'instant") + "</p></div>" +
      '<div class="ring" aria-label="' + done + " sujets lus sur " + total + '"><svg viewBox="0 0 54 54"><circle class="track" cx="27" cy="27" r="22"/>' +
      '<circle class="prog" cx="27" cy="27" r="22" stroke-dasharray="' + C.toFixed(1) + '" stroke-dashoffset="' + (C * (1 - ratio)).toFixed(1) + '"/></svg>' +
      "<b>" + done + "/" + total + "</b></div></div>" +
      '<div class="brief-stats"><div><b>' + total + "</b><span>sujets</span></div><div><b>" + DATA.stats.articles +
      "</b><span>articles</span></div><div><b>" + DATA.stats.sources + "</b><span>sources</span></div></div></section>";

    var withStories = CATS.filter(function (c) { return c.stories.length; });
    if (withStories.length) {
      var heroCat = withStories[0], hero = heroCat.stories[0];
      html += '<div class="section-head"><h2>À la une</h2></div>';
      html += '<button class="hero tap" style="--c:' + heroCat.color + '" data-emoji="' + esc(heroCat.emoji) + '" data-story="' + esc(hero.id) + '">' +
        '<span class="tag">' + esc(heroCat.short) + "</span><h3>" + esc(hero.title) + "</h3><p>" + esc(hero.summary) + "</p>" +
        '<span class="meta">' + esc(hero.sources.join(" · ")) + "</span></button>";
      if (withStories.length > 1) {
        html += '<div class="rail" style="margin-top:12px">' + withStories.slice(1).map(function (c) {
          var s = c.stories[0];
          return '<button class="mini tap' + (store.isRead(s.id) ? " read" : "") + '" style="--c:' + c.color + '" data-story="' + esc(s.id) + '">' +
            '<span class="cat">' + esc(c.emoji + " " + c.short) + "</span><h4>" + esc(s.title) + "</h4>" +
            '<span class="meta">' + esc(plural(s.sources.length, "source")) + " · " + esc(s.time) + "</span></button>";
        }).join("") + "</div>";
      }
    }

    CATS.forEach(function (c) {
      html += '<div class="section-head"><h2>' + esc(c.emoji) + " " + esc(c.title) + '</h2><a class="see" href="#/rubriques/' + esc(c.id) + '">Tout' + icon("chev") + "</a></div>";
      if (c.stories.length) html += '<div class="group">' + c.stories.slice(0, 3).map(function (s, i) { return storyRow(c, s, i); }).join("") + "</div>";
      else html += '<div class="group"><div class="row"><span class="main"><span class="s">Rien de nouveau sur les dernières 24h.</span></span></div></div>';
    });

    if (DATA.quotes.length) {
      html += '<div class="section-head"><h2>Marchés</h2><a class="see" href="#/marches">Tout' + icon("chev") + "</a></div>";
      html += '<div class="rail">' + DATA.quotes.slice(0, 8).map(function (q) {
        var v = q.change["1j"], cls = trendClass(v);
        return '<a class="tick tap" href="#/marches"><div class="n">' + esc(q.name) + '</div><div class="p">' + esc(q.price) +
          '</div><div class="chg ' + cls + '">' + pct(v) + "</div>" + sparkline(q.history.slice(-6), cls) + "</a>";
      }).join("") + "</div>";
    }
    html += footnote();
    return { title: "Aujourd'hui", html: html };
  }

  function viewRubriques(catId) {
    var cat = catById(catId) || catById(store.pref("rubrique", CATS[0].id)) || CATS[0];
    store.setPref("rubrique", cat.id);
    var html = '<div class="large-title"><div class="eyebrow">' + esc(DATA.dateLong) + "</div><h1>Rubriques</h1></div>";
    html += '<div class="chips-bar"><div class="chips" role="tablist">' + CATS.map(function (c) {
      var n = unreadCount(c);
      return '<a class="chip tap" role="tab" style="--c:' + c.color + '" aria-selected="' + (c.id === cat.id) + '" href="#/rubriques/' + esc(c.id) + '">' +
        esc(c.emoji) + " " + esc(c.short) + (n ? '<span class="badge">' + n + "</span>" : "") + "</a>";
    }).join("") + "</div></div>";

    html += '<div id="cat-content" style="--c:' + cat.color + '">';
    if (cat.overview) {
      html += '<div class="overview"><div class="k">L\'essentiel · ' + esc(cat.title) + "</div><p>" + esc(cat.overview) + "</p>" +
        '<div class="m">' + esc(plural(cat.stories.length, "sujet")) + " · " + esc(plural(cat.articleCount, "article")) + " analysés</div></div>";
    }
    if (cat.stories.length) {
      html += '<div class="cards">' + cat.stories.map(function (s, i) { return storyCard(cat, s, i); }).join("") + "</div>";
    } else {
      html += emptyState("moon", "C'est calme", "Aucun article dans cette rubrique sur les dernières 24h.");
    }
    if (cat.id === "tech" && DATA.quotes.length) {
      html += '<div class="section-head"><h2>Cours de bourse</h2><a class="see" href="#/marches">Tout' + icon("chev") + "</a></div>" +
        quoteList(DATA.quotes.slice(0, 5), "1j");
    }
    html += "</div>" + footnote();
    return { title: cat.title, html: html, after: function () {
      var sel = view.querySelector('.chip[aria-selected="true"]');
      if (sel && sel.scrollIntoView) sel.scrollIntoView({ inline: "center", block: "nearest" });
      enableSwipe(cat);
    } };
  }

  function quoteList(quotes, period) {
    return '<div class="group">' + quotes.map(function (q) {
      var v = q.change[period], cls = trendClass(v);
      var hist = period === "1j" ? q.history.slice(-2) : period === "5j" ? q.history.slice(-6) : q.history;
      var tick = q.symbol.replace("^", "").replace(".PA", "").slice(0, 5);
      return '<a class="row qrow tap" href="' + esc(q.link) + '" target="_blank" rel="noopener">' +
        '<span class="ticker">' + esc(tick) + '</span><span class="main"><span class="t">' + esc(q.name) + '</span><span class="s">' + esc(q.symbol) + "</span></span>" +
        sparkline(hist, cls) + '<span class="r"><div class="p">' + esc(q.price) + '</div><span class="pill ' + cls + '">' + pct(v) + "</span></span></a>";
    }).join("") + "</div>";
  }

  function viewMarches() {
    var period = store.pref("periode", "1j");
    var labels = { "1j": "1 jour", "5j": "5 jours", "1m": "1 mois" };
    var html = '<div class="large-title"><div class="eyebrow">Cours différés</div><h1>Marchés</h1></div>';
    if (!DATA.quotes.length) return { title: "Marchés", html: html + emptyState("chart", "Cours indisponibles", "Les cours n'ont pas pu être récupérés aujourd'hui.") };
    html += '<div class="segmented" role="group" aria-label="Période">' + ["1j", "5j", "1m"].map(function (p) {
      return '<button data-period="' + p + '" aria-pressed="' + (p === period) + '">' + labels[p] + "</button>";
    }).join("") + "</div>";
    html += '<div id="quotes">' + quoteList(DATA.quotes, period) + "</div>";
    var tech = catById("tech");
    if (tech && tech.stories.length) {
      html += '<div class="section-head"><h2>' + esc(tech.emoji) + ' Actus tech</h2><a class="see" href="#/rubriques/tech">Tout' + icon("chev") + "</a></div>";
      html += '<div class="group">' + tech.stories.slice(0, 3).map(function (s, i) { return storyRow(tech, s, i); }).join("") + "</div>";
    }
    html += '<p class="footnote">Données Yahoo Finance, différées et fournies à titre indicatif. Mise à jour à ' + esc(DATA.generatedAt) + ".</p>";
    return { title: "Marchés", html: html };
  }

  function viewEnregistres() {
    var all = store.saved();
    var items = Object.keys(all).map(function (k) { return all[k]; }).sort(function (a, b) { return b.at - a.at; });
    var html = '<div class="large-title"><div class="eyebrow">' + esc(plural(items.length, "sujet")) + "</div><h1>Enregistrés</h1></div>";
    if (!items.length) return { title: "Enregistrés", html: html + emptyState("bookmark", "Aucun sujet enregistré", "Touche « Enregistrer » sur un sujet pour le retrouver ici, même les jours suivants.") };
    html += '<div class="cards" style="margin-top:12px">' + items.map(function (it, i) {
      return storyCard(it.cat, it.story, i).replace('<span class="num">' + (i + 1) + "</span>",
        '<span class="num">' + esc(it.cat.emoji + " " + it.cat.short) + "</span>");
    }).join("") + "</div>";
    return { title: "Enregistrés", html: html };
  }

  function footnote() {
    return '<p class="footnote">' + (DATA.aiGenerated
      ? "Résumés rédigés par IA à partir des titres et chapôs des articles : vérifie les détails importants dans les sources."
      : "Résumés = chapôs fournis par les journaux.") + "<br>Mis à jour le " + esc(DATA.dateLong) + " à " + esc(DATA.generatedAt) + ".</p>";
  }

  /* ---------------- Fiche d'un sujet ---------------- */
  var sheetOpenedByPush = false;

  function renderSheet(found) {
    var cat = found.cat, s = found.story, saved = store.isSaved(s.id);
    sheet.style.setProperty("--c", cat.color);
    var html = '<div class="sheet-top"><span class="cat">' + esc(cat.emoji) + " " + esc(cat.short) + "</span>" +
      '<button class="icon-btn" data-close aria-label="Fermer">' + icon("close") + "</button></div>" +
      '<h2 id="sheet-title">' + esc(s.title) + "</h2>" +
      '<div class="meta">' + esc(plural(s.sources.length, "source")) + " · " + (found.archived ? "enregistré" : "mis à jour à " + esc(s.time)) + "</div>" +
      '<p class="summary">' + esc(s.summary) + "</p>" +
      '<div class="actions"><button class="action tap' + (saved ? " on" : "") + '" data-save>' + icon("bookmark") + "<span>" + (saved ? "Enregistré" : "Enregistrer") + "</span></button>" +
      '<button class="action tap" data-share>' + icon("share") + "<span>Partager</span></button></div>" +
      '<div class="group-title">Lire dans la presse · ' + s.articles.length + "</div>" +
      '<div class="group">' + s.articles.map(function (a) {
        var link = /^https?:\/\//.test(a.link) ? a.link : "#";
        return '<a class="row src-row" href="' + esc(link) + '" target="_blank" rel="noopener">' + avatar(a.source) +
          '<span class="main"><span class="t">' + esc(a.title) + '</span><span class="s">' + esc(a.source) + " · " + esc(a.time) + "</span></span>" +
          icon("ext").replace("<svg", '<svg class="ext"') + "</a>";
      }).join("") + "</div>" +
      (DATA.aiGenerated ? '<p class="disclaimer">Résumé généré automatiquement à partir des articles ci-dessus.</p>' : "");
    sheetBody.innerHTML = html;
    sheetBody.scrollTop = 0;
  }

  function openSheet(found) {
    renderSheet(found);
    store.markRead(found.story.id);
    sheet.hidden = false; backdrop.hidden = false;
    document.body.classList.add("locked");
    requestAnimationFrame(function () { requestAnimationFrame(function () {
      sheet.classList.add("open"); backdrop.classList.add("open");
      var c = sheet.querySelector("[data-close]"); if (c) c.focus({ preventScroll: true });
    }); });
  }
  function hideSheet() {
    if (sheet.hidden) return;
    sheet.classList.remove("open"); backdrop.classList.remove("open");
    sheet.style.transform = "";
    document.body.classList.remove("locked");
    setTimeout(function () { if (!sheet.classList.contains("open")) { sheet.hidden = true; backdrop.hidden = true; } }, 380);
    refreshReadState();
  }
  function requestClose() {
    if (sheetOpenedByPush) history.back();
    else location.replace(location.hash.split("~")[0] || "#/");
  }

  sheet.addEventListener("click", function (e) {
    if (e.target.closest("[data-close]")) { requestClose(); return; }
    var found = findStory(currentStoryId);
    if (!found) return;
    if (e.target.closest("[data-save]")) {
      var on = store.toggleSaved(found.cat, found.story);
      haptic(); toast(on ? "Ajouté aux enregistrés" : "Retiré des enregistrés");
      renderSheet(found);
    } else if (e.target.closest("[data-share]")) {
      var first = found.story.articles[0];
      var payload = { title: found.story.title, text: found.story.title + "\n\n" + found.story.summary, url: first ? first.link : location.href };
      if (navigator.share) navigator.share(payload).catch(function () {});
      else if (navigator.clipboard) navigator.clipboard.writeText(payload.text + "\n" + payload.url).then(function () { toast("Copié dans le presse-papiers"); });
    }
  });
  backdrop.addEventListener("click", requestClose);
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !sheet.hidden) requestClose(); });

  // Glisser vers le bas pour fermer
  (function () {
    var startY = null, dy = 0;
    function start(y) { startY = y; dy = 0; sheet.classList.add("dragging"); }
    function move(y) { if (startY == null) return; dy = Math.max(0, y - startY); sheet.style.transform = "translateY(" + dy + "px)"; }
    function end() {
      if (startY == null) return;
      sheet.classList.remove("dragging"); startY = null;
      if (dy > 110) requestClose(); else sheet.style.transform = "";
    }
    var grab = document.getElementById("sheet-grabber");
    grab.addEventListener("touchstart", function (e) { start(e.touches[0].clientY); }, { passive: true });
    sheetBody.addEventListener("touchstart", function (e) { if (sheetBody.scrollTop <= 0) start(e.touches[0].clientY); }, { passive: true });
    window.addEventListener("touchmove", function (e) {
      if (startY == null) return;
      var y = e.touches[0].clientY;
      if (y < startY && dy === 0) { startY = null; sheet.classList.remove("dragging"); return; } // défilement normal
      move(y);
    }, { passive: true });
    window.addEventListener("touchend", end);
  })();

  /* ---------------- Balayage gauche/droite entre rubriques ---------------- */
  function enableSwipe(cat) {
    var el = document.getElementById("cat-content");
    if (!el) return;
    var x0 = null, y0 = null;
    el.addEventListener("touchstart", function (e) { x0 = e.touches[0].clientX; y0 = e.touches[0].clientY; }, { passive: true });
    el.addEventListener("touchend", function (e) {
      if (x0 == null) return;
      var dx = e.changedTouches[0].clientX - x0, dy = e.changedTouches[0].clientY - y0;
      x0 = null;
      if (Math.abs(dx) < 70 || Math.abs(dx) < Math.abs(dy) * 1.5) return;
      var i = CATS.indexOf(cat), next = CATS[(i + (dx < 0 ? 1 : CATS.length - 1)) % CATS.length];
      location.replace("#/rubriques/" + next.id);
    }, { passive: true });
  }

  /* ---------------- Routeur ---------------- */
  var currentStoryId = null, currentRoute = null;

  function parse() {
    var h = location.hash.replace(/^#/, "") || "/";
    var parts = h.split("~");
    var seg = parts[0].split("/").filter(Boolean);
    return { tab: seg[0] || "today", arg: seg[1], story: parts[1] ? decodeURIComponent(parts[1]) : null, base: parts[0] || "/" };
  }

  function renderView(r) {
    var v = r.tab === "rubriques" ? viewRubriques(r.arg)
      : r.tab === "marches" ? viewMarches()
      : r.tab === "enregistres" ? viewEnregistres()
      : viewToday();
    view.innerHTML = v.html;
    view.classList.remove("view-enter"); void view.offsetWidth; view.classList.add("view-enter");
    navTitle.textContent = v.title;
    document.title = v.title + " · Infos du jour";
    document.querySelectorAll(".tabbar a").forEach(function (a) {
      var active = a.dataset.tab === (r.tab === "today" ? "today" : r.tab);
      if (active) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
    });
    updateBadges();
    if (v.after) v.after();
  }

  function route() {
    var r = parse();
    var key = r.tab + "/" + (r.arg || "");
    if (key !== currentRoute) {
      var sameTab = currentRoute && currentRoute.split("/")[0] === r.tab;
      var y = window.scrollY;
      renderView(r);
      currentRoute = key;
      // Changer de rubrique garde la position du sélecteur ; changer d'onglet remonte en haut
      window.scrollTo(0, sameTab && r.tab === "rubriques" ? Math.min(y, view.querySelector(".chips-bar") ? view.querySelector(".chips-bar").offsetTop - 44 : 0) : 0);
      onScroll();
    }
    if (r.story) {
      var found = findStory(r.story);
      if (found) { currentStoryId = r.story; openSheet(found); return; }
    }
    if (currentStoryId) { currentStoryId = null; sheetOpenedByPush = false; hideSheet(); }
  }

  function refreshReadState() {
    var r = parse();
    var y = window.scrollY;
    var rail = view.querySelector(".chips"), railX = rail ? rail.scrollLeft : 0;
    renderView(r);
    view.classList.remove("view-enter");
    window.scrollTo(0, y);
    rail = view.querySelector(".chips"); if (rail) rail.scrollLeft = railX;
  }

  function updateBadges() {
    var n = CATS.reduce(function (acc, c) { return acc + unreadCount(c); }, 0);
    var tab = document.querySelector('.tabbar a[data-tab="rubriques"]');
    var b = tab.querySelector(".count");
    if (n) { if (!b) { b = document.createElement("span"); b.className = "count"; tab.appendChild(b); } b.textContent = n > 99 ? "99+" : n; }
    else if (b) b.remove();
  }

  // Ouvrir un sujet
  view.addEventListener("click", function (e) {
    var el = e.target.closest("[data-story]");
    if (el) {
      e.preventDefault();
      sheetOpenedByPush = true;
      location.hash = parse().base + "~" + encodeURIComponent(el.dataset.story);
      return;
    }
    var seg = e.target.closest("[data-period]");
    if (seg) {
      store.setPref("periode", seg.dataset.period); haptic();
      view.querySelectorAll("[data-period]").forEach(function (b) { b.setAttribute("aria-pressed", b === seg); });
      document.getElementById("quotes").innerHTML = quoteList(DATA.quotes, seg.dataset.period);
    }
  });
  // Toucher l'onglet actif = remonter en haut
  document.querySelector(".tabbar").addEventListener("click", function (e) {
    var a = e.target.closest("a");
    if (a && a.getAttribute("aria-current") === "page") { e.preventDefault(); window.scrollTo({ top: 0, behavior: "smooth" }); }
    haptic();
  });

  function onScroll() { navbar.classList.toggle("scrolled", window.scrollY > 36); }
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("hashchange", route);
  route();
})();
