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

  var btnAccept  = document.getElementById("btn-accept");
  var btnDecline = document.getElementById("btn-decline");
  var btnRetry   = document.getElementById("btn-retry");

  var busy = false;

  function show(name) {
    Object.keys(views).forEach(function (k) {
      views[k].hidden = (k !== name);
    });
  }

  function showError(msg) {
    document.getElementById("error-text").textContent = msg;
    show("error");
  }

  function showDone(title, text) {
    document.getElementById("done-title").textContent = title;
    document.getElementById("done-text").textContent = text;
    show("done");
  }

  function haptic(type) {
    try { tg.HapticFeedback.notificationOccurred(type); } catch (e) { /* non ovunque */ }
  }

  /* ---------------------------------------------------------------- avvio */

  if (!tg || !tg.initData) {
    // Pagina aperta in un browser normale, non dentro Telegram.
    showError("Apri questa pagina da Telegram.");
    return;
  }

  tg.ready();
  tg.expand();

  /*
   * Il pop-up di conferma alla chiusura serve a distinguere "ho deciso" da
   * "ho fatto swipe". Non è una garanzia — il backend ha comunque bisogno
   * dello sweeper — ma riduce i casi.
   */
  try { tg.enableClosingConfirmation(); } catch (e) { /* client vecchi */ }

  /* --------------------------------------------------------- regolamento */

  function loadRules() {
    show("loading");
    fetch("api/rules", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ init_data: tg.initData })
    })
      .then(function (r) {
        return r.json().then(function (data) {
          return { status: r.status, data: data };
        });
      })
      .then(function (res) {
        if (res.status === 409 && res.data.reason === "no_join_request") {
          // Aperta dal profilo del bot, senza join request in corso.
          showDone(
            "Nessuna richiesta in sospeso",
            "Questa pagina serve quando chiedi di entrare nel gruppo."
          );
          return;
        }
        if (!res.data.ok) {
          showError(res.data.error || "Errore imprevisto.");
          return;
        }
        renderRules(res.data.title, res.data.text);
        show("rules");
      })
      .catch(function () {
        showError("Non riesco a contattare il bot. Controlla la connessione.");
      });
  }

  /*
   * Il testo del regolamento arriva dal bot: va inserito come TESTO, mai come
   * HTML, altrimenti chi può modificare pydb.user_joined_message_text esegue
   * script nella Mini App.
   */
  function renderRules(title, text) {
    if (title) document.getElementById("rules-title").textContent = title;
    document.getElementById("rules-body").textContent = text || "";
  }

  /* ------------------------------------------------------------- risposta */

  function send(action) {
    if (busy) return;
    busy = true;
    btnAccept.disabled = true;
    btnDecline.disabled = true;

    if (tg.MainButton && tg.MainButton.showProgress) {
      try { tg.MainButton.showProgress(); } catch (e) { /* ignora */ }
    }

    fetch("api/join", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ init_data: tg.initData, action: action })
    })
      .then(function (r) {
        return r.json().then(function (data) {
          return { status: r.status, data: data };
        });
      })
      .then(function (res) {
        if (res.status === 409 && res.data.reason === "no_join_request") {
          showDone("Nessuna richiesta in sospeso", "Non c'è niente da confermare.");
          return;
        }
        if (!res.data.ok) {
          // Riabilita: l'errore può essere temporaneo.
          busy = false;
          btnAccept.disabled = false;
          btnDecline.disabled = false;
          haptic("error");
          showError(res.data.error || "Errore imprevisto.");
          return;
        }

        haptic("success");

        // La conferma di chiusura non serve più: la decisione è presa.
        try { tg.disableClosingConfirmation(); } catch (e) { /* ignora */ }

        if (action === "accept") {
          showDone("Fatto", "Sei stato aggiunto al gruppo.");
        } else {
          showDone("Ok", "La richiesta è stata annullata.");
        }

        // Chiusura non immediata: l'utente deve vedere l'esito.
        setTimeout(function () {
          try { tg.close(); } catch (e) { /* ignora */ }
        }, 1500);
      })
      .catch(function () {
        busy = false;
        btnAccept.disabled = false;
        btnDecline.disabled = false;
        haptic("error");
        showError("Non riesco a contattare il bot. Riprova.");
      });
  }

  btnAccept.addEventListener("click", function () { send("accept"); });

  btnDecline.addEventListener("click", function () {
    // Un "non accetto" per sbaglio è irreversibile: meglio una conferma.
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
