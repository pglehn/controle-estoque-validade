document.addEventListener("DOMContentLoaded", () => {
  const select = document.getElementById("id_lote");
  const output = document.getElementById("saldo-lote");
  if (!select || !output) return;
  let requestId = 0;
  async function mostrarSaldo() {
    const atual = ++requestId;
    if (!select.value) { output.textContent = ""; return; }
    output.textContent = "Consultando saldo…";
    try {
      const url = output.dataset.api.replace("/0/", "/" + encodeURIComponent(select.value) + "/");
      const response = await fetch(url, {headers: {"Accept": "application/json"}});
      if (!response.ok) throw new Error("Consulta indisponível");
      const dados = await response.json();
      if (atual !== requestId) return;
      output.textContent = "Saldo atual: " + dados.saldo + " " + dados.unidade + " · Validade: " + dados.validade;
    } catch (_) {
      if (atual === requestId) output.textContent = "Não foi possível consultar o saldo agora; você ainda pode enviar o formulário.";
    }
  }
  select.addEventListener("change", mostrarSaldo);
  mostrarSaldo();
});
