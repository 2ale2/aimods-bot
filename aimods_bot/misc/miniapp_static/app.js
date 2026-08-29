/*
 * Client della Mini App.
 *
 * Manda initData al backend, che ne verifica la firma HMAC. Il client NON
 * decide niente: non legge il query_id, non si fida di quello che vede.
 * Tutto quello che conta lo stabilisce il server dalla firma.
 */

(function () {
  "use strict";

  var tg = window.Telegram && window.Telegram.WebApp;

  var views = {
    loading: document.getElementById("view-loading"),
    rules:   document.getElementById("view-rules"),
    done:    document.getElementById("view-done"),
    error:   document.getElementById("view-error")
  };

  var btnAcceptFallback = document.getElementById("btn-accept-fallback");
  var btnDecline        = document.getElementById("btn-decline");
  var btnRetry          = document.getElementById("btn-retry");
  var rulesBody         = document.getElementById("rules-body");

  var busy = false;

  /* MainButton nativo: presente su tutti i client moderni. Se manca si usa
     il bottone HTML di fallback dentro la pagina. */
  var mainBtn = tg && tg.MainButton && tg.MainButton.setText ? tg.MainButton : null;

  function show(name) {
    Object.keys(views).forEach(function (k) {
      views[k].hidden = (k !== name);
    });
    // Il MainButton vive fuori dalla pagina: va nascosto a mano quando si
    // cambia schermata, altrimenti resta li' sopra l'esito.
    if (mainBtn && name !== "rules") {
      try { mainBtn.hide(); } catch (e) { /* ignora */ }
    }
  }

  function showError(msg) {
    document.getElementById("error-text").textContent = msg;
    show("error");
  }

  function showDone(title, text, ok) {
    var icon = document.getElementById("done-icon");
    icon.className = "icon" + (ok ? " icon-ok" : "");
    icon.textContent = ok ? "\u2713" : "\u2022";
    document.getElementById("done-title").textContent = title;
    document.getElementById("done-text").textContent = text;
    show("done");
  }

  function haptic(type) {
    try { tg.HapticFeedback.notificationOccurred(type); } catch (e) { /* non ovunque */ }
  }

  function closeSoon(ms) {
    setTimeout(function () {
      try { tg.close(); } catch (e) { /* ignora */ }
    }, ms);
  }

  /* ---------------------------------------------------------------- avvio */

  if (!tg || !tg.initData) {
    showError("Apri questa pagina da Telegram.");
    return;
  }

  tg.ready();
  tg.expand();

  /* Header dello stesso colore dello sfondo: la finestra sembra una schermata
     sola invece di una pagina web dentro una cornice. */
  try {
    tg.setBackgroundColor("secondary_bg_color");
    tg.setHeaderColor("secondary_bg_color");
  } catch (e) { /* client vecchi */ }

  /*
   * Il pop-up di conferma alla chiusura serve a distinguere "ho deciso" da
   * "ho fatto swipe". Non e' una garanzia — il backend ha comunque bisogno
   * dello sweeper — ma riduce i casi.
   */
  try { tg.enableClosingConfirmation(); } catch (e) { /* client vecchi */ }

  /* ------------------------------------------------ rendering regolamento */

  /*
   * Il testo arriva dal bot in "HTML Telegram" (b, i, u, s, code, pre, a).
   * NON usare innerHTML sul testo grezzo: chi controlla
   * user_joined_message_text eseguirebbe script qui dentro, con l'initData a
   * portata di mano. Qui si escapa TUTTO e poi si riabilitano solo i tag noti.
   */
  function renderTelegramHtml(raw) {
    var out = raw
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

    // Riabilita i tag inline semplici, dopo l'escape.
    out = out.replace(
      /&lt;(\/?)(b|strong|i|em|u|s|strike|del|code|pre)&gt;/gi,
      "<$1$2>"
    );

    // <a href="..."> solo con URL http/https.
    out = out.replace(
      /&lt;a href=(?:&quot;|"|')(https?:\/\/[^"'&<>\s]+)(?:&quot;|"|')&gt;/gi,
      '<a href="$1">'
    );
    out = out.replace(/&lt;\/a&gt;/gi, "</a>");

    // Righe vuote -> paragrafi, a capo singoli -> <br>. Il testo del bot usa
    // gli a capo per la struttura, che senza questo collasserebbe.
    var blocks = out.split(/\n\s*\n/);
    return blocks
      .map(function (b) {
        return "<p>" + b.replace(/\n/g, "<br>") + "</p>";
      })
      .join("");
  }

  function renderRules(text) {
    rulesBody.innerHTML = renderTelegramHtml(text || "");
  }

  /* I link vanno aperti FUORI dalla Mini App: dentro l'iframe di Telegram Web
     molti siti rifiutano di caricarsi, e su mobile l'utente perderebbe la
     schermata del regolamento. */
  rulesBody.addEventListener("click", function (e) {
    var a = e.target.closest ? e.target.closest("a") : null;
    if (!a || !a.href) return;
    e.preventDefault();
    try { tg.openLink(a.href); } catch (err) { window.open(a.href, "_blank"); }
  });

  /* --------------------------------------------------------- caricamento */

  function post(path, payload) {
    return fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).then(function (r) {
      return r.json().then(function (data) {
        return { status: r.status, data: data };
      });
    });
  }

  function loadRules() {
    show("loading");
    post("api/rules", { init_data: tg.initData })
      .then(function (res) {
        if (res.status === 409 && res.data.reason === "no_join_request") {
          showDone(
            "Nessuna richiesta in sospeso",
            "Questa pagina serve quando chiedi di entrare nel gruppo.",
            false
          );
          return;
        }
        if (!res.data.ok) {
          showError(res.data.error || "Errore imprevisto.");
          return;
        }
        renderRules(res.data.text);
        show("rules");
        setupAcceptButton();
      })
      .catch(function () {
        showError("Non riesco a contattare il bot. Controlla la connessione.");
      });
  }

  function setupAcceptButton() {
    if (mainBtn) {
      mainBtn.setText("Accetto il regolamento");
      mainBtn.onClick(function () { send("accept"); });
      mainBtn.show();
      try { mainBtn.enable(); } catch (e) { /* ignora */ }
    } else {
      btnAcceptFallback.hidden = false;
    }
  }

  function lockUi(locked) {
    busy = locked;
    btnDecline.disabled = locked;
    btnAcceptFallback.disabled = locked;
    if (!mainBtn) return;
    try {
      if (locked) { mainBtn.showProgress(); mainBtn.disable(); }
      else { mainBtn.hideProgress(); mainBtn.enable(); }
    } catch (e) { /* ignora */ }
  }

  /* ------------------------------------------------------------- risposta */

  function send(action) {
    if (busy) return;
    lockUi(true);

    post("api/join", { init_data: tg.initData, action: action })
      .then(function (res) {
        if (res.status === 409 && res.data.reason === "no_join_request") {
          showDone("Nessuna richiesta in sospeso", "Non c'e' niente da confermare.", false);
          return;
        }

        if (res.status === 409 && res.data.reason === "already_answered") {
          // Richiesta gia' gestita altrove. NON sappiamo con quale esito,
          // quindi non lo dichiariamo: succede aprendo la Mini App due volte
          // e rispondendo dalla prima.
          try { tg.disableClosingConfirmation(); } catch (e) { /* ignora */ }
          showDone(
            "Richiesta gia' gestita",
            "Questa richiesta e' gia' stata chiusa. Controlla se sei nel gruppo.",
            false
          );
          closeSoon(2500);
          return;
        }

        if (!res.data.ok) {
          lockUi(false);
          haptic("error");
          showError(res.data.error || "Errore imprevisto.");
          return;
        }

        haptic("success");
        try { tg.disableClosingConfirmation(); } catch (e) { /* ignora */ }

        if (action === "accept") {
          showDone("Fatto", "Richiesta confermata: ora puoi entrare nel gruppo.", true);
        } else {
          showDone("Ok", "La richiesta e' stata annullata.", false);
        }
        closeSoon(1800);
      })
      .catch(function () {
        lockUi(false);
        haptic("error");
        showError("Non riesco a contattare il bot. Riprova.");
      });
  }

  btnAcceptFallback.addEventListener("click", function () { send("accept"); });

  btnDecline.addEventListener("click", function () {
    // Un "non accetto" per sbaglio e' difficile da annullare: meglio chiedere.
    if (tg.showConfirm) {
      tg.showConfirm("Vuoi annullare la richiesta di ingresso?", function (ok) {
        if (ok) send("decline");
      });
    } else {
      send("decline");
    }
  });

  btnRetry.addEventListener("click", loadRules);

  loadRules();
})();
