import { api } from "./api.js";
import { $, appReady, message } from "./app.js";

appReady.then(() => {
  $("#join-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const joined = await api("/api/experiments/join", {
        method:"POST",
        body:JSON.stringify({
          code:$("#experiment-code").value.trim(),
          consentement:$("#consent").checked,
        }),
      });
      sessionStorage.setItem("memoriae_session", joined.session_id);
      window.location.href = "/experience";
    } catch (error) { message(error.message, true); }
  });
});
