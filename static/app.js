const state = {
  data: null,
  selectedWorkflowId: "workflow-support",
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function loadState() {
  state.data = await api("/api/state");
  if (!state.data.workflows.some((wf) => wf.id === state.selectedWorkflowId)) {
    state.selectedWorkflowId = state.data.workflows[0]?.id;
  }
  render();
}

function render() {
  renderShell();
  renderTemplates();
  renderRuns();
  renderAgents();
  renderWorkflowSelect();
  renderWorkflow();
  renderMessages();
  renderEvents();
}

function renderShell() {
  const { settings, metrics } = state.data;
  $("#provider").textContent = `${settings.llm_provider} runtime`;
  $("#telegram-status").textContent = settings.telegram_enabled ? "Telegram: live polling" : "Telegram: simulator mode";
  $("#metrics").innerHTML = [
    metric("Agents", metrics.agents),
    metric("Workflows", metrics.workflows),
    metric("Messages", metrics.messages),
    metric("Completion", `${Math.round(metrics.completion_rate * 100)}%`),
    metric("Tokens", metrics.total_tokens),
    metric("Cost cents", metrics.total_cost_cents),
  ].join("");
}

function metric(label, value) {
  return `<div class="metric"><strong>${escapeHtml(value)}</strong><span>${label}</span></div>`;
}

function renderTemplates() {
  $("#templates").innerHTML = state.data.templates
    .map(
      (tpl) => `
      <article class="template">
        <h4>${escapeHtml(tpl.name)}</h4>
        <p>${escapeHtml(tpl.description)}</p>
      </article>`
    )
    .join("");
}

function renderRuns() {
  $("#recent-runs").innerHTML =
    state.data.runs
      .slice(0, 8)
      .map(
        (run) => `
        <article class="run-card">
          <h4>${escapeHtml(run.workflow_id)} · ${escapeHtml(run.status)}</h4>
          <p>${escapeHtml(run.input)}</p>
          <div class="pill-row">
            <span class="pill">${run.token_count} tokens</span>
            <span class="pill">${run.cost_cents} cents</span>
          </div>
        </article>`
      )
      .join("") || "<p>No runs yet.</p>";
}

function renderAgents() {
  $("#agent-list").innerHTML = state.data.agents
    .map(
      (agent) => `
      <article class="agent-card" data-agent="${agent.id}">
        <h4>${escapeHtml(agent.name)}</h4>
        <p>${escapeHtml(agent.role)}</p>
        <div class="pill-row">
          ${agent.tools.map((tool) => `<span class="pill">${escapeHtml(tool)}</span>`).join("")}
        </div>
      </article>`
    )
    .join("");
  $$("#agent-list .agent-card").forEach((card) => {
    card.addEventListener("click", () => fillAgentForm(card.dataset.agent));
  });
}

function renderWorkflowSelect() {
  const select = $("#workflow-select");
  select.innerHTML = state.data.workflows
    .map((wf) => `<option value="${wf.id}" ${wf.id === state.selectedWorkflowId ? "selected" : ""}>${escapeHtml(wf.name)}</option>`)
    .join("");
}

function renderWorkflow() {
  const wf = selectedWorkflow();
  if (!wf) return;
  const agentsById = Object.fromEntries(state.data.agents.map((agent) => [agent.id, agent]));
  const svgEdges = wf.edges
    .map((edge) => {
      const from = wf.nodes.find((node) => node.id === edge.from);
      const to = wf.nodes.find((node) => node.id === edge.to);
      if (!from || !to) return "";
      const x1 = from.x + 210;
      const y1 = from.y + 46;
      const x2 = to.x;
      const y2 = to.y + 46;
      const midX = (x1 + x2) / 2;
      return `
        <path d="M ${x1} ${y1} C ${midX} ${y1}, ${midX} ${y2}, ${x2} ${y2}" stroke="#245bdb" stroke-width="2" fill="none" marker-end="url(#arrow)" />
        <text x="${midX - 38}" y="${Math.min(y1, y2) - 8}" fill="#647184" font-size="12">${escapeHtml(edge.label || edge.condition)}</text>`;
    })
    .join("");
  const nodes = wf.nodes
    .map((node) => {
      const agent = agentsById[node.agent_id] || { name: node.agent_id, role: "missing" };
      return `
        <div class="node" style="left:${node.x}px; top:${node.y}px">
          <strong>${escapeHtml(agent.name)}</strong>
          <span>${escapeHtml(agent.role)}</span>
          <div class="pill-row"><span class="pill">${escapeHtml(node.id)}</span></div>
        </div>`;
    })
    .join("");
  $("#workflow-canvas").innerHTML = `
    <svg class="workflow-svg" viewBox="0 0 820 360">
      <defs>
        <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth">
          <path d="M0,0 L0,6 L9,3 z" fill="#245bdb"></path>
        </marker>
      </defs>
      ${svgEdges}
    </svg>
    ${nodes}`;
}

function renderMessages() {
  const html =
    state.data.messages
      .slice(0, 30)
      .map(
        (msg) => `
        <article class="message">
          <strong>${escapeHtml(msg.sender)} -> ${escapeHtml(msg.recipient)}</strong>
          <p>${escapeHtml(msg.content)}</p>
          <div class="pill-row"><span class="pill">${escapeHtml(msg.channel)}</span><span class="pill">${escapeHtml(msg.created_at)}</span></div>
        </article>`
      )
      .join("") || "<p>No messages yet.</p>";
  $("#message-list").innerHTML = html;
  $("#trace-list").innerHTML = html;
}

function renderEvents() {
  $("#event-list").innerHTML =
    state.data.events
      .slice(0, 60)
      .map(
        (event) => `
        <article class="event">
          <strong>${escapeHtml(event.type)}</strong>
          <p>${escapeHtml(event.message)}</p>
          <div class="pill-row"><span class="pill">${escapeHtml(event.created_at)}</span></div>
        </article>`
      )
      .join("") || "<p>No events yet.</p>";
}

function fillAgentForm(agentId) {
  const agent = state.data.agents.find((item) => item.id === agentId);
  if (!agent) return;
  const form = $("#agent-form");
  const fields = form.elements;
  fields.id.value = agent.id;
  fields.name.value = agent.name;
  fields.role.value = agent.role;
  fields.model.value = agent.model;
  fields.tools.value = agent.tools.join(", ");
  fields.channels.value = agent.channels.join(", ");
  fields.system_prompt.value = agent.system_prompt;
  fields.memory.value = JSON.stringify(agent.memory, null, 2);
  fields.guardrails.value = agent.guardrails.join("\n");
}

function selectedWorkflow() {
  return state.data.workflows.find((wf) => wf.id === state.selectedWorkflowId);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function parseList(value) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function wireEvents() {
  $$(".nav-item").forEach((item) => {
    item.addEventListener("click", () => {
      $$(".nav-item").forEach((nav) => nav.classList.remove("active"));
      $$(".view").forEach((view) => view.classList.remove("active"));
      item.classList.add("active");
      $(`#${item.dataset.view}`).classList.add("active");
      $("#view-title").textContent = item.textContent;
    });
  });

  $("#refresh-btn").addEventListener("click", loadState);
  $("#seed-btn").addEventListener("click", async () => {
    state.data = await api("/api/demo/seed", { method: "POST", body: "{}" });
    render();
  });
  $("#workflow-select").addEventListener("change", (event) => {
    state.selectedWorkflowId = event.target.value;
    renderWorkflow();
  });
  $("#run-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const input = new FormData(event.target).get("input");
    const res = await api(`/api/workflows/${state.selectedWorkflowId}/run`, {
      method: "POST",
      body: JSON.stringify({ input, channel: "web" }),
    });
    $("#run-output").textContent = `Queued ${res.run_id}. Watch Monitor for the trace.`;
    setTimeout(loadState, 900);
  });
  $("#channel-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = new FormData(event.target).get("message");
    await api("/api/channel/local", {
      method: "POST",
      body: JSON.stringify({ workflow_id: "workflow-support", message }),
    });
    setTimeout(loadState, 900);
  });
  $("#agent-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.target;
    const fields = form.elements;
    const payload = {
      id: fields.id.value || undefined,
      name: fields.name.value,
      role: fields.role.value,
      model: fields.model.value,
      tools: parseList(fields.tools.value),
      channels: parseList(fields.channels.value),
      system_prompt: fields.system_prompt.value,
      memory: JSON.parse(fields.memory.value || "{}"),
      schedules: [],
      skills: [],
      interaction_rules: [],
      guardrails: fields.guardrails.value.split("\n").map((item) => item.trim()).filter(Boolean),
    };
    const path = payload.id ? `/api/agents/${payload.id}` : "/api/agents";
    const method = payload.id ? "PUT" : "POST";
    await api(path, { method, body: JSON.stringify(payload) });
    form.reset();
    await loadState();
  });

  const events = new EventSource("/api/events");
  events.onmessage = () => loadState();
  ["run.completed", "agent.completed", "agent.started", "channel.telegram.received"].forEach((type) => {
    events.addEventListener(type, () => loadState());
  });
}

wireEvents();
loadState().catch((err) => {
  document.body.innerHTML = `<pre>${escapeHtml(err.stack || err.message)}</pre>`;
});
