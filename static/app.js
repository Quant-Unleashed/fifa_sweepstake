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
  renderModelStrip();
  renderMatchSpotlight();
  renderPlayers();
  renderRules();
  renderAlerts();
  renderStandings();
  renderKnockoutDraw();
  renderMatches();
  renderTeams();
}

function renderMatchSpotlight() {
  const liveMatches = dashboard.matches
    .filter((match) => match.status === "live" || isCurrentWindow(match))
    .sort((a, b) => matchTime(a) - matchTime(b));
  const lastMatches = dashboard.matches
    .filter((match) => isFinished(match))
    .sort((a, b) => matchTime(b) - matchTime(a))
    .slice(0, 3);
  const upcomingMatches = dashboard.matches
    .filter((match) => !isFinished(match) && match.status !== "live" && !isCurrentWindow(match))
    .sort((a, b) => matchTime(a) - matchTime(b))
    .filter((match) => matchTime(match) >= Date.now())
    .slice(0, 3);
  const fallbackUpcoming = dashboard.matches
    .filter((match) => !isFinished(match) && match.status !== "live" && !isCurrentWindow(match))
    .sort((a, b) => matchTime(a) - matchTime(b))
    .slice(0, 3);
  const nextMatches = upcomingMatches.length ? upcomingMatches : fallbackUpcoming;

  document.querySelector("#matchSpotlight").innerHTML = `
    ${matchPanel("Live score", liveMatches.slice(0, 3), "No live match right now.")}
    ${matchPanel("Last 3 matches", lastMatches, "No completed scores loaded yet.")}
    ${matchPanel("Next 3 matches", nextMatches, "No upcoming fixtures loaded.")}
  `;
}

function matchPanel(title, matches, emptyText) {
  return `
    <article class="match-panel">
      <h2>${title}</h2>
      <div class="match-panel-list">
        ${matches.length ? matches.map(matchCard).join("") : `<p class="empty-state">${emptyText}</p>`}
      </div>
    </article>
  `;
}

function matchCard(match) {
  return `
    <div class="mini-match ${match.status === "live" ? "is-live" : ""}">
      <div>
        <span>${match.display_date || match.date || ""}</span>
        <strong>${teamLabel(match.home_team)} <small>vs</small> ${teamLabel(match.away_team)}</strong>
      </div>
      <em>${score(match)}</em>
    </div>
  `;
}

function renderSummary() {
  const totalInvested = dashboard.players.reduce((sum, player) => sum + player.invested, 0);
  const totalConfirmed = dashboard.players.reduce((sum, player) => sum + player.confirmed_winnings, 0);
  const totalEv = dashboard.players.reduce((sum, player) => sum + player.expected_value, 0);
  const activeTeams = dashboard.teams.filter((team) => team.status === "active").length;
  const items = [
    ["Pot", currency.format(totalInvested)],
    ["Guaranteed", currency.format(totalConfirmed)],
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
        .map((team) => `<span class="chip ${team.status === "eliminated" ? "eliminated" : ""}">${team.flag} ${team.name}</span>`)
        .join("");
      return `
        <article class="player-card">
          <div class="player-title">
            <h3>${player.name}</h3>
            <span>${player.team_count} teams</span>
          </div>
          <div class="money-line">
            ${miniStat("Invested", currency.format(player.invested))}
            ${miniStat("Guaranteed", currency.format(player.confirmed_winnings))}
            ${miniStat("EV", currency.format(player.expected_value))}
          </div>
          <div class="money-line two">
            ${miniStat("Actual net", signedMoney(player.actual_profit))}
            ${miniStat("EV net", signedMoney(player.ev_profit))}
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

function renderModelStrip() {
  const model = dashboard.probability_model || {};
  document.querySelector("#modelStrip").innerHTML = `
    <div>
      <span>Probability model</span>
      <strong>${model.label || "Rank/performance model"}</strong>
      <p>${model.description || "Uses standings, seed strength, and manual title overrides."}</p>
    </div>
  `;
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
    .filter((match) => !query || String(match.home_team).toLowerCase().includes(query) || String(match.away_team).toLowerCase().includes(query))
    .map((match) => `
      <tr class="${match.needs_result ? "needs-result" : ""}">
        <td>${match.display_date || match.date || ""}</td>
        <td>${stageLabel(match.stage)}</td>
        <td><strong>${teamLabel(match.home_team)}</strong><br><span class="muted">vs ${teamLabel(match.away_team)}</span></td>
        <td>${match.location || "TBC"}</td>
        <td>${score(match)}</td>
        <td>${statusBadge(match)}</td>
        <td>${probabilityCell(match.home_probability, teamLabel(match.home_team))}<br>${probabilityCell(match.away_probability, teamLabel(match.away_team))}</td>
      </tr>
    `);
  document.querySelector("#matches").innerHTML = rows.join("") || `<tr><td colspan="7">No matches found.</td></tr>`;
}

function renderTeams() {
  document.querySelector("#teams").innerHTML = dashboard.teams
    .slice()
    .sort((a, b) => a.owner.localeCompare(b.owner) || a.name.localeCompare(b.name))
    .map((team) => `
      <tr>
        <td><strong>${team.flag} ${team.name}</strong></td>
        <td>${team.owner}</td>
        <td>${team.group}</td>
        <td><span class="status ${team.status}">${team.status}</span>${team.exit_stage ? `<br><span class="muted">${stageLabel(team.exit_stage)}</span>` : ""}</td>
        <td>${probabilityCell(team.title_probability, "Title")}<br>${probabilityCell(team.survival_probability, "Survive")}</td>
        <td>${currency.format(team.confirmed_payout)}</td>
        <td>${currency.format(team.possible_payout)}</td>
      </tr>
    `)
    .join("");
}

function renderStandings() {
  const groups = [...new Set(dashboard.standings.map((row) => row.group))].sort();
  document.querySelector("#standingsPanel").innerHTML = `
    <div class="standings-grid">
      ${groups.map((group) => standingsTable(group)).join("")}
    </div>
  `;
}

function standingsTable(group) {
  const rows = dashboard.standings.filter((row) => row.group === group);
  return `
    <article class="standings-card">
      <h3>Group ${group}</h3>
      <table class="compact-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Team</th>
            <th>P</th>
            <th>W</th>
            <th>D</th>
            <th>L</th>
            <th>GF</th>
            <th>GA</th>
            <th>GD</th>
            <th>Pts</th>
            <th>Path</th>
            <th>Surv.</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((row) => `
            <tr>
              <td>${row.position}</td>
              <td><strong>${row.flag} ${row.team}</strong><br><span class="muted">${row.owner}</span></td>
              <td>${row.played}</td>
              <td>${row.won}</td>
              <td>${row.drawn}</td>
              <td>${row.lost}</td>
              <td>${row.gf}</td>
              <td>${row.ga}</td>
              <td>${signedNumber(row.gd)}</td>
              <td><strong>${row.points}</strong></td>
              <td><span class="status">${row.qualification}</span></td>
              <td>${percent.format(teamByName(row.team)?.survival_probability || 0)}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </article>
  `;
}

function renderKnockoutDraw() {
  const rounds = dashboard.knockout_draw || [];
  document.querySelector("#drawPanel").innerHTML = rounds.length
    ? `<div class="draw-grid">${rounds.map(drawRound).join("")}</div>`
    : `<article class="alert-card"><h3>No knockout draw yet</h3><p>Knockout fixtures will appear here once placeholders or live feed data are available.</p></article>`;
}

function drawRound(round) {
  return `
    <article class="draw-round">
      <h3>${round.label}</h3>
      ${round.matches.map((match) => `
        <div class="draw-match ${match.status}">
          <div class="draw-meta">
            <span>${match.display_date || ""}</span>
            ${statusBadge(match)}
          </div>
          ${drawTeam(match, "home")}
          <small>vs</small>
          ${drawTeam(match, "away")}
          <em>${score(match)}</em>
        </div>
      `).join("")}
    </article>
  `;
}

function drawTeam(match, side) {
  const name = match[`${side}_team`];
  const isWinner = match.winner && match.winner === name;
  const isEliminated = isFinished(match) && match.winner && match.winner !== name;
  const status = teamByName(name)?.status;
  const classes = [
    "draw-team",
    isWinner ? "winner" : "",
    isEliminated || status === "eliminated" ? "eliminated" : "",
  ].filter(Boolean).join(" ");
  return `<strong class="${classes}">${teamLabel(name)}</strong>`;
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

function teamLabel(name) {
  const flag = dashboard.team_flags?.[name] || "";
  return `${flag ? `${flag} ` : ""}${name}`;
}

function signedMoney(value) {
  const amount = currency.format(Math.abs(value));
  if (value > 0) return `+${amount}`;
  if (value < 0) return `-${amount}`;
  return currency.format(0);
}

function signedNumber(value) {
  if (value > 0) return `+${value}`;
  return String(value);
}

function teamByName(name) {
  return dashboard.teams.find((team) => team.name === name);
}

function score(match) {
  if (match.home_score === null || match.home_score === undefined || match.away_score === null || match.away_score === undefined) return "-";
  return `${match.home_score} - ${match.away_score}`;
}

function statusBadge(match) {
  if (match.needs_result) {
    return `<span class="status needs-result">Needs result</span>`;
  }
  return `<span class="status ${match.status}">${match.status}</span>`;
}

function isFinished(match) {
  return match.status === "finished" || (match.home_score !== null && match.home_score !== undefined && match.away_score !== null && match.away_score !== undefined);
}

function isCurrentWindow(match) {
  if (isFinished(match)) return false;
  const start = matchTime(match);
  if (start === Number.MAX_SAFE_INTEGER) return false;
  const now = Date.now();
  const fourHours = 4 * 60 * 60 * 1000;
  return start <= now && now - start <= fourHours;
}

function matchTime(match) {
  const value = Date.parse(match.date || "");
  return Number.isNaN(value) ? Number.MAX_SAFE_INTEGER : value;
}

function stageLabel(stage) {
  return String(stage || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

document.querySelector("#ownerFilter").addEventListener("change", renderMatches);
document.querySelector("#stageFilter").addEventListener("change", renderMatches);
document.querySelector("#matchSearch").addEventListener("input", renderMatches);
document.querySelectorAll("[data-tab]").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll("[data-tab]").forEach((tab) => tab.classList.toggle("active", tab === button));
    document.querySelector("#standingsPanel").classList.toggle("hidden", button.dataset.tab !== "standings");
    document.querySelector("#drawPanel").classList.toggle("hidden", button.dataset.tab !== "draw");
  });
});
loadDashboard();
