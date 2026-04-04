const state = {
  data: null,
  reviewData: null,
  briefData: null,
  bubbleDetail: null,
  loading: true,
  detailLoading: false,
  briefLoading: false,
  detailRequestId: 0,
  view: "recent",
  previousView: "recent",
  query: "",
  selectedBubbleId: null,
  selectedSessionId: null,
  selectedProjectKey: null,
  briefProjectKey: null,
  reviewFilter: "all",
  reviewSort: "recently_marked",
  matterSaving: false,
  reviewSaving: false,
  briefCopyStatus: "",
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

const REVIEW_STATES = ["unreviewed", "open", "used", "stale"];

const REVIEW_META = {
  unreviewed: {
    label: "Unreviewed",
    description: "Freshly marked, not revisited yet.",
  },
  open: {
    label: "Open",
    description: "Still active or worth carrying forward.",
  },
  used: {
    label: "Used",
    description: "Already folded back into the work.",
  },
  stale: {
    label: "Stale",
    description: "Kept for context, no longer active.",
  },
};

const REVIEW_SORT_META = {
  recently_marked: "Recently marked",
  recently_reviewed: "Recently reviewed",
  oldest_open: "Oldest open",
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

const matteredBubbles = () =>
  (state.data?.bubbles ?? []).filter((bubble) => bubble.mattered);

const currentBriefProjectKey = () =>
  state.briefProjectKey || state.selectedProjectKey || state.data?.projects?.[0]?.project_key || null;

const briefBubbleIds = () => {
  if (!state.briefData) return [];
  return Array.from(
    new Set([
      ...(state.briefData.top_mattered ?? []).map((bubble) => bubble.id),
      ...(state.briefData.open_items ?? []).map((bubble) => bubble.id),
      ...(state.briefData.recurring_signals ?? []).map((entry) => entry.bubble.id),
    ])
  );
};

const ensureReviewVisibilityForBubble = (bubbleId) => {
  const bubble = bubbleById(bubbleId);
  if (!bubble || state.view !== "review" || !bubble.mattered) return;
  const reviewState = bubble.review_state || "unreviewed";
  if (state.reviewFilter !== "all" && state.reviewFilter !== reviewState) {
    state.reviewFilter = reviewState;
  }
};

const primeSelectedBubble = (bubbleId) => {
  if (!bubbleId || state.selectedBubbleId === bubbleId) return;
  state.selectedBubbleId = bubbleId;
  state.bubbleDetail = null;
  void loadBubbleDetail(bubbleId);
};

const setSelectedBubble = (bubbleId) => {
  state.selectedBubbleId = bubbleId;
  state.bubbleDetail = null;
  renderDetail();
  renderMain();
  void loadBubbleDetail(bubbleId);
};

const setView = (nextView, options = {}) => {
  if (state.view !== "search") {
    state.previousView = state.view;
  }
  state.view = nextView;
  if (options.sessionId !== undefined) state.selectedSessionId = options.sessionId;
  if (options.projectKey !== undefined) state.selectedProjectKey = options.projectKey;
  if (options.bubbleId !== undefined) state.selectedBubbleId = options.bubbleId;
  if (nextView === "brief") {
    state.briefProjectKey = state.briefProjectKey || state.selectedProjectKey || state.data?.projects?.[0]?.project_key || null;
    state.briefCopyStatus = "";
  }
  syncNav();
  render();
  if (nextView === "brief" && state.data) {
    void loadBrief({
      projectKey: currentBriefProjectKey(),
      force: !state.briefData,
    });
  }
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
  if (bubble.mattered && bubble.review_state) {
    chips.push(`<span class="chip">${escapeHtml(REVIEW_META[bubble.review_state]?.label || bubble.review_state)}</span>`);
  }
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

const reviewSortKey = (bubble) => {
  const reviewedAt = bubble.reviewed_at ? new Date(bubble.reviewed_at).getTime() : 0;
  const matteredAt = bubble.mattered_at ? new Date(bubble.mattered_at).getTime() : 0;
  const timestamp = bubble.timestamp ? new Date(bubble.timestamp).getTime() : 0;
  return Math.max(reviewedAt || 0, matteredAt || 0, timestamp || 0);
};

const reviewGroups = () => {
  return REVIEW_STATES.map((reviewState) => ({
    key: reviewState,
    meta: REVIEW_META[reviewState],
    bubbles: state.reviewData?.groups?.[reviewState] ?? [],
  }));
};

const sortReviewBubbles = (bubbles, reviewState) => {
  const items = [...bubbles];
  if (state.reviewSort === "recently_reviewed") {
    return items.sort((left, right) => {
      const leftTime = left.reviewed_at ? new Date(left.reviewed_at).getTime() : 0;
      const rightTime = right.reviewed_at ? new Date(right.reviewed_at).getTime() : 0;
      return rightTime - leftTime || reviewSortKey(right) - reviewSortKey(left);
    });
  }
  if (state.reviewSort === "oldest_open") {
    if (reviewState !== "open") {
      return items.sort((left, right) => reviewSortKey(right) - reviewSortKey(left));
    }
    return items.sort((left, right) => {
      const leftTime = left.mattered_at ? new Date(left.mattered_at).getTime() : 0;
      const rightTime = right.mattered_at ? new Date(right.mattered_at).getTime() : 0;
      return leftTime - rightTime || reviewSortKey(left) - reviewSortKey(right);
    });
  }
  return items.sort((left, right) => reviewSortKey(right) - reviewSortKey(left));
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
  const mattered = matteredBubbles();
  if (!mattered.length) {
    elements.mainContent.replaceChildren(
      buildEmptyState(
        "No mattered bubbles yet",
        "Mark a bubble as mattered from the detail panel and it will appear here."
      )
    );
    return;
  }
  if (!bubbleById(state.selectedBubbleId)?.mattered) {
    primeSelectedBubble(mattered[0].id);
  }
  renderBubbleGroups(mattered);
};

const renderReview = () => {
  const groups = reviewGroups().map((group) => ({
    ...group,
    bubbles: sortReviewBubbles(group.bubbles, group.key),
  }));
  const total = groups.reduce((sum, group) => sum + group.bubbles.length, 0);
  if (!total) {
    elements.mainContent.replaceChildren(
      buildEmptyState(
        "No mattered bubbles to review",
        "Mark a bubble as mattered first. It will land here as unreviewed and move through the review states."
      )
    );
    return;
  }
  if (!bubbleById(state.selectedBubbleId)?.mattered) {
    const firstBubble = groups.find((group) => group.bubbles[0])?.bubbles[0];
    if (firstBubble) primeSelectedBubble(firstBubble.id);
  }

  const visibleGroups =
    state.reviewFilter === "all"
      ? groups
      : groups.filter((group) => group.key === state.reviewFilter);

  const visibleBubbleIds = new Set(
    visibleGroups.flatMap((group) => group.bubbles.map((bubble) => bubble.id))
  );
  if (!visibleBubbleIds.has(state.selectedBubbleId)) {
    const firstVisibleBubble = visibleGroups.find((group) => group.bubbles[0])?.bubbles[0];
    if (firstVisibleBubble) primeSelectedBubble(firstVisibleBubble.id);
  }

  const hints = state.reviewData?.hints ?? [];

  elements.mainContent.innerHTML = "";
  const stack = document.createElement("div");
  stack.className = "section-stack";
  stack.innerHTML = `
    <section class="review-summary">
      <button
        class="review-summary-card ${state.reviewFilter === "all" ? "is-active" : ""}"
        data-review-filter="all"
      >
        <div class="card-meta">All mattered</div>
        <strong>${total}</strong>
        <p>Everything currently in the review loop.</p>
      </button>
      ${groups
        .map(
          (group) => `
            <button
              class="review-summary-card ${state.reviewFilter === group.key ? "is-active" : ""}"
              data-review-filter="${group.key}"
            >
              <div class="card-meta">${escapeHtml(group.meta.label)}</div>
              <strong>${group.bubbles.length}</strong>
              <p>${escapeHtml(group.meta.description)}</p>
            </button>
          `
        )
        .join("")}
    </section>
    <section class="review-controls">
      <div class="review-filter-row">
        <button class="chip-button ${state.reviewFilter === "all" ? "is-active" : ""}" data-review-filter="all">All</button>
        ${REVIEW_STATES.map(
          (reviewState) => `
            <button class="chip-button ${state.reviewFilter === reviewState ? "is-active" : ""}" data-review-filter="${reviewState}">
              ${escapeHtml(REVIEW_META[reviewState].label)}
            </button>
          `
        ).join("")}
      </div>
      <label class="review-sort-shell">
        <span>Sort</span>
        <select id="review-sort-select" class="review-sort-select">
          ${Object.entries(REVIEW_SORT_META)
            .map(
              ([value, label]) => `
                <option value="${value}" ${state.reviewSort === value ? "selected" : ""}>${escapeHtml(label)}</option>
              `
            )
            .join("")}
        </select>
      </label>
    </section>
    ${
      hints.length
        ? `
          <section class="resurface-strip">
            ${hints
              .map(
                (hint) => `
                  <button class="resurface-card" data-jump-bubble="${hint.bubble.id}">
                    <span class="context-label">${escapeHtml(hint.label)}</span>
                    <strong>${escapeHtml(hint.bubble.project_name || "No project")}</strong>
                    <p>${escapeHtml(hint.copy)}</p>
                    <span class="context-copy">${escapeHtml(hint.bubble.preview)}</span>
                  </button>
                `
              )
              .join("")}
          </section>
        `
        : ""
    }
  `;

  visibleGroups.forEach((group) => {
    const section = document.createElement("section");
    section.innerHTML = `
      <div class="section-header">
        <div>
          <h3 class="section-title">${escapeHtml(group.meta.label)}</h3>
          <p class="section-copy">${escapeHtml(group.meta.description)}</p>
        </div>
        <span class="muted">${group.bubbles.length}</span>
      </div>
      ${
        group.bubbles.length
          ? `<div class="card-list">${group.bubbles.map((bubble) => bubbleCard(bubble, { compact: true })).join("")}</div>`
          : '<div class="review-empty">Nothing here right now.</div>'
      }
    `;
    stack.append(section);
  });
  elements.mainContent.append(stack);
};

const renderBrief = () => {
  if (!state.briefData && !state.briefLoading) {
    void loadBrief({ projectKey: currentBriefProjectKey(), force: true });
  }

  if (state.briefLoading && !state.briefData) {
    elements.mainContent.replaceChildren(
      buildEmptyState("Building brief", "Glimmer is assembling the most relevant project context.")
    );
    return;
  }

  const brief = state.briefData;
  if (!brief) {
    elements.mainContent.replaceChildren(
      buildEmptyState("No brief yet", "Mark a few bubbles as mattered and Glimmer will build a project brief here.")
    );
    return;
  }

  const candidateIds = briefBubbleIds();
  if (candidateIds.length && !candidateIds.includes(state.selectedBubbleId)) {
    primeSelectedBubble(candidateIds[0]);
  }

  const projectOptions = state.data?.projects ?? [];
  const summary = brief.summary ?? {};
  const topMattered = brief.top_mattered ?? [];
  const openItems = brief.open_items ?? [];
  const recurring = brief.recurring_signals ?? [];
  const recurringCount = recurring.length;

  elements.mainContent.innerHTML = `
    <section class="brief-hero">
      <div class="brief-copy-shell">
        <p class="eyebrow">Before you begin</p>
        <h3>${escapeHtml(brief.scope.project_label || "Brief")}</h3>
        <p class="section-copy">A project-specific recall pack built from the bubbles you marked as mattered.</p>
      </div>
      <div class="brief-controls-shell">
        <label class="review-sort-shell brief-project-shell">
          <span>Project</span>
          <select id="brief-project-select" class="review-sort-select">
            ${projectOptions
              .map(
                (project) => `
                  <option value="${escapeHtml(project.project_key)}" ${project.project_key === (brief.scope.project_key || currentBriefProjectKey()) ? "selected" : ""}>
                    ${escapeHtml(project.project_label)}
                  </option>
                `
              )
              .join("")}
          </select>
        </label>
        <div class="brief-action-row">
          <button class="secondary-button" data-copy-brief="plain">Copy plain</button>
          <button class="link-button" data-copy-brief="markdown">Copy markdown</button>
        </div>
        ${state.briefCopyStatus ? `<p class="matter-meta">${escapeHtml(state.briefCopyStatus)}</p>` : ""}
      </div>
    </section>
    <section class="review-summary brief-summary-grid">
      <div class="review-summary-card">
        <div class="card-meta">Mattered</div>
        <strong>${summary.mattered_count ?? 0}</strong>
        <p>Signals you explicitly kept from this project.</p>
      </div>
      <div class="review-summary-card">
        <div class="card-meta">Open</div>
        <strong>${summary.open_count ?? 0}</strong>
        <p>Items still active in the review loop.</p>
      </div>
      <div class="review-summary-card">
        <div class="card-meta">Unreviewed</div>
        <strong>${summary.unreviewed_count ?? 0}</strong>
        <p>Freshly marked bubbles you have not revisited yet.</p>
      </div>
      <div class="review-summary-card">
        <div class="card-meta">Recurring</div>
        <strong>${recurringCount}</strong>
        <p>Repeated themes Glimmer can already surface here.</p>
      </div>
    </section>
  `;

  const stack = document.createElement("div");
  stack.className = "section-stack";
  stack.innerHTML = `
    <section>
      <div class="section-header">
        <div>
          <h3 class="section-title">Top Mattered</h3>
          <p class="section-copy">The three strongest signals to read before you continue working.</p>
        </div>
        <span class="muted">${topMattered.length}</span>
      </div>
      ${topMattered.length ? `<div class="card-list">${topMattered.map((bubble) => bubbleCard(bubble, { compact: true })).join("")}</div>` : '<div class="review-empty">No mattered bubbles for this project yet.</div>'}
    </section>
    <section>
      <div class="section-header">
        <div>
          <h3 class="section-title">Open Items</h3>
          <p class="section-copy">Still-active matters that should stay in working memory.</p>
        </div>
        <span class="muted">${openItems.length}</span>
      </div>
      ${openItems.length ? `<div class="card-list">${openItems.map((bubble) => bubbleCard(bubble, { compact: true })).join("")}</div>` : '<div class="review-empty">Nothing open right now.</div>'}
    </section>
    <section>
      <div class="section-header">
        <div>
          <h3 class="section-title">Recurring Signals</h3>
          <p class="section-copy">Themes that keep showing up in mattered bubbles around this project.</p>
        </div>
        <span class="muted">${recurring.length}</span>
      </div>
      ${
        recurring.length
          ? `<div class="resurface-strip">${recurring
              .map(
                (entry) => `
                  <button class="resurface-card" data-jump-bubble="${entry.bubble.id}">
                    <span class="context-label">${escapeHtml(entry.match_count.toString())} matches · ${escapeHtml((entry.shared_tokens || []).slice(0, 3).join(", ") || "shared themes")}</span>
                    <strong>${escapeHtml(entry.bubble.project_name || "No project")}</strong>
                    <p>${escapeHtml(entry.bubble.matter_note || "No note attached.")}</p>
                    <span class="context-copy">${escapeHtml(entry.bubble.preview)}</span>
                  </button>
                `
              )
              .join("")}</div>`
          : '<div class="review-empty">No recurring signals yet.</div>'
      }
    </section>
  `;

  elements.mainContent.append(stack);
};

const renderDetail = () => {
  const mattered = matteredBubbles();
  if ((state.view === "mattered" || state.view === "review") && mattered.length === 0) {
    elements.detail.replaceChildren(
      buildEmptyState(
        state.view === "review" ? "Nothing to review yet" : "Nothing marked yet",
        state.view === "review"
          ? "Mark a bubble as mattered first. Review states appear here once something enters the loop."
          : "Mark a bubble as mattered and it will appear here with notes and review controls."
      )
    );
    return;
  }

  const bubble = bubbleById(state.selectedBubbleId);
  if (bubble) {
    const detail = state.bubbleDetail?.bubble?.id === bubble.id ? state.bubbleDetail : null;
    const session = detail?.session ?? sessionForBubble(bubble);
    const detailBusy = state.matterSaving || state.reviewSaving;
    const reviewState = bubble.review_state || "unreviewed";
    const previousBubble = detail?.previous_bubble ?? null;
    const nextBubble = detail?.next_bubble ?? null;
    const relatedMattered = detail?.related_mattered ?? [];
    const recurrenceMatches = detail?.recurrence_matches ?? [];
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
              ${detailBusy ? "disabled" : ""}
            >${escapeHtml(bubble.matter_note || "")}</textarea>
            <div class="matter-actions">
              <button class="link-button" data-save-matter="${bubble.id}" ${detailBusy ? "disabled" : ""}>
                ${state.matterSaving ? "Saving..." : bubble.mattered ? "Save note" : "Mark mattered"}
              </button>
              ${
                bubble.mattered
                  ? `<button class="secondary-button" data-clear-matter="${bubble.id}" ${detailBusy ? "disabled" : ""}>Unmark</button>`
                  : ""
              }
            </div>
            ${
              bubble.mattered_at
                ? `<p class="matter-meta">Marked ${escapeHtml(formatDateTime(bubble.mattered_at))}${bubble.matter_updated_at && bubble.matter_updated_at !== bubble.mattered_at ? ` · updated ${escapeHtml(formatDateTime(bubble.matter_updated_at))}` : ""}</p>`
                : ""
            }
            ${state.detailLoading ? '<p class="matter-meta">Loading related context…</p>' : ""}
            ${
              bubble.mattered
                ? `
                  <section class="review-panel">
                    <div class="matter-head">
                      <div>
                        <p class="eyebrow">Review State</p>
                        <p class="matter-copy">Move mattered bubbles through a small review loop instead of letting them pile up.</p>
                      </div>
                    </div>
                    <div class="review-state-row">
                      ${REVIEW_STATES.map(
                        (stateValue) => `
                          <button
                            class="chip-button ${reviewState === stateValue ? "is-active" : ""}"
                            data-review-state-bubble="${bubble.id}"
                            data-review-state-value="${stateValue}"
                            ${detailBusy ? "disabled" : ""}
                          >
                            ${escapeHtml(REVIEW_META[stateValue].label)}
                          </button>
                        `
                      ).join("")}
                    </div>
                    <p class="matter-meta">
                      ${escapeHtml(REVIEW_META[reviewState]?.description || "")}
                      ${bubble.reviewed_at ? ` · updated ${escapeHtml(formatDateTime(bubble.reviewed_at))}` : ""}
                    </p>
                  </section>
                `
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
            ${bubble.mattered ? `<div class="meta-item"><dt>Review state</dt><dd>${escapeHtml(REVIEW_META[reviewState]?.label || reviewState)}</dd></div>` : ""}
          </dl>
        </section>
        ${
          session
            ? `
              <section class="detail-block">
                <p class="eyebrow">Session Context</p>
                <div class="context-list">
                  <button class="context-link" ${previousBubble ? `data-jump-bubble="${previousBubble.id}"` : "disabled"}>
                    <span class="context-label">Previous bubble</span>
                    <span class="context-copy">${escapeHtml(previousBubble?.preview || "None")}</span>
                  </button>
                  <button class="context-link" ${nextBubble ? `data-jump-bubble="${nextBubble.id}"` : "disabled"}>
                    <span class="context-label">Next bubble</span>
                    <span class="context-copy">${escapeHtml(nextBubble?.preview || "None")}</span>
                  </button>
                </div>
              </section>
            `
            : ""
        }
        ${
          bubble.project_name && relatedMattered.length
            ? `
              <section class="detail-block">
                <p class="eyebrow">Related Mattered</p>
                <div class="context-list">
                  ${relatedMattered
                    .map(
                      (entry) => `
                        <button class="context-link" data-jump-bubble="${entry.id}">
                          <span class="context-label">${escapeHtml(REVIEW_META[entry.review_state || "unreviewed"]?.label || "Mattered")} · ${escapeHtml(formatShort(entry.mattered_at || entry.timestamp))}</span>
                          <span class="context-copy">${escapeHtml(entry.preview)}</span>
                        </button>
                      `
                    )
                    .join("")}
                </div>
              </section>
            `
            : ""
        }
        ${
          recurrenceMatches.length
            ? `
              <section class="detail-block">
                <p class="eyebrow">Recurring Signals</p>
                <div class="context-list">
                  ${recurrenceMatches
                    .map(
                      (match) => `
                        <button class="context-link" data-jump-bubble="${match.bubble.id}">
                          <span class="context-label">
                            ${match.same_project ? "Same project" : "Cross-project"} · shared ${escapeHtml((match.shared_tokens || []).slice(0, 3).join(", "))}
                          </span>
                          <span class="context-copy">${escapeHtml(match.bubble.preview)}</span>
                        </button>
                      `
                    )
                    .join("")}
                </div>
              </section>
            `
            : ""
        }
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

const buildBriefCopyText = (mode = "plain") => {
  if (!state.briefData) return "";
  const brief = state.briefData;
  const summary = brief.summary ?? {};
  const lineForBubble = (bubble) => {
    const reviewState = bubble.review_state || "unreviewed";
    const parts = [`[${reviewState}] ${bubble.text}`];
    if (bubble.matter_note) parts.push(`note: ${bubble.matter_note}`);
    parts.push(`id: ${bubble.id}`);
    return parts.join(" | ");
  };

  if (mode === "markdown") {
    return [
      `# Glimmer Brief: ${brief.scope.project_label || "Brief"}`,
      "",
      `- Scope: ${brief.scope.source}${brief.scope.cwd ? ` · cwd=${brief.scope.cwd}` : ""}`,
      `- Summary: ${summary.mattered_count ?? 0} mattered, ${summary.open_count ?? 0} open, ${summary.unreviewed_count ?? 0} unreviewed, ${summary.used_count ?? 0} used, ${summary.stale_count ?? 0} stale`,
      "",
      "## Top Mattered",
      ...(brief.top_mattered?.length
        ? brief.top_mattered.map((bubble) => `- ${lineForBubble(bubble)}`)
        : ["- No mattered bubbles for this project yet."]),
      "",
      "## Open Items",
      ...(brief.open_items?.length
        ? brief.open_items.map((bubble) => `- ${lineForBubble(bubble)}`)
        : ["- Nothing open right now."]),
      "",
      "## Recurring Signals",
      ...(brief.recurring_signals?.length
        ? brief.recurring_signals.map(
            (entry) =>
              `- ${lineForBubble(entry.bubble)} | matches: ${entry.match_count} | shared: ${(entry.shared_tokens || []).join(", ") || "shared themes"}`
          )
        : ["- No recurring signals yet."]),
    ].join("\n");
  }

  return [
    `Brief: ${brief.scope.project_label || "Brief"}`,
    `Scope: ${brief.scope.source}${brief.scope.cwd ? `  cwd=${brief.scope.cwd}` : ""}`,
    `Mattered: ${summary.mattered_count ?? 0}  Open: ${summary.open_count ?? 0}  Unreviewed: ${summary.unreviewed_count ?? 0}  Used: ${summary.used_count ?? 0}  Stale: ${summary.stale_count ?? 0}`,
    "",
    "Top mattered",
    ...(brief.top_mattered?.length
      ? brief.top_mattered.map((bubble) => `  - ${lineForBubble(bubble)}`)
      : ["  none yet"]),
    "",
    "Open items",
    ...(brief.open_items?.length
      ? brief.open_items.map((bubble) => `  - ${lineForBubble(bubble)}`)
      : ["  nothing open right now"]),
    "",
    "Recurring signals",
    ...(brief.recurring_signals?.length
      ? brief.recurring_signals.map(
          (entry) =>
            `  - ${lineForBubble(entry.bubble)} | matches=${entry.match_count} | shared=${(entry.shared_tokens || []).join(", ") || "shared themes"}`
        )
      : ["  none yet"]),
  ].join("\n");
};

const copyBrief = async (mode = "plain") => {
  const text = buildBriefCopyText(mode);
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    state.briefCopyStatus = mode === "markdown" ? "Copied markdown brief." : "Copied plain brief.";
  } catch (error) {
    console.error("Failed to copy brief:", error);
    state.briefCopyStatus = "Copy failed in this browser.";
  }
  renderMain();
};

const loadBrief = async ({ projectKey = currentBriefProjectKey(), force = false } = {}) => {
  if (state.briefLoading) return;
  if (!force && state.briefData?.scope?.project_key === projectKey) return;

  state.briefLoading = true;
  if (state.view === "brief") renderMain();
  try {
    const params = new URLSearchParams();
    if (projectKey) {
      params.set("project", projectKey);
    } else if (state.selectedSessionId) {
      params.set("session", state.selectedSessionId);
    }
    const response = await fetch(`/api/brief?${params.toString()}`, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Brief failed with ${response.status}`);
    }
    const payload = await response.json();
    state.briefData = payload;
    state.briefProjectKey = payload.scope?.project_key || projectKey || null;
    if (state.briefProjectKey) {
      state.selectedProjectKey = state.briefProjectKey;
    }
  } catch (error) {
    console.error("Failed to load brief:", error);
    state.briefData = null;
  } finally {
    state.briefLoading = false;
    if (state.view === "brief") {
      renderMain();
      renderDetail();
    }
  }
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

const saveReviewState = async (bubbleId, reviewState) => {
  state.reviewSaving = true;
  renderDetail();
  try {
    const response = await fetch("/api/review-state", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        bubble_id: bubbleId,
        review_state: reviewState,
      }),
    });
    if (!response.ok) {
      throw new Error(`Review update failed with ${response.status}`);
    }
    await loadData();
  } catch (error) {
    console.error("Failed to update review state:", error);
  } finally {
    state.reviewSaving = false;
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
    brief: ["Project recall before you begin", "Brief"],
    recent: ["Recent bubbles", "Recent"],
    mattered: ["Bubbles you marked as mattered", "Mattered"],
    review: ["Review mattered bubbles", "Review"],
    projects: ["Archive by project", "Projects"],
    sessions: ["Archive by session", "Sessions"],
    search: ["Search local history", "Search"],
  };
  const [eyebrow, title] = titles[state.view] || titles.recent;
  elements.viewEyebrow.textContent = eyebrow;
  elements.viewTitle.textContent = title;

  if (state.view === "brief") {
    renderBrief();
    return;
  }
  if (state.view === "recent") {
    renderBubbleGroups((state.data?.bubbles ?? []).slice(0, 120));
    return;
  }
  if (state.view === "mattered") {
    renderMattered();
    return;
  }
  if (state.view === "review") {
    renderReview();
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

const loadBubbleDetail = async (bubbleId) => {
  const bubble = bubbleById(bubbleId);
  if (!bubble) {
    state.bubbleDetail = null;
    state.detailLoading = false;
    renderDetail();
    return;
  }

  const requestId = state.detailRequestId + 1;
  state.detailRequestId = requestId;
  state.detailLoading = true;
  renderDetail();
  try {
    const response = await fetch(`/api/bubbles/${encodeURIComponent(bubbleId)}`, {
      cache: "no-store",
    });
    if (!response.ok) {
      throw new Error(`Bubble detail failed with ${response.status}`);
    }
    const payload = await response.json();
    if (state.detailRequestId !== requestId) return;
    state.bubbleDetail = payload;
  } catch (error) {
    console.error("Failed to load bubble detail:", error);
    if (state.detailRequestId !== requestId) return;
    state.bubbleDetail = null;
  } finally {
    if (state.detailRequestId === requestId) {
      state.detailLoading = false;
      renderDetail();
    }
  }
};

const loadData = async () => {
  state.loading = true;
  renderMain();
  const [indexResponse, reviewResponse] = await Promise.all([
    fetch("/api/index", { cache: "no-store" }),
    fetch("/api/review", { cache: "no-store" }),
  ]);
  state.data = await indexResponse.json();
  state.reviewData = await reviewResponse.json();
  state.loading = false;

  if (!bubbleById(state.selectedBubbleId) && state.data.bubbles[0]) {
    state.selectedBubbleId = state.data.bubbles[0].id;
  }
  if (!state.selectedSessionId && state.data.sessions[0]) {
    state.selectedSessionId = state.data.sessions[0].session_id;
  }
  if (!state.selectedProjectKey && state.data.projects[0]) {
    state.selectedProjectKey = state.data.projects[0].project_key;
  }
  if (!state.briefProjectKey && state.data.projects[0]) {
    state.briefProjectKey = state.selectedProjectKey || state.data.projects[0].project_key;
  }

  render();
  if (state.selectedBubbleId) {
    void loadBubbleDetail(state.selectedBubbleId);
  }
  if (state.view === "brief" || state.briefData) {
    void loadBrief({
      projectKey: currentBriefProjectKey(),
      force: true,
    });
  }
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

elements.mainContent.addEventListener("change", (event) => {
  if (event.target.id === "review-sort-select") {
    state.reviewSort = event.target.value;
    renderMain();
    return;
  }
  if (event.target.id === "brief-project-select") {
    state.briefProjectKey = event.target.value || null;
    state.briefCopyStatus = "";
    void loadBrief({
      projectKey: state.briefProjectKey,
      force: true,
    });
  }
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

  const copyBriefButton = event.target.closest("[data-copy-brief]");
  if (copyBriefButton) {
    void copyBrief(copyBriefButton.dataset.copyBrief || "plain");
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

  const reviewFilterButton = event.target.closest("[data-review-filter]");
  if (reviewFilterButton) {
    state.reviewFilter = reviewFilterButton.dataset.reviewFilter;
    renderMain();
    return;
  }

  const clearMatterButton = event.target.closest("[data-clear-matter]");
  if (clearMatterButton && !state.matterSaving) {
    void saveMatter(clearMatterButton.dataset.clearMatter, false);
    return;
  }

  const reviewStateButton = event.target.closest("[data-review-state-bubble]");
  if (reviewStateButton && !state.reviewSaving && !state.matterSaving) {
    void saveReviewState(
      reviewStateButton.dataset.reviewStateBubble,
      reviewStateButton.dataset.reviewStateValue
    );
    return;
  }

  const jumpBubbleButton = event.target.closest("[data-jump-bubble]");
  if (jumpBubbleButton && !jumpBubbleButton.disabled) {
    ensureReviewVisibilityForBubble(jumpBubbleButton.dataset.jumpBubble);
    setSelectedBubble(jumpBubbleButton.dataset.jumpBubble);
  }
});

void loadData();
