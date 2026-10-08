/* Landing page: price board, one sign-in for everybody (each role is sent to its own dashboard), buyer registration. */
(function (w) {
  "use strict";
  var E = w.E, h = E.h;

  E.i18n({
    en: {
      "h.title": "Sell and buy farm produce and livestock, simply.", "h.lead": "List your crops or animals from any phone, even without internet. A verified Agent checks them, the buyer's money waits safely in escrow, and you are paid by mobile money.",
      "h.board": "Prices today", "h.board_sub": "Average asking price of items waiting for buyers", "h.noprices": "No items are listed right now. Prices appear here as farmers list.",
      "h.product": "Product", "h.avg": "Average", "h.range": "Range", "h.unit": "per",
      "s.title": "Sign in", "s.pw": "Password", "s.sms": "SMS code", "s.phone": "Phone number", "s.password": "Password", "s.in": "Sign in",
      "s.sendcode": "Send me a code", "s.code": "6-digit code", "s.verify": "Verify and sign in", "s.sent": "If this number is registered, a code was sent by SMS.",
      "s.hint_pw": "Buyers, Agents, administrators and government.", "s.hint_sms": "Farmers and buyers: we text you a 6-digit code.",
      "hint.bad_phone": "This is not a valid Rwandan phone number.", "hint.not_registered": "TEST SYSTEM: this number is not registered. Ask an Agent to register the farmer first.", "hint.staff_use_password": "TEST SYSTEM: Agents, administrators and government sign in with a password, not an SMS code.", "hint.pending_payment": "TEST SYSTEM: registration is not paid yet. Approve the payment first (Admin > Test tools, or the Agent screen).", "hint.suspended": "TEST SYSTEM: this account is suspended.", "hint.too_many_requests": "TEST SYSTEM: too many codes requested. Wait 10 minutes.", "s.new": "New buyer? Create an account", "s.farmer": "Farmers: you register through your sector Agent, or by dialing {code} on any phone. A buyer account is the only one you can open yourself.", "s.expired": "Your session ended. Please sign in again.",
      "r.title": "Create a buyer account", "r.name": "Full name", "r.id": "National ID (16 digits)", "r.pw": "Password (8+ characters)", "r.loc": "Where you are", "r.consent": "I agree that E-Soko stores my data to run this service.",
      "r.fee": "A one-time registration fee of {fee} is paid by mobile money.", "r.go": "Register", "r.done": "Registered. Approve the mobile-money prompt on your phone (fee {fee}), then sign in.",
      "r.sim": "Test system: simulate that I approved the payment", "r.simdone": "Payment approved. You can sign in now.", "r.nodata": "Do not use a real National ID on the test system.",
      "st.1": "List", "st.1t": "Farmers list produce or animals on the website or by dialing {code} on any phone.", "st.2": "Pay safely", "st.2t": "The buyer's money is held in escrow. Nobody is paid before the goods are checked.",
      "st.3": "Verify", "st.3t": "A local Agent checks quality, weight and ear tags, and the government documents that apply.", "st.4": "Get paid", "st.4t": "On handover the farmer is paid by mobile money. Unsold goods get a code to pass the market gate.",
      "f.help": "Help", "f.dial": "Dial", "f.test": "This is a test system. Payments and SMS are simulated."
    },
    rw: {
      "h.title": "Gura kandi ugurishe ibihingwa n'amatungo mu buryo bworoshye.", "h.lead": "Andikisha ibihingwa cyangwa amatungo yawe kuri telefone iyo ari yo yose, ntibisaba interineti. Agent wemewe arabipima, amafaranga y'umuguzi abikwa neza (escrow), nawe ukishyurwa kuri mobile money.",
      "h.board": "Ibiciro by'uyu munsi", "h.board_sub": "Impuzandengo y'ibiciro by'ibitegereje abaguzi", "h.noprices": "Nta kintu cyanditswe ubu. Ibiciro bizagaragara abahinzi nibamara kwandikisha.",
      "h.product": "Igicuruzwa", "h.avg": "Impuzandengo", "h.range": "Hagati ya", "h.unit": "kuri",
      "s.title": "Injira", "s.pw": "Ijambo ry'ibanga", "s.sms": "Kode ya SMS", "s.phone": "Nimero ya telefone", "s.password": "Ijambo ry'ibanga", "s.in": "Injira",
      "s.sendcode": "Nyoherereza kode", "s.code": "Kode y'imibare 6", "s.verify": "Emeza winjire", "s.sent": "Niba iyi nimero yanditse, kode yoherejwe kuri SMS.",
      "s.hint_pw": "Abaguzi, Agents, abayobozi n'abakozi ba Leta.", "s.hint_sms": "Abahinzi n'abaguzi: tuzakwoherereza kode y'imibare 6.",
      "hint.bad_phone": "Iyi si nimero ya telefone y'u Rwanda.", "hint.not_registered": "IKIZAMINI: iyi nimero ntiyanditswe. Saba Agent yandike umuhinzi mbere.", "hint.staff_use_password": "IKIZAMINI: Agents, abayobozi n'abakozi ba Leta binjira bakoresheje ijambo ry'ibanga, si kode ya SMS.", "hint.pending_payment": "IKIZAMINI: kwiyandikisha ntikurishyurwa. Banza wemeze ubwishyu (Admin > Ibikoresho by'ikizamini, cyangwa kuri Agent).", "hint.suspended": "IKIZAMINI: iyi konti yahagaritswe.", "hint.too_many_requests": "IKIZAMINI: wasabye kode inshuro nyinshi. Tegereza iminota 10.", "s.new": "Uri umuguzi mushya? Fungura konti", "s.farmer": "Abahinzi: iyandikishe kwa Agent wo mu murenge wawe, cyangwa uhamagare {code} kuri telefone iyo ari yo yose. Konti y'umuguzi ni yo yonyine wafungura ubwawe.", "s.expired": "Igihe cyawe cyarangiye. Ongera winjire.",
      "r.title": "Fungura konti y'umuguzi", "r.name": "Amazina yombi", "r.id": "Indangamuntu (imibare 16)", "r.pw": "Ijambo ry'ibanga (inyuguti 8+)", "r.loc": "Aho uherereye", "r.consent": "Nemeye ko E-Soko ibika amakuru yanjye kugira ngo ntange serivisi.",
      "r.fee": "Wishyura inshuro imwe gusa amafaranga yo kwiyandikisha ({fee}) kuri mobile money.", "r.go": "Iyandikishe", "r.done": "Wiyandikishije. Emeza ubwishyu kuri telefone yawe ({fee}), hanyuma winjire.",
      "r.sim": "Sisitemu y'ikizamini: wigane ko nemeje ubwishyu", "r.simdone": "Ubwishyu bwemejwe. Ushobora kwinjira.", "r.nodata": "Ntukoreshe Indangamuntu nyayo kuri sisitemu y'ikizamini.",
      "st.1": "Andikisha", "st.1t": "Abahinzi bandikisha ku rubuga cyangwa bahamagara {code} kuri telefone iyo ari yo yose.", "st.2": "Ishyura neza", "st.2t": "Amafaranga y'umuguzi abikwa (escrow). Nta wishyurwa mbere y'uko ibicuruzwa bipimwa.",
      "st.3": "Pima", "st.3t": "Agent wo mu gace apima ubwiza, ibiro n'ikarita y'itungo, ndetse n'ibyangombwa bya Leta bikenewe.", "st.4": "Wishyurwe", "st.4t": "Iyo bimaze kuzanwa, umuhinzi yishyurwa kuri mobile money. Ibitaguzwe bihabwa kode yo kunyura ku irembo ry'isoko.",
      "f.help": "Ubufasha", "f.dial": "Hamagara", "f.test": "Iyi ni sisitemu y'ikizamini. Ubwishyu na SMS ni ibyo kwigana."
    },
    fr: {
      "h.title": "Vendez et achetez produits agricoles et bétail, simplement.", "h.lead": "Enregistrez vos cultures ou animaux depuis n'importe quel téléphone, même sans internet. Un agent vérifié les contrôle, l'argent de l'acheteur reste en séquestre, et vous êtes payé par mobile money.",
      "h.board": "Prix du jour", "h.board_sub": "Prix moyen demandé des articles en attente d'acheteurs", "h.noprices": "Aucun article pour le moment. Les prix apparaîtront dès les premières annonces.",
      "h.product": "Produit", "h.avg": "Moyenne", "h.range": "Fourchette", "h.unit": "par",
      "s.title": "Connexion", "s.pw": "Mot de passe", "s.sms": "Code SMS", "s.phone": "Numéro de téléphone", "s.password": "Mot de passe", "s.in": "Se connecter",
      "s.sendcode": "Envoyez-moi un code", "s.code": "Code à 6 chiffres", "s.verify": "Valider et se connecter", "s.sent": "Si ce numéro est enregistré, un code a été envoyé par SMS.",
      "s.hint_pw": "Acheteurs, agents, administrateurs et État.", "s.hint_sms": "Agriculteurs et acheteurs : nous envoyons un code à 6 chiffres.",
      "hint.bad_phone": "Numéro de téléphone rwandais invalide.", "hint.not_registered": "TEST : ce numéro n'est pas inscrit. Demandez à un agent d'inscrire l'agriculteur.", "hint.staff_use_password": "TEST : agents, administrateurs et gouvernement se connectent avec un mot de passe.", "hint.pending_payment": "TEST : l'inscription n'est pas payée. Validez d'abord le paiement.", "hint.suspended": "TEST : ce compte est suspendu.", "hint.too_many_requests": "TEST : trop de codes demandés. Attendez 10 minutes.", "s.new": "Nouvel acheteur ? Créer un compte", "s.farmer": "Agriculteurs : inscrivez-vous auprès de l'agent de votre secteur, ou en composant {code} depuis n'importe quel téléphone. Seul le compte acheteur peut être créé par vous-même.", "s.expired": "Votre session a expiré. Reconnectez-vous.",
      "r.title": "Créer un compte acheteur", "r.name": "Nom complet", "r.id": "Identifiant national (16 chiffres)", "r.pw": "Mot de passe (8+ caractères)", "r.loc": "Votre localité", "r.consent": "J'accepte que E-Soko conserve mes données pour fournir ce service.",
      "r.fee": "Des frais d'inscription uniques de {fee} sont payés par mobile money.", "r.go": "S'inscrire", "r.done": "Inscrit. Validez l'invite mobile money sur votre téléphone ({fee}), puis connectez-vous.",
      "r.sim": "Système de test : simuler que j'ai validé le paiement", "r.simdone": "Paiement validé. Vous pouvez vous connecter.", "r.nodata": "N'utilisez pas un vrai identifiant national sur le système de test.",
      "st.1": "Annoncer", "st.1t": "Les agriculteurs enregistrent leurs produits sur le site ou en composant {code} depuis n'importe quel téléphone.", "st.2": "Payer en sécurité", "st.2t": "L'argent de l'acheteur est séquestré. Personne n'est payé avant le contrôle.",
      "st.3": "Vérifier", "st.3t": "Un agent local contrôle qualité, poids, boucles d'oreille et documents de l'État requis.", "st.4": "Être payé", "st.4t": "À la remise, l'agriculteur est payé par mobile money. Les invendus reçoivent un code pour la porte du marché.",
      "f.help": "Aide", "f.dial": "Composez", "f.test": "Ceci est un système de test. Paiements et SMS sont simulés."
    }
  });

  var root = E.$("root"), cfg = { mode: "test" };
  var farmerNote = E.h("p", { class: "muted small" });
  function setFarmerNote() { farmerNote.textContent = E.t("s.farmer", { code: cfg.shortcode || "*801#" }); }
  setFarmerNote(); E.onLang(setFarmerNote);

  function priceBoard() {
    var box = h("div", { class: "board live" });
    E.api("/public/prices", { anon: true }).then(function (rows) {
      if (!rows.length) { E.fill(box, h("div", { class: "board-row" }, h("span", { class: "name", text: E.t("h.noprices") }))); return; }
      var head = h("div", { class: "board-row board-head" }, h("span", { class: "name", text: E.t("h.product") }), h("span", { class: "price", text: E.t("h.avg") }), h("span", { class: "qty", text: E.t("h.range") }));
      E.fill(box, [head].concat(rows.map(function (r, i) {
        return h("div", { class: "board-row", style: "--i:" + i },
          h("span", { class: "name", text: E.name(r) }),
          h("span", { class: "price", text: E.money(r.avg_price) + " / " + E.unitName(r.unit) }),
          h("span", { class: "qty", text: E.num(r.min_price) + " - " + E.num(r.max_price) }));
      })));
    }).catch(function () { E.fill(box, h("div", { class: "board-row" }, h("span", { class: "name", text: E.t("h.noprices") }))); });
    return box;
  }

  function signIn() {
    var mode = "pw", seg = h("div", { class: "seg", role: "tablist" }), body = h("div"), err = h("div", { class: "err", role: "alert" });
    var phone = h("input", { type: "tel", inputmode: "tel", autocomplete: "username", placeholder: "07xx xxx xxx" });
    var pass = h("input", { type: "password", autocomplete: "current-password" });
    var code = h("input", { inputmode: "numeric", maxlength: "6", autocomplete: "one-time-code" });
    var go = h("button", { class: "btn block", style: "margin-top:16px" });
    var codeBlock = h("div", { class: "hidden" }), sent = false;

    function done(j) { E.session.set(j.token, j.user); w.location.href = E.home(j.user.role); }
    function render() {
      E.fill(seg, [["pw", "s.pw"], ["sms", "s.sms"]].map(function (m) {
        return h("button", { role: "tab", "aria-selected": mode === m[0] ? "true" : "false", text: E.t(m[1]),
          on: { click: function () { mode = m[0]; err.textContent = ""; render(); } } });
      }));
      E.fill(body, [h("p", { class: "muted small", text: E.t(mode === "pw" ? "s.hint_pw" : "s.hint_sms") }),
        E.field(E.t("s.phone"), phone), mode === "pw" ? E.field(E.t("s.password"), pass) : null,
        mode === "sms" ? E.fill(codeBlock, [E.field(E.t("s.code"), code)]) : null]);
      codeBlock.classList.toggle("hidden", !(mode === "sms" && sent));
      go.textContent = mode === "pw" ? E.t("s.in") : E.t(sent ? "s.verify" : "s.sendcode");
    }
    go.addEventListener("click", function () {
      err.textContent = "";
      E.busy(go, function () {
        if (mode === "pw") return E.api("/auth/login", { body: { phone: phone.value, password: pass.value }, anon: true }).then(done);
        if (!sent) return E.api("/auth/request-otp", { body: { phone: phone.value }, anon: true }).then(function (r) {
          if (r && r.test_hint) { err.textContent = E.t("hint." + r.test_hint); return; }
          sent = true; render(); E.toast(E.t("s.sent"));
        });
        return E.api("/auth/verify-otp", { body: { phone: phone.value, code: code.value }, anon: true }).then(done);
      }).catch(function (e) { err.textContent = E.err(e); });
    });
    [phone, pass, code].forEach(function (i) { i.addEventListener("keydown", function (e) { if (e.key === "Enter") go.click(); }); });
    E.onLang(render);
    render();
    var expired = /expired=1/.test(w.location.search) ? h("div", { class: "notice", text: E.t("s.expired") }) : null;
    return h("div", { class: "signin" }, h("h2", { text: E.t("s.title"), "data-i": "s.title" }), expired, seg, body, go, err,
      h("p", { style: "margin-top:14px" }, h("button", { class: "link", "data-i": "s.new", text: E.t("s.new"), on: { click: registerModal } })),
      farmerNote);
  }

  function registerModal() {
    E.locs().then(function (locs) {
      E.modal(E.t("r.title"), function (close) {
        var name = h("input", { autocomplete: "name" }), ph = h("input", { type: "tel", inputmode: "tel" }), nid = h("input", { inputmode: "numeric", maxlength: "16" });
        var pw = h("input", { type: "password", autocomplete: "new-password" });
        var loc = E.select([["", "-"]].concat(E.villageOptions(locs)));
        var consent = h("input", { type: "checkbox", id: "consent" });
        var err = h("div", { class: "err", role: "alert" }), ok = h("div", { class: "okmsg", role: "status" });
        var go = h("button", { class: "btn", text: E.t("r.go") });
        var fee = E.money(cfg.registration_fee || 500);
        var sim = h("button", { class: "btn sun hidden", text: E.t("r.sim") });
        go.addEventListener("click", function () {
          err.textContent = "";
          E.busy(go, function () {
            return E.api("/auth/register-buyer", { anon: true, body: { name: name.value, phone: ph.value, national_id: nid.value, password: pw.value,
              language: E.lang, location_id: loc.value ? Number(loc.value) : null, consent: consent.checked } }).then(function () {
              ok.textContent = E.t("r.done", { fee: fee }); go.classList.add("hidden");
              if (cfg.test_payments) sim.classList.remove("hidden");
            });
          }).catch(function (e) { err.textContent = E.err(e); });
        });
        sim.addEventListener("click", function () {
          E.busy(sim, function () { return E.api("/test/approve-registration", { anon: true, body: { phone: ph.value } }).then(function () { ok.textContent = E.t("r.simdone"); sim.classList.add("hidden"); }); });
        });
        return h("div", null, h("p", { class: "muted small", text: E.t("r.fee", { fee: fee }) }), cfg.mode === "test" ? h("p", { class: "small", text: E.t("r.nodata") }) : null,
          E.field(E.t("r.name"), name), E.field(E.t("phone"), ph), E.field(E.t("r.id"), nid), E.field(E.t("r.pw"), pw), E.field(E.t("r.loc"), loc),
          h("label", { class: "check", for: "consent" }, consent, h("span", { text: E.t("r.consent") })), err, ok,
          h("div", { class: "actions" }, h("button", { class: "btn sec", text: E.t("close"), on: { click: close } }), sim, go));
      });
    });
  }

  function page() {
    var code = cfg.shortcode || "*123#";
    E.fill(root, [
      h("div", { id: "tb" }),
      h("header", { class: "top" }, h("div", { class: "top-in" }, E.logo(), h("div", { class: "grow" }), E.langSelect())),
      h("div", { class: "band tall" }),
      h("main", null,
        h("section", { class: "hero" },
          h("div", null, h("h1", { "data-i": "h.title", text: E.t("h.title") }), h("p", { class: "lead", "data-i": "h.lead", text: E.t("h.lead") }),
            E.section(E.t("h.board"), h("span", { text: E.t("h.board_sub") }), priceBoard())),
          signIn()),
        h("div", { class: "steps" }, [1, 2, 3, 4].map(function (n) {
          return h("div", { class: "step" }, h("b", { text: "0" + n }), h("h3", { text: E.t("st." + n) }), h("p", { class: "muted", text: E.t("st." + n + "t", { code: code }) }));
        }))),
      h("footer", { class: "site" }, h("div", { class: "band", style: "margin-bottom:14px" }),
        h("div", null, E.t("f.dial") + " ", h("b", { text: code }), cfg.support_phone ? "  |  " + E.t("f.help") + ": " + cfg.support_phone : ""),
        cfg.mode === "test" ? h("div", { text: E.t("f.test") }) : null)
    ]);
    E.fill(E.$("tb"), E.testBar(cfg));
  }

  /* already signed in? go straight to the right dashboard */
  function start() {
    E.config().then(function (c) {
      cfg = c; setFarmerNote();
      if (E.session.token() && !/expired=1/.test(w.location.search)) {
        E.api("/auth/me").then(function (j) { w.location.replace(E.home(j.user.role)); }).catch(function () { page(); });
      } else { page(); }
    });
  }
  E.onLang(function () { if (root.firstChild) page(); });
  start();
})(window);
