const state = {
  data: null,
  loading: true,
  view: "recent",
  previousView: "recent",
  query: "",
  selectedBubbleId: null,
  selectedSessionId: null,
  selectedProjectKey: null,
  matterSaving: false,
};

const elements = {
  overview: document.getElementById("overview"),
  generatedAt: document.getElementById("generated-at"),
  mainContent: document.getElementById("main-content"),
  detail: document.getElementById("detail"),
  viewEyebrow: document.getElementById("view-eyebrow"),
  viewTitle: document.getElementById("view-title"),
  searchInput: document.getElementById("search-input"),
  refreshButton: document.getElementById("refresh-button"),
  navLinks: Array.from(document.querySelectorAll(".nav-link")),
  emptyTemplate: document.getElementById("empty-state-template"),
};

const formatDateTime = (value) => {
  if (!value) return "Unknown";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
};

const formatShort = (value) => {
  if (!value) return "Unknown";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
};

const dayLabel = (value) => {
  if (!value) return "Unknown";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown";
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const target = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const diff = Math.round((today - target) / 86400000);
  if (diff === 0) return "Today";
  if (diff === 1) return "Yesterday";
  return new Intl.DateTimeFormat(undefined, {
    month: "long",
    day: "numeric",
    year: "numeric",
  }).format(date);
};

const escapeHtml = (value) =>
  String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");

const bubbleById = (bubbleId) =>
  state.data?.bubbles.find((bubble) => bubble.id === bubbleId) ?? null;

const sessionById = (sessionId) =>
  state.data?.sessions.find((session) => session.session_id === sessionId) ?? null;

const projectByKey = (projectKey) =>
  state.data?.projects.find((project) => project.project_key === projectKey) ?? null;

const sessionForBubble = (bubble) => {
  if (!bubble?.session_id) return null;
  return sessionById(bubble.session_id);
};

const setSelectedBubble = (bubbleId) => {
  state.selectedBubbleId = bubbleId;
  renderDetail();
  renderMain();
};

const setView = (nextView, options = {}) => {
  if (state.view !== "search") {
    state.previousView = state.view;
  }
  state.view = nextView;
  if (options.sessionId !== undefined) state.selectedSessionId = options.sessionId;
  if (options.projectKey !== undefined) state.selectedProjectKey = options.projectKey;
  if (options.bubbleId !== undefined) state.selectedBubbleId = options.bubbleId;
  syncNav();
  render();
};

const syncNav = () => {
  const active = state.view === "project" ? "projects" : state.view === "session" ? "sessions" : state.view;
  elements.navLinks.forEach((link) => {
    link.classList.toggle("is-active", link.dataset.view === active);
  });
};

const buildEmptyState = (title, copy) => {
  const fragment = elements.emptyTemplate.content.cloneNode(true);
  fragment.querySelector("h3").textContent = title;
  fragment.querySelector("p").textContent = copy;
  return fragment;
};

const renderOverview = () => {
  const overview = state.data?.overview;
  if (!overview) return;
  elements.overview.innerHTML = `
    <div class="overview-card"><strong>${overview.bubble_count}</strong><span class="muted">Bubbles</span></div>
    <div class="overview-card"><strong>${overview.session_count}</strong><span class="muted">Sessions</span></div>
    <div class="overview-card"><strong>${overview.project_count}</strong><span class="muted">Projects</span></div>
    <button class="overview-card overview-card-button" data-view="mattered">
      <strong>${overview.mattered_count ?? 0}</strong>
      <span class="muted">Mattered</span>
    </button>
  `;
  elements.generatedAt.textContent = `Updated ${formatShort(state.data.generated_at)}`;
};

const bubbleChips = (bubble) => {
  const chips = [];
  if (bubble.mattered) chips.push(`<span class="chip chip-accent">Mattered</span>`);
  if (bubble.project_name) chips.push(`<span class="chip">${escapeHtml(bubble.project_name)}</span>`);
  if (bubble.git_branch) chips.push(`<span class="chip">${escapeHtml(bubble.git_branch)}</span>`);
  if (bubble.trigger_type && bubble.trigger_type !== "unknown") {
    chips.push(`<span class="chip">${escapeHtml(bubble.trigger_type)}</span>`);
  }
  return chips.length ? `<div class="chip-row">${chips.join("")}</div>` : "";
};

const bubbleCard = (bubble, { compact = false } = {}) => `
  <article class="card card-bubble ${bubble.id === state.selectedBubbleId ? "is-selected" : ""}" data-bubble-id="${bubble.id}">
    <div class="card-head">
      <div class="card-meta">${escapeHtml(bubble.companion)}</div>
      <div class="card-time">${escapeHtml(formatShort(bubble.timestamp))}</div>
    </div>
    <p class="card-text">${escapeHtml(compact ? bubble.preview : bubble.text)}</p>
    ${bubbleChips(bubble)}
  </article>
`;

const renderBubbleGroups = (bubbles) => {
  if (!bubbles.length) {
    elements.mainContent.replaceChildren(
      buildEmptyState("Nothing here yet", "Capture a few bubbles and they will appear here.")
    );
    return;
  }
  const grouped = new Map();
  bubbles.forEach((bubble) => {
    const key = dayLabel(bubble.timestamp);
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key).push(bubble);
  });

  elements.mainContent.innerHTML = "";
  const stack = document.createElement("div");
  stack.className = "section-stack";
  grouped.forEach((entries, label) => {
    const section = document.createElement("section");
    section.innerHTML = `
      <div class="section-header">
        <h3 class="section-title">${escapeHtml(label)}</h3>
        <span class="muted">${entries.length}</span>
      </div>
      <div class="card-list">${entries.map((bubble) => bubbleCard(bubble)).join("")}</div>
    `;
    stack.append(section);
  });
  elements.mainContent.append(stack);
};

const renderProjects = () => {
  const projects = state.data?.projects ?? [];
  elements.mainContent.innerHTML = "";
  if (!projects.length) {
    elements.mainContent.replaceChildren(
      buildEmptyState("No projects yet", "Open Glimmer in a few session-aware runs and project cards will show up here.")
    );
    return;
  }

  const wrap = document.createElement("div");
  wrap.className = "card-grid";
  wrap.innerHTML = projects
    .map(
      (project) => `
        <article class="card card-project ${project.project_key === state.selectedProjectKey ? "is-selected" : ""}" data-project-key="${escapeHtml(project.project_key)}">
          <div class="card-head">
            <div class="card-meta">Project</div>
            <div class="card-time">${escapeHtml(formatShort(project.last_seen_at))}</div>
          </div>
          <h3 class="card-title">${escapeHtml(project.project_label)}</h3>
          <div class="chip-row">
            <span class="chip">${project.bubble_count} bubbles</span>
            <span class="chip">${project.session_count} sessions</span>
            ${project.mattered_count ? `<span class="chip chip-accent">${project.mattered_count} mattered</span>` : ""}
          </div>
          <p class="card-text">${escapeHtml(project.latest_bubble_preview || "No bubble preview yet.")}</p>
          <div class="card-meta">${escapeHtml((project.branches || []).join(" · ") || "No branch context")}</div>
        </article>
      `
    )
    .join("");
  elements.mainContent.append(wrap);
};

const renderProjectDetail = () => {
  const project = projectByKey(state.selectedProjectKey);
  if (!project) {
    setView("projects");
    return;
  }
  const sessions = (state.data?.sessions ?? []).filter(
    (session) => session.project_label === project.project_key
  );
  elements.viewEyebrow.textContent = "Project archive";
  elements.viewTitle.textContent = project.project_label;
  elements.mainContent.innerHTML = `
    <section class="session-header">
      <span class="back-link" data-back-to="projects">← Back to projects</span>
      <h3>${escapeHtml(project.project_label)}</h3>
      <div class="chip-row">
        <span class="chip">${project.bubble_count} bubbles</span>
        <span class="chip">${project.session_count} sessions</span>
        ${project.mattered_count ? `<span class="chip chip-accent">${project.mattered_count} mattered</span>` : ""}
        <span class="chip">Last seen ${escapeHtml(formatShort(project.last_seen_at))}</span>
      </div>
      <p class="card-text">${escapeHtml(project.latest_bubble_preview || "No preview yet.")}</p>
    </section>
    <section class="section-stack">
      ${sessions
        .map(
          (session) => `
            <article class="card card-session ${session.session_id === state.selectedSessionId ? "is-selected" : ""}" data-session-id="${session.session_id}">
              <div class="card-head">
                <div class="card-meta">Session</div>
                <div class="card-time">${escapeHtml(formatShort(session.started_at))}</div>
              </div>
              <h3 class="card-title">${escapeHtml(session.project_label)}</h3>
              <div class="chip-row">
                <span class="chip">${session.bubble_count} bubbles</span>
                ${session.mattered_count ? `<span class="chip chip-accent">${session.mattered_count} mattered</span>` : ""}
                <span class="chip">${escapeHtml(session.git_branch || "No branch")}</span>
              </div>
              <p class="card-text">${escapeHtml(session.latest_bubble_preview || "No preview yet.")}</p>
              <div class="card-meta">${escapeHtml(session.cwd || "No cwd recorded")}</div>
            </article>
          `
        )
        .join("")}
    </section>
  `;
};

const renderSessions = () => {
  const sessions = state.data?.sessions ?? [];
  elements.mainContent.innerHTML = "";
  if (!sessions.length) {
    elements.mainContent.replaceChildren(
      buildEmptyState("No sessions yet", "Run Glimmer in Claude Code and the session timeline will appear here.")
    );
    return;
  }
  const stack = document.createElement("div");
  stack.className = "card-list";
  stack.innerHTML = sessions
    .map(
      (session) => `
        <article class="card card-session ${session.session_id === state.selectedSessionId ? "is-selected" : ""}" data-session-id="${session.session_id}">
          <div class="card-head">
            <div class="card-meta">${escapeHtml(session.project_label)}</div>
            <div class="card-time">${escapeHtml(formatShort(session.started_at))}</div>
          </div>
          <h3 class="card-title">${escapeHtml(session.project_label)}</h3>
          <div class="chip-row">
            <span class="chip">${session.bubble_count} bubbles</span>
            ${session.mattered_count ? `<span class="chip chip-accent">${session.mattered_count} mattered</span>` : ""}
            <span class="chip">${escapeHtml(session.git_branch || "No branch")}</span>
            <span class="chip">${session.ended_at ? "Ended" : "Open"}</span>
          </div>
          <p class="card-text">${escapeHtml(session.latest_bubble_preview || "No bubble preview yet.")}</p>
          <div class="card-meta">${escapeHtml(session.cwd || "No cwd recorded")}</div>
        </article>
      `
    )
    .join("");
  elements.mainContent.append(stack);
};

const renderSessionDetail = () => {
  const session = sessionById(state.selectedSessionId);
  if (!session) {
    setView("sessions");
    return;
  }
  elements.viewEyebrow.textContent = "Session timeline";
  elements.viewTitle.textContent = session.project_label;
  elements.mainContent.innerHTML = `
    <section class="session-header">
      <span class="back-link" data-back-to="sessions">← Back to sessions</span>
      <h3>${escapeHtml(session.project_label)}</h3>
      <div class="chip-row">
        <span class="chip">${session.bubble_count} bubbles</span>
        <span class="chip">${escapeHtml(session.git_branch || "No branch")}</span>
        <span class="chip">${session.is_repo_root ? "Repo root" : "Nested or non-repo"}</span>
      </div>
      <div class="meta-line">${escapeHtml(session.cwd || "No cwd recorded")} · ${escapeHtml(formatDateTime(session.started_at))}${session.ended_at ? ` → ${escapeHtml(formatDateTime(session.ended_at))}` : ""}</div>
    </section>
    <section class="timeline">
      ${session.bubbles.map((bubble) => bubbleCard(bubble)).join("")}
    </section>
  `;
  if (!state.selectedBubbleId && session.bubbles[0]) {
    state.selectedBubbleId = session.bubbles[0].id;
  }
};

const renderSearch = () => {
  const query = state.query.trim().toLowerCase();
  if (!query) {
    elements.mainContent.replaceChildren(
      buildEmptyState("Search the archive", "Type a remembered phrase and Glimmer will pull matching bubbles from the local history.")
    );
    return;
  }
  const bubbles = (state.data?.bubbles ?? []).filter((bubble) => {
    const haystack = [
      bubble.text,
      bubble.project_name,
      bubble.git_branch,
      bubble.companion,
      bubble.trigger_type,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return haystack.includes(query);
  });
  renderBubbleGroups(bubbles);
};

const renderMattered = () => {
  const mattered = (state.data?.bubbles ?? []).filter((bubble) => bubble.mattered);
  if (!mattered.length) {
    elements.mainContent.replaceChildren(
      buildEmptyState(
        "No mattered bubbles yet",
        "Mark a bubble as mattered from the detail panel and it will appear here."
      )
    );
    return;
  }
  renderBubbleGroups(mattered);
};

const renderDetail = () => {
  const bubble = bubbleById(state.selectedBubbleId);
  if (bubble) {
    const session = sessionForBubble(bubble);
    elements.detail.innerHTML = `
      <div class="detail-stack">
        <section class="detail-block">
          <p class="eyebrow">Bubble</p>
          <h3 class="detail-title">${escapeHtml(bubble.companion)}</h3>
          <p class="detail-copy">${escapeHtml(bubble.text)}</p>
          <section class="matter-panel">
            <div class="matter-head">
              <div>
                <p class="eyebrow">This Mattered</p>
                <p class="matter-copy">Mark the bubble and leave a short note about why it mattered.</p>
              </div>
              ${bubble.mattered ? '<span class="matter-badge">Marked</span>' : ""}
            </div>
            <textarea
              id="matter-note-input"
              class="matter-note-input"
              placeholder="Optional note about why this mattered."
            >${escapeHtml(bubble.matter_note || "")}</textarea>
            <div class="matter-actions">
              <button class="link-button" data-save-matter="${bubble.id}">
                ${state.matterSaving ? "Saving..." : bubble.mattered ? "Save note" : "Mark mattered"}
              </button>
              ${
                bubble.mattered
                  ? `<button class="secondary-button" data-clear-matter="${bubble.id}" ${state.matterSaving ? "disabled" : ""}>Unmark</button>`
                  : ""
              }
            </div>
            ${
              bubble.mattered_at
                ? `<p class="matter-meta">Marked ${escapeHtml(formatDateTime(bubble.mattered_at))}${bubble.matter_updated_at && bubble.matter_updated_at !== bubble.mattered_at ? ` · updated ${escapeHtml(formatDateTime(bubble.matter_updated_at))}` : ""}</p>`
                : ""
            }
          </section>
          ${session ? `<button class="link-button" data-open-session="${session.session_id}">Open session</button>` : ""}
        </section>
        <section class="detail-block">
          <dl class="meta-list">
            <div class="meta-item"><dt>Timestamp</dt><dd>${escapeHtml(formatDateTime(bubble.timestamp))}</dd></div>
            <div class="meta-item"><dt>Project</dt><dd>${escapeHtml(bubble.project_name || "No project")}</dd></div>
            <div class="meta-item"><dt>Branch</dt><dd>${escapeHtml(bubble.git_branch || "No branch")}</dd></div>
            <div class="meta-item"><dt>CWD</dt><dd>${escapeHtml(bubble.cwd || "No cwd")}</dd></div>
            <div class="meta-item"><dt>Trigger</dt><dd>${escapeHtml(bubble.trigger_type || "Unknown")}</dd></div>
            <div class="meta-item"><dt>Source</dt><dd>${escapeHtml(bubble.source || "legacy")}</dd></div>
            <div class="meta-item"><dt>Mattered</dt><dd>${bubble.mattered ? "Yes" : "No"}</dd></div>
          </dl>
        </section>
      </div>
    `;
    return;
  }

  const session = sessionById(state.selectedSessionId);
  if (session) {
    elements.detail.innerHTML = `
      <div class="detail-stack">
        <section class="detail-block">
          <p class="eyebrow">Session</p>
          <h3 class="detail-title">${escapeHtml(session.project_label)}</h3>
          <p class="detail-copy">${escapeHtml(session.latest_bubble_preview || "No bubbles in this session.")}</p>
        </section>
        <section class="detail-block">
          <dl class="meta-list">
            <div class="meta-item"><dt>Started</dt><dd>${escapeHtml(formatDateTime(session.started_at))}</dd></div>
            <div class="meta-item"><dt>Ended</dt><dd>${escapeHtml(session.ended_at ? formatDateTime(session.ended_at) : "Open")}</dd></div>
            <div class="meta-item"><dt>Project</dt><dd>${escapeHtml(session.project_label)}</dd></div>
            <div class="meta-item"><dt>Branch</dt><dd>${escapeHtml(session.git_branch || "No branch")}</dd></div>
            <div class="meta-item"><dt>CWD</dt><dd>${escapeHtml(session.cwd || "No cwd")}</dd></div>
          </dl>
        </section>
      </div>
    `;
    return;
  }

  const project = projectByKey(state.selectedProjectKey);
  if (project) {
    elements.detail.innerHTML = `
      <div class="detail-stack">
        <section class="detail-block">
          <p class="eyebrow">Project</p>
          <h3 class="detail-title">${escapeHtml(project.project_label)}</h3>
          <p class="detail-copy">${escapeHtml(project.latest_bubble_preview || "No preview available yet.")}</p>
        </section>
        <section class="detail-block">
          <dl class="meta-list">
            <div class="meta-item"><dt>Bubbles</dt><dd>${project.bubble_count}</dd></div>
            <div class="meta-item"><dt>Sessions</dt><dd>${project.session_count}</dd></div>
            <div class="meta-item"><dt>Last seen</dt><dd>${escapeHtml(formatDateTime(project.last_seen_at))}</dd></div>
            <div class="meta-item"><dt>Branches</dt><dd>${escapeHtml((project.branches || []).join(", ") || "No branch context")}</dd></div>
          </dl>
        </section>
      </div>
    `;
    return;
  }

  elements.detail.replaceChildren(
    buildEmptyState("Select something", "Choose a bubble, session, or project to inspect the details on the right.")
  );
};

const saveMatter = async (bubbleId, marked) => {
  const noteInput = document.getElementById("matter-note-input");
  state.matterSaving = true;
  renderDetail();
  try {
    const response = await fetch("/api/matters", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        bubble_id: bubbleId,
        marked,
        note: noteInput?.value ?? "",
      }),
    });
    if (!response.ok) {
      throw new Error(`Save failed with ${response.status}`);
    }
    await loadData();
  } catch (error) {
    console.error("Failed to save mattered bubble:", error);
  } finally {
    state.matterSaving = false;
    renderDetail();
  }
};

const renderMain = () => {
  if (state.loading || !state.data) {
    elements.mainContent.replaceChildren(
      buildEmptyState("Loading archive", "Glimmer is reading your local bubble history.")
    );
    return;
  }

  if (state.view === "project") {
    renderProjectDetail();
    return;
  }
  if (state.view === "session") {
    renderSessionDetail();
    return;
  }

  const titles = {
    recent: ["Recent bubbles", "Recent"],
    mattered: ["Bubbles you marked as mattered", "Mattered"],
    projects: ["Archive by project", "Projects"],
    sessions: ["Archive by session", "Sessions"],
    search: ["Search local history", "Search"],
  };
  const [eyebrow, title] = titles[state.view] || titles.recent;
  elements.viewEyebrow.textContent = eyebrow;
  elements.viewTitle.textContent = title;

  if (state.view === "recent") {
    renderBubbleGroups((state.data?.bubbles ?? []).slice(0, 120));
    return;
  }
  if (state.view === "mattered") {
    renderMattered();
    return;
  }
  if (state.view === "projects") {
    renderProjects();
    return;
  }
  if (state.view === "sessions") {
    renderSessions();
    return;
  }
  renderSearch();
};

const render = () => {
  syncNav();
  renderOverview();
  renderMain();
  renderDetail();
};

const loadData = async () => {
  state.loading = true;
  renderMain();
  const response = await fetch("/api/index", { cache: "no-store" });
  state.data = await response.json();
  state.loading = false;

  if (!state.selectedBubbleId && state.data.bubbles[0]) {
    state.selectedBubbleId = state.data.bubbles[0].id;
  }
  if (!state.selectedSessionId && state.data.sessions[0]) {
    state.selectedSessionId = state.data.sessions[0].session_id;
  }
  if (!state.selectedProjectKey && state.data.projects[0]) {
    state.selectedProjectKey = state.data.projects[0].project_key;
  }

  render();
};

elements.navLinks.forEach((link) => {
  link.addEventListener("click", () => {
    state.query = "";
    elements.searchInput.value = "";
    setView(link.dataset.view);
  });
});

elements.searchInput.addEventListener("input", (event) => {
  state.query = event.target.value;
  if (state.query.trim()) {
    state.view = "search";
  } else if (state.view === "search") {
    state.view = state.previousView === "search" ? "recent" : state.previousView;
  }
  syncNav();
  renderMain();
});

elements.refreshButton.addEventListener("click", () => {
  void loadData();
});

document.addEventListener("click", (event) => {
  const bubbleCardElement = event.target.closest("[data-bubble-id]");
  if (bubbleCardElement) {
    setSelectedBubble(bubbleCardElement.dataset.bubbleId);
    return;
  }

  const sessionCardElement = event.target.closest("[data-session-id]");
  if (sessionCardElement) {
    const sessionId = sessionCardElement.dataset.sessionId;
    const session = sessionById(sessionId);
    setView("session", {
      sessionId,
      bubbleId: session?.bubbles?.[0]?.id ?? null,
    });
    return;
  }

  const projectCardElement = event.target.closest("[data-project-key]");
  if (projectCardElement) {
    setView("project", { projectKey: projectCardElement.dataset.projectKey });
    return;
  }

  const openSessionButton = event.target.closest("[data-open-session]");
  if (openSessionButton) {
    const sessionId = openSessionButton.dataset.openSession;
    const session = sessionById(sessionId);
    setView("session", {
      sessionId,
      bubbleId: session?.bubbles?.[0]?.id ?? null,
    });
    return;
  }

  const backButton = event.target.closest("[data-back-to]");
  if (backButton) {
    setView(backButton.dataset.backTo);
    return;
  }

  const viewButton = event.target.closest("[data-view]");
  if (viewButton && viewButton.closest(".overview")) {
    state.query = "";
    elements.searchInput.value = "";
    setView(viewButton.dataset.view);
    return;
  }

  const saveMatterButton = event.target.closest("[data-save-matter]");
  if (saveMatterButton && !state.matterSaving) {
    void saveMatter(saveMatterButton.dataset.saveMatter, true);
    return;
  }

  const clearMatterButton = event.target.closest("[data-clear-matter]");
  if (clearMatterButton && !state.matterSaving) {
    void saveMatter(clearMatterButton.dataset.clearMatter, false);
  }
});

void loadData();
