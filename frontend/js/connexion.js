import { api } from "./api.js";
import { $, appReady, message } from "./app.js";

appReady.then(() => {
  $("#login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await api("/api/auth/login", {
        method:"POST",
        body:JSON.stringify({ username:$("#username").value.trim(), password:$("#password").value }),
      });
      window.location.href = "/chercheur";
    } catch (error) { message(error.message, true); }
  });
});
