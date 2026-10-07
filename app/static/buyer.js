/* Buyer portal: market, my orders (price-change answers, test payment), account. */
(function (w) {
  "use strict";
  var E = w.E, h = E.h;

  E.i18n({
    en: {
      "t.market": "Market", "t.orders": "My orders", "t.acc": "Account",
      "m.cat": "Product", "m.grp": "Type", "m.village": "Village", "m.where": "Where", "m.detail": "Details", "m.buy": "Buy", "m.none": "Nothing for sale with these filters.",
      "m.confirm": "Buy {item} for {total}? The money is held safely until the Agent verifies the goods.", "m.pay": "Approve the mobile-money prompt on your phone ({total}).",
      "m.female": "female", "m.male": "male", "m.months": "months", "m.grade": "Grade",
      "o.spent": "Spent (completed)", "o.progress": "In progress", "o.answer": "Needs your answer", "o.none": "You have no orders yet.",
      "o.accept": "Accept new price", "o.decline": "Decline and refund", "o.newtotal": "New total: {total}", "o.sim": "Test system: simulate that I approved the payment", "o.simdone": "Payment approved.",
      "o.simnone": "No payment is waiting.", "o.collect": "Verified. Collect from the Agent."
    },
    rw: {
      "t.market": "Isoko", "t.orders": "Ibyo naguze", "t.acc": "Konti",
      "m.cat": "Igicuruzwa", "m.grp": "Ubwoko", "m.village": "Umudugudu", "m.where": "Aho biri", "m.detail": "Ibisobanuro", "m.buy": "Gura", "m.none": "Nta gicuruzwa kiboneka hakurikijwe ibyo washatse.",
      "m.confirm": "Gura {item} kuri {total}? Amafaranga abikwa neza kugeza igihe Agent azapimira ibicuruzwa.", "m.pay": "Emeza ubwishyu kuri telefone yawe ({total}).",
      "m.female": "ingore", "m.male": "ingabo", "m.months": "amezi", "m.grade": "Icyiciro",
      "o.spent": "Amafaranga wakoresheje (byarangiye)", "o.progress": "Bikomeje", "o.answer": "Bikeneye igisubizo cyawe", "o.none": "Nta cyo uragura.",
      "o.accept": "Emera igiciro gishya", "o.decline": "Anga usubizwe amafaranga", "o.newtotal": "Igiteranyo gishya: {total}", "o.sim": "Sisitemu y'ikizamini: wigane ko nemeje ubwishyu", "o.simdone": "Ubwishyu bwemejwe.",
      "o.simnone": "Nta bwishyu butegereje.", "o.collect": "Byemejwe. Genda ubifate kwa Agent."
    },
    fr: {
      "t.market": "Marché", "t.orders": "Mes commandes", "t.acc": "Compte",
      "m.cat": "Produit", "m.grp": "Type", "m.village": "Village", "m.where": "Lieu", "m.detail": "Détails", "m.buy": "Acheter", "m.none": "Rien à vendre avec ces filtres.",
      "m.confirm": "Acheter {item} pour {total} ? L'argent est séquestré jusqu'à la vérification par l'agent.", "m.pay": "Validez l'invite mobile money sur votre téléphone ({total}).",
      "m.female": "femelle", "m.male": "mâle", "m.months": "mois", "m.grade": "Qualité",
      "o.spent": "Dépensé (terminé)", "o.progress": "En cours", "o.answer": "Votre réponse est attendue", "o.none": "Aucune commande pour le moment.",
      "o.accept": "Accepter le nouveau prix", "o.decline": "Refuser et être remboursé", "o.newtotal": "Nouveau total : {total}", "o.sim": "Système de test : simuler que j'ai validé le paiement", "o.simdone": "Paiement validé.",
      "o.simnone": "Aucun paiement en attente.", "o.collect": "Vérifié. À retirer chez l'agent."
    }
  });

  var cfg = {}, filt = { grp: "", cat: "", loc: "" };

  function market(main) {
    var list = h("div");
    Promise.all([E.cats(), E.locs()]).then(function (r) {
      var cats = r[0], locs = r[1];
      var grp = E.select([["", E.t("all")], ["crop", E.t("grp.crop")], ["livestock", E.t("grp.livestock")]], filt.grp);
      var cat = E.select([["", E.t("all")]].concat(cats.filter(function (c) { return !filt.grp || c.grp === filt.grp; }).map(function (c) { return [c.code, E.name(c)]; })), filt.cat);
      var loc = E.select([["", E.t("all")]].concat(E.villageOptions(locs)), filt.loc);
      grp.addEventListener("change", function () { filt = { grp: grp.value, cat: "", loc: loc.value }; market(main); });
      cat.addEventListener("change", function () { filt.cat = cat.value; load(); });
      loc.addEventListener("change", function () { filt.loc = loc.value; load(); });
      E.fill(main, [h("div", { class: "filters" }, E.field(E.t("m.grp"), grp), E.field(E.t("m.cat"), cat), E.field(E.t("m.village"), loc)), list]);
      load();
      function load() {
        E.fill(list, E.loading());
        E.api("/products" + (filt.cat ? "?category=" + encodeURIComponent(filt.cat) : "") + (filt.loc ? (filt.cat ? "&" : "?") + "location_id=" + filt.loc : "")).then(function (rows) {
          if (filt.grp) rows = rows.filter(function (p) { return p.grp === filt.grp; });
          E.fill(list, E.table([
            { label: E.t("m.cat"), render: function (p) { return h("div", null, h("b", { text: E.name(p) }), h("div", { class: "muted small code", text: p.code })); } },
            { label: E.t("qty"), num: true, render: function (p) { return E.num(p.quantity) + " " + E.unitName(p.unit); } },
            { label: E.t("price"), num: true, render: function (p) { return E.money(p.price_per_unit); } },
            { label: E.t("total"), num: true, render: function (p) { return E.money(Math.round(p.quantity * p.price_per_unit)); } },
            { label: E.t("m.detail"), render: function (p) {
              var t = [];
              if (p.sex) t.push(E.t("m." + p.sex)); if (p.age_months) t.push(p.age_months + " " + E.t("m.months")); if (p.grade) t.push(E.t("m.grade") + " " + p.grade);
              return h("div", { class: "tags" }, t.map(function (x) { return h("span", { class: "tag", text: x }); }));
            } },
            { label: E.t("m.where"), render: function (p) { return (p.village || "-") + ", " + (p.sector || ""); } },
            { label: "", render: function (p) { return h("button", { class: "btn small", text: E.t("m.buy"), on: { click: function () { buy(p); } } }); } }
          ], rows, E.t("m.none")));
        }).catch(function (e) { E.fill(list, h("div", { class: "notice bad", text: E.err(e) })); });
      }
    });
  }

  function buy(p) {
    var total = Math.round(p.quantity * p.price_per_unit);
    E.confirm(E.t("m.buy"), E.t("m.confirm", { item: E.name(p) + " " + E.num(p.quantity) + " " + E.unitName(p.unit), total: E.money(total) }), E.t("m.buy")).then(function (yes) {
      if (!yes) return;
      E.api("/orders", { body: { product_id: p.id } }).then(function () { E.toast(E.t("m.pay", { total: E.money(total) })); w.location.hash = "orders"; select("orders"); })
        .catch(function (e) { E.toast(E.err(e), true); });
    });
  }

  function orders(main) {
    E.fill(main, E.loading());
    E.api("/portal/buyer").then(function (d) {
      var t = d.totals, pending = d.orders.some(function (o) { return o.status === "awaiting_payment"; });
      var sim = cfg.test_payments && pending ? h("button", { class: "btn sun", text: E.t("o.sim") }) : null;
      if (sim) sim.addEventListener("click", function () { E.busy(sim, function () { return E.api("/test/approve-mine", { body: {} }).then(function (r) { E.toast(r.approved ? E.t("o.simdone") : E.t("o.simnone")); orders(main); }); }); });
      E.fill(main, [
        E.kpis([{ label: E.t("o.spent"), value: E.money(t.spent), tone: "accent" }, { label: E.t("o.progress"), value: E.num(t.in_progress) }, { label: E.t("o.answer"), value: E.num(t.needs_your_answer), tone: t.needs_your_answer ? "soil" : "" }]),
        sim ? h("p", null, sim) : null,
        E.table([
          { label: E.t("product"), render: function (o) { return h("div", null, h("b", { text: E.name(o) }), h("div", { class: "muted small code", text: o.product })); } },
          { label: E.t("qty"), num: true, render: function (o) { return E.num(o.quantity) + " " + E.unitName(o.unit); } },
          { label: E.t("total"), num: true, render: function (o) { return E.money(o.status === "revision_pending" && o.revised_total ? o.revised_total : o.total_amount); } },
          { label: E.t("status"), render: function (o) { return h("div", null, E.orderStatus(o.status), o.status === "verified" ? h("div", { class: "muted small", text: E.t("o.collect") }) : null); } },
          { label: E.t("date"), render: function (o) { return E.date(o.created_at); } },
          { label: "", render: function (o) {
            if (o.status !== "revision_pending") return "";
            function answer(accept) { E.api("/orders/" + o.order_id + "/revision", { body: { accept: accept } }).then(function () { orders(main); }).catch(function (e) { E.toast(E.err(e), true); }); }
            return h("div", null, h("div", { class: "small", text: E.t("o.newtotal", { total: E.money(o.revised_total) }) }),
              h("div", { class: "actions" }, h("button", { class: "btn small", text: E.t("o.accept"), on: { click: function () { answer(true); } } }),
                h("button", { class: "btn small danger", text: E.t("o.decline"), on: { click: function () { answer(false); } } })));
          } }
        ], d.orders, E.t("o.none"))
      ]);
    }).catch(function (e) { E.fill(main, h("div", { class: "notice bad", text: E.err(e) })); });
  }

  var select = function () {};
  E.guard(["buyer"]).then(function (u) {
    E.config().then(function (c) {
      cfg = c;
      var s = E.shell(E.$("root"), { user: u, tabs: [{ id: "market", label: "t.market" }, { id: "orders", label: "t.orders" }, { id: "acc", label: "t.acc" }],
        onTab: function (id, main) { if (id === "market") market(main); else if (id === "orders") orders(main); else E.fill(main, E.accountPanel(u, true)); } });
      select = s.select;
    });
  }).catch(function () {});
})(window);
