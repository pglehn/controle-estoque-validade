document.addEventListener("DOMContentLoaded", () => {
  const button = document.getElementById("alternar-contraste");
  if (!button) return;
  const key = "estoque_alto_contraste";
  let enabled = false;
  try {
    enabled = window.localStorage.getItem(key) === "1";
  } catch (_) {
    // O controle continua funcionando durante a página se o armazenamento estiver indisponível.
  }

  function apply() {
    document.documentElement.classList.toggle("alto-contraste", enabled);
    button.setAttribute("aria-pressed", String(enabled));
    button.textContent = enabled ? "Alto contraste: ativado" : "Alto contraste: desativado";
  }

  button.addEventListener("click", () => {
    enabled = !enabled;
    try { window.localStorage.setItem(key, enabled ? "1" : "0"); } catch (_) {}
    apply();
  });
  apply();
});
