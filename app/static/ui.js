/* E-Soko shared building blocks used by several signed-in pages: account panel, overview dashboard, permit form. */
(function (w) {
  "use strict";
  var E = w.E, h = E.h;

  E.i18n({
    en: {
      "fc.title": "Choose your own password", "fc.help": "You were given a temporary password. Choose your own password to continue.", "fc.temp": "Temporary password", "acc.title": "Your account", "acc.password": "Change password", "acc.current": "Current password", "acc.new": "New password (8+ characters)",
      "acc.done": "Password changed.", "acc.err.wrong_current_password": "The current password is not correct.", "acc.err.weak_password": "Use at least 8 characters, different from the old one.",
      "acc.sms": "You sign in with an SMS code, so there is no password to change.",
      "ov.group": "Show", "ov.days": "Period", "ov.district": "District", "ov.sector": "Sector", "ov.d7": "Last 7 days", "ov.d30": "Last 30 days", "ov.d90": "Last 90 days", "ov.d365": "Last year",
      "ov.livestock": "Livestock", "ov.crops": "Crops", "ov.heads_listed": "Animals listed", "ov.heads_available": "Animals waiting for buyers", "ov.heads_sold": "Animals sold",
      "ov.listed": "Listings", "ov.available": "Waiting for buyers", "ov.sold": "Sold", "ov.unsold": "Unsold", "ov.value": "Value sold", "ov.farmers": "Farmers", "ov.keepers": "Livestock keepers",
      "ov.listed_q": "Listed", "ov.avail_q": "Available", "ov.sold_q": "Sold", "ov.avg": "Average price", "ov.nolist": "No listings in this period.",
      "ov.sex": "Animals by sex", "ov.female": "Female", "ov.male": "Male", "ov.village": "By village", "ov.daily": "Listings per day", "ov.items": "listings",
      "permit.title": "Record a document", "permit.type": "Document", "permit.ref": "Reference number", "permit.valid": "Valid until", "permit.note": "Note",
      "permit.none": "No document rules are switched on yet.", "permit.done": "Document recorded.", "permit.hint": "Record only a document you have seen.",
      "rules.name": "Rule", "rules.when": "Checked when", "rules.applies": "Applies to", "rules.state": "State", "rules.issuer": "Issued by",
      "when.listing": "A farmer lists a product", "when.purchase": "A buyer buys", "when.handover": "Payout to the farmer", "when.market_entry": "Entry to the market",
      "applies.all": "Everything", "applies.crop": "All crops", "applies.livestock": "All livestock", "rules.blocking": "Blocks the step", "rules.advisory": "Shown only", "rules.off": "Off",
      "subject.user": "Person", "subject.product": "Product"
    },
    rw: {
      "fc.title": "Hitamo ijambo ry'ibanga ryawe", "fc.help": "Wahawe ijambo ry'ibanga ry'agateganyo. Hitamo irindi ryawe kugira ngo ukomeze.", "fc.temp": "Ijambo ry'ibanga ry'agateganyo", "acc.title": "Konti yawe", "acc.password": "Hindura ijambo ry'ibanga", "acc.current": "Ijambo ry'ibanga risanzwe", "acc.new": "Ijambo ry'ibanga rishya (inyuguti 8+)",
      "acc.done": "Ijambo ry'ibanga rihinduwe.", "acc.err.wrong_current_password": "Ijambo ry'ibanga risanzwe si ryo.", "acc.err.weak_password": "Koresha nibura inyuguti 8, zitandukanye n'izo wakoreshaga.",
      "acc.sms": "Winjira ukoresheje kode ya SMS, nta jambo ry'ibanga ufite ryo guhindura.",
      "ov.group": "Erekana", "ov.days": "Igihe", "ov.district": "Akarere", "ov.sector": "Umurenge", "ov.d7": "Iminsi 7 ishize", "ov.d30": "Iminsi 30 ishize", "ov.d90": "Iminsi 90 ishize", "ov.d365": "Umwaka ushize",
      "ov.livestock": "Amatungo", "ov.crops": "Ibihingwa", "ov.heads_listed": "Amatungo yanditswe", "ov.heads_available": "Amatungo ategereje abaguzi", "ov.heads_sold": "Amatungo yaguzwe",
      "ov.listed": "Ibyanditswe", "ov.available": "Bitegereje abaguzi", "ov.sold": "Byaguzwe", "ov.unsold": "Ibitaguzwe", "ov.value": "Agaciro k'ibyaguzwe", "ov.farmers": "Abahinzi", "ov.keepers": "Aborozi",
      "ov.listed_q": "Byanditswe", "ov.avail_q": "Bihari", "ov.sold_q": "Byaguzwe", "ov.avg": "Impuzandengo y'igiciro", "ov.nolist": "Nta cyanditswe muri iki gihe.",
      "ov.sex": "Amatungo hakurikijwe igitsina", "ov.female": "Ingore", "ov.male": "Ingabo", "ov.village": "Ku mudugudu", "ov.daily": "Ibyanditswe buri munsi", "ov.items": "byanditswe",
      "permit.title": "Andika icyangombwa", "permit.type": "Icyangombwa", "permit.ref": "Nimero y'icyangombwa", "permit.valid": "Gifite agaciro kugeza ku itariki", "permit.note": "Icyitonderwa",
      "permit.none": "Nta tegeko ry'ibyangombwa riraboneka.", "permit.done": "Icyangombwa cyanditswe.", "permit.hint": "Andika gusa icyangombwa wabonye.",
      "rules.name": "Itegeko", "rules.when": "Igihe rigenzurwa", "rules.applies": "Rireba", "rules.state": "Imiterere", "rules.issuer": "Gitangwa na",
      "when.listing": "Umuhinzi yandikisha igicuruzwa", "when.purchase": "Umuguzi agura", "when.handover": "Kwishyura umuhinzi", "when.market_entry": "Kwinjira ku isoko",
      "applies.all": "Byose", "applies.crop": "Ibihingwa byose", "applies.livestock": "Amatungo yose", "rules.blocking": "Rihagarika igikorwa", "rules.advisory": "Riragaragara gusa", "rules.off": "Ntirikora",
      "subject.user": "Umuntu", "subject.product": "Igicuruzwa"
    },
    fr: {
      "fc.title": "Choisissez votre mot de passe", "fc.help": "Un mot de passe temporaire vous a été donné. Choisissez le vôtre pour continuer.", "fc.temp": "Mot de passe temporaire", "acc.title": "Votre compte", "acc.password": "Changer le mot de passe", "acc.current": "Mot de passe actuel", "acc.new": "Nouveau mot de passe (8+ caractères)",
      "acc.done": "Mot de passe modifié.", "acc.err.wrong_current_password": "Le mot de passe actuel est incorrect.", "acc.err.weak_password": "Au moins 8 caractères, différents de l'ancien.",
      "acc.sms": "Vous vous connectez par code SMS : il n'y a pas de mot de passe à changer.",
      "ov.group": "Afficher", "ov.days": "Période", "ov.district": "District", "ov.sector": "Secteur", "ov.d7": "7 derniers jours", "ov.d30": "30 derniers jours", "ov.d90": "90 derniers jours", "ov.d365": "Dernière année",
      "ov.livestock": "Élevage", "ov.crops": "Cultures", "ov.heads_listed": "Animaux enregistrés", "ov.heads_available": "Animaux en attente d'acheteurs", "ov.heads_sold": "Animaux vendus",
      "ov.listed": "Annonces", "ov.available": "En attente d'acheteurs", "ov.sold": "Vendus", "ov.unsold": "Invendus", "ov.value": "Valeur vendue", "ov.farmers": "Agriculteurs", "ov.keepers": "Éleveurs",
      "ov.listed_q": "Enregistré", "ov.avail_q": "Disponible", "ov.sold_q": "Vendu", "ov.avg": "Prix moyen", "ov.nolist": "Aucune annonce sur cette période.",
      "ov.sex": "Animaux par sexe", "ov.female": "Femelles", "ov.male": "Mâles", "ov.village": "Par village", "ov.daily": "Annonces par jour", "ov.items": "annonces",
      "permit.title": "Enregistrer un document", "permit.type": "Document", "permit.ref": "Numéro de référence", "permit.valid": "Valide jusqu'au", "permit.note": "Note",
      "permit.none": "Aucune règle de document n'est activée.", "permit.done": "Document enregistré.", "permit.hint": "N'enregistrez qu'un document que vous avez vu.",
      "rules.name": "Règle", "rules.when": "Contrôlée quand", "rules.applies": "S'applique à", "rules.state": "État", "rules.issuer": "Délivré par",
      "when.listing": "Un agriculteur enregistre un produit", "when.purchase": "Un acheteur achète", "when.handover": "Paiement de l'agriculteur", "when.market_entry": "Entrée au marché",
      "applies.all": "Tout", "applies.crop": "Toutes les cultures", "applies.livestock": "Tout l'élevage", "rules.blocking": "Bloque l'étape", "rules.advisory": "Affichée seulement", "rules.off": "Désactivée",
      "subject.user": "Personne", "subject.product": "Produit"
    }
  });

  /* ------------------------------------------------------------ cached lookups */
  var catP = null, locP = null;
  E.cats = function () { return catP || (catP = E.api("/categories", { anon: true }).catch(function () { catP = null; return []; })); };
  E.locs = function () { return locP || (locP = E.api("/locations", { anon: true }).catch(function () { locP = null; return []; })); };
  E.catName = function (cats, code) {
    for (var i = 0; i < cats.length; i++) if (cats[i].code === code) return E.name(cats[i]);
    return code;
  };
  E.unitName = function (u) { return E.t("unit." + u); };
  E.i18n({
    en: { "unit.sack": "sacks", "unit.bunch": "bunches", "unit.kg": "kg", "unit.head": "head" },
    rw: { "unit.sack": "imifuka", "unit.bunch": "ibitoki", "unit.kg": "kg", "unit.head": "imitwe" },
    fr: { "unit.sack": "sacs", "unit.bunch": "régimes", "unit.kg": "kg", "unit.head": "têtes" }
  });
  E.villageOptions = function (locs) {
    return locs.map(function (l) { return [String(l.id), l.village + " (" + l.sector + ")"]; });
  };

  /* ------------------------------------------------------------ account panel */
  /** Shown when a SuperAdmin/Admin gave this person a temporary password: nothing else works until they choose their own. */
  E.forceChange = function () {
    E.modal(E.t("fc.title"), function () {
      var cur = h("input", { type: "password", autocomplete: "current-password" });
      var nw = h("input", { type: "password", autocomplete: "new-password" });
      var err = h("div", { class: "err", role: "alert" });
      var btn = h("button", { class: "btn", text: E.t("save") });
      var out = h("button", { class: "btn sec", text: E.t("out"), on: { click: function () { E.session.clear(); window.location.replace("/"); } } });
      btn.addEventListener("click", function () {
        err.textContent = "";
        E.busy(btn, function () {
          return E.api("/auth/change-password", { body: { current: cur.value, new: nw.value } }).then(function () { window.location.reload(); });
        }).catch(function (e) { var k = "acc.err." + e.message; err.textContent = E.t(k) === k ? E.err(e) : E.t(k); });
      });
      return h("div", null, h("p", { text: E.t("fc.help") }), E.field(E.t("fc.temp"), cur), E.field(E.t("acc.new"), nw), err,
        h("div", { class: "actions" }, out, btn));
    }, true);
  };

  E.accountPanel = function (user, canChangePassword) {
    var cur = h("input", { type: "password", autocomplete: "current-password" });
    var nw = h("input", { type: "password", autocomplete: "new-password" });
    var msg = h("div", { class: "okmsg", role: "status" });
    var err = h("div", { class: "err", role: "alert" });
    var btn = h("button", { class: "btn", text: E.t("save") });
    btn.addEventListener("click", function () {
      err.textContent = ""; msg.textContent = "";
      E.api("/auth/change-password", { body: { current: cur.value, new: nw.value } }).then(function () {
        msg.textContent = E.t("acc.done"); cur.value = ""; nw.value = "";
      }).catch(function (e) { var k = "acc.err." + e.message; err.textContent = E.t(k) === k ? E.err(e) : E.t(k); });
    });
    return E.section(E.t("acc.title"), null, h("div", { class: "panel", style: "max-width:480px" },
      h("p", null, h("b", { text: user.name }), h("br"), h("span", { class: "muted", text: user.phone + "  " + E.t("role." + user.role) })),
      canChangePassword === false ? h("p", { class: "muted", text: E.t("acc.sms") }) : [
        h("h3", { text: E.t("acc.password") }),
        E.field(E.t("acc.current"), cur), E.field(E.t("acc.new"), nw), h("p", null, btn), msg, err]));
  };

  /* ------------------------------------------------------------ rules (read-only table) */
  E.rulesTable = function (rules) {
    return E.table([
      { label: E.t("rules.name"), render: function (r) { return h("div", null, h("b", { text: E.name(r) }), h("div", { class: "muted small", text: r.code })); } },
      { label: E.t("rules.when"), render: function (r) { return E.t("when." + r.required_at); } },
      { label: E.t("rules.applies"), render: function (r) { return E.t("applies." + r.applies_to) === "applies." + r.applies_to ? r.applies_to : E.t("applies." + r.applies_to); } },
      { label: E.t("rules.issuer"), key: "issuer" },
      { label: E.t("rules.state"), render: function (r) { return r.active ? E.status(r.mandatory ? "bad" : "wait", E.t(r.mandatory ? "rules.blocking" : "rules.advisory")) : E.status("", E.t("rules.off")); } }
    ], rules);
  };

  /* ------------------------------------------------------------ record a document (permit) */
  /** opts: {subject:'product'|'user', product_id, user_id, role:'farmer'|'buyer', onDone} */
  E.permitModal = function (opts) {
    return E.api("/agent/permit-types").then(function (types) {
      var list = types.filter(function (t) { return t.subject === opts.subject && (opts.subject === "product" || !t.role_scope || t.role_scope === (opts.role || "farmer")); });
      E.modal(E.t("permit.title"), function (close) {
        if (!list.length) return h("div", null, h("p", { text: E.t("permit.none") }), h("div", { class: "actions" }, h("button", { class: "btn", text: E.t("close"), on: { click: close } })));
        var type = E.select(list.map(function (t) { return [t.code, E.name(t)]; }));
        var ref = h("input", { maxlength: "60" }), until = h("input", { type: "date" }), note = h("input", { maxlength: "120" });
        var err = h("div", { class: "err", role: "alert" });
        var ok = h("button", { class: "btn", text: E.t("save") });
        ok.addEventListener("click", function () {
          err.textContent = "";
          E.busy(ok, function () {
            return E.api("/agent/permits", { body: { type_code: type.value, user_id: opts.user_id || null, product_id: opts.product_id || null,
              reference: ref.value || null, valid_until: until.value || null, note: note.value || null } })
              .then(function () { close(); E.toast(E.t("permit.done")); if (opts.onDone) opts.onDone(); });
          }).catch(function () {});
        });
        return h("div", null, h("p", { class: "muted small", text: E.t("permit.hint") }),
          E.field(E.t("permit.type"), type), E.field(E.t("permit.ref"), ref), E.field(E.t("permit.valid"), until), E.field(E.t("permit.note"), note), err,
          h("div", { class: "actions" }, h("button", { class: "btn sec", text: E.t("cancel"), on: { click: close } }), ok));
      });
    }).catch(function (e) { E.toast(E.err(e), true); });
  };

  /* ------------------------------------------------------------ overview (crops + livestock) */
  E.overview = function (el) {
    var st = { group: "", days: "30", district: "", sector: "" }, locs = [];
    var bar = h("div", { class: "filters" }), body = h("div");
    E.add(el, [bar, body]);

    function controls() {
      var grp = E.select([["", E.t("all")], ["livestock", E.t("ov.livestock")], ["crop", E.t("ov.crops")]], st.group);
      var days = E.select([["7", E.t("ov.d7")], ["30", E.t("ov.d30")], ["90", E.t("ov.d90")], ["365", E.t("ov.d365")]], st.days);
      var districts = [""].concat(Array.from(new Set(locs.map(function (l) { return l.district; }))).sort());
      var dist = E.select(districts.map(function (d) { return [d, d || E.t("all")]; }), st.district);
      var sectors = [""].concat(Array.from(new Set(locs.filter(function (l) { return !st.district || l.district === st.district; }).map(function (l) { return l.sector; }))).sort());
      var sec = E.select(sectors.map(function (d) { return [d, d || E.t("all")]; }), st.sector);
      function go() { st = { group: grp.value, days: days.value, district: dist.value, sector: (dist.value !== st.district ? "" : sec.value) }; controls(); load(); }
      [grp, days, dist, sec].forEach(function (s) { s.addEventListener("change", go); });
      E.fill(bar, [E.field(E.t("ov.group"), grp, "f-wrap"), E.field(E.t("ov.days"), days, "f-wrap"), E.field(E.t("ov.district"), dist, "f-wrap"), E.field(E.t("ov.sector"), sec, "f-wrap"),
        h("button", { class: "btn sec", text: E.t("refresh"), on: { click: load } })]);
    }

    function catTable(d, grp) {
      var rows = d.categories.filter(function (c) { return c.grp === grp && c.listed_items > 0; });
      return E.table([
        { label: E.t("product"), render: function (c) { return E.name(c); } },
        { label: E.t("ov.listed_q"), num: true, render: function (c) { return E.num(c.listed_qty) + " " + E.unitName(c.unit); } },
        { label: E.t("ov.avail_q"), num: true, render: function (c) { return E.num(c.available_qty); } },
        { label: E.t("ov.sold_q"), num: true, render: function (c) { return E.num(c.sold_qty); } },
        { label: E.t("ov.unsold"), num: true, render: function (c) { return E.num(c.unsold_items); } },
        { label: E.t("ov.avg"), num: true, render: function (c) { return E.money(c.avg_price); } },
        { label: E.t("ov.value"), num: true, render: function (c) { return E.money(c.sold_value); } }
      ], rows, E.t("ov.nolist"));
    }

    function render(d) {
      var out = [], L = d.totals.livestock, C = d.totals.crop;
      if (L) {
        out.push(E.section(E.t("ov.livestock"), null, [
          E.kpis([{ label: E.t("ov.heads_listed"), value: E.num(L.heads_listed), tone: "soil" }, { label: E.t("ov.heads_available"), value: E.num(L.heads_available) },
            { label: E.t("ov.heads_sold"), value: E.num(L.heads_sold) }, { label: E.t("ov.value"), value: E.money(L.sold_value) }, { label: E.t("ov.keepers"), value: E.num(L.active_farmers) }]),
          catTable(d, "livestock")]));
        var sx = d.livestock_by_sex || {}, tot = (sx.female || 0) + (sx.male || 0);
        if (tot > 0) {
          out.push(E.section(E.t("ov.sex"), null, h("div", { class: "panel" }, ["female", "male"].map(function (k) {
            return h("div", { class: "hbar" }, h("span", { class: "nm", text: E.t("ov." + k) }),
              h("span", { class: "tr" }, h("span", { class: "fl soil", style: "display:block;width:" + Math.round(100 * (sx[k] || 0) / tot) + "%" })),
              h("span", { class: "vl", text: E.num(sx[k] || 0) }));
          }))));
        }
      }
      if (C) {
        out.push(E.section(E.t("ov.crops"), null, [
          E.kpis([{ label: E.t("ov.listed"), value: E.num(C.listed_items), tone: "accent" }, { label: E.t("ov.available"), value: E.num(C.available_items) },
            { label: E.t("ov.sold"), value: E.num(C.sold_items) }, { label: E.t("ov.unsold"), value: E.num(C.unsold_items) },
            { label: E.t("ov.value"), value: E.money(C.sold_value) }, { label: E.t("ov.farmers"), value: E.num(C.active_farmers) }]),
          catTable(d, "crop")]));
      }
      var vmax = Math.max.apply(null, d.by_village.map(function (v) { return v.items; }).concat([1]));
      out.push(E.section(E.t("ov.village"), null, d.by_village.length ? h("div", { class: "panel" }, d.by_village.slice(0, 12).map(function (v) {
        return h("div", { class: "hbar" }, h("span", { class: "nm", text: v.village + " (" + E.t("ov." + (v.grp === "crop" ? "crops" : "livestock")) + ")" }),
          h("span", { class: "tr" }, h("span", { class: "fl" + (v.grp === "livestock" ? " soil" : ""), style: "display:block;width:" + Math.max(2, Math.round(100 * v.items / vmax)) + "%" })),
          h("span", { class: "vl", text: E.num(v.items) }));
      })) : E.empty(E.t("ov.nolist"))));
      var byDay = {};
      d.daily.forEach(function (r) { byDay[r.day] = (byDay[r.day] || 0) + r.items; });
      var days = Object.keys(byDay).sort(), dmax = Math.max.apply(null, days.map(function (k) { return byDay[k]; }).concat([1]));
      out.push(E.section(E.t("ov.daily"), null, days.length ? h("div", { class: "panel" },
        h("div", { class: "days", role: "img", "aria-label": E.t("ov.daily") }, days.map(function (k) {
          return h("div", { class: "d", title: k + ": " + byDay[k] + " " + E.t("ov.items"), style: "height:" + Math.max(4, Math.round(100 * byDay[k] / dmax)) + "%" });
        })), h("div", { class: "days-axis" }, h("span", { text: days[0] }), h("span", { text: days[days.length - 1] }))) : E.empty(E.t("ov.nolist"))));
      E.fill(body, out);
    }

    function load() {
      E.fill(body, E.loading());
      var q = "?days=" + st.days + (st.group ? "&group=" + st.group : "") + (st.sector ? "&sector=" + encodeURIComponent(st.sector) : "") +
        (st.district ? "&district=" + encodeURIComponent(st.district) : "");
      E.api("/dashboard/overview" + q).then(render).catch(function (e) {
        E.fill(body, h("div", { class: "notice bad" }, E.err(e), " ", h("button", { class: "link", text: E.t("retry"), on: { click: load } })));
      });
    }
    E.locs().then(function (l) { locs = l; controls(); load(); });
    E.onLang(function () { controls(); load(); });
  };
})(window);
