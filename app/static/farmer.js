/* Farmer / livestock keeper portal: overview, sell, my items, documents, account. */
(function (w) {
  "use strict";
  var E = w.E, h = E.h;

  E.i18n({
    en: {
      "t.ov": "Overview", "t.sell": "Sell", "t.items": "My items", "t.docs": "Documents", "t.acc": "Account",
      "f.hello": "Hello, {name}", "f.paid": "Paid to you", "f.waiting": "Waiting for payout", "f.fees": "Fees to deduct", "f.listed": "Items for sale",
      "f.codes": "Market gate codes", "f.codes_h": "Show this code at the market gate for items that did not sell.", "f.nocodes": "No codes right now.", "f.valid": "valid until",
      "f.pay": "Recent payouts", "f.nopay": "No payouts yet.",
      "sl.title": "Put an item up for sale", "sl.cat": "What are you selling?", "sl.qty": "Quantity", "sl.price": "Price per unit (Frw)", "sl.total": "Expected total",
      "sl.tag": "Ear-tag / ID number", "sl.sex": "Sex", "sl.female": "Female", "sl.male": "Male", "sl.age": "Age (months)", "sl.notes": "Notes", "sl.go": "List for sale",
      "sl.done": "Listed. Code: {code}. Bring it to your Agent when it is sold.", "sl.blocked": "Missing documents: {names}. Ask your Agent to record them first.",
      "it.code": "Code", "it.what": "Item", "it.qty": "Quantity", "it.price": "Price", "it.status": "Status", "it.date": "Listed",
      "dc.h": "Government documents recorded for you", "dc.none": "No documents recorded.", "dc.ref": "Reference", "dc.until": "Valid until", "dc.for": "For"
    },
    rw: {
      "t.ov": "Incamake", "t.sell": "Gurisha", "t.items": "Ibyanjye", "t.docs": "Ibyangombwa", "t.acc": "Konti",
      "f.hello": "Muraho, {name}", "f.paid": "Wamaze kwishyurwa", "f.waiting": "Utegereje kwishyurwa", "f.fees": "Amafaranga azakurwaho", "f.listed": "Ibigurishwa",
      "f.codes": "Kode z'irembo ry'isoko", "f.codes_h": "Erekana iyi kode ku irembo ry'isoko ku bicuruzwa bitaguzwe.", "f.nocodes": "Nta kode zihari ubu.", "f.valid": "igeza ku itariki",
      "f.pay": "Ubwishyu buheruka", "f.nopay": "Nta bwishyu burabaho.",
      "sl.title": "Andikisha igicuruzwa", "sl.cat": "Urigurisha iki?", "sl.qty": "Umubare", "sl.price": "Igiciro kuri buri gipimo (Frw)", "sl.total": "Yose hamwe",
      "sl.tag": "Nimero y'ikarita y'itungo", "sl.sex": "Igitsina", "sl.female": "Ingore", "sl.male": "Ingabo", "sl.age": "Imyaka y'itungo (amezi)", "sl.notes": "Icyitonderwa", "sl.go": "Andikisha",
      "sl.done": "Cyanditswe. Kode: {code}. Nikigurwa, kizane kwa Agent.", "sl.blocked": "Hari ibyangombwa bibura: {names}. Saba Agent kubyandika mbere.",
      "it.code": "Kode", "it.what": "Igicuruzwa", "it.qty": "Umubare", "it.price": "Igiciro", "it.status": "Imiterere", "it.date": "Cyanditswe",
      "dc.h": "Ibyangombwa bya Leta byanditswe kuri wowe", "dc.none": "Nta cyangombwa cyanditswe.", "dc.ref": "Nimero", "dc.until": "Gifite agaciro kugeza ku", "dc.for": "Ku"
    },
    fr: {
      "t.ov": "Aperçu", "t.sell": "Vendre", "t.items": "Mes articles", "t.docs": "Documents", "t.acc": "Compte",
      "f.hello": "Bonjour, {name}", "f.paid": "Déjà payé", "f.waiting": "Paiement en attente", "f.fees": "Frais à déduire", "f.listed": "Articles en vente",
      "f.codes": "Codes de la porte du marché", "f.codes_h": "Montrez ce code à la porte du marché pour les invendus.", "f.nocodes": "Aucun code pour le moment.", "f.valid": "valide jusqu'au",
      "f.pay": "Derniers paiements", "f.nopay": "Aucun paiement pour le moment.",
      "sl.title": "Mettre un article en vente", "sl.cat": "Que vendez-vous ?", "sl.qty": "Quantité", "sl.price": "Prix par unité (Frw)", "sl.total": "Total prévu",
      "sl.tag": "Numéro de boucle / identifiant", "sl.sex": "Sexe", "sl.female": "Femelle", "sl.male": "Mâle", "sl.age": "Âge (mois)", "sl.notes": "Notes", "sl.go": "Mettre en vente",
      "sl.done": "Enregistré. Code : {code}. Apportez-le à votre agent une fois vendu.", "sl.blocked": "Documents manquants : {names}. Demandez à votre agent de les enregistrer.",
      "it.code": "Code", "it.what": "Article", "it.qty": "Quantité", "it.price": "Prix", "it.status": "Statut", "it.date": "Enregistré",
      "dc.h": "Documents de l'État enregistrés pour vous", "dc.none": "Aucun document enregistré.", "dc.ref": "Référence", "dc.until": "Valide jusqu'au", "dc.for": "Pour"
    }
  });

  var data = null, user = null;
  function load() { return E.api("/portal/farmer").then(function (d) { data = d; return d; }); }

  function overview(main) {
    var t = data.totals, bs = t.by_status || {};
    E.fill(main, [
      h("div", { class: "page-head" }, h("h2", { text: E.t("f.hello", { name: user.name }) }), h("span", { class: "muted", text: data.profile.location ? data.profile.location.village + ", " + data.profile.location.sector : "" })),
      E.kpis([{ label: E.t("f.paid"), value: E.money(t.paid_out), tone: "accent" }, { label: E.t("f.waiting"), value: E.money(t.waiting_for_payment) },
        { label: E.t("f.fees"), value: E.money(t.fees_to_be_deducted) }, { label: E.t("f.listed"), value: E.num(bs.Available || 0) }]),
      E.section(E.t("f.codes"), h("span", { text: E.t("f.codes_h") }), data.clearances.length ? h("div", { class: "code-list" }, data.clearances.map(function (c) {
        return h("div", { class: "code-card" }, h("div", { class: "big-code", text: c.code }), h("div", { class: "meta", text: c.product + " - " + E.t("f.valid") + " " + E.dateTime(c.valid_until) }));
      })) : E.empty(E.t("f.nocodes"))),
      E.section(E.t("f.pay"), null, E.table([{ label: E.t("date"), key: "date" }, { label: E.t("product"), key: "product" }, { label: E.t("amount"), num: true, render: function (r) { return E.money(r.amount); } }], data.payouts, E.t("f.nopay")))
    ]);
  }

  function sell(main) {
    E.cats().then(function (cats) {
      var cat = E.select(cats.map(function (c) { return [c.code, E.t("grp." + c.grp) + " - " + E.name(c)]; }));
      var qty = h("input", { type: "number", min: "0", step: "any", inputmode: "decimal" }), price = h("input", { type: "number", min: "0", inputmode: "numeric" });
      var tag = h("input", { maxlength: "30" }), sex = E.select([["", "-"], ["female", E.t("sl.female")], ["male", E.t("sl.male")]]), age = h("input", { type: "number", min: "0", inputmode: "numeric" });
      var notes = h("input", { maxlength: "200" }), total = h("div", { class: "muted", role: "status" }), err = h("div", { class: "err", role: "alert" });
      var live = h("div", { class: "row" }, E.field(E.t("sl.tag"), tag), E.field(E.t("sl.sex"), sex), E.field(E.t("sl.age"), age));
      var warn = h("div");
      var go = h("button", { class: "btn", text: E.t("sl.go") });
      function cur() { return cats.filter(function (c) { return c.code === cat.value; })[0]; }
      function refresh() {
        var c = cur();
        live.classList.toggle("hidden", !c || c.grp !== "livestock");
        total.textContent = qty.value && price.value ? E.t("sl.total") + ": " + E.money(Math.round(Number(qty.value) * Number(price.value))) + (c ? " / " + E.unitName(c.unit) : "") : "";
        var b = data.listing_blocked.filter(function (x) { return x.category === cat.value; })[0];
        E.fill(warn, b ? h("div", { class: "notice bad", text: E.t("sl.blocked", { names: b.missing.join(", ") }) }) : null);
      }
      [cat, qty, price].forEach(function (i) { i.addEventListener("input", refresh); });
      go.addEventListener("click", function () {
        err.textContent = "";
        var c = cur(), body = { category: cat.value, quantity: Number(qty.value), price_per_unit: Number(price.value) };
        if (c.grp === "livestock") { body.tag_number = tag.value || null; body.sex = sex.value || null; body.age_months = age.value ? Number(age.value) : null; }
        if (notes.value) body.notes = notes.value;
        E.busy(go, function () {
          return E.api("/portal/farmer/listings", { body: body }).then(function (r) {
            E.toast(E.t("sl.done", { code: r.code || r.product_code || "" })); qty.value = ""; price.value = ""; tag.value = ""; return load().then(refresh);
          });
        }).catch(function (e) { err.textContent = E.err(e); });
      });
      E.fill(main, E.section(E.t("sl.title"), null, h("div", { class: "panel", style: "max-width:640px" },
        E.field(E.t("sl.cat"), cat), h("div", { class: "row" }, E.field(E.t("sl.qty"), qty), E.field(E.t("sl.price"), price)), total, live, E.field(E.t("sl.notes"), notes), warn, err,
        h("p", { style: "margin-top:14px" }, go))));
      refresh();
    });
  }

  function items(main) {
    E.fill(main, E.section(E.t("t.items"), null, E.table([
      { label: E.t("it.code"), render: function (r) { return h("span", { class: "code", text: r.code }); } },
      { label: E.t("it.what"), render: function (r) { return E.name(r); } },
      { label: E.t("it.qty"), num: true, render: function (r) { return E.num(r.quantity) + " " + E.unitName(r.unit); } },
      { label: E.t("it.price"), num: true, render: function (r) { return E.money(r.price_per_unit); } },
      { label: E.t("it.status"), render: function (r) { return E.productStatus(r.status); } },
      { label: E.t("it.date"), render: function (r) { return E.date(r.created_at); } }
    ], data.listings)));
  }

  function docs(main) {
    E.fill(main, E.section(E.t("dc.h"), null, E.table([
      { label: E.t("permit.type"), render: function (r) { return E.name(r); } }, { label: E.t("dc.ref"), key: "reference" },
      { label: E.t("dc.until"), render: function (r) { return E.date(r.valid_until); } }, { label: E.t("dc.for"), render: function (r) { return r.product || E.t("subject.user"); } }
    ], data.permits, E.t("dc.none"))));
  }

  E.guard(["farmer"]).then(function (u) {
    user = u;
    load().then(function () {
      E.shell(E.$("root"), { user: u, tabs: [{ id: "ov", label: "t.ov" }, { id: "sell", label: "t.sell" }, { id: "items", label: "t.items" }, { id: "docs", label: "t.docs" }, { id: "acc", label: "t.acc" }],
        onTab: function (id, main) {
          if (id === "ov") overview(main); else if (id === "sell") sell(main); else if (id === "items") items(main); else if (id === "docs") docs(main);
          else E.fill(main, E.accountPanel(u, false));
        } });
    });
  }).catch(function () {});
})(window);
