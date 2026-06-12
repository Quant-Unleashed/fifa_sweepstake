let dashboard = null;

const currency = new Intl.NumberFormat("en-GB", {
  style: "currency",
  currency: "GBP",
});

const percent = new Intl.NumberFormat("en-GB", {
  style: "percent",
  maximumFractionDigits: 1,
});

async function loadDashboard() {
  const response = await fetch("/api/dashboard");
  dashboard = await response.json();
  populateFilters();
  renderAll();
}

function renderAll() {
  renderSummary();
  renderPlayers();
  renderRules();
  renderAlerts();
  renderMatches();
  renderTeams();
}

function renderSummary() {
  const totalInvested = dashboard.players.reduce((sum, player) => sum + player.invested, 0);
  const totalConfirmed = dashboard.players.reduce((sum, player) => sum + player.confirmed_winnings, 0);
  const totalEv = dashboard.players.reduce((sum, player) => sum + player.expected_value, 0);
  const activeTeams = dashboard.teams.filter((team) => team.status === "active").length;
  const items = [
    ["Pot", currency.format(totalInvested)],
    ["Confirmed paid out", currency.format(totalConfirmed)],
    ["Combined EV", currency.format(totalEv)],
    ["Teams alive", `${activeTeams}/48`],
  ];
  document.querySelector("#summaryBar").innerHTML = items
    .map(([label, value]) => `<div class="metric"><span>${label}</span><strong>${value}</strong></div>`)
    .join("");
}

function renderPlayers() {
  document.querySelector("#players").innerHTML = dashboard.players
    .map((player) => {
      const chips = player.teams
        .map((team) => `<span class="chip ${team.status === "eliminated" ? "eliminated" : ""}">${team.name}</span>`)
        .join("");
      return `
        <article class="player-card">
          <h3>${player.name}</h3>
          <div class="money-line">
            ${miniStat("Invested", currency.format(player.invested))}
            ${miniStat("Confirmed", currency.format(player.confirmed_winnings))}
            ${miniStat("EV", currency.format(player.expected_value))}
          </div>
          <p><strong>${player.active_count}</strong> active, <strong>${player.eliminated_count}</strong> eliminated</p>
          <div class="team-chips">${chips}</div>
        </article>
      `;
    })
    .join("");
}

function miniStat(label, value) {
  return `<div class="mini-stat"><span>${label}</span><strong>${value}</strong></div>`;
}

function renderRules() {
  const labels = {
    group_stage: "Group stage exit",
    round_of_32: "Round of 32 exit",
    round_of_16: "Round of 16 exit",
    quarterfinal: "Quarterfinal exit",
    semifinal: "Semifinal exit",
    runner_up: "Runner-up",
    winner: "Winner",
  };
  document.querySelector("#rules").innerHTML = Object.entries(dashboard.settings.payouts)
    .map(([stage, payout]) => `<div class="rule-row"><span>${labels[stage] || stage}</span><strong>${currency.format(payout)}</strong></div>`)
    .join("");
}

function renderAlerts() {
  const alerts = dashboard.alerts.length
    ? dashboard.alerts.slice(0, 6)
    : [{ title: "No finished-match impacts yet", body: "Once results are entered, this feed will explain what changed." }];
  document.querySelector("#alerts").innerHTML = alerts
    .map((alert) => `<article class="alert-card"><h3>${alert.title}</h3><p>${alert.body}</p></article>`)
    .join("");
}

function renderMatches() {
  const owner = document.querySelector("#ownerFilter").value;
  const stage = document.querySelector("#stageFilter").value;
  const query = document.querySelector("#matchSearch").value.trim().toLowerCase();
  const ownerTeams = new Set(
    dashboard.teams.filter((team) => !owner || team.owner === owner).map((team) => team.name)
  );
  const rows = dashboard.matches
    .filter((match) => !stage || match.stage === stage)
    .filter((match) => !owner || ownerTeams.has(match.home_team) || ownerTeams.has(match.away_team))
    .filter((match) => !query || match.home_team.toLowerCase().includes(query) || match.away_team.toLowerCase().includes(query))
    .map((match) => `
      <tr>
        <td>${match.date || ""}</td>
        <td>${stageLabel(match.stage)}</td>
        <td><strong>${match.home_team}</strong><br><span class="muted">vs ${match.away_team}</span></td>
        <td>${score(match)}</td>
        <td><span class="status ${match.status}">${match.status}</span></td>
        <td>${probabilityCell(match.home_probability, match.home_team)}<br>${probabilityCell(match.away_probability, match.away_team)}</td>
      </tr>
    `);
  document.querySelector("#matches").innerHTML = rows.join("") || `<tr><td colspan="6">No matches found.</td></tr>`;
}

function renderTeams() {
  document.querySelector("#teams").innerHTML = dashboard.teams
    .slice()
    .sort((a, b) => a.owner.localeCompare(b.owner) || a.name.localeCompare(b.name))
    .map((team) => `
      <tr>
        <td><strong>${team.name}</strong></td>
        <td>${team.owner}</td>
        <td>${team.group}</td>
        <td><span class="status ${team.status}">${team.status}</span>${team.exit_stage ? `<br><span class="muted">${stageLabel(team.exit_stage)}</span>` : ""}</td>
        <td>${probabilityCell(team.title_probability, "")}</td>
        <td>${currency.format(team.confirmed_payout)}</td>
        <td>${currency.format(team.possible_payout)}</td>
      </tr>
    `)
    .join("");
}

function populateFilters() {
  const owners = [...new Set(dashboard.players.map((player) => player.name))];
  document.querySelector("#ownerFilter").innerHTML = `<option value="">All owners</option>` + owners.map((owner) => `<option>${owner}</option>`).join("");
  const stages = [...new Set(dashboard.matches.map((match) => match.stage))];
  document.querySelector("#stageFilter").innerHTML = `<option value="">All stages</option>` + stages.map((stage) => `<option value="${stage}">${stageLabel(stage)}</option>`).join("");
}

function probabilityCell(value, label) {
  const safeValue = Number(value || 0);
  return `<span class="muted">${label ? `${label} ` : ""}${percent.format(safeValue)}</span><div class="prob-bar"><span style="width:${safeValue * 100}%"></span></div>`;
}

function score(match) {
  if (match.home_score === null || match.away_score === null) return "-";
  return `${match.home_score} - ${match.away_score}`;
}

function stageLabel(stage) {
  return String(stage || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

document.querySelector("#ownerFilter").addEventListener("change", renderMatches);
document.querySelector("#stageFilter").addEventListener("change", renderMatches);
document.querySelector("#matchSearch").addEventListener("input", renderMatches);
loadDashboard();
