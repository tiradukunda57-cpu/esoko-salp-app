/* E-Soko shared client: session, API, translations, small UI helpers. No framework, no inline scripts (CSP). */
(function (w) {
  "use strict";
  var E = (w.E = {});
  var store = {
    get: function (k) { try { return w.localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { w.localStorage.setItem(k, v); } catch (e) { /* private mode */ } },
    del: function (k) { try { w.localStorage.removeItem(k); } catch (e) { /* private mode */ } }
  };

  /* ------------------------------------------------------------ DOM helpers */
  E.h = function (tag, props) {
    var el = document.createElement(tag), i, k;
    props = props || {};
    for (k in props) {
      if (!Object.prototype.hasOwnProperty.call(props, k) || props[k] === null || props[k] === undefined || props[k] === false) continue;
      if (k === "class") el.className = props[k];
      else if (k === "text") el.textContent = props[k];
      else if (k === "on") { for (var ev in props.on) el.addEventListener(ev, props.on[ev]); }
      else if (k === "value") el.value = props[k];
      else if (k === "checked") el.checked = !!props[k];
      else if (k === "disabled") el.disabled = !!props[k];
      else el.setAttribute(k, props[k] === true ? "" : props[k]);
    }
    for (i = 2; i < arguments.length; i++) E.add(el, arguments[i]);
    return el;
  };
  E.add = function (el, kid) {
    if (kid === null || kid === undefined || kid === false) return el;
    if (Array.isArray(kid)) { kid.forEach(function (x) { E.add(el, x); }); return el; }
    el.appendChild(kid.nodeType ? kid : document.createTextNode(String(kid)));
    return el;
  };
  E.$ = function (id) { return document.getElementById(id); };
  E.clear = function (el) { while (el.firstChild) el.removeChild(el.firstChild); return el; };
  E.fill = function (el, kids) { E.clear(el); E.add(el, kids); return el; };

  /* ------------------------------------------------------------ language */
  var dict = { en: {}, rw: {}, fr: {} };
  E.langs = [["rw", "Kinyarwanda"], ["en", "English"], ["fr", "Français"]];
  E.lang = store.get("esoko_lang") || "rw";
  if (!dict[E.lang]) E.lang = "rw";
  E.i18n = function (add) { Object.keys(add).forEach(function (l) { Object.assign(dict[l] = dict[l] || {}, add[l]); }); };
  E.t = function (key, vars) {
    var s = (dict[E.lang] && dict[E.lang][key]) || dict.en[key] || key;
    if (vars) Object.keys(vars).forEach(function (k) { s = s.split("{" + k + "}").join(vars[k]); });
    return s;
  };
  var langHooks = [];
  E.onLang = function (fn) { langHooks.push(fn); };
  E.setLang = function (l) {
    E.lang = l; store.set("esoko_lang", l); document.documentElement.lang = l;
    E.applyI18n(); langHooks.forEach(function (fn) { fn(l); });
  };
  E.applyI18n = function (root) {
    var r = root || document;
    [].forEach.call(r.querySelectorAll("[data-i]"), function (n) { n.textContent = E.t(n.getAttribute("data-i")); });
    [].forEach.call(r.querySelectorAll("[data-ph]"), function (n) { n.setAttribute("placeholder", E.t(n.getAttribute("data-ph"))); });
    [].forEach.call(r.querySelectorAll("[data-aria]"), function (n) { n.setAttribute("aria-label", E.t(n.getAttribute("data-aria"))); });
  };
  E.langSelect = function () {
    var s = E.h("select", { "aria-label": "Language", on: { change: function () { E.setLang(s.value); } } },
      E.langs.map(function (l) { return E.h("option", { value: l[0], text: l[1] }); }));
    s.value = E.lang;
    return s;
  };
  document.documentElement.lang = E.lang;

  /* ------------------------------------------------------------ formatting */
  E.money = function (n) { return (n === null || n === undefined ? "-" : Number(n).toLocaleString("en-US")) + " Frw"; };
  E.num = function (n) { return n === null || n === undefined ? "-" : Number(n).toLocaleString("en-US"); };
  E.date = function (s) { return s ? String(s).slice(0, 10) : "-"; };
  E.dateTime = function (s) { return s ? String(s).slice(0, 16).replace("T", " ") : "-"; };
  E.name = function (o) { return o["name_" + E.lang] || o.name_en || o.name || ""; };

  /* ------------------------------------------------------------ session + API */
  E.session = {
    token: function () { return store.get("esoko_token"); },
    user: function () { try { return JSON.parse(store.get("esoko_user") || "null"); } catch (e) { return null; } },
    set: function (token, user) { store.set("esoko_token", token); store.set("esoko_user", JSON.stringify(user)); },
    clear: function () { store.del("esoko_token"); store.del("esoko_user"); }
  };
  var HOME = { farmer: "/farmer", buyer: "/buyer", agent: "/agent", gate: "/agent", admin: "/admin", superadmin: "/admin", government: "/dashboard" };
  E.home = function (role) { return HOME[role] || "/"; };
  E.logout = function () { E.session.clear(); w.location.href = "/"; };

  E.api = function (path, opts) {
    opts = opts || {};
    var headers = { Accept: "application/json" }, token = E.session.token();
    if (opts.body !== undefined) headers["Content-Type"] = "application/json";
    if (token && !opts.anon) headers.Authorization = "Bearer " + token;
    return fetch(path, { method: opts.method || (opts.body !== undefined ? "POST" : "GET"), headers: headers,
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined })
      .then(function (r) {
        var ct = r.headers.get("content-type") || "";
        return (ct.indexOf("json") >= 0 ? r.json() : r.text()).catch(function () { return {}; }).then(function (j) {
          if (r.status === 401 && token && !opts.anon) { E.session.clear(); w.location.href = "/?expired=1"; throw new Error("session"); }
          if (!r.ok) {
            var m = (j && (j.error || j.detail)) || r.status;
            if (typeof m !== "string") m = JSON.stringify(m);
            var e = new Error(m); e.status = r.status; throw e;
          }
          return j;
        });
      });
  };

  /** Page guard: confirms the stored token still works and the role may see this page. */
  E.guard = function (roles) {
    if (!E.session.token()) { w.location.replace("/"); return Promise.reject(new Error("no session")); }
    return E.api("/auth/me").then(function (j) {
      var u = j.user;
      E.session.set(E.session.token(), u);
      if (roles.indexOf(u.role) < 0) { w.location.replace(E.home(u.role)); throw new Error("wrong role"); }
      if (u.must_change_password && E.forceChange) { E.forceChange(); return new Promise(function () {}); }
      return u;
    });
  };

  /* ------------------------------------------------------------ friendly errors */
  E.i18n({
    en: {
      "e.wrong phone or password": "Wrong phone number or password.",
      "e.too many attempts": "Too many attempts. Wait a few minutes and try again.",
      "e.duplicate": "This phone number or National ID is already registered.",
      "e.bad_phone": "Enter a valid Rwandan phone number, for example 0788123456.",
      "e.bad_id": "The National ID must have 16 digits.",
      "e.bad_name": "Enter the full name.",
      "e.weak_password": "The password needs at least 8 characters.",
      "e.no_consent": "You must agree that E-Soko stores your data.",
      "e.farmer_not_active": "This farmer has not paid the registration fee yet.",
      "e.buyer_not_active": "Your account is not active yet. Approve the registration payment first.",
      "e.not_available": "Someone else just bought this item.",
      "e.bad_quantity": "Enter a valid quantity.",
      "e.bad_price": "Enter a valid price.",
      "e.tag_already_listed": "This ear-tag number is already listed.",
      "e.outside_agent_area": "This is outside your sector.",
      "e.agent_has_no_area": "Your account has no area yet. Ask the administrator.",
      "e.forbidden": "You are not allowed to do this.",
      "e.new_price_must_be_lower": "The new price must be lower than the listed price.",
      "e.not_ready_for_verification": "This item is not waiting for verification.",
      "e.order_not_verified": "Verify the item first.",
      "e.permit_required": "A government permit is missing: {names}",
      "e.session": "Your session ended. Please sign in again.",
      "e.network": "No connection. Check your internet and try again."
    },
    rw: {
      "e.wrong phone or password": "Nimero ya telefone cyangwa ijambo ry'ibanga si byo.",
      "e.too many attempts": "Wagerageje inshuro nyinshi. Tegereza iminota mike, hanyuma wongere ugerageze.",
      "e.duplicate": "Iyi nimero cyangwa Indangamuntu isanzwe yanditse.",
      "e.bad_phone": "Andika nimero y'u Rwanda nyayo, urugero 0788123456.",
      "e.bad_id": "Indangamuntu igomba kuba imibare 16.",
      "e.bad_name": "Andika amazina yombi.",
      "e.weak_password": "Ijambo ry'ibanga rigomba kuba nibura inyuguti 8.",
      "e.no_consent": "Ugomba kwemera ko E-Soko ibika amakuru yawe.",
      "e.farmer_not_active": "Uyu muhinzi ntaratanga amafaranga yo kwiyandikisha.",
      "e.buyer_not_active": "Konti yawe ntirakora. Banza wemeze ubwishyu bwo kwiyandikisha.",
      "e.not_available": "Hari undi muntu umaze kugura iki gicuruzwa.",
      "e.bad_quantity": "Andika umubare nyawo.",
      "e.bad_price": "Andika igiciro nyacyo.",
      "e.tag_already_listed": "Iyi nimero y'ikarita y'itungo isanzwe yanditse.",
      "e.outside_agent_area": "Ibi biri hanze y'umurenge wawe.",
      "e.agent_has_no_area": "Konti yawe nta gace ifite. Baza umuyobozi.",
      "e.forbidden": "Ntabwo wemerewe gukora ibi.",
      "e.new_price_must_be_lower": "Igiciro gishya kigomba kuba munsi y'icyanditswe.",
      "e.not_ready_for_verification": "Iki gicuruzwa ntikiri mu bitegereje gupimwa.",
      "e.order_not_verified": "Banza upime igicuruzwa.",
      "e.permit_required": "Hari icyangombwa cya Leta kibura: {names}",
      "e.session": "Igihe cyawe cyarangiye. Ongera winjire.",
      "e.network": "Nta murongo wa interineti. Gerageza nanone."
    },
    fr: {
      "e.wrong phone or password": "Numéro de téléphone ou mot de passe incorrect.",
      "e.too many attempts": "Trop de tentatives. Attendez quelques minutes.",
      "e.duplicate": "Ce numéro ou cet identifiant est déjà enregistré.",
      "e.bad_phone": "Entrez un numéro rwandais valide, par exemple 0788123456.",
      "e.bad_id": "L'identifiant national doit avoir 16 chiffres.",
      "e.bad_name": "Entrez le nom complet.",
      "e.weak_password": "Le mot de passe doit avoir au moins 8 caractères.",
      "e.no_consent": "Vous devez accepter que E-Soko conserve vos données.",
      "e.farmer_not_active": "Cet agriculteur n'a pas encore payé l'inscription.",
      "e.buyer_not_active": "Votre compte n'est pas encore actif. Validez d'abord le paiement d'inscription.",
      "e.not_available": "Quelqu'un vient d'acheter ce produit.",
      "e.bad_quantity": "Entrez une quantité valide.",
      "e.bad_price": "Entrez un prix valide.",
      "e.tag_already_listed": "Ce numéro de boucle est déjà enregistré.",
      "e.outside_agent_area": "C'est en dehors de votre secteur.",
      "e.agent_has_no_area": "Votre compte n'a pas encore de zone. Demandez à l'administrateur.",
      "e.forbidden": "Action non autorisée.",
      "e.new_price_must_be_lower": "Le nouveau prix doit être inférieur au prix enregistré.",
      "e.not_ready_for_verification": "Ce produit n'attend pas de vérification.",
      "e.order_not_verified": "Vérifiez d'abord le produit.",
      "e.permit_required": "Un permis de l'État manque : {names}",
      "e.session": "Votre session a expiré. Reconnectez-vous.",
      "e.network": "Pas de connexion. Vérifiez internet et réessayez."
    }
  });
  E.err = function (e) {
    var m = (e && e.message) || String(e);
    if (m === "session") return E.t("e.session");
    if (m === "Failed to fetch" || m.indexOf("NetworkError") >= 0) return E.t("e.network");
    if (m.indexOf("permit_required:") === 0) return E.t("e.permit_required", { names: m.split(":")[1].split(",").join(", ") });
    if (m.indexOf("too many attempts") === 0) return E.t("e.too many attempts");
    var key = "e." + m;
    var out = E.t(key);
    return out === key ? m : out;
  };

  /* ------------------------------------------------------------ shared words */
  E.i18n({
    en: {
      app: "E-Soko", out: "Sign out", loading: "Loading…", retry: "Try again", save: "Save", cancel: "Cancel", close: "Close",
      ok: "OK", search: "Search", refresh: "Refresh", none: "Nothing here yet.", back: "Back", prev: "Previous", next: "Next",
      yes: "Yes", no: "No", test_bar: "TEST SYSTEM: payments and text messages are simulated. No real money moves.",
      "role.farmer": "Farmer / livestock keeper", "role.buyer": "Buyer", "role.agent": "Agent", "role.gate": "Market gate officer",
      "role.admin": "Administrator", "role.superadmin": "Owner (SuperAdmin)", "role.government": "Government",
      "ps.Available": "Awaiting buyer", "ps.Reserved": "Payment pending", "ps.Sold": "Sold, bring to Agent", "ps.Verified": "Verified",
      "ps.PaidOut": "Paid", "ps.Unsold": "Unsold", "ps.Rejected": "Rejected", "ps.Expired": "Expired",
      "os.awaiting_payment": "Awaiting payment", "os.funded": "Paid, awaiting Agent", "os.revision_pending": "Price changed by Agent",
      "os.verified": "Verified, ready to collect", "os.completed": "Completed", "os.cancelled": "Cancelled", "os.refunded": "Refunded",
      "grp.crop": "Crops", "grp.livestock": "Livestock", all: "All", village: "Village", sector: "Sector", district: "District",
      phone: "Phone number", name: "Full name", qty: "Quantity", price: "Price", total: "Total", status: "Status", date: "Date",
      product: "Product", code: "Code", amount: "Amount", reference: "Reference", actions: "Actions"
    },
    rw: {
      app: "E-Soko", out: "Sohoka", loading: "Tegereza…", retry: "Gerageza nanone", save: "Bika", cancel: "Reka", close: "Funga",
      ok: "Sawa", search: "Shakisha", refresh: "Vugurura", none: "Nta kintu kirimo.", back: "Subira inyuma", prev: "Ibibanjirije", next: "Ibikurikira",
      yes: "Yego", no: "Oya", test_bar: "SISITEMU Y'IKIZAMINI: ubwishyu n'ubutumwa ni ibyo kwigana. Nta mafaranga nyayo anyura hano.",
      "role.farmer": "Umuhinzi / Umworozi", "role.buyer": "Umuguzi", "role.agent": "Agent", "role.gate": "Ushinzwe irembo ry'isoko",
      "role.admin": "Umuyobozi (Admin)", "role.superadmin": "Nyiri sisitemu (SuperAdmin)", "role.government": "Leta",
      "ps.Available": "Kitegereje umuguzi", "ps.Reserved": "Kiri kwishyurwa", "ps.Sold": "Cyaguzwe, kizane kwa Agent", "ps.Verified": "Cyemejwe",
      "ps.PaidOut": "Cyishyuwe", "ps.Unsold": "Kitaguzwe", "ps.Rejected": "Cyanzwe", "ps.Expired": "Cyarangiye",
      "os.awaiting_payment": "Utegereje kwishyura", "os.funded": "Wishyuye, utegereje Agent", "os.revision_pending": "Agent yahinduye igiciro",
      "os.verified": "Byemejwe, uze gufata", "os.completed": "Byarangiye", "os.cancelled": "Byahagaritswe", "os.refunded": "Wasubijwe amafaranga",
      "grp.crop": "Ibihingwa", "grp.livestock": "Amatungo", all: "Byose", village: "Umudugudu", sector: "Umurenge", district: "Akarere",
      phone: "Nimero ya telefone", name: "Amazina yombi", qty: "Umubare", price: "Igiciro", total: "Igiteranyo", status: "Imiterere", date: "Itariki",
      product: "Igicuruzwa", code: "Kode", amount: "Amafaranga", reference: "Nimero", actions: "Ibyo gukora"
    },
    fr: {
      app: "E-Soko", out: "Déconnexion", loading: "Chargement…", retry: "Réessayer", save: "Enregistrer", cancel: "Annuler", close: "Fermer",
      ok: "OK", search: "Rechercher", refresh: "Actualiser", none: "Rien pour le moment.", back: "Retour", prev: "Précédent", next: "Suivant",
      yes: "Oui", no: "Non", test_bar: "SYSTÈME DE TEST : paiements et SMS sont simulés. Aucun argent réel ne circule.",
      "role.farmer": "Agriculteur / éleveur", "role.buyer": "Acheteur", "role.agent": "Agent", "role.gate": "Agent de la porte du marché",
      "role.admin": "Administrateur", "role.superadmin": "Propriétaire (SuperAdmin)", "role.government": "Gouvernement",
      "ps.Available": "En attente d'acheteur", "ps.Reserved": "Paiement en cours", "ps.Sold": "Vendu, chez l'agent", "ps.Verified": "Vérifié",
      "ps.PaidOut": "Payé", "ps.Unsold": "Invendu", "ps.Rejected": "Refusé", "ps.Expired": "Expiré",
      "os.awaiting_payment": "Paiement en attente", "os.funded": "Payé, chez l'agent", "os.revision_pending": "Prix modifié par l'agent",
      "os.verified": "Vérifié, à retirer", "os.completed": "Terminé", "os.cancelled": "Annulé", "os.refunded": "Remboursé",
      "grp.crop": "Cultures", "grp.livestock": "Élevage", all: "Tout", village: "Village", sector: "Secteur", district: "District",
      phone: "Numéro de téléphone", name: "Nom complet", qty: "Quantité", price: "Prix", total: "Total", status: "Statut", date: "Date",
      product: "Produit", code: "Code", amount: "Montant", reference: "Référence", actions: "Actions"
    }
  });

  /** Colour of the status dot for product and order states. */
  var KIND = { Available: "info", Reserved: "wait", Sold: "wait", Verified: "info", PaidOut: "ok", Unsold: "", Rejected: "bad", Expired: "",
    awaiting_payment: "wait", funded: "wait", revision_pending: "wait", verified: "info", completed: "ok", cancelled: "", refunded: "bad",
    succeeded: "ok", pending: "wait", failed: "bad", accrued: "wait", settled: "ok", approved: "ok", revoked: "bad", active: "ok",
    pending_payment: "wait", suspended: "bad", queued: "wait", sent: "ok" };
  E.status = function (state, label) { return E.h("span", { class: "st " + (KIND[state] || ""), text: label || state }); };
  E.productStatus = function (s) { return E.status(s, E.t("ps." + s)); };
  E.orderStatus = function (s) { return E.status(s, E.t("os." + s)); };

  /* ------------------------------------------------------------ table */
  /** cols: [{label, key, num, render(row) -> node|string, nowrap}] */
  E.table = function (cols, rows, emptyText) {
    if (!rows || !rows.length) return E.empty(emptyText || E.t("none"));
    var head = E.h("tr", null, cols.map(function (c) { return E.h("th", { class: c.num ? "n" : "", text: c.label }); }));
    var body = rows.map(function (r) {
      return E.h("tr", null, cols.map(function (c) {
        var v = c.render ? c.render(r) : r[c.key];
        return E.h("td", { class: (c.num ? "n " : "") + (c.nowrap ? "nw" : "") }, v === null || v === undefined || v === "" ? "-" : v);
      }));
    });
    return E.h("div", { class: "tbl-wrap" }, E.h("table", null, E.h("thead", null, head), E.h("tbody", null, body)));
  };
  E.empty = function (text) { return E.h("div", { class: "empty" }, E.h("div", { class: "band" }), E.h("div", { text: text })); };
  E.loading = function () { return E.h("div", null, E.h("div", { class: "skel", style: "width:60%" }), E.h("div", { class: "skel" }), E.h("div", { class: "skel", style: "width:80%" })); };
  E.kpis = function (items) {
    return E.h("div", { class: "kpis" }, items.map(function (k) {
      return E.h("div", { class: "kpi " + (k.tone || "") }, E.h("div", { class: "v", text: k.value }), E.h("div", { class: "l", text: k.label }));
    }));
  };
  E.section = function (title, aside, body) {
    return E.h("section", { class: "section" }, E.h("h2", null, E.h("span", { text: title }), aside ? E.h("span", { class: "aside" }, aside) : null), body);
  };
  E.field = function (label, input, wrapClass) {
    return E.h("div", { class: wrapClass || "f-wrap" }, E.h("label", { class: "f", text: label }), input);
  };
  E.select = function (options, value, props) {
    var s = E.h("select", props || {}, options.map(function (o) { return E.h("option", { value: o[0], text: o[1] }); }));
    if (value !== undefined && value !== null) s.value = value;
    return s;
  };

  /* ------------------------------------------------------------ toast + modal */
  E.toast = function (msg, bad) {
    var t = E.h("div", { class: "toast" + (bad ? " bad" : ""), role: "status", text: msg });
    document.body.appendChild(t);
    setTimeout(function () { if (t.parentNode) t.parentNode.removeChild(t); }, bad ? 6000 : 3200);
  };
  /** Opens a dialog. build(close) returns the content node. Returns close(). */
  E.modal = function (title, build, locked) {
    var bg = E.h("div", { class: "modal-bg" });
    var box = E.h("div", { class: "modal", role: "dialog", "aria-modal": "true", "aria-label": title });
    function close() { if (bg.parentNode) bg.parentNode.removeChild(bg); document.removeEventListener("keydown", onKey); }
    function onKey(e) { if (e.key === "Escape") close(); }
    if (!locked) { bg.addEventListener("mousedown", function (e) { if (e.target === bg) close(); }); document.addEventListener("keydown", onKey); }
    E.add(box, [E.h("h3", { text: title }), build(close)]);
    bg.appendChild(box); document.body.appendChild(bg);
    var first = box.querySelector("input, select, button"); if (first) first.focus();
    return close;
  };
  E.confirm = function (title, body, okLabel, danger) {
    return new Promise(function (resolve) {
      E.modal(title, function (close) {
        return E.h("div", null, E.h("p", { text: body }),
          E.h("div", { class: "actions" },
            E.h("button", { class: "btn sec", text: E.t("cancel"), on: { click: function () { close(); resolve(false); } } }),
            E.h("button", { class: "btn" + (danger ? " danger" : ""), text: okLabel || E.t("ok"), on: { click: function () { close(); resolve(true); } } })));
      });
    });
  };
  /** Runs fn() (a promise) while the button is disabled; shows errors as a toast. */
  E.busy = function (btn, fn) {
    btn.disabled = true;
    return Promise.resolve().then(fn).catch(function (e) { E.toast(E.err(e), true); throw e; })
      .then(function (v) { btn.disabled = false; return v; }, function (e) { btn.disabled = false; });
  };

  /* ------------------------------------------------------------ config + page shell */
  var cfgPromise = null;
  E.config = function () { return cfgPromise || (cfgPromise = E.api("/config/public", { anon: true }).catch(function () { return { mode: "test" }; })); };
  E.testBar = function (cfg) { return cfg.mode === "test" ? E.h("div", { class: "testbar", "data-i": "test_bar", text: E.t("test_bar") }) : null; };
  E.logo = function () { return E.h("a", { class: "brand", href: "/" }, E.h("img", { src: "/static/img/logo.svg", alt: "", width: 30, height: 30 }), E.h("span", { text: "E-Soko" })); };

  /**
   * Builds the signed-in page frame.
   * opts: {user, tabs:[{id, label_key}], onTab(id)}  ->  {main, select(id)}
   */
  E.shell = function (root, opts) {
    var u = opts.user, tabsEl = null, main = E.h("main", { id: "main" }), current = null;
    var who = E.h("div", { class: "who" }, E.h("b", { text: u.name }), E.h("span", { text: E.t("role." + u.role) }));
    var top = E.h("header", { class: "top" }, E.h("div", { class: "top-in" }, E.logo(), E.h("div", { class: "grow" }), who, E.langSelect(),
      E.h("button", { class: "btn ghost", text: E.t("out"), "data-i": "out", on: { click: E.logout } })));
    var testSlot = E.h("div");
    E.add(root, [testSlot, top, E.h("div", { class: "band" })]);
    E.config().then(function (cfg) { E.fill(testSlot, E.testBar(cfg)); });
    function select(id, silent) {
      current = id;
      [].forEach.call(tabsEl.children, function (b) { b.setAttribute("aria-selected", b.getAttribute("data-id") === id ? "true" : "false"); });
      if (!silent) w.history.replaceState(null, "", "#" + id);
      opts.onTab(id, main);
    }
    if (opts.tabs && opts.tabs.length > 1) {
      tabsEl = E.h("div", { class: "tabs-in", role: "tablist" });
      opts.tabs.forEach(function (t) {
        tabsEl.appendChild(E.h("button", { class: "tab", role: "tab", "data-id": t.id, "data-i": t.label, text: E.t(t.label), "aria-selected": "false",
          on: { click: function () { select(t.id); } } }));
      });
      E.add(root, E.h("nav", { class: "tabs" }, tabsEl));
    } else {
      tabsEl = E.h("div");
    }
    root.appendChild(main);
    E.onLang(function () {
      E.fill(who, [E.h("b", { text: u.name }), E.h("span", { text: E.t("role." + u.role) })]);
      if (current) opts.onTab(current, main);
    });
    var start = (w.location.hash || "").slice(1);
    var ids = (opts.tabs || []).map(function (t) { return t.id; });
    select(ids.indexOf(start) >= 0 ? start : ids[0], true);
    return { main: main, select: select };
  };

  E.copy = function (text) {
    if (navigator.clipboard) navigator.clipboard.writeText(text).then(function () { E.toast(E.t("ok")); });
  };
})(window);
