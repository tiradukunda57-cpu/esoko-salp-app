/* USSD phone simulator (test systems only). Talks to POST /ussd exactly like a telecom gateway would. */
(function (w) {
  "use strict";
  var E = w.E, h = E.h;
  E.i18n({
    en: { "u.title": "USSD simulator", "u.help": "Try the phone menu a farmer sees when dialing the shortcode. Nothing is sent to a real phone.", "u.phone": "Phone number to simulate", "u.dial": "Dial", "u.send": "Send", "u.reset": "New session",
      "u.sim": "Test system: simulate that this number approved the registration payment", "u.simdone": "Registration payment approved.", "u.ended": "Session ended. Dial again." },
    rw: { "u.title": "Isuzuma rya USSD", "u.help": "Gerageza menu ihabwa umuhinzi ahamagaye kode ngufi. Nta kigera kuri telefone nyayo.", "u.phone": "Nimero ya telefone yo kwigana", "u.dial": "Hamagara", "u.send": "Ohereza", "u.reset": "Itangira rishya",
      "u.sim": "Ikizamini: wigane ko iyi nimero yemeje ubwishyu bwo kwiyandikisha", "u.simdone": "Ubwishyu bwo kwiyandikisha bwemejwe.", "u.ended": "Igihe cyarangiye. Ongera uhamagare." },
    fr: { "u.title": "Simulateur USSD", "u.help": "Essayez le menu vu par un agriculteur qui compose le code court. Rien n'est envoyé à un vrai téléphone.", "u.phone": "Numéro à simuler", "u.dial": "Composer", "u.send": "Envoyer", "u.reset": "Nouvelle session",
      "u.sim": "Test : simuler que ce numéro a validé le paiement d'inscription", "u.simdone": "Paiement d'inscription validé.", "u.ended": "Session terminée. Recomposez." }
  });
  var root = E.$("root"), steps = [], cfg = {};
  var screen = h("div", { class: "phone-screen", role: "status", "aria-live": "polite" }), input = h("input", { inputmode: "numeric", autocomplete: "off", "aria-label": "USSD" });
  var phone = h("input", { type: "tel", value: "0788000111" }), btn = h("button", { class: "btn sun", text: E.t("u.dial") }), live = false;

  function call() {
    var body = "phoneNumber=" + encodeURIComponent(phone.value) + "&text=" + encodeURIComponent(steps.join("*"));
    btn.disabled = true;
    fetch("/ussd", { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body: body }).then(function (r) { return r.text(); }).then(function (t) {
      var end = t.indexOf("END") === 0; screen.textContent = t.replace(/^(CON|END)\s?/, "") + (end ? "\n\n" + E.t("u.ended") : "");
      live = !end; btn.textContent = E.t(live ? "u.send" : "u.dial"); btn.disabled = false; input.value = ""; input.focus();
      if (end) steps = [];
    }).catch(function () { screen.textContent = E.t("e.network"); btn.disabled = false; });
  }
  btn.addEventListener("click", function () {
    if (live) { steps.push(input.value); } else { steps = (input.value && !/^\*/.test(input.value)) ? [input.value] : []; }
    call();
  });
  input.addEventListener("keydown", function (e) { if (e.key === "Enter") btn.click(); });

  E.config().then(function (c) {
    cfg = c;
    if (!c.ussd_simulator) { E.fill(root, h("main", null, E.empty("404"))); return; }
    var sim = h("button", { class: "btn sec", text: E.t("u.sim") });
    sim.addEventListener("click", function () { E.busy(sim, function () { return E.api("/test/approve-registration", { anon: true, body: { phone: phone.value } }).then(function () { E.toast(E.t("u.simdone")); }); }); });
    var reset = h("button", { class: "link", text: E.t("u.reset"), on: { click: function () { steps = []; live = false; btn.textContent = E.t("u.dial"); screen.textContent = ""; } } });
    E.fill(root, [E.testBar(c), h("header", { class: "top" }, h("div", { class: "top-in" }, E.logo(), h("div", { class: "grow" }), E.langSelect())), h("div", { class: "band" }),
      h("main", null, h("div", { class: "page-head" }, h("h1", { style: "font-size:2rem", text: E.t("u.title") })), h("p", { class: "muted", text: E.t("u.help") }),
        h("div", { class: "cols" },
          h("div", { class: "phone" }, screen, h("div", { class: "phone-in" }, input, btn), h("p", { style: "text-align:center;margin:10px 0 0" }, reset)),
          h("div", { class: "panel" }, E.field(E.t("u.phone"), phone), h("p", { class: "muted small", text: c.shortcode || "" }), h("p", null, sim))))]);
    screen.textContent = "Dial " + (c.shortcode || "*123#") + " then press the button.";
    input.value = "";
  });
})(window);
