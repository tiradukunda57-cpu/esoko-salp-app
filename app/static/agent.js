/* Agent (and market-gate officer) console: verification queue, farmers, gate check, account. */
(function (w) {
  "use strict";
  var E = w.E, h = E.h;

  E.i18n({
    en: {
      "t.queue": "To verify", "t.farmers": "Farmers", "t.gate": "Gate check", "t.acc": "Account",
      "q.none": "Nothing is waiting in your area.", "q.farmer": "Farmer", "q.buyer": "Buyer", "q.verify": "Verify", "q.handover": "Hand over and pay", "q.docs": "Record document",
      "q.missing": "Missing documents", "q.blocking": "blocks payout", "q.ready": "Verified: waiting for the buyer to collect",
      "v.title": "Verify {code}", "v.result": "Result", "v.approve": "Approve", "v.downgrade": "Lower the price", "v.reject": "Reject", "v.grade": "Grade", "v.weight": "Weight (kg)",
      "v.newprice": "New price per unit (Frw)", "v.tag": "Ear-tag / ID number", "v.note": "Note", "v.done": "Saved.", "v.hand": "Handover recorded. Payout sent.",
      "fm.search": "Search name or phone", "fm.register": "Register a farmer", "fm.list": "List for farmer", "fm.status": "Status", "fm.none": "No farmers found.",
      "fm.consent": "The farmer agrees that E-Soko stores their data.", "fm.fee": "Registration fee {fee} is paid by the farmer by mobile money.", "fm.done": "Farmer registered.", "fm.sim": "Test system: simulate payment approval",
      "fm.pick": "Farmer", "fm.listed": "Listed. Code: {code}",
      "g.title": "Check a market gate code", "g.code": "Code from the farmer", "g.check": "Check", "g.valid": "Valid: let it in", "g.used": "Already used", "g.expired": "Expired",
      "g.unknown": "Unknown code", "g.permit_missing": "A government document is missing", "g.missing": "Missing: {names}"
    },
    rw: {
      "t.queue": "Bipimwa", "t.farmers": "Abahinzi", "t.gate": "Irembo", "t.acc": "Konti",
      "q.none": "Nta kintu gitegereje mu gace kawe.", "q.farmer": "Umuhinzi", "q.buyer": "Umuguzi", "q.verify": "Pima", "q.handover": "Tanga wishyure", "q.docs": "Andika icyangombwa",
      "q.missing": "Ibyangombwa bibura", "q.blocking": "bihagarika kwishyura", "q.ready": "Byapimwe: utegereje ko umuguzi aza gufata",
      "v.title": "Pima {code}", "v.result": "Icyemezo", "v.approve": "Emeza", "v.downgrade": "Manura igiciro", "v.reject": "Anga", "v.grade": "Icyiciro", "v.weight": "Ibiro (kg)",
      "v.newprice": "Igiciro gishya kuri buri gipimo (Frw)", "v.tag": "Nomero y'ikarita y'itungo", "v.note": "Icyitonderwa", "v.done": "Byabitswe.", "v.hand": "Gutanga byanditswe. Ubwishyu bwoherejwe.",
      "fm.search": "Shakisha izina cyangwa telefone", "fm.register": "Andika umuhinzi", "fm.list": "Andikisha ku muhinzi", "fm.status": "Imiterere", "fm.none": "Nta muhinzi uboneka.",
      "fm.consent": "Umuhinzi yemeye ko E-Soko ibika amakuru ye.", "fm.fee": "Umuhinzi yishyura {fee} yo kwiyandikisha kuri mobile money.", "fm.done": "Umuhinzi yanditswe.", "fm.sim": "Sisitemu y'ikizamini: wigane ubwishyu",
      "fm.pick": "Umuhinzi", "fm.listed": "Cyanditswe. Kode: {code}",
      "g.title": "Genzura kode y'irembo", "g.code": "Kode y'umuhinzi", "g.check": "Genzura", "g.valid": "Irakora: reka yinjire", "g.used": "Yarakoreshejwe", "g.expired": "Yararangiye",
      "g.unknown": "Kode itazwi", "g.permit_missing": "Haburamo icyangombwa cya Leta", "g.missing": "Habura: {names}"
    },
    fr: {
      "t.queue": "À vérifier", "t.farmers": "Agriculteurs", "t.gate": "Porte", "t.acc": "Compte",
      "q.none": "Rien en attente dans votre zone.", "q.farmer": "Agriculteur", "q.buyer": "Acheteur", "q.verify": "Vérifier", "q.handover": "Remettre et payer", "q.docs": "Enregistrer un document",
      "q.missing": "Documents manquants", "q.blocking": "bloque le paiement", "q.ready": "Vérifié : en attente du retrait par l'acheteur",
      "v.title": "Vérifier {code}", "v.result": "Résultat", "v.approve": "Approuver", "v.downgrade": "Baisser le prix", "v.reject": "Refuser", "v.grade": "Qualité", "v.weight": "Poids (kg)",
      "v.newprice": "Nouveau prix par unité (Frw)", "v.tag": "Numéro de boucle / identifiant", "v.note": "Note", "v.done": "Enregistré.", "v.hand": "Remise enregistrée. Paiement envoyé.",
      "fm.search": "Rechercher nom ou téléphone", "fm.register": "Inscrire un agriculteur", "fm.list": "Enregistrer pour un agriculteur", "fm.status": "Statut", "fm.none": "Aucun agriculteur trouvé.",
      "fm.consent": "L'agriculteur accepte que E-Soko conserve ses données.", "fm.fee": "Les frais d'inscription de {fee} sont payés par l'agriculteur en mobile money.", "fm.done": "Agriculteur inscrit.", "fm.sim": "Système de test : simuler la validation du paiement",
      "fm.pick": "Agriculteur", "fm.listed": "Enregistré. Code : {code}",
      "g.title": "Vérifier un code de la porte", "g.code": "Code de l'agriculteur", "g.check": "Vérifier", "g.valid": "Valide : laissez entrer", "g.used": "Déjà utilisé", "g.expired": "Expiré",
      "g.unknown": "Code inconnu", "g.permit_missing": "Un document de l'État manque", "g.missing": "Manque : {names}"
    }
  });

  var cfg = {};

  function queue(main) {
    E.fill(main, E.loading());
    Promise.all([E.api("/agent/queue"), E.cats()]).then(function (r) {
      var rows = r[0], cats = r[1];
      if (!rows.length) { E.fill(main, E.empty(E.t("q.none"))); return; }
      E.fill(main, h("div", { class: "qlist" }, rows.map(function (q) {
        var ready = q.product_status === "Verified" || q.order_status === "verified";
        var cat = cats.filter(function (c) { return c.code === q.category; })[0] || {};
        var meta = [E.t("q.farmer") + ": " + q.farmer_name + " " + q.farmer_phone, E.t("q.buyer") + ": " + q.buyer_name, (q.village || "-") + ", " + (q.sector || "")];
        if (q.tag_number) meta.push(q.tag_number);
        var acts = h("div", { class: "actions" });
        if (ready) acts.appendChild(h("button", { class: "btn", text: E.t("q.handover"), on: { click: function () { handover(q, main); } } }));
        else acts.appendChild(h("button", { class: "btn", text: E.t("q.verify"), on: { click: function () { verify(q, cat, main); } } }));
        acts.appendChild(h("button", { class: "btn sec", text: E.t("q.docs"), on: { click: function () { E.permitModal({ subject: "product", product_id: q.product_id, onDone: function () { queue(main); } }); } } }));
        return h("div", { class: "qcard" + (ready ? " ready" : "") },
          h("div", null, h("h3", null, (cat.name_en ? E.name(cat) : q.category) + " - " + E.num(q.quantity) + " " + E.unitName(q.unit), " ", h("span", { class: "code muted small", text: q.code })),
            h("div", { class: "meta", text: meta.join("  |  ") }),
            h("div", { style: "margin-top:6px" }, E.orderStatus(q.order_status), " ", h("b", { text: E.money(q.total_amount) })),
            ready ? h("div", { class: "muted small", text: E.t("q.ready") }) : null,
            q.permits_missing && q.permits_missing.length ? h("div", { class: "tags", style: "margin-top:6px" }, [h("span", { class: "small", text: E.t("q.missing") + ":" })].concat(q.permits_missing.map(function (m) {
              return h("span", { class: "tag" + (m.mandatory ? " bad" : ""), text: m.name + (m.mandatory ? " (" + E.t("q.blocking") + ")" : "") }); }))) : null),
          acts);
      })));
    }).catch(function (e) { E.fill(main, h("div", { class: "notice bad", text: E.err(e) })); });
  }

  function verify(q, cat, main) {
    E.modal(E.t("v.title", { code: q.code }), function (close) {
      var res = E.select([["approve", E.t("v.approve")], ["downgrade", E.t("v.downgrade")], ["reject", E.t("v.reject")]]);
      var grade = E.select([["", "-"], ["A", "A"], ["B", "B"]]), weight = h("input", { type: "number", min: "0", step: "any" });
      var np = h("input", { type: "number", min: "0" }), tag = h("input", { maxlength: "30", value: q.tag_number || "" }), note = h("input", { maxlength: "200" });
      var err = h("div", { class: "err", role: "alert" }), ok = h("button", { class: "btn", text: E.t("save") });
      var npw = E.field(E.t("v.newprice"), np), tagw = E.field(E.t("v.tag"), tag);
      function sync() { npw.classList.toggle("hidden", res.value !== "downgrade"); tagw.classList.toggle("hidden", cat.grp !== "livestock" || res.value === "reject"); }
      res.addEventListener("change", sync); sync();
      ok.addEventListener("click", function () {
        err.textContent = "";
        var body = { product_id: q.product_id, result: res.value, grade: grade.value || null, weight: weight.value ? Number(weight.value) : null, note: note.value || null };
        if (res.value === "downgrade") body.new_price = Number(np.value);
        if (cat.grp === "livestock" && tag.value) body.tag_number = tag.value;
        E.busy(ok, function () { return E.api("/agent/verify", { body: body }).then(function () { close(); E.toast(E.t("v.done")); queue(main); }); }).catch(function (e) { err.textContent = E.err(e); });
      });
      return h("div", null, E.field(E.t("v.result"), res), h("div", { class: "row" }, E.field(E.t("v.grade"), grade), E.field(E.t("v.weight"), weight)), npw, tagw, E.field(E.t("v.note"), note), err,
        h("div", { class: "actions" }, h("button", { class: "btn sec", text: E.t("cancel"), on: { click: close } }), ok));
    });
  }

  function handover(q, main) {
    E.confirm(E.t("q.handover"), q.code + " - " + E.money(q.total_amount), E.t("q.handover")).then(function (yes) {
      if (!yes) return;
      E.api("/agent/handover", { body: { order_id: q.order_id } }).then(function () { E.toast(E.t("v.hand")); queue(main); }).catch(function (e) { E.toast(E.err(e), true); });
    });
  }

  function farmers(main) {
    var q = h("input", { type: "search", placeholder: E.t("fm.search") }), list = h("div"), timer = null;
    function load() {
      E.api("/agent/farmers" + (q.value ? "?q=" + encodeURIComponent(q.value) : "")).then(function (rows) {
        E.fill(list, E.table([
          { label: E.t("name"), key: "name" }, { label: E.t("phone"), key: "phone", nowrap: true }, { label: E.t("village"), render: function (r) { return r.village + (r.sector ? " (" + r.sector + ")" : ""); } },
          { label: E.t("fm.status"), render: function (r) { return E.status(r.status, r.status); } },
          { label: "", render: function (r) {
            var a = h("div", { class: "actions" });
            if (r.status === "active") {
              a.appendChild(h("button", { class: "btn small", text: E.t("fm.list"), on: { click: function () { listFor(r, load); } } }));
              a.appendChild(h("button", { class: "btn small sec", text: E.t("q.docs"), on: { click: function () { E.permitModal({ subject: "user", user_id: r.id, role: "farmer" }); } } }));
            }
            return a;
          } }
        ], rows, E.t("fm.none")));
      }).catch(function (e) { E.fill(list, h("div", { class: "notice bad", text: E.err(e) })); });
    }
    q.addEventListener("input", function () { clearTimeout(timer); timer = setTimeout(load, 300); });
    E.fill(main, [h("div", { class: "filters" }, E.field(E.t("search"), q), h("button", { class: "btn", text: E.t("fm.register"), on: { click: function () { register(load); } } })), list]);
    load();
  }

  function register(done) {
    E.locs().then(function (locs) {
      E.modal(E.t("fm.register"), function (close) {
        var name = h("input"), ph = h("input", { type: "tel", inputmode: "tel" }), nid = h("input", { inputmode: "numeric", maxlength: "16" });
        var loc = E.select(E.villageOptions(locs)), consent = h("input", { type: "checkbox", id: "fconsent" });
        var err = h("div", { class: "err", role: "alert" }), ok = h("div", { class: "okmsg", role: "status" });
        var go = h("button", { class: "btn", text: E.t("save") }), sim = h("button", { class: "btn sun hidden", text: E.t("fm.sim") });
        go.addEventListener("click", function () {
          err.textContent = "";
          E.busy(go, function () {
            return E.api("/agent/register-farmer", { body: { name: name.value, phone: ph.value, national_id: nid.value, language: "rw", location_id: loc.value ? Number(loc.value) : null, consent: consent.checked } })
              .then(function () { ok.textContent = E.t("fm.done"); go.classList.add("hidden"); if (cfg.test_payments) sim.classList.remove("hidden"); done(); });
          }).catch(function (e) { err.textContent = E.err(e); });
        });
        sim.addEventListener("click", function () { E.busy(sim, function () { return E.api("/test/approve-registration", { body: { phone: ph.value } }).then(function () { sim.classList.add("hidden"); done(); }); }); });
        return h("div", null, h("p", { class: "muted small", text: E.t("fm.fee", { fee: E.money(cfg.registration_fee || 500) }) }), E.field(E.t("name"), name), E.field(E.t("phone"), ph), E.field(E.t("r.id"), nid), E.field(E.t("village"), loc),
          h("label", { class: "check", for: "fconsent" }, consent, h("span", { text: E.t("fm.consent") })), err, ok,
          h("div", { class: "actions" }, h("button", { class: "btn sec", text: E.t("close"), on: { click: close } }), sim, go));
      });
    });
  }

  function listFor(farmer, done) {
    E.cats().then(function (cats) {
      E.modal(E.t("fm.list") + ": " + farmer.name, function (close) {
        var cat = E.select(cats.map(function (c) { return [c.code, E.t("grp." + c.grp) + " - " + E.name(c)]; }));
        var qty = h("input", { type: "number", min: "0", step: "any" }), price = h("input", { type: "number", min: "0" });
        var tag = h("input", { maxlength: "30" }), sex = E.select([["", "-"], ["female", E.t("sl.female")], ["male", E.t("sl.male")]]), age = h("input", { type: "number", min: "0" });
        var live = h("div", { class: "row" }, E.field(E.t("sl.tag"), tag), E.field(E.t("sl.sex"), sex), E.field(E.t("sl.age"), age));
        var err = h("div", { class: "err", role: "alert" }), ok = h("button", { class: "btn", text: E.t("sl.go") });
        function sync() { var c = cats.filter(function (x) { return x.code === cat.value; })[0]; live.classList.toggle("hidden", !c || c.grp !== "livestock"); }
        cat.addEventListener("change", sync); sync();
        ok.addEventListener("click", function () {
          err.textContent = "";
          E.busy(ok, function () {
            return E.api("/agent/list-product", { body: { farmer_id: farmer.id, category: cat.value, quantity: Number(qty.value), price_per_unit: Number(price.value),
              tag_number: tag.value || null, sex: sex.value || null, age_months: age.value ? Number(age.value) : null } })
              .then(function (r) { close(); E.toast(E.t("fm.listed", { code: r.code })); done(); });
          }).catch(function (e) { err.textContent = E.err(e); });
        });
        return h("div", null, E.field(E.t("sl.cat"), cat), h("div", { class: "row" }, E.field(E.t("sl.qty"), qty), E.field(E.t("sl.price"), price)), live, err,
          h("div", { class: "actions" }, h("button", { class: "btn sec", text: E.t("cancel"), on: { click: close } }), ok));
      });
    });
  }

  function gate(main) {
    var code = h("input", { maxlength: "20", autocapitalize: "characters", autocomplete: "off" }), out = h("div"), go = h("button", { class: "btn", text: E.t("g.check") });
    function check() {
      E.busy(go, function () {
        return E.api("/gate/verify/" + encodeURIComponent(code.value.trim())).then(function (r) {
          var kind = r.status === "valid" ? "valid" : r.status === "permit_missing" ? "wait" : "bad";
          E.fill(out, h("div", { class: "result " + kind }, h("h3", { text: E.t("g." + r.status) }),
            r.product ? h("p", { text: [r.product, E.num(r.quantity) + " " + E.unitName(r.unit), r.farmer, r.village].join(" - ") }) : null,
            r.missing ? h("p", { text: E.t("g.missing", { names: r.missing.join(", ") }) }) : null));
        });
      }).catch(function (e) { E.fill(out, h("div", { class: "notice bad", text: E.err(e) })); });
    }
    go.addEventListener("click", check);
    code.addEventListener("keydown", function (e) { if (e.key === "Enter") check(); });
    E.fill(main, E.section(E.t("g.title"), null, h("div", { class: "panel", style: "max-width:480px" }, E.field(E.t("g.code"), code), h("p", { style: "margin-top:12px" }, go), out)));
  }

  E.guard(["agent", "gate"]).then(function (u) {
    E.config().then(function (c) {
      cfg = c;
      var tabs = u.role === "gate" ? [{ id: "gate", label: "t.gate" }, { id: "acc", label: "t.acc" }]
        : [{ id: "queue", label: "t.queue" }, { id: "farmers", label: "t.farmers" }, { id: "gate", label: "t.gate" }, { id: "acc", label: "t.acc" }];
      E.shell(E.$("root"), { user: u, tabs: tabs, onTab: function (id, main) {
        if (id === "queue") queue(main); else if (id === "farmers") farmers(main); else if (id === "gate") gate(main); else E.fill(main, E.accountPanel(u, true));
      } });
    });
  }).catch(function () {});
})(window);
