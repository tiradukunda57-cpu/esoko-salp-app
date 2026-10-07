/* Admin / SuperAdmin console. SuperAdmin additionally edits fees, catalogue and rules, and can browse the database. */
(function (w) {
  "use strict";
  var E = w.E, h = E.h;

  E.i18n({
    en: {
      "t.ov": "Overview", "t.people": "People", "t.fees": "Fees", "t.cat": "Products", "t.rules": "Gov. rules", "t.places": "Villages", "t.tools": "Test tools", "t.data": "Database", "t.audit": "Activity log", "t.acc": "Account",
      "a.users": "Accounts", "a.gmv": "Sales completed", "a.reg": "Registration fees", "a.comm": "Commission", "a.fees": "Listing and gate fees collected", "a.accr": "Fees waiting to be collected", "a.failed": "Failed payments",
      "a.items": "Items by state",
      "p.role": "Role", "p.all": "All roles", "p.q": "Search name or phone", "p.add": "Add staff", "p.reset": "New password", "p.resetq": "Set a new temporary password for this person? The old one stops working.", "p.resetdone": "New password (shown only now - write it down and give it to the person):", "p.suspend": "Suspend", "p.activate": "Activate", "p.pw": "Password (8+ characters)", "p.area": "Area (for Agents)",
      "p.created": "Staff account created.", "p.permit": "Record document",
      "fe.registration_fee": "Registration fee (Frw)", "fe.listing_fee": "Listing fee (Frw)", "fe.commission_bps": "Commission (basis points: 200 = 2%)", "fe.clearance_fee": "Market gate code fee (Frw)",
      "fe.saved": "Saved.", "fe.readonly": "Only the SuperAdmin can change fees.",
      "c.add": "Add a product or animal type", "c.code": "Code (letters, e.g. rabbits)", "c.prefix": "3 capital letters", "c.unit": "Unit", "c.grp": "Group", "c.rw": "Name in Kinyarwanda", "c.en": "Name in English", "c.fr": "Name in French",
      "c.on": "On sale", "c.off": "Hidden", "c.hide": "Hide", "c.show": "Show", "c.done": "Added.",
      "ru.add": "Add a government rule", "ru.help": "A rule is data. Add it when the Government asks for a new document. Keep it off until the start date.", "ru.code": "Code (lower case, e.g. vet_certificate)",
      "ru.subject": "Applies to", "ru.at": "Checked when", "ru.applies": "Which products", "ru.issuer": "Issued by", "ru.mandatory": "Blocks the step when missing", "ru.active": "In force",
      "ru.sub_user": "A person", "ru.sub_product": "A product", "ru.done": "Rule added.", "ru.toggle_on": "Switch on", "ru.toggle_off": "Switch off", "ru.block": "Make blocking", "ru.advise": "Make advisory",
      "pl.title": "Add villages", "pl.help": "One village per line: village, cell, sector, district. Existing lines are skipped.", "pl.go": "Add villages", "pl.result": "Added {added}, skipped {skipped}.", "pl.errors": "Lines with problems",
      "tl.title": "Run the Tuesday/Friday checkup now", "tl.go": "Run checkup", "tl.help": "Sold items get a congratulation SMS. Unsold items get a gate code. Safe to run twice.", "tl.done": "Checkup finished.",
      "tl.pay": "Payments waiting for approval (test system)", "tl.nopay": "No payments waiting.", "tl.ok": "Approve", "tl.fail": "Decline", "tl.sms": "Text messages (test system: nothing is sent to real phones)", "tl.nosms": "No messages yet.",
      "d.title": "Database", "d.help": "Read-only view of every table, for the SuperAdmin only. Passwords and ID hashes are never shown. Every view is written to the activity log.",
      "d.engine": "Engine", "d.rows": "rows", "d.back": "All tables", "d.search": "Search in this table", "d.csv": "Download CSV", "d.hidden": "Hidden for safety", "d.page": "{from}-{to} of {total}", "d.empty": "No rows.",
      "d.neon": "For raw SQL, open your Neon project and use its SQL Editor or Tables page.",
      "au.when": "When", "au.who": "User", "au.action": "Action", "au.what": "On", "au.detail": "Detail"
    },
    rw: {
      "t.ov": "Incamake", "t.people": "Abantu", "t.fees": "Amafaranga", "t.cat": "Ibicuruzwa", "t.rules": "Amategeko ya Leta", "t.places": "Imidugudu", "t.tools": "Ibikoresho by'ikizamini", "t.data": "Database", "t.audit": "Ibyakozwe", "t.acc": "Konti",
      "a.users": "Konti", "a.gmv": "Ibyagurishijwe byarangiye", "a.reg": "Amafaranga yo kwiyandikisha", "a.comm": "Komisiyo", "a.fees": "Amafaranga yakusanyijwe yo kwandikisha no ku irembo", "a.accr": "Amafaranga ategereje gukusanywa", "a.failed": "Ubwishyu bwanze",
      "a.items": "Ibicuruzwa ukurikije imiterere",
      "p.role": "Uruhare", "p.all": "Uruhare rwose", "p.q": "Shakisha izina cyangwa telefone", "p.add": "Ongeraho umukozi", "p.reset": "Ijambo ry'ibanga rishya", "p.resetq": "Ushaka guha uyu muntu ijambo ry'ibanga rishya ry'agateganyo? Irisanzwe rizahita ritongera gukora.", "p.resetdone": "Ijambo ry'ibanga rishya. Rigaragara ubu gusa: ryandike, urihe uwo muntu.", "p.suspend": "Hagarika", "p.activate": "Subizaho konti", "p.pw": "Ijambo ry'ibanga (inyuguti 8+)", "p.area": "Agace (kuri Agent)",
      "p.created": "Konti y'umukozi yafunguwe.", "p.permit": "Andika icyangombwa",
      "fe.registration_fee": "Amafaranga yo kwiyandikisha (Frw)", "fe.listing_fee": "Amafaranga yo kwandikisha igicuruzwa (Frw)", "fe.commission_bps": "Komisiyo (basis points: 200 = 2%)", "fe.clearance_fee": "Amafaranga ya kode y'irembo (Frw)",
      "fe.saved": "Byabitswe.", "fe.readonly": "SuperAdmin wenyine ashobora guhindura amafaranga.",
      "c.add": "Ongeraho ubwoko bw'igicuruzwa cyangwa itungo", "c.code": "Kode (inyuguti, urugero rabbits)", "c.prefix": "Inyuguti 3 nkuru", "c.unit": "Igipimo", "c.grp": "Itsinda", "c.rw": "Izina mu Kinyarwanda", "c.en": "Izina mu Cyongereza", "c.fr": "Izina mu Gifaransa",
      "c.on": "Kirigurishwa", "c.off": "Cyahishwe", "c.hide": "Hisha", "c.show": "Erekana", "c.done": "Byongewe.",
      "ru.add": "Ongeraho itegeko rya Leta", "ru.help": "Itegeko ribikwa nk'amakuru, si code. Ryongeremo igihe Leta isabye icyangombwa gishya. Ririreke ritari gukora kugeza ku itariki ritangiriraho.", "ru.code": "Kode (inyuguti nto, urugero vet_certificate)",
      "ru.subject": "Rireba", "ru.at": "Rigenzurwa", "ru.applies": "Ibicuruzwa riareba", "ru.issuer": "Gitangwa na", "ru.mandatory": "Rihagarika igikorwa iyo icyangombwa kibuze", "ru.active": "Rirakora",
      "ru.sub_user": "Umuntu", "ru.sub_product": "Igicuruzwa", "ru.done": "Itegeko ryongewe.", "ru.toggle_on": "Rikore", "ru.toggle_off": "Rihagarike", "ru.block": "Rihindure rihagarika", "ru.advise": "Rihindure inama gusa",
      "pl.title": "Ongeraho imidugudu", "pl.help": "Umudugudu umwe ku murongo: umudugudu, akagari, umurenge, akarere. Imirongo isanzwe irasimbukwa.", "pl.go": "Ongeraho", "pl.result": "Hongewe {added}, hasimbutse {skipped}.", "pl.errors": "Imirongo ifite ikibazo",
      "tl.title": "Kora ubu igenzura ryo ku wa Kabiri/ku wa Gatanu", "tl.go": "Kora igenzura", "tl.help": "Ibyaguzwe byoherezwa ubutumwa bwo gushimira. Ibitaguzwe bihabwa kode y'irembo. Wabikora kabiri nta kibazo kibaye.", "tl.done": "Igenzura ryarangiye.",
      "tl.pay": "Ubwishyu butegereje kwemezwa (sisitemu y'ikizamini)", "tl.nopay": "Nta bwishyu butegereje.", "tl.ok": "Emeza", "tl.fail": "Anga", "tl.sms": "Ubutumwa bwa SMS (ikizamini: nta butumwa bwoherezwa kuri telefone nyazo)", "tl.nosms": "Nta butumwa buraboneka.",
      "d.title": "Database", "d.help": "Kureba gusa buri mbonerahamwe, kuri SuperAdmin wenyine. Amagambo y'ibanga n'ibimenyetso bya hash z'indangamuntu ntibigaragara. Buri gusoma kose kubikwa mu bikorwa byakozwe.",
      "d.engine": "Ubwoko bwa database", "d.rows": "imirongo", "d.back": "Imbonerahamwe zose", "d.search": "Shakisha muri iyi mbonerahamwe", "d.csv": "Kuramo CSV", "d.hidden": "Byahishwe ku mutekano", "d.page": "{from}-{to} muri {total}", "d.empty": "Nta mirongo.",
      "d.neon": "Ushaka gukoresha SQL ubwawe, fungura umushinga wawe kuri Neon ukoreshe SQL Editor cyangwa Tables.",
      "au.when": "Igihe", "au.who": "Uwabikoze", "au.action": "Igikorwa", "au.what": "Kuri", "au.detail": "Ibisobanuro"
    },
    fr: {
      "t.ov": "Aperçu", "t.people": "Personnes", "t.fees": "Frais", "t.cat": "Produits", "t.rules": "Règles de l'État", "t.places": "Villages", "t.tools": "Outils de test", "t.data": "Base de données", "t.audit": "Journal", "t.acc": "Compte",
      "a.users": "Comptes", "a.gmv": "Ventes terminées", "a.reg": "Frais d'inscription", "a.comm": "Commission", "a.fees": "Frais d'annonce et de porte perçus", "a.accr": "Frais en attente de perception", "a.failed": "Paiements échoués",
      "a.items": "Articles par état",
      "p.role": "Rôle", "p.all": "Tous les rôles", "p.q": "Rechercher nom ou téléphone", "p.add": "Ajouter du personnel", "p.reset": "Nouveau mot de passe", "p.resetq": "Définir un nouveau mot de passe temporaire ? L'ancien ne fonctionnera plus.", "p.resetdone": "Nouveau mot de passe (affiché une seule fois) :", "p.suspend": "Suspendre", "p.activate": "Réactiver", "p.pw": "Mot de passe (8+ caractères)", "p.area": "Zone (pour les agents)",
      "p.created": "Compte du personnel créé.", "p.permit": "Enregistrer un document",
      "fe.registration_fee": "Frais d'inscription (Frw)", "fe.listing_fee": "Frais d'annonce (Frw)", "fe.commission_bps": "Commission (points de base : 200 = 2 %)", "fe.clearance_fee": "Frais du code de porte (Frw)",
      "fe.saved": "Enregistré.", "fe.readonly": "Seul le SuperAdmin peut modifier les frais.",
      "c.add": "Ajouter un type de produit ou d'animal", "c.code": "Code (lettres, ex. rabbits)", "c.prefix": "3 majuscules", "c.unit": "Unité", "c.grp": "Groupe", "c.rw": "Nom en kinyarwanda", "c.en": "Nom en anglais", "c.fr": "Nom en français",
      "c.on": "En vente", "c.off": "Masqué", "c.hide": "Masquer", "c.show": "Afficher", "c.done": "Ajouté.",
      "ru.add": "Ajouter une règle de l'État", "ru.help": "Une règle est une donnée. Ajoutez-la quand l'État exige un nouveau document. Laissez-la désactivée jusqu'à la date d'entrée en vigueur.", "ru.code": "Code (minuscules, ex. vet_certificate)",
      "ru.subject": "Concerne", "ru.at": "Contrôlée quand", "ru.applies": "Quels produits", "ru.issuer": "Délivré par", "ru.mandatory": "Bloque l'étape si absent", "ru.active": "En vigueur",
      "ru.sub_user": "Une personne", "ru.sub_product": "Un produit", "ru.done": "Règle ajoutée.", "ru.toggle_on": "Activer", "ru.toggle_off": "Désactiver", "ru.block": "Rendre bloquante", "ru.advise": "Rendre indicative",
      "pl.title": "Ajouter des villages", "pl.help": "Un village par ligne : village, cellule, secteur, district. Les lignes existantes sont ignorées.", "pl.go": "Ajouter", "pl.result": "{added} ajoutés, {skipped} ignorés.", "pl.errors": "Lignes avec problème",
      "tl.title": "Lancer le contrôle du mardi/vendredi maintenant", "tl.go": "Lancer le contrôle", "tl.help": "Les articles vendus reçoivent un SMS de félicitations, les invendus un code de porte. Peut être lancé deux fois.", "tl.done": "Contrôle terminé.",
      "tl.pay": "Paiements en attente de validation (système de test)", "tl.nopay": "Aucun paiement en attente.", "tl.ok": "Valider", "tl.fail": "Refuser", "tl.sms": "SMS (système de test : rien n'est envoyé aux vrais téléphones)", "tl.nosms": "Aucun message.",
      "d.title": "Base de données", "d.help": "Vue en lecture seule de chaque table, réservée au SuperAdmin. Les mots de passe et empreintes d'identifiants ne sont jamais affichés. Chaque consultation est journalisée.",
      "d.engine": "Moteur", "d.rows": "lignes", "d.back": "Toutes les tables", "d.search": "Rechercher dans cette table", "d.csv": "Télécharger en CSV", "d.hidden": "Masqué par sécurité", "d.page": "{from}-{to} sur {total}", "d.empty": "Aucune ligne.",
      "d.neon": "Pour du SQL brut, ouvrez votre projet Neon et utilisez son SQL Editor ou la page Tables.",
      "au.when": "Quand", "au.who": "Utilisateur", "au.action": "Action", "au.what": "Sur", "au.detail": "Détail"
    }
  });

  var me = null, cfg = {}, isSuper = false;
  function fail(el) { return function (e) { E.fill(el, h("div", { class: "notice bad", text: E.err(e) })); }; }

  /* ---------------------------------------------------------------- overview */
  function overview(main) {
    var top = h("div"), rest = h("div");
    E.fill(main, [top, rest]);
    E.api("/admin/summary").then(function (s) {
      var users = 0; Object.keys(s.users).forEach(function (k) { users += s.users[k]; });
      var i = s.income;
      E.fill(top, [E.kpis([{ label: E.t("a.users"), value: E.num(users) }, { label: E.t("a.gmv"), value: E.money(s.gmv_completed), tone: "accent" }, { label: E.t("a.reg"), value: E.money(i.registration_fees) },
        { label: E.t("a.comm"), value: E.money(i.commission) }, { label: E.t("a.fees"), value: E.money(i.listing_and_clearance_fees_settled) }, { label: E.t("a.accr"), value: E.money(i.fees_accrued_not_yet_collected) },
        { label: E.t("a.failed"), value: E.num(s.failed_payments), tone: s.failed_payments ? "soil" : "" }]),
        E.section(E.t("a.items"), null, Object.keys(s.products).length ? h("div", { class: "tags" }, Object.keys(s.products).map(function (k) { return h("span", { class: "tag", text: E.t("ps." + k) + ": " + s.products[k] }); })) : E.empty(E.t("none")))]);
    }).catch(fail(top));
    E.overview(rest);
  }

  /* ---------------------------------------------------------------- people */
  function people(main) {
    var role = E.select([["", E.t("p.all")]].concat(["farmer", "buyer", "agent", "gate", "admin", "government", "superadmin"].map(function (r) { return [r, E.t("role." + r)]; })));
    var q = h("input", { type: "search" }), list = h("div"), timer = null;
    function load() {
      E.api("/admin/users?" + (role.value ? "role=" + role.value + "&" : "") + (q.value ? "q=" + encodeURIComponent(q.value) : "")).then(function (rows) {
        E.fill(list, E.table([
          { label: E.t("name"), key: "name" }, { label: E.t("phone"), key: "phone", nowrap: true }, { label: "ID ****", render: function (u) { return u.national_id_last4 || "-"; } }, { label: E.t("p.role"), render: function (u) { return E.t("role." + u.role); } },
          { label: E.t("status"), render: function (u) { return E.status(u.status, u.status); } }, { label: E.t("date"), render: function (u) { return E.date(u.created_at); } },
          { label: "", render: function (u) {
            if (u.role === "superadmin" || u.id === me.id) return "";
            var a = h("div", { class: "actions" });
            if (u.status === "active") a.appendChild(h("button", { class: "btn small danger", text: E.t("p.suspend"), on: { click: function () { setStatus(u, "suspended"); } } }));
            else a.appendChild(h("button", { class: "btn small", text: E.t("p.activate"), on: { click: function () { setStatus(u, "active"); } } }));
            if (isSuper || ["agent", "gate", "farmer", "buyer"].indexOf(u.role) >= 0) a.appendChild(h("button", { class: "btn small sec", text: E.t("p.reset"), on: { click: function () { resetPw(u); } } }));
            if (u.role === "farmer" || u.role === "buyer") a.appendChild(h("button", { class: "btn small sec", text: E.t("p.permit"), on: { click: function () { E.permitModal({ subject: "user", user_id: u.id, role: u.role }); } } }));
            return a;
          } }
        ], rows));
      }).catch(fail(list));
    }
    function resetPw(u) {
      E.confirm(E.t("p.reset"), E.t("p.resetq") + " (" + u.name + ", " + u.phone + ")", E.t("p.reset")).then(function (yes) {
        if (!yes) return;
        E.api("/admin/users/" + u.id + "/reset-password", { body: {} }).then(function (r) {
          E.modal(E.t("p.reset"), function (close) {
            return h("div", null, h("p", { text: E.t("p.resetdone") }), h("p", null, h("strong", { class: "mono", style: "font-size:1.4rem;user-select:all", text: r.password })),
              h("div", { class: "actions" }, h("button", { class: "btn", text: "OK", on: { click: close } })));
          });
        }).catch(function (e) { E.toast(E.err(e), true); });
      });
    }
    function setStatus(u, s) { E.api("/admin/users/" + u.id + "/status", { body: { status: s } }).then(load).catch(function (e) { E.toast(E.err(e), true); }); }
    role.addEventListener("change", load);
    q.addEventListener("input", function () { clearTimeout(timer); timer = setTimeout(load, 300); });
    E.fill(main, [h("div", { class: "filters" }, E.field(E.t("p.role"), role), E.field(E.t("search"), q), h("button", { class: "btn", text: E.t("p.add"), on: { click: function () { addStaff(load); } } })), list]);
    load();
  }
  function addStaff(done) {
    E.locs().then(function (locs) {
      E.modal(E.t("p.add"), function (close) {
        var roles = isSuper ? ["agent", "gate", "admin", "government"] : ["agent", "gate"];
        var role = E.select(roles.map(function (r) { return [r, E.t("role." + r)]; })), name = h("input"), ph = h("input", { type: "tel" }), pw = h("input", { type: "password", autocomplete: "new-password" });
        var loc = E.select([["", "-"]].concat(E.villageOptions(locs))), err = h("div", { class: "err", role: "alert" }), ok = h("button", { class: "btn", text: E.t("save") });
        var locw = E.field(E.t("p.area"), loc);
        function sync() { locw.classList.toggle("hidden", role.value !== "agent"); } role.addEventListener("change", sync); sync();
        ok.addEventListener("click", function () {
          err.textContent = "";
          E.busy(ok, function () { return E.api("/admin/users", { body: { role: role.value, name: name.value, phone: ph.value, password: pw.value, location_id: role.value === "agent" && loc.value ? Number(loc.value) : null } })
            .then(function () { close(); E.toast(E.t("p.created")); done(); }); }).catch(function (e) { err.textContent = E.err(e); });
        });
        return h("div", null, E.field(E.t("p.role"), role), E.field(E.t("name"), name), E.field(E.t("phone"), ph), E.field(E.t("p.pw"), pw), locw, err,
          h("div", { class: "actions" }, h("button", { class: "btn sec", text: E.t("cancel"), on: { click: close } }), ok));
      });
    });
  }

  /* ---------------------------------------------------------------- fees */
  function fees(main) {
    E.fill(main, E.loading());
    E.api("/admin/fees").then(function (f) {
      var keys = ["registration_fee", "listing_fee", "commission_bps", "clearance_fee"], inputs = {};
      var rows = keys.map(function (k) {
        inputs[k] = h("input", { type: "number", min: "0", value: f[k], disabled: !isSuper });
        var b = h("button", { class: "btn small", text: E.t("save"), disabled: !isSuper });
        b.addEventListener("click", function () { E.busy(b, function () { return E.api("/admin/fees", { method: "PUT", body: { key: k, value: Number(inputs[k].value) } }).then(function () { E.toast(E.t("fe.saved")); }); }); });
        return h("div", { class: "row", style: "margin-bottom:10px" }, E.field(E.t("fe." + k), inputs[k]), h("div", null, b));
      });
      E.fill(main, E.section(E.t("t.fees"), null, h("div", { class: "panel", style: "max-width:560px" }, isSuper ? null : h("p", { class: "muted", text: E.t("fe.readonly") }), rows)));
    }).catch(fail(main));
  }

  /* ---------------------------------------------------------------- catalogue */
  function catalog(main) {
    E.fill(main, E.loading());
    E.api("/admin/categories").then(function (cats) {
      E.fill(main, [isSuper ? h("p", null, h("button", { class: "btn", text: E.t("c.add"), on: { click: function () { addCategory(function () { catalog(main); }); } } })) : null,
        E.table([{ label: E.t("product"), render: function (c) { return h("div", null, h("b", { text: E.name(c) }), h("div", { class: "muted small code", text: c.code + " / " + c.prefix })); } },
          { label: E.t("m.grp"), render: function (c) { return E.t("grp." + c.grp); } }, { label: E.t("c.unit"), render: function (c) { return E.unitName(c.unit); } },
          { label: E.t("status"), render: function (c) { return E.status(c.active ? "ok" : "", E.t(c.active ? "c.on" : "c.off")); } },
          { label: "", render: function (c) { return isSuper ? h("button", { class: "btn small sec", text: E.t(c.active ? "c.hide" : "c.show"), on: { click: function () {
            E.api("/admin/categories/" + c.code + "/active", { body: { active: !c.active } }).then(function () { catalog(main); }).catch(function (e) { E.toast(E.err(e), true); }); } } }) : ""; } }], cats)]);
    }).catch(fail(main));
  }
  function addCategory(done) {
    E.modal(E.t("c.add"), function (close) {
      var code = h("input", { maxlength: "30" }), prefix = h("input", { maxlength: "3" }), unit = E.select([["head", E.unitName("head")], ["sack", E.unitName("sack")], ["bunch", E.unitName("bunch")], ["kg", "kg"]]);
      var grp = E.select([["livestock", E.t("grp.livestock")], ["crop", E.t("grp.crop")]]), rw = h("input"), en = h("input"), fr = h("input");
      var err = h("div", { class: "err", role: "alert" }), ok = h("button", { class: "btn", text: E.t("save") });
      ok.addEventListener("click", function () {
        err.textContent = "";
        E.busy(ok, function () { return E.api("/admin/categories", { body: { code: code.value.trim().toLowerCase(), grp: grp.value, prefix: prefix.value.trim().toUpperCase(), unit: unit.value, name_rw: rw.value, name_en: en.value, name_fr: fr.value } })
          .then(function () { close(); E.toast(E.t("c.done")); done(); }); }).catch(function (e) { err.textContent = E.err(e); });
      });
      return h("div", null, E.field(E.t("c.code"), code), h("div", { class: "row" }, E.field(E.t("c.prefix"), prefix), E.field(E.t("c.grp"), grp), E.field(E.t("c.unit"), unit)),
        E.field(E.t("c.rw"), rw), E.field(E.t("c.en"), en), E.field(E.t("c.fr"), fr), err, h("div", { class: "actions" }, h("button", { class: "btn sec", text: E.t("cancel"), on: { click: close } }), ok));
    });
  }

  /* ---------------------------------------------------------------- government rules */
  function rules(main) {
    E.fill(main, E.loading());
    E.api("/admin/permit-types").then(function (list) {
      function patch(r, ch) { E.api("/admin/permit-types/" + r.code, { method: "PATCH", body: ch }).then(function () { rules(main); }).catch(function (e) { E.toast(E.err(e), true); }); }
      E.fill(main, [h("p", { class: "muted", text: E.t("ru.help") }), isSuper ? h("p", null, h("button", { class: "btn", text: E.t("ru.add"), on: { click: function () { addRule(function () { rules(main); }); } } })) : null,
        E.table([
          { label: E.t("rules.name"), render: function (r) { return h("div", null, h("b", { text: E.name(r) }), h("div", { class: "muted small", text: r.code })); } },
          { label: E.t("ru.subject"), render: function (r) { return E.t("ru.sub_" + r.subject); } },
          { label: E.t("rules.when"), render: function (r) { return E.t("when." + r.required_at); } },
          { label: E.t("rules.applies"), render: function (r) { return r.applies_to; } },
          { label: E.t("rules.state"), render: function (r) { return r.active ? E.status(r.mandatory ? "bad" : "wait", E.t(r.mandatory ? "rules.blocking" : "rules.advisory")) : E.status("", E.t("rules.off")); } },
          { label: "", render: function (r) { return isSuper ? h("div", { class: "actions" },
            h("button", { class: "btn small" + (r.active ? " danger" : ""), text: E.t(r.active ? "ru.toggle_off" : "ru.toggle_on"), on: { click: function () { patch(r, { active: !r.active }); } } }),
            h("button", { class: "btn small sec", text: E.t(r.mandatory ? "ru.advise" : "ru.block"), on: { click: function () { patch(r, { mandatory: !r.mandatory }); } } })) : ""; } }
        ], list)]);
    }).catch(fail(main));
  }
  var STAGES = { user: [["listing", "when.listing"], ["purchase", "when.purchase"]], product: [["handover", "when.handover"], ["market_entry", "when.market_entry"]] };
  function addRule(done) {
    E.cats().then(function (cats) {
      E.modal(E.t("ru.add"), function (close) {
        var code = h("input"), rw = h("input"), en = h("input"), fr = h("input"), issuer = h("input"), subject = E.select([["product", E.t("ru.sub_product")], ["user", E.t("ru.sub_user")]]);
        var at = h("select"), applies = E.select([["all", E.t("applies.all")], ["crop", E.t("applies.crop")], ["livestock", E.t("applies.livestock")]].concat(cats.map(function (c) { return [c.code, E.name(c)]; })));
        var mand = h("input", { type: "checkbox", id: "mand" }), act = h("input", { type: "checkbox", id: "act" });
        var err = h("div", { class: "err", role: "alert" }), ok = h("button", { class: "btn", text: E.t("save") });
        function sync() { E.fill(at, STAGES[subject.value].map(function (s) { return h("option", { value: s[0], text: E.t(s[1]) }); })); } subject.addEventListener("change", sync); sync();
        ok.addEventListener("click", function () {
          err.textContent = "";
          E.busy(ok, function () { return E.api("/admin/permit-types", { body: { code: code.value.trim(), name_rw: rw.value, name_en: en.value, name_fr: fr.value, subject: subject.value, required_at: at.value, applies_to: applies.value,
            issuer: issuer.value || null, mandatory: mand.checked, active: act.checked } }).then(function () { close(); E.toast(E.t("ru.done")); done(); }); }).catch(function (e) { err.textContent = E.err(e); });
        });
        return h("div", null, E.field(E.t("ru.code"), code), E.field(E.t("c.rw"), rw), E.field(E.t("c.en"), en), E.field(E.t("c.fr"), fr), E.field(E.t("ru.issuer"), issuer),
          h("div", { class: "row" }, E.field(E.t("ru.subject"), subject), E.field(E.t("ru.at"), at)), E.field(E.t("ru.applies"), applies),
          h("label", { class: "check", for: "mand" }, mand, h("span", { text: E.t("ru.mandatory") })), h("label", { class: "check", for: "act" }, act, h("span", { text: E.t("ru.active") })), err,
          h("div", { class: "actions" }, h("button", { class: "btn sec", text: E.t("cancel"), on: { click: close } }), ok));
      });
    });
  }

  /* ---------------------------------------------------------------- villages */
  function places(main) {
    var ta = h("textarea", { rows: "10", placeholder: "Kagugu, Kagugu, Mana, Ngororero", spellcheck: "false" }), out = h("div"), go = h("button", { class: "btn", text: E.t("pl.go") });
    go.addEventListener("click", function () {
      E.busy(go, function () { return E.api("/admin/locations", { body: { text: ta.value } }).then(function (r) {
        _locP(); E.fill(out, [h("div", { class: "okmsg", text: E.t("pl.result", { added: r.added, skipped: r.skipped }) }),
          r.errors && r.errors.length ? h("div", { class: "notice bad" }, h("b", { text: E.t("pl.errors") }), h("pre", { text: r.errors.join("\n") })) : null]);
      }); });
    });
    E.fill(main, E.section(E.t("pl.title"), null, h("div", { class: "panel" }, h("p", { class: "muted", text: E.t("pl.help") }), ta, h("p", { style: "margin-top:12px" }, go), out)));
  }
  function _locP() { /* force the cached village list to reload next time */ E.locs = (function (orig) { return function () { return E.api("/locations", { anon: true }).catch(function () { return []; }); }; })(E.locs); }

  /* ---------------------------------------------------------------- test tools + one-off jobs */
  function tools(main) {
    var cp = h("div"), op = h("div");
    var run = h("button", { class: "btn", text: E.t("tl.go") });
    run.addEventListener("click", function () {
      E.confirm(E.t("tl.title"), E.t("tl.help"), E.t("tl.go")).then(function (yes) { if (!yes) return; E.busy(run, function () { return E.api("/admin/checkup", { body: {} }).then(function (r) { E.toast(E.t("tl.done") + " " + JSON.stringify(r.totals || {})); }); }); });
    });
    var parts = [isSuper ? E.section(E.t("tl.title"), null, h("div", { class: "panel" }, h("p", { class: "muted", text: E.t("tl.help") }), run)) : null];
    if (cfg.test_payments) parts.push(E.section(E.t("tl.pay"), null, cp));
    if (cfg.test_sms) parts.push(E.section(E.t("tl.sms"), null, op));
    E.fill(main, parts);
    function pay() {
      E.api("/admin/payments/pending").then(function (rows) {
        E.fill(cp, E.table([{ label: E.t("date"), render: function (r) { return E.dateTime(r.created_at); } }, { label: E.t("name"), key: "name" }, { label: E.t("phone"), key: "msisdn" }, { label: E.t("p.role"), key: "type" },
          { label: E.t("amount"), num: true, render: function (r) { return E.money(r.amount); } },
          { label: "", render: function (r) { function go(ok) { E.api("/admin/payments/confirm", { body: { provider_ref: r.provider_ref, success: ok } }).then(pay).catch(function (e) { E.toast(E.err(e), true); }); }
            return h("div", { class: "actions" }, h("button", { class: "btn small", text: E.t("tl.ok"), on: { click: function () { go(true); } } }), h("button", { class: "btn small danger", text: E.t("tl.fail"), on: { click: function () { go(false); } } })); } }], rows, E.t("tl.nopay")));
      }).catch(fail(cp));
    }
    function sms() {
      E.api("/admin/outbox").then(function (rows) {
        E.fill(op, [h("p", null, h("button", { class: "btn small sec", text: E.t("refresh"), on: { click: sms } })),
          E.table([{ label: E.t("date"), render: function (r) { return E.dateTime(r.created_at); } }, { label: E.t("phone"), key: "msisdn", nowrap: true }, { label: "SMS", key: "text" }], rows, E.t("tl.nosms"))]);
      }).catch(fail(op));
    }
    if (cfg.test_payments) pay(); if (cfg.test_sms) sms();
  }

  /* ---------------------------------------------------------------- database explorer (SuperAdmin) */
  function data(main) {
    var st = { table: null, offset: 0, q: "" }, LIMIT = 25;
    function tables() {
      E.fill(main, E.loading());
      E.api("/admin/db/tables").then(function (d) {
        E.fill(main, E.section(E.t("d.title"), h("span", { text: E.t("d.engine") + ": " + d.database }), h("div", null,
          h("p", { class: "muted", text: E.t("d.help") }),
          h("div", { class: "tablist" }, d.tables.map(function (t) { return h("button", { on: { click: function () { st = { table: t.name, offset: 0, q: "" }; rows(); } } }, h("b", { text: t.name }), h("span", { text: E.num(t.rows) + " " + E.t("d.rows") })); })),
          h("p", { class: "muted small", style: "margin-top:16px", text: E.t("d.neon") }))));
      }).catch(fail(main));
    }
    function url(fmt) { return "/admin/db/tables/" + st.table + "?limit=" + (fmt === "csv" ? 50000 : LIMIT) + "&offset=" + (fmt === "csv" ? 0 : st.offset) + (st.q ? "&q=" + encodeURIComponent(st.q) : "") + (fmt === "csv" ? "&format=csv" : ""); }
    function rows() {
      var body = h("div"), q = h("input", { type: "search", value: st.q, placeholder: E.t("d.search") }), timer = null;
      q.addEventListener("input", function () { clearTimeout(timer); timer = setTimeout(function () { st.q = q.value; st.offset = 0; load(); }, 350); });
      var csv = h("button", { class: "btn sec", text: E.t("d.csv") });
      csv.addEventListener("click", function () {
        E.busy(csv, function () { return fetch(url("csv"), { headers: { Authorization: "Bearer " + E.session.token() } }).then(function (r) { if (!r.ok) throw new Error(String(r.status)); return r.blob(); }).then(function (b) {
          var a = document.createElement("a"); a.href = URL.createObjectURL(b); a.download = st.table + ".csv"; document.body.appendChild(a); a.click(); a.remove(); setTimeout(function () { URL.revokeObjectURL(a.href); }, 2000); }); });
      });
      E.fill(main, [h("div", { class: "page-head" }, h("h2", { text: st.table }), h("button", { class: "link", text: E.t("d.back"), on: { click: tables } })),
        h("div", { class: "filters" }, E.field(E.t("search"), q), csv), body]);
      load();
      function load() {
        E.fill(body, E.loading());
        E.api(url()).then(function (d) {
          var from = d.total ? d.offset + 1 : 0, to = Math.min(d.offset + d.limit, d.total);
          var prev = h("button", { class: "btn small sec", text: E.t("prev"), disabled: d.offset <= 0, on: { click: function () { st.offset = Math.max(0, st.offset - LIMIT); load(); } } });
          var next = h("button", { class: "btn small sec", text: E.t("next"), disabled: to >= d.total, on: { click: function () { st.offset += LIMIT; load(); } } });
          E.fill(body, [d.hidden.length ? h("p", { class: "muted small", text: E.t("d.hidden") + ": " + d.hidden.join(", ") }) : null,
            d.rows.length ? h("div", { class: "tbl-wrap" }, h("table", null, h("thead", null, h("tr", null, d.columns.map(function (c) { return h("th", { text: c }); }))),
              h("tbody", null, d.rows.map(function (r) { return h("tr", null, r.map(function (v) { return h("td", { class: typeof v === "number" ? "n" : "", text: v === null ? "∅" : String(v) }); })); })))) : E.empty(E.t("d.empty")),
            h("div", { class: "pager" }, prev, next, h("span", { class: "muted small", text: E.t("d.page", { from: from, to: to, total: d.total }) }))]);
        }).catch(fail(body));
      }
    }
    tables();
  }

  /* ---------------------------------------------------------------- activity log */
  function audit(main) {
    E.fill(main, E.loading());
    E.api("/admin/audit?limit=200").then(function (rows) {
      E.fill(main, E.table([{ label: E.t("au.when"), render: function (r) { return E.dateTime(r.created_at); }, nowrap: true }, { label: E.t("au.who"), key: "actor_id" }, { label: E.t("au.action"), render: function (r) { return h("span", { class: "code", text: r.action }); } },
        { label: E.t("au.what"), render: function (r) { return (r.entity || "") + (r.entity_id ? " #" + r.entity_id : ""); } }, { label: E.t("au.detail"), render: function (r) { return h("span", { class: "small muted", text: r.detail }); } }], rows));
    }).catch(fail(main));
  }

  E.guard(["admin", "superadmin"]).then(function (u) {
    me = u; isSuper = u.role === "superadmin";
    E.config().then(function (c) {
      cfg = c;
      var tabs = [["ov", "t.ov"], ["people", "t.people"], ["fees", "t.fees"], ["cat", "t.cat"], ["rules", "t.rules"], ["places", "t.places"], ["tools", "t.tools"]];
      if (isSuper) tabs.push(["data", "t.data"], ["audit", "t.audit"]);
      tabs.push(["acc", "t.acc"]);
      var fn = { ov: overview, people: people, fees: fees, cat: catalog, rules: rules, places: places, tools: tools, data: data, audit: audit };
      E.shell(E.$("root"), { user: u, tabs: tabs.map(function (t) { return { id: t[0], label: t[1] }; }), onTab: function (id, main) { if (fn[id]) fn[id](main); else E.fill(main, E.accountPanel(u, true)); } });
    });
  }).catch(function () {});
})(window);
