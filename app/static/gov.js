/* Government dashboard: aggregated crops + livestock numbers and the rules currently in force. Read-only. */
(function (w) {
  "use strict";
  var E = w.E, h = E.h;
  E.i18n({
    en: { "t.ov": "Overview", "t.rules": "Document rules", "t.acc": "Account", "g.rules_h": "Government documents the platform checks", "g.rules_p": "These rules are managed by the platform owner and can be changed without new software." },
    rw: { "t.ov": "Incamake", "t.rules": "Amategeko y'ibyangombwa", "t.acc": "Konti", "g.rules_h": "Ibyangombwa bya Leta sisitemu igenzura", "g.rules_p": "Aya mategeko acungwa na nyiri sisitemu kandi ashobora guhinduka nta gukenera porogaramu nshya." },
    fr: { "t.ov": "Aperçu", "t.rules": "Règles de documents", "t.acc": "Compte", "g.rules_h": "Documents de l'État contrôlés par la plateforme", "g.rules_p": "Ces règles sont gérées par le propriétaire de la plateforme et modifiables sans nouveau logiciel." }
  });
  E.guard(["government"]).then(function (u) {
    E.shell(E.$("root"), { user: u, tabs: [{ id: "ov", label: "t.ov" }, { id: "rules", label: "t.rules" }, { id: "acc", label: "t.acc" }], onTab: function (id, main) {
      if (id === "ov") { E.clear(main); E.overview(main); }
      else if (id === "rules") {
        E.fill(main, E.loading());
        E.api("/admin/permit-types").then(function (r) { E.fill(main, E.section(E.t("g.rules_h"), null, [h("p", { class: "muted", text: E.t("g.rules_p") }), E.rulesTable(r)])); })
          .catch(function (e) { E.fill(main, h("div", { class: "notice bad", text: E.err(e) })); });
      } else E.fill(main, E.accountPanel(u, true));
    } });
  }).catch(function () {});
})(window);
