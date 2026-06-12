let dashboard = null;
let password = sessionStorage.getItem("adminPassword") || "";

const statusEl = document.querySelector("#adminStatus");

document.querySelector("#loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  password = document.querySelector("#passwordInput").value;
  sessionStorage.setItem("adminPassword", password);
  await loadAdmin();
});

document.querySelector("#syncButton").addEventListener("click", async () => {
  const result = await adminFetch("/api/admin/sync", { method: "POST" });
  setStatus(result.cache.message);
  await loadAdmin();
});

document.querySelector("#exportButton").addEventListener("click", async () => {
  const backup = await adminFetch("/api/admin/export");
  const blob = new Blob([JSON.stringify(backup, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "fifa-sweepstake-backup.json";
  link.click();
  URL.revokeObjectURL(url);
});

document.querySelector("#importInput").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  const payload = JSON.parse(await file.text());
  await adminFetch("/api/admin/import", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  setStatus("Backup imported.");
  await loadAdmin();
});

async function loadAdmin() {
  const response = await fetch("/api/dashboard");
  dashboard = await response.json();
  try {
    await adminFetch("/api/admin/export");
  } catch {
    setStatus("Wrong password or missing ADMIN_PASSWORD.");
    return;
  }
  document.querySelector("#loginPanel").classList.add("hidden");
  document.querySelector("#adminActions").classList.remove("hidden");
  document.querySelector("#adminContent").classList.remove("hidden");
  renderMatches();
  renderTeams();
  renderAlerts();
  setStatus(dashboard.cache.message);
}

function renderMatches() {
  document.querySelector("#adminMatches").innerHTML = dashboard.matches
    .map((match) => `
      <article class="admin-row">
        <h3>${match.date} - ${match.home_team} vs ${match.away_team}</h3>
        <form data-match-id="${match.id}">
          <input name="home_score" type="number" placeholder="Home" value="${match.home_score ?? ""}" />
          <input name="away_score" type="number" placeholder="Away" value="${match.away_score ?? ""}" />
          <select name="status">
            ${option("scheduled", match.status)}
            ${option("live", match.status)}
            ${option("finished", match.status)}
          </select>
          <input name="winner" placeholder="Winner" value="${match.winner ?? ""}" />
          <input name="home_probability" type="number" min="0" max="1" step="0.01" value="${match.home_probability ?? 0.5}" />
          <input name="away_probability" type="number" min="0" max="1" step="0.01" value="${match.away_probability ?? 0.5}" />
          <button type="submit">Save</button>
        </form>
      </article>
    `)
    .join("");
  document.querySelectorAll("[data-match-id]").forEach((form) => {
    form.addEventListener("submit", saveMatch);
  });
}

function renderTeams() {
  document.querySelector("#adminTeams").innerHTML = dashboard.teams
    .slice()
    .sort((a, b) => a.owner.localeCompare(b.owner) || a.name.localeCompare(b.name))
    .map((team) => `
      <article class="admin-row">
        <h3>${team.name} <span class="muted">${team.owner}</span></h3>
        <form data-team-id="${team.id}">
          <select name="status">
            ${option("active", team.status)}
            ${option("eliminated", team.status)}
          </select>
          <select name="exit_stage">
            ${option("", team.exit_stage, "No exit")}
            ${option("group_stage", team.exit_stage, "Group stage")}
            ${option("round_of_32", team.exit_stage, "Round of 32")}
            ${option("round_of_16", team.exit_stage, "Round of 16")}
            ${option("quarterfinal", team.exit_stage, "Quarterfinal")}
            ${option("semifinal", team.exit_stage, "Semifinal")}
            ${option("runner_up", team.exit_stage, "Runner-up")}
            ${option("winner", team.exit_stage, "Winner")}
          </select>
          <input name="manual_title_probability" type="number" min="0" max="1" step="0.001" placeholder="Title prob." value="${team.manual_title_probability ?? ""}" />
          <button type="submit">Save</button>
        </form>
      </article>
    `)
    .join("");
  document.querySelectorAll("[data-team-id]").forEach((form) => {
    form.addEventListener("submit", saveTeam);
  });
}

function renderAlerts() {
  const alerts = dashboard.alerts.length
    ? dashboard.alerts
    : [{ title: "No WhatsApp summaries yet", whatsapp_text: "Finish a match first, then summaries will appear here." }];
  document.querySelector("#adminAlerts").innerHTML = alerts
    .map((alert) => `
      <article class="alert-card">
        <h3>${alert.title}</h3>
        <textarea readonly>${alert.whatsapp_text}</textarea>
        <button class="secondary" type="button" data-copy="${encodeURIComponent(alert.whatsapp_text)}">Copy</button>
      </article>
    `)
    .join("");
  document.querySelectorAll("[data-copy]").forEach((button) => {
    button.addEventListener("click", async () => {
      await navigator.clipboard.writeText(decodeURIComponent(button.dataset.copy));
      setStatus("Copied WhatsApp text.");
    });
  });
}

async function saveMatch(event) {
  event.preventDefault();
  const form = event.currentTarget;
  await adminFetch(`/api/admin/matches/${form.dataset.matchId}`, {
    method: "POST",
    body: JSON.stringify(formPayload(form)),
  });
  setStatus("Match saved.");
  await loadAdmin();
}

async function saveTeam(event) {
  event.preventDefault();
  const form = event.currentTarget;
  await adminFetch(`/api/admin/teams/${form.dataset.teamId}`, {
    method: "POST",
    body: JSON.stringify(formPayload(form)),
  });
  setStatus("Team saved.");
  await loadAdmin();
}

async function adminFetch(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Password": password,
      ...(options.headers || {}),
    },
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

function formPayload(form) {
  const payload = {};
  new FormData(form).forEach((value, key) => {
    payload[key] = value === "" ? null : value;
  });
  return payload;
}

function option(value, selected, label = value) {
  return `<option value="${value}" ${value === (selected ?? "") ? "selected" : ""}>${label}</option>`;
}

function setStatus(message) {
  statusEl.textContent = message || "";
}

if (password) {
  document.querySelector("#passwordInput").value = password;
  loadAdmin();
}
