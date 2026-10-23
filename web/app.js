(() => {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const state = {
    view: "home",
    mode: localStorage.getItem("vf-mode") || "daily",
    cap: null,
    templatePrompt: "",
    caps: [],
    tasks: [],
    projectFilter: "all",
    task: null,
    taskId: null,
    events: [],
    lastSeq: 0,
    es: null,
    reconnectTimer: null,
    streamClosed: false,
    running: false,
    replaying: false,
    steps: [],
    planStatus: [],
    files: new Map(),
    diffs: new Map(),
    selectedFile: null,
    userPickedFile: false,
    checks: [],
    lastItem: null,
    stepCards: new Map(),
    timelineLimit: 80,
    previewUrl: "",
    typeTimers: new Set(),
  };

  const els = {
    home: $("#homeView"),
    projectsView: $("#projectsView"),
    workspace: $("#workspaceView"),
    composer: $("#composer"),
    prompt: $("#promptInput"),
    runBtn: $("#runBtn"),
    capPicker: $("#capPicker"),
    templateNote: $("#templateNote"),
    recentGrid: $("#recentGrid"),
    recentCount: $("#recentCount"),
    projectsGrid: $("#projectsGrid"),
    projectFilters: $("#projectFilters"),
    projectStats: $("#projectStats"),
    projectsNewBtn: $("#projectsNewBtn"),
    homeLink: $("#homeLink"),
    projectsLink: $("#projectsLink"),
    allProjectsLink: $("#allProjectsLink"),
    modeSwitch: $("#modeSwitch"),
    conn: $("#conn"),
    taskEyebrow: $("#taskEyebrow"),
    taskTitle: $("#taskTitle"),
    runStatus: $("#runStatus"),
    flowTitle: $("#flowTitle"),
    planSteps: $("#planSteps"),
    timeline: $("#timeline"),
    promptCard: $("#promptCard"),
    refineForm: $("#refineForm"),
    refineInput: $("#refineInput"),
    refineBtn: $("#refineBtn"),
    refineHint: $("#refineHint"),
    agentOrb: $("#agentOrb"),
    stageLabel: $("#stageLabel"),
    stageMeta: $("#stageMeta"),
    dailyView: $("#dailyView"),
    codingView: $("#codingView"),
    outcomeTitle: $("#outcomeTitle"),
    outcomeText: $("#outcomeText"),
    outcomeChecks: $("#outcomeChecks"),
    previewFrame: $("#previewFrame"),
    miniFrame: $("#miniFrame"),
    previewLoading: $("#previewLoading"),
    previewUrl: $("#previewUrl"),
    browserTag: $("#browserTag"),
    miniState: $("#miniState"),
    fileTree: $("#fileTree"),
    fileCount: $("#fileCount"),
    diffPath: $("#diffPath"),
    diffLanguage: $("#diffLanguage"),
    diffStats: $("#diffStats"),
    diffView: $("#diffView"),
    terminal: $("#terminal"),
    termStatus: $("#termStatus"),
    toast: $("#toast"),
    deployBtn: $("#deployBtn"),
    downloadBtn: $("#downloadBtn"),
    openNewBtn: $("#openNewBtn"),
    replayBtn: $("#replayBtn"),
    copyCodeBtn: $("#copyCodeBtn"),
    backBtn: $("#backBtn"),
    newTaskBtn: $("#newTaskBtn"),
    logoutBtn: $("#logoutBtn"),
    brandHome: $("#brandHome"),
  };

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  async function api(path, options = {}) {
    const response = await fetch(path, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    if (!response.ok) {
      if (response.status === 401) {
        location.replace("/login?next=" + encodeURIComponent(location.pathname + location.search));
      }
      let detail = response.statusText;
      try {
        const body = await response.json();
        detail = body.detail || detail;
      } catch (_) {}
      throw new Error(detail);
    }
    return response.json();
  }

  let toastTimer = null;
  function toast(message) {
    els.toast.textContent = message;
    els.toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => els.toast.classList.remove("show"), 2600);
  }

  function setConn(kind, text) {
    els.conn.className = "conn " + (kind || "");
    els.conn.querySelector("span").textContent = text;
  }

  function setStatus(kind, text) {
    els.runStatus.className = "status-pill " + kind;
    els.runStatus.innerHTML = "<i></i><span>" + escapeHtml(text) + "</span>";
  }

  function setMode(mode, persist = true) {
    state.mode = mode === "coding" ? "coding" : "daily";
    if (persist) localStorage.setItem("vf-mode", state.mode);
    els.modeSwitch.dataset.mode = state.mode;
    $$(".mode-btn").forEach((btn) => {
      const active = btn.dataset.mode === state.mode;
      btn.classList.toggle("active", active);
      btn.setAttribute("aria-selected", String(active));
    });
    if (!els.workspace.classList.contains("hidden")) {
      els.dailyView.classList.toggle("hidden", state.mode === "coding");
      els.codingView.classList.toggle("hidden", state.mode !== "coding");
      els.stageLabel.textContent = state.mode === "coding" ? "CODE CHANGES" : "DAILY OUTPUT";
      els.stageMeta.textContent = state.mode === "coding" ? "GIT SNAPSHOT" : "LIVE PREVIEW";
      if (state.mode === "coding" && state.selectedFile) renderDiff(state.selectedFile, true);
    }
  }

  function setRunning(running) {
    state.running = running;
    els.runBtn.disabled = running;
    els.runBtn.querySelector(".run-label").textContent = running ? "生成中…" : "开始生成";
    els.agentOrb.classList.toggle("running", running);
  }

  function setRefineState(enabled, hint = "") {
    if (!els.refineForm) return;
    if (!state.taskId) {
      els.refineForm.classList.add("hidden");
      return;
    }
    els.refineForm.classList.remove("hidden");
    els.refineInput.disabled = !enabled;
    els.refineBtn.disabled = !enabled;
    els.refineForm.classList.toggle("disabled", !enabled);
    els.refineHint.textContent = hint || (enabled ? "基于当前成果继续对话" : "Agent 正在处理…");
  }

  function clearTypeTimers() {
    state.typeTimers.forEach((timer) => clearInterval(timer));
    state.typeTimers.clear();
  }

  function typewrite(element, text, animate = true, speed = 13) {
    if (!element) return;
    clearInterval(element._typeTimer);
    if (!animate) {
      element.textContent = text;
      return;
    }
    element.textContent = "";
    const caret = document.createElement("span");
    caret.className = "caret";
    element.appendChild(caret);
    let index = 0;
    const step = Math.max(1, Math.ceil(text.length / 60));
    const timer = setInterval(() => {
      index = Math.min(text.length, index + step);
      element.textContent = text.slice(0, index);
      if (index < text.length) element.appendChild(caret);
      else {
        clearInterval(timer);
        caret.remove();
        state.typeTimers.delete(timer);
      }
    }, Math.max(8, speed));
    element._typeTimer = timer;
    state.typeTimers.add(timer);
  }

  function formatTime(iso) {
    try {
      const date = new Date(iso);
      return date.toLocaleTimeString("zh-CN", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
    } catch (_) {
      return "";
    }
  }

  function relativeTime(iso) {
    try {
      const diff = Date.now() - new Date(iso).getTime();
      const mins = Math.max(0, Math.floor(diff / 60000));
      if (mins < 1) return "刚刚";
      if (mins < 60) return mins + " 分钟前";
      const hours = Math.floor(mins / 60);
      if (hours < 24) return hours + " 小时前";
      return Math.floor(hours / 24) + " 天前";
    } catch (_) {
      return "";
    }
  }

  function scrollTimeline() {
    els.timeline.scrollTo({ top: els.timeline.scrollHeight, behavior: "smooth" });
  }

  function trimTimeline() {
    while (els.timeline.children.length > state.timelineLimit) {
      els.timeline.removeChild(els.timeline.firstElementChild);
    }
  }

  function addTimeline({ type = "thought", title = "", summary = "", time = "", animate = true, meta = "" }) {
    const item = document.createElement("div");
    item.className = "tl-item " + type;
    item.innerHTML =
      '<div class="tl-head"><span class="tl-title">' +
      escapeHtml(title) +
      '</span><span class="tl-time">' +
      escapeHtml(time || "") +
      "</span></div>" +
      (meta ? '<div class="tl-meta">' + escapeHtml(meta) + "</div>" : "") +
      '<div class="tl-summary"></div>';
    els.timeline.appendChild(item);
    trimTimeline();
    const summaryEl = $(".tl-summary", item);
    typewrite(summaryEl, summary, animate);
    state.lastItem = item;
    scrollTimeline();
    return item;
  }

  function appendChip(item, text, className = "tl-tool") {
    if (!item) return;
    const chip = document.createElement("span");
    chip.className = className;
    chip.textContent = text;
    item.appendChild(chip);
  }

  function terminal(text, className = "") {
    const line = document.createElement("div");
    line.className = "term-line " + className;
    line.textContent = text;
    els.terminal.appendChild(line);
    els.terminal.scrollTop = els.terminal.scrollHeight;
    while (els.terminal.children.length > 120) els.terminal.removeChild(els.terminal.firstElementChild);
  }

  function renderPlan() {
    if (!state.steps.length) {
      els.planSteps.innerHTML = "";
      return;
    }
    els.planSteps.innerHTML = state.steps
      .map((step, index) => {
        const status = state.planStatus[index] || "pending";
        return (
          '<div class="plan-step ' +
          status +
          '" data-index="' +
          index +
          '" style="--i:' +
          index +
          '"><span class="plan-index">0' +
          (index + 1) +
          '</span><span class="plan-name">' +
          escapeHtml(step) +
          '</span><span class="plan-state"></span></div>'
        );
      })
      .join("");
  }

  function updatePlan(index, status) {
    state.planStatus[index] = status;
    renderPlan();
  }

  function resetWorkspace() {
    closeStream();
    state.task = null;
    state.taskId = null;
    state.events = [];
    state.lastSeq = 0;
    state.running = false;
    state.replaying = false;
    state.steps = [];
    state.planStatus = [];
    state.files.clear();
    state.diffs.clear();
    state.selectedFile = null;
    state.userPickedFile = false;
    state.checks = [];
    state.lastItem = null;
    state.stepCards.clear();
    state.previewUrl = "";
    clearTypeTimers();
    els.timeline.innerHTML = "";
    els.planSteps.innerHTML = "";
    els.fileTree.innerHTML = '<div class="empty-state small">等待 Agent 写入文件…</div>';
    els.fileCount.textContent = "0";
    els.diffView.innerHTML =
      '<div class="diff-empty"><div class="empty-icon">⌘</div><b>代码会在这里逐行出现</b><span>Agent 写入文件后，你可以看到每一次新增与修改。</span></div>';
    els.diffPath.textContent = "index.html";
    els.diffLanguage.textContent = "HTML";
    els.diffStats.textContent = "0 changes";
    els.terminal.innerHTML = '<div class="term-line muted">$ vibeforge agent --wait</div>';
    els.termStatus.textContent = "IDLE";
    els.outcomeTitle.textContent = "正在生成…";
    els.outcomeText.textContent = "Agent 正在规划、写文件并验证结果。";
    els.outcomeChecks.innerHTML =
      '<div class="check-skeleton"></div><div class="check-skeleton"></div><div class="check-skeleton"></div>';
    els.previewLoading.classList.remove("hide");
    els.previewFrame.src = "about:blank";
    els.miniFrame.src = "about:blank";
    els.previewUrl.textContent = "/tasks/--/";
    els.browserTag.textContent = "LOCAL";
    els.miniState.textContent = "WAITING";
    els.promptCard.innerHTML = "";
    els.refineForm.classList.add("hidden");
    els.refineInput.value = "";
    els.agentOrb.className = "agent-orb";
    els.flowTitle.textContent = "正在拆解任务";
    els.taskEyebrow.textContent = "AGENT RUN / --";
    els.taskTitle.textContent = "正在理解你的想法…";
    setStatus("running", "PLANNING");
    setRunning(true);
    setConn("live", "STREAMING");
    setMode(state.mode, false);
  }

  function animateView(element) {
    if (!element) return;
    element.classList.remove("view-enter");
    void element.offsetWidth;
    element.classList.add("view-enter");
  }

  function setView(view) {
    state.view = view;
    document.body.dataset.view = view;
    els.home.classList.toggle("hidden", view !== "home");
    els.projectsView.classList.toggle("hidden", view !== "projects");
    els.workspace.classList.toggle("hidden", view !== "workspace");
    els.modeSwitch.classList.toggle("hidden", view !== "workspace");
    els.homeLink.classList.toggle("current", view === "home");
    els.projectsLink.classList.toggle("current", view === "projects");
    animateView(view === "home" ? els.home : view === "projects" ? els.projectsView : els.workspace);
  }

  function showWorkspace() {
    setView("workspace");
    setMode(state.mode, false);
    window.scrollTo({ top: 0, behavior: "auto" });
  }

  function goHome(push = true) {
    closeStream();
    state.task = null;
    state.taskId = null;
    state.events = [];
    state.lastSeq = 0;
    setRunning(false);
    setConn("", "LOCAL");
    setView("home");
    if (push) history.pushState({}, "", "/");
    loadRecent();
    window.scrollTo({ top: 0, behavior: "auto" });
    setTimeout(() => els.prompt.focus(), 80);
  }

  function goProjects(push = true) {
    closeStream();
    state.task = null;
    state.taskId = null;
    state.events = [];
    state.lastSeq = 0;
    setRunning(false);
    setConn("", "LOCAL");
    setView("projects");
    if (push) history.pushState({}, "", "/projects");
    loadProjects();
    window.scrollTo({ top: 0, behavior: "auto" });
  }

  function openProject(taskId, push = true) {
    if (!taskId) return;
    if (push) history.pushState({}, "", "/projects/" + encodeURIComponent(taskId));
    loadTask(taskId);
  }

  function renderCapabilities() {
    if (!state.caps.length) return;
    $$(".cap-chip").forEach((chip) => {
      const cap = state.caps.find((item) => item.key === chip.dataset.cap);
      if (cap) chip.title = cap.description;
    });
  }

  function applyTemplate(cap) {
    if (!cap) return;
    state.cap = cap.key;
    state.templatePrompt = cap.prompt || cap.example || "";
    $$(".cap-chip").forEach((chip) => chip.classList.toggle("active", chip.dataset.cap === state.cap));
    if (state.templatePrompt) {
      els.prompt.value = state.templatePrompt;
      els.templateNote.textContent = (cap.label || "模板") + " · 已填入专用提示词，可直接生成或修改";
      els.templateNote.classList.add("active");
      els.prompt.focus();
      els.prompt.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }

  function updateTemplateNote() {
    if (!state.cap) {
      els.templateNote.textContent = "选择一个模板，专用提示词会自动填入；也可以直接描述你的想法。";
      els.templateNote.classList.remove("active");
      return;
    }
    const cap = state.caps.find((item) => item.key === state.cap);
    const unchanged = els.prompt.value.trim() === state.templatePrompt.trim();
    if (unchanged) {
      els.templateNote.textContent = (cap?.label || "模板") + " · 已填入专用提示词，可直接生成或修改";
      els.templateNote.classList.add("active");
    } else {
      els.templateNote.textContent = "已修改模板提示词，提交时会根据内容自动识别能力。";
      els.templateNote.classList.remove("active");
    }
  }

  async function loadCapabilities() {
    try {
      const data = await api("/api/capabilities");
      state.caps = data.items || [];
      renderCapabilities();
    } catch (error) {
      console.warn(error);
    }
  }

  const fallbackCapInfo = {
    game: { key: "game", label: "小游戏", short: "GAME" },
    website: { key: "website", label: "网站", short: "WEB" },
    image: { key: "image", label: "图片", short: "IMAGE" },
    video: { key: "video", label: "视频", short: "VIDEO" },
    resume: { key: "resume", label: "简历", short: "CV" },
    travel: { key: "travel", label: "旅游攻略", short: "TRIP" },
    adapt: { key: "adapt", label: "适配制作", short: "ADAPT" },
    code: { key: "code", label: "编程", short: "CODE" },
  };
  const coverGlyphs = { game: "▶", website: "Aa", image: "IMG", video: "VID", resume: "CV", travel: "↗", adapt: "▣", code: "</>" };

  function capInfo(key) {
    return state.caps.find((item) => item.key === key) || fallbackCapInfo[key] || fallbackCapInfo.website;
  }

  async function fetchTasks() {
    const data = await api("/api/tasks");
    state.tasks = data.items || [];
    return state.tasks;
  }

  function projectCardHtml(task, index) {
    const info = capInfo(task.capability);
    const interrupted = task.status === "interrupted";
    const status = task.status === "done" ? "DEPLOYED" : task.status === "error" ? "FAILED" : interrupted ? "INTERRUPTED" : "RUNNING";
    const color = task.status === "error" || interrupted ? "var(--red)" : "var(--green)";
    const revision = task.revision ? "REV " + task.revision : "V1";
    const indexLabel = String(index + 1).padStart(2, "0");
    const title = task.title || task.prompt || "未命名项目";
    return (
      '<a class="project-card" href="/projects/' +
      encodeURIComponent(task.id) +
      '" data-project-id="' +
      task.id +
      '" style="--i:' +
      index +
      '"><div class="project-cover cover-' +
      escapeHtml(task.capability || "website") +
      '"><span class="cover-label">' +
      escapeHtml(info.short) +
      '</span><span class="cover-index">' +
      indexLabel +
      '</span><span class="cover-glyph">' +
      escapeHtml(coverGlyphs[task.capability] || "·") +
      '</span></div><div class="project-card-body"><div class="project-card-top"><span>' +
      escapeHtml(info.label) +
      " / " +
      escapeHtml(relativeTime(task.created_at)) +
      '</span><span class="project-status"><i style="background:' +
      color +
      '"></i>' +
      escapeHtml(status) +
      '</span></div><h3>' +
      escapeHtml(title) +
      "</h3><p>" +
      escapeHtml(task.prompt || "") +
      '</p><div class="project-card-foot"><span>' +
      escapeHtml(revision) +
      "</span><span>" +
      escapeHtml((task.capability || "website").toUpperCase()) +
      "</span></div></div></a>"
    );
  }

  function renderProjectGrid(container, items) {
    if (!container) return;
    if (!items.length) {
      container.innerHTML = '<div class="empty-state">还没有项目。从一句话开始，生成第一个。</div>';
      return;
    }
    container.innerHTML = items.map((task, index) => projectCardHtml(task, index)).join("");
  }

  async function loadRecent() {
    try {
      const items = await fetchTasks();
      const recent = items.slice(0, 6);
      els.recentCount.textContent = items.length ? recent.length + " / " + items.length + " 个项目" : "还没有项目";
      renderProjectGrid(els.recentGrid, recent);
    } catch (error) {
      console.warn(error);
    }
  }

  function renderProjectStats(items) {
    if (!els.projectStats) return;
    const deployed = items.filter((task) => task.status === "done").length;
    const revisions = items.reduce((sum, task) => sum + (task.revision || 0), 0);
    els.projectStats.innerHTML =
      '<span class="stat-pill"><b>' + items.length + "</b> 个项目</span>" +
      '<span class="stat-pill"><b>' + deployed + "</b> 已部署</span>" +
      '<span class="stat-pill"><b>' + revisions + "</b> 次修改</span>";
  }

  function renderProjectFilters(items) {
    if (!els.projectFilters) return;
    const order = ["game", "website", "image", "video", "resume", "travel", "adapt", "code"];
    const available = order.filter((key) => items.some((task) => task.capability === key));
    const keys = ["all", ...available];
    els.projectFilters.innerHTML = keys
      .map((key) => {
        const count = key === "all" ? items.length : items.filter((task) => task.capability === key).length;
        const label = key === "all" ? "全部" : capInfo(key).label;
        return (
          '<button class="filter-chip ' +
          (state.projectFilter === key ? "active" : "") +
          '" data-filter="' +
          key +
          '" type="button">' +
          escapeHtml(label) +
          " · " +
          count +
          "</button>"
        );
      })
      .join("");
  }

  function renderFilteredProjects() {
    const items = state.projectFilter === "all" ? state.tasks : state.tasks.filter((task) => task.capability === state.projectFilter);
    renderProjectGrid(els.projectsGrid, items);
  }

  async function loadProjects() {
    try {
      await fetchTasks();
      renderProjectStats(state.tasks);
      renderProjectFilters(state.tasks);
      renderFilteredProjects();
    } catch (error) {
      console.warn(error);
      if (els.projectsGrid) els.projectsGrid.innerHTML = '<div class="empty-state">项目加载失败，请刷新重试。</div>';
    }
  }

  function setTaskHeading(task) {
    const info = capInfo(task.capability);
    let label = info.short + " / " + task.id.toUpperCase();
    if (task.revision) label += " / REV " + task.revision;
    els.taskEyebrow.textContent = label;
    els.taskTitle.textContent = task.title || task.prompt || "未命名项目";
  }

  function createTask(prompt) {
    if (!prompt.trim()) {
      els.prompt.focus();
      toast("先写一句你想做的东西");
      return;
    }
    resetWorkspace();
    showWorkspace();
    const selectedCapability =
      state.cap && state.templatePrompt && prompt.trim() === state.templatePrompt.trim() ? state.cap : null;
    api("/api/tasks", {
      method: "POST",
      body: JSON.stringify({ prompt: prompt.trim(), capability: selectedCapability }),
    })
      .then((data) => {
        state.task = data.task;
        state.taskId = data.task.id;
        setTaskHeading(data.task);
        els.promptCard.innerHTML = "<b>YOUR PROMPT</b>" + escapeHtml(prompt.trim());
        els.previewUrl.textContent = data.task.url;
        history.pushState({}, "", "/projects/" + encodeURIComponent(data.task.id));
        openStream(data.task.id);
        loadRecent();
      })
      .catch((error) => {
        setStatus("error", "FAILED");
        setRunning(false);
        setConn("error", "OFFLINE");
        addTimeline({ type: "error", title: "REQUEST FAILED", summary: error.message, time: formatTime(new Date()) });
        toast("任务创建失败：" + error.message);
      });
  }

  function openStream(taskId) {
    closeStream();
    state.streamClosed = false;
    const source = new EventSource("/api/tasks/" + encodeURIComponent(taskId) + "/events?after=" + state.lastSeq);
    state.es = source;
    source.onopen = () => {
      setConn("live", "STREAMING");
      if (state.reconnectTimer) {
        clearTimeout(state.reconnectTimer);
        state.reconnectTimer = null;
      }
    };
    source.onmessage = (event) => {
      let payload;
      try {
        payload = JSON.parse(event.data);
      } catch (_) {
        return;
      }
      if (!payload || typeof payload.seq !== "number" || payload.seq <= state.lastSeq) return;
      state.lastSeq = payload.seq;
      state.events.push(payload);
      handleEvent(payload, { animate: true });
    };
    source.onerror = () => {
      if (!state.running || state.streamClosed) return;
      setConn("error", "RECONNECTING");
      fetch("/api/auth/me")
        .then((response) => {
          if (response.status === 401) {
            location.replace("/login?next=" + encodeURIComponent(location.pathname + location.search));
          }
        })
        .catch(() => {});
      source.close();
      state.es = null;
      if (state.reconnectTimer) return;
      state.reconnectTimer = setTimeout(() => {
        state.reconnectTimer = null;
        if (state.running && state.taskId) openStream(state.taskId);
      }, 1600);
    };
  }

  function closeStream() {
    state.streamClosed = true;
    if (state.es) {
      state.es.close();
      state.es = null;
    }
    if (state.reconnectTimer) {
      clearTimeout(state.reconnectTimer);
      state.reconnectTimer = null;
    }
  }

  async function loadTask(taskId, push = false) {
    resetWorkspace();
    showWorkspace();
    try {
      const data = await api("/api/tasks/" + encodeURIComponent(taskId));
      state.task = data.task;
      state.taskId = data.task.id;
      state.events = data.events || [];
      state.lastSeq = state.events.length ? state.events[state.events.length - 1].seq : 0;
      els.promptCard.innerHTML = "<b>YOUR PROMPT</b>" + escapeHtml(data.task.prompt || "");
      setTaskHeading(data.task);
      els.previewUrl.textContent = data.task.url;
      setRefineState(
        !["queued", "running", "deploying"].includes(data.task.status),
        ["queued", "running", "deploying"].includes(data.task.status) ? "Agent 正在运行…" : "基于当前成果继续修改"
      );
      if (state.events.length) {
        replayEvents(state.events, 0, false);
      }
      if (["queued", "running", "deploying"].includes(data.task.status)) {
        setRunning(true);
        setStatus("running", "RUNNING");
        openStream(data.task.id);
      } else {
        const isError = data.task.status === "error";
        const isInterrupted = data.task.status === "interrupted";
        setRunning(false);
        setStatus(isError || isInterrupted ? "error" : "done", isInterrupted ? "INTERRUPTED" : isError ? "FAILED" : "DEPLOYED");
        setConn(isInterrupted ? "error" : "", isInterrupted ? "INTERRUPTED" : "LOCAL");
      }
      const projectPath = "/projects/" + encodeURIComponent(data.task.id);
      if (location.pathname !== projectPath) history.replaceState({}, "", projectPath);
    } catch (error) {
      goHome();
      toast("加载任务失败：" + error.message);
    }
  }

  function handleEvent(event, options = {}) {
    const animate = options.animate !== false && !options.replay;
    const replay = Boolean(options.replay);
    const time = formatTime(event.ts || new Date().toISOString());
    switch (event.type) {
      case "task_started": {
        els.taskEyebrow.textContent = (event.label || event.capability || "agent").toUpperCase() + " / " + (state.taskId || "");
        els.taskTitle.textContent = event.label ? event.label + " · 正在生成" : "正在理解你的想法…";
        els.flowTitle.textContent = "正在拆解任务";
        setStatus("running", "PLANNING");
        setRunning(true);
        addTimeline({
          type: "thought",
          title: "TASK ACCEPTED",
          summary: "已理解你的描述，正在把它拆成可执行的设计与工程步骤。",
          time,
          animate,
        });
        break;
      }
      case "intent": {
        els.stageMeta.textContent = (event.label || "").toUpperCase() + " / LIVE PREVIEW";
        addTimeline({
          type: "thought",
          title: "INTENT / " + (event.label || ""),
          summary: event.description || "已识别能力类型。",
          time,
          animate,
        });
        break;
      }
      case "plan": {
        state.steps = Array.isArray(event.steps) ? event.steps : [];
        state.planStatus = state.steps.map(() => "pending");
        renderPlan();
        els.flowTitle.textContent = (event.label || "Agent") + " · " + state.steps.length + " 个步骤";
        setStatus("running", "RUNNING");
        addTimeline({
          type: "thought",
          title: "PLAN READY",
          summary: state.steps.map((step, index) => "0" + (index + 1) + " " + step).join("  ·  "),
          time,
          animate,
        });
        break;
      }
      case "step_started": {
        if (typeof event.index === "number") {
          updatePlan(event.index, "active");
          setStatus("running", "STEP 0" + (event.index + 1));
          addTimeline({
            type: "step",
            title: "STEP 0" + (event.index + 1),
            summary: event.title || "",
            time,
            animate,
          });
          els.flowTitle.textContent = event.title || els.flowTitle.textContent;
          state.stepCards.set(event.index, state.lastItem);
          terminal("▸ step " + (event.index + 1) + " · " + (event.title || ""), "");
        }
        break;
      }
      case "step_done": {
        if (typeof event.index === "number") {
          updatePlan(event.index, "done");
          const card = state.stepCards.get(event.index);
          if (card) appendChip(card, event.summary || "DONE", "tl-verify");
        }
        break;
      }
      case "thinking": {
        const item = addTimeline({
          type: "thought",
          title: "THINKING",
          summary: event.summary || "",
          time,
          animate,
        });
        if (event.detail) {
          const detail = document.createElement("div");
          detail.className = "tl-summary";
          detail.style.marginTop = "4px";
          detail.style.color = "var(--muted-2)";
          detail.textContent = event.detail;
          item.appendChild(detail);
        }
        if (event.source) {
          const sourceLabel =
            event.source === "llm"
              ? "LLM DIRECTOR"
              : event.source === "media" || event.source === "media-edit"
                ? "MEDIA RENDER"
                : "LOCAL DIRECTOR";
          appendChip(item, sourceLabel, "tl-verify");
        }
        break;
      }
      case "tool_call": {
        const label = (event.name || "tool") + " · " + (event.summary || "");
        appendChip(state.lastItem, label, "tl-tool");
        terminal("$ " + (event.name || "tool") + " " + JSON.stringify(event.args || {}), "");
        els.termStatus.textContent = "RUNNING";
        break;
      }
      case "tool_result": {
        terminal("✓ " + (event.summary || event.name || "done"), event.ok === false ? "err" : "ok");
        if (event.name === "python_execute") els.termStatus.textContent = event.ok ? "OK" : "FAILED";
        break;
      }
      case "file_diff": {
        const path = event.path || "index.html";
        const before = event.before || "";
        const after = event.after || "";
        state.files.set(path, { content: after, language: event.language || "text" });
        state.diffs.set(path, {
          before,
          after,
          language: event.language || "text",
          created: Boolean(event.created),
          reason: event.reason || "",
          stats: event.stats || {},
        });
        renderFileTree();
        if (!state.userPickedFile) {
          state.selectedFile = state.files.has("index.html") ? "index.html" : path;
          renderDiff(state.selectedFile, animate);
        } else if (state.selectedFile === path) {
          renderDiff(path, animate);
        }
        const added = countLines(after) - countLines(before);
        addTimeline({
          type: "file",
          title: "FILE / " + path,
          summary: (event.created ? "创建 " : "更新 ") + path + " · " + (added >= 0 ? "+" + added : added) + " 行" + (event.reason ? " · " + event.reason : ""),
          time,
          animate,
        });
        terminal("✓ " + path + " · " + (event.created ? "created" : "updated") + " (" + countLines(after) + " lines)", "ok");
        els.termStatus.textContent = "WROTE";
        break;
      }
      case "preview_ready": {
        setPreview(event.url || (state.task && state.task.url));
        els.outcomeTitle.textContent = event.title || "页面已可预览";
        els.outcomeText.textContent = "代码已经写入，Agent 正在做最后的自检。";
        break;
      }
      case "asset_created": {
        addTimeline({
          type: "file",
          title: "ASSET / " + (event.path || ""),
          summary: (event.summary || "媒体素材已保存") + " · " + Math.round((event.bytes || 0) / 1024) + " KB",
          time,
          animate,
        });
        terminal("✓ asset " + (event.path || "") + " · " + (event.mime || ""), "ok");
        break;
      }
      case "media_progress": {
        setStatus("running", event.status || "RENDERING");
        els.flowTitle.textContent = event.message || "正在生成媒体素材";
        if (event.message) {
          addTimeline({
            type: "thought",
            title: "MEDIA / " + (event.status || "PROGRESS"),
            summary: event.message,
            time,
            animate,
          });
        }
        terminal("◆ " + (event.message || "media progress"), "");
        break;
      }
      case "verify": {
        upsertCheck(event.name || "check", Boolean(event.ok), event.detail || "");
        renderChecks();
        const item = addTimeline({
          type: event.ok ? "verify-ok" : "error",
          title: "VERIFY / " + (event.name || ""),
          summary: (event.ok ? "通过" : "未通过") + (event.detail ? " · " + event.detail : ""),
          time,
          animate,
        });
        appendChip(item, event.ok ? "PASS" : "FAIL", "tl-verify" + (event.ok ? "" : " fail"));
        terminal((event.ok ? "✓ " : "✗ ") + (event.name || "check") + " · " + (event.detail || ""), event.ok ? "ok" : "err");
        break;
      }
      case "deployed": {
        setPreview(event.url || (state.task && state.task.url));
        els.browserTag.textContent = "LIVE";
        els.outcomeTitle.textContent = event.title || (state.task && state.task.title) || "已上线";
        els.outcomeText.textContent = "已部署到本地 Agent Server，页面可直接交互。";
        addTimeline({
          type: "deploy",
          title: "DEPLOYED",
          summary: "已发布到 " + (event.url || "本地静态路由"),
          time,
          animate,
        });
        terminal("✔ deployed → " + (event.url || ""), "ok");
        setStatus("running", "VERIFYING");
        break;
      }
      case "done": {
        const isRefine = event.source === "llm-edit" || event.source === "media-edit";
        const refineFailed = event.source === "refine-failed";
        setRunning(false);
        setStatus("done", refineFailed ? "UNCHANGED" : "DEPLOYED");
        setConn("", "LOCAL");
        if (state.task) {
          state.task.revision = event.revision || state.task.revision;
          state.task.status = "done";
          if (event.title) state.task.title = event.title;
          setTaskHeading(state.task);
        }
        els.flowTitle.textContent = refineFailed ? "修改未应用" : isRefine ? "修改完成" : "交付完成";
        els.agentOrb.className = "agent-orb done";
        els.outcomeTitle.textContent = event.title || (state.task && state.task.title) || "已完成";
        els.outcomeText.textContent = event.summary || "页面已完成并通过自检。";
        setRefineState(true, refineFailed ? "修改未应用，可以再试" : "基于当前成果继续修改");
        if (Array.isArray(event.checks)) {
          event.checks.forEach((check) => upsertCheck(check.name, check.ok, check.detail));
          renderChecks();
        }
        addTimeline({
          type: "done",
          title: refineFailed ? "UNCHANGED" : "COMPLETE",
          summary: event.summary || "任务完成。",
          time,
          animate,
        });
        terminal("● task complete · " + (event.url || ""), "ok");
        els.termStatus.textContent = "DONE";
        closeStream();
        if (!replay) {
          loadRecent();
          toast(refineFailed ? "修改未应用，原页面保持不变" : isRefine ? "修改已应用并重新部署" : "生成完成，已部署到本地");
        }
        break;
      }
      case "refine_started": {
        setRunning(true);
        setStatus("running", "REFINING");
        setRefineState(false, "Agent 正在修改…");
        els.flowTitle.textContent = "根据对话修改";
        addTimeline({
          type: "step",
          title: "YOUR EDIT",
          summary: event.instruction || "",
          time,
          animate,
        });
        terminal("$ refine · " + (event.instruction || ""), "");
        break;
      }
      case "refine_failed": {
        setRunning(false);
        setStatus("done", "UNCHANGED");
        setRefineState(true, "修改未应用，可以再试");
        addTimeline({
          type: "error",
          title: "EDIT NOT APPLIED",
          summary: event.message || "修改未应用，原页面保持不变。",
          time,
          animate,
        });
        terminal("✗ " + (event.message || "refine failed"), "err");
        break;
      }
      case "interrupted": {
        setRunning(false);
        setStatus("error", "INTERRUPTED");
        setConn("error", "INTERRUPTED");
        closeStream();
        els.flowTitle.textContent = "任务已中断";
        setRefineState(Boolean(state.taskId), "可以继续尝试修改");
        addTimeline({
          type: "error",
          title: "INTERRUPTED",
          summary: event.message || "任务在服务重启前中断，原产物已保留。",
          time,
          animate,
        });
        terminal("! " + (event.message || "task interrupted"), "err");
        break;
      }
      case "error": {
        setRunning(false);
        setStatus("error", "FAILED");
        setConn("error", "ERROR");
        els.agentOrb.className = "agent-orb";
        addTimeline({
          type: "error",
          title: "ERROR",
          summary: event.message || "生成中断",
          time,
          animate,
        });
        terminal("✗ " + (event.message || "error"), "err");
        els.termStatus.textContent = "ERROR";
        closeStream();
        if (!replay) toast(event.message || "生成中断");
        break;
      }
      default:
        break;
    }
    if (event.type === "task_started" && state.task) {
      els.taskTitle.textContent = state.task.title || state.task.prompt || "正在生成";
    }
  }

  function upsertCheck(name, ok, detail) {
    const existing = state.checks.find((check) => check.name === name);
    if (existing) {
      existing.ok = ok;
      existing.detail = detail;
    } else {
      state.checks.push({ name, ok, detail });
    }
  }

  function renderChecks() {
    if (!state.checks.length) return;
    els.outcomeChecks.innerHTML = state.checks
      .map(
        (check) =>
          '<span class="check-item ' +
          (check.ok ? "" : "fail") +
          '" title="' +
          escapeHtml(check.detail || "") +
          '"><i></i>' +
          escapeHtml(check.name) +
          "</span>"
      )
      .join("");
  }

  function countLines(text) {
    return String(text || "").split("\n").length;
  }

  function renderFileTree() {
    const paths = Array.from(state.files.keys()).sort((a, b) => {
      if (a === "index.html") return -1;
      if (b === "index.html") return 1;
      return a.localeCompare(b);
    });
    els.fileCount.textContent = String(paths.length);
    if (!paths.length) {
      els.fileTree.innerHTML = '<div class="empty-state small">等待 Agent 写入文件…</div>';
      return;
    }
    els.fileTree.innerHTML = paths
      .map((path) => {
        const diff = state.diffs.get(path);
        let badge = "";
        if (diff) {
          const before = countLines(diff.before);
          const after = countLines(diff.after);
          const delta = after - before;
          if (delta > 0) badge = "+" + delta;
        }
        return (
          '<button class="file-row ' +
          (path === state.selectedFile ? "active" : "") +
          '" type="button" data-file="' +
          escapeHtml(path) +
          '"><span class="file-icon">' +
          escapeHtml(fileExt(path)) +
          "</span><span>" +
          escapeHtml(path) +
          '</span><span class="file-badge">' +
          escapeHtml(badge) +
          "</span></button>"
        );
      })
      .join("");
  }

  function fileExt(path) {
    const ext = path.split(".").pop().toLowerCase();
    return { html: "<>", py: "PY", json: "{}", md: "MD", css: "#", js: "JS" }[ext] || "·";
  }

  function computeDiff(before, after) {
    const a = String(before || "").split("\n");
    const b = String(after || "").split("\n");
    if (!before) return b.map((line, index) => ({ type: "add", line, newNo: index + 1 }));
    if (!after) return a.map((line, index) => ({ type: "del", line, oldNo: index + 1 }));
    if (a.length * b.length > 260000) {
      return [
        ...a.map((line, index) => ({ type: "del", line, oldNo: index + 1 })),
        ...b.map((line, index) => ({ type: "add", line, newNo: index + 1 })),
      ];
    }
    const dp = Array.from({ length: a.length + 1 }, () => new Uint16Array(b.length + 1));
    for (let i = a.length - 1; i >= 0; i -= 1) {
      for (let j = b.length - 1; j >= 0; j -= 1) {
        dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
      }
    }
    const ops = [];
    let i = 0;
    let j = 0;
    while (i < a.length && j < b.length) {
      if (a[i] === b[j]) {
        ops.push({ type: "same", line: a[i], oldNo: i + 1, newNo: j + 1 });
        i += 1;
        j += 1;
      } else if (dp[i + 1][j] >= dp[i][j + 1]) {
        ops.push({ type: "del", line: a[i], oldNo: i + 1 });
        i += 1;
      } else {
        ops.push({ type: "add", line: b[j], newNo: j + 1 });
        j += 1;
      }
    }
    while (i < a.length) ops.push({ type: "del", line: a[i], oldNo: i + 1 }), (i += 1);
    while (j < b.length) ops.push({ type: "add", line: b[j], newNo: j + 1 }), (j += 1);
    return ops;
  }

  function renderDiff(path, animate = false) {
    const diff = state.diffs.get(path);
    if (!diff) {
      const file = state.files.get(path);
      if (!file) return;
      state.diffs.set(path, { before: "", after: file.content, language: file.language, created: true });
    }
    const data = state.diffs.get(path);
    const ops = computeDiff(data.before, data.after);
    const additions = ops.filter((op) => op.type === "add").length;
    const deletions = ops.filter((op) => op.type === "del").length;
    els.diffPath.textContent = path;
    els.diffLanguage.textContent = String(data.language || "text").toUpperCase();
    els.diffStats.textContent = "+" + additions + " −" + deletions;
    let oldNo = 1;
    let newNo = 1;
    els.diffView.innerHTML = ops
      .map((op, index) => {
        let ln = "";
        if (op.type === "add") {
          ln = String(op.newNo || newNo++);
        } else if (op.type === "del") {
          ln = String(op.oldNo || oldNo++);
        } else {
          ln = String(op.oldNo || oldNo++);
          newNo = (op.newNo || newNo) + 1;
        }
        const delay = animate ? Math.min(900, index * 3) : 0;
        return (
          '<div class="diff-line ' +
          op.type +
          '" style="animation-delay:' +
          delay +
          'ms"><span class="ln">' +
          ln +
          '</span><span class="sign">' +
          (op.type === "add" ? "+" : op.type === "del" ? "−" : " ") +
          '</span><span class="code">' +
          (escapeHtml(op.line) || " ") +
          "</span></div>"
        );
      })
      .join("");
    if (animate) {
      requestAnimationFrame(() => {
        els.diffView.scrollTop = Math.max(0, els.diffView.scrollHeight - els.diffView.clientHeight);
      });
    } else {
      els.diffView.scrollTop = 0;
    }
  }

  function setPreview(url) {
    if (!url) return;
    state.previewUrl = url;
    const bust = url + (url.includes("?") ? "&" : "?") + "v=" + Date.now();
    els.previewFrame.onload = () => {
      els.previewLoading.classList.add("hide");
      els.browserTag.textContent = "LIVE";
      els.miniState.textContent = "LIVE";
    };
    els.previewFrame.src = bust;
    els.miniFrame.src = bust;
    els.previewUrl.textContent = url;
    els.previewLoading.classList.remove("hide");
  }

  function renderOutcomeIdle() {
    if (!state.checks.length) {
      els.outcomeChecks.innerHTML = '<div class="check-skeleton"></div><div class="check-skeleton"></div><div class="check-skeleton"></div>';
    }
  }

  function replayEvents(events, delay = 220, animate = true) {
    clearTypeTimers();
    els.timeline.innerHTML = "";
    els.planSteps.innerHTML = "";
    state.planStatus = [];
    state.files.clear();
    state.diffs.clear();
    state.selectedFile = null;
    state.userPickedFile = false;
    state.checks = [];
    state.lastItem = null;
    state.stepCards.clear();
    els.fileTree.innerHTML = '<div class="empty-state small">等待 Agent 写入文件…</div>';
    els.fileCount.textContent = "0";
    els.terminal.innerHTML = '<div class="term-line muted">$ vibeforge agent --wait</div>';
    renderOutcomeIdle();
    state.replaying = true;
    events.forEach((event, index) => {
      setTimeout(() => {
        handleEvent(event, { animate, replay: true });
        if (index === events.length - 1) {
          state.replaying = false;
          const last = events[events.length - 1];
          if (last.type === "done") {
            setRunning(false);
            setStatus("done", "DEPLOYED");
            setConn("", "LOCAL");
          } else if (last.type === "error") {
            setRunning(false);
            setStatus("error", "FAILED");
          }
        }
      }, index * delay);
    });
  }

  function replayTimeline() {
    if (!state.events.length) {
      toast("还没有可回放的事件");
      return;
    }
    if (state.running) {
      toast("任务运行中，完成后可以重播");
      return;
    }
    const events = state.events.slice();
    replayEvents(events, 260, true);
    toast("正在回放 Agent 过程");
  }

  async function refineTask() {
    if (!state.taskId) return toast("还没有可修改的项目");
    if (state.running) return toast("Agent 正在处理，请稍候");
    const instruction = els.refineInput.value.trim();
    if (!instruction) {
      els.refineInput.focus();
      return;
    }
    els.refineInput.value = "";
    state.running = true;
    setRunning(true);
    setStatus("running", "REFINING");
    setRefineState(false, "正在提交修改…");
    try {
      await api("/api/tasks/" + encodeURIComponent(state.taskId) + "/refine", {
        method: "POST",
        body: JSON.stringify({ instruction }),
      });
      openStream(state.taskId);
    } catch (error) {
      state.running = false;
      setRunning(false);
      setStatus("done", "UNCHANGED");
      setRefineState(true, "修改请求失败，可以重试");
      addTimeline({
        type: "error",
        title: "EDIT FAILED",
        summary: error.message || "修改请求失败",
        time: formatTime(new Date().toISOString()),
      });
      terminal("✗ " + (error.message || "refine request failed"), "err");
      toast("修改失败：" + error.message);
    }
  }

  async function deployTask() {
    if (!state.taskId) return;
    els.deployBtn.disabled = true;
    try {
      const data = await api("/api/tasks/" + encodeURIComponent(state.taskId) + "/deploy", { method: "POST" });
      setPreview(data.url);
      setStatus("done", "DEPLOYED");
      toast("已重新部署：" + data.url);
    } catch (error) {
      toast("部署失败：" + error.message);
    } finally {
      els.deployBtn.disabled = false;
    }
  }

  function openNewWindow() {
    if (state.previewUrl) window.open(state.previewUrl, "_blank", "noopener");
    else toast("还没有可打开的页面");
  }

  async function copyCurrentCode() {
    if (!state.selectedFile) {
      toast("还没有可复制的文件");
      return;
    }
    const file = state.files.get(state.selectedFile);
    if (!file) return;
    try {
      await navigator.clipboard.writeText(file.content);
      toast("已复制 " + state.selectedFile);
    } catch (_) {
      toast("复制失败，请在新窗口查看");
    }
  }

  function bind() {
    els.composer.addEventListener("submit", (event) => {
      event.preventDefault();
      createTask(els.prompt.value);
    });
    els.prompt.addEventListener("keydown", (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
        event.preventDefault();
        createTask(els.prompt.value);
      }
    });
    els.capPicker.addEventListener("click", (event) => {
      const chip = event.target.closest("[data-cap]");
      if (!chip) return;
      const cap = state.caps.find((item) => item.key === chip.dataset.cap);
      if (cap) applyTemplate(cap);
    });
    els.prompt.addEventListener("input", updateTemplateNote);
    els.refineForm.addEventListener("submit", (event) => {
      event.preventDefault();
      refineTask();
    });
    els.recentGrid.addEventListener("click", (event) => {
      const card = event.target.closest("[data-task]");
      if (card) loadTask(card.dataset.task, true);
    });
    $$(".mode-btn").forEach((btn) => btn.addEventListener("click", () => setMode(btn.dataset.mode)));
    els.newTaskBtn.addEventListener("click", () => goHome());
    els.logoutBtn.addEventListener("click", async () => {
      try {
        await fetch("/api/auth/logout", { method: "POST" });
      } finally {
        location.replace("/login");
      }
    });
    els.brandHome.addEventListener("click", (event) => {
      event.preventDefault();
      goHome();
    });
    els.homeLink.addEventListener("click", (event) => {
      event.preventDefault();
      goHome();
    });
    els.projectsLink.addEventListener("click", (event) => {
      event.preventDefault();
      goProjects();
    });
    els.allProjectsLink.addEventListener("click", (event) => {
      event.preventDefault();
      goProjects();
    });
    els.projectsNewBtn.addEventListener("click", () => goHome());
    els.backBtn.addEventListener("click", () => goProjects());
    els.deployBtn.addEventListener("click", deployTask);
    els.downloadBtn.addEventListener("click", () => {
      if (!state.taskId) return toast("还没有可导出的项目");
      window.location.href = "/api/tasks/" + encodeURIComponent(state.taskId) + "/bundle";
    });
    els.openNewBtn.addEventListener("click", openNewWindow);
    els.replayBtn.addEventListener("click", replayTimeline);
    els.copyCodeBtn.addEventListener("click", copyCurrentCode);
    document.addEventListener("click", (event) => {
      const project = event.target.closest("[data-project-id]");
      if (project) {
        event.preventDefault();
        openProject(project.dataset.projectId);
        return;
      }
      const file = event.target.closest("[data-file]");
      if (file) {
        state.selectedFile = file.dataset.file;
        state.userPickedFile = true;
        renderFileTree();
        renderDiff(state.selectedFile, true);
      }
    });
    els.projectFilters.addEventListener("click", (event) => {
      const chip = event.target.closest("[data-filter]");
      if (!chip) return;
      state.projectFilter = chip.dataset.filter;
      renderProjectFilters(state.tasks);
      renderFilteredProjects();
    });
    els.terminal.addEventListener("click", () => {});
    window.addEventListener("popstate", () => {
      const path = decodeURIComponent(location.pathname);
      if (path.startsWith("/projects/")) {
        const id = path.slice("/projects/".length);
        if (id) loadTask(id);
        else goProjects(false);
      } else if (path === "/projects") {
        goProjects(false);
      } else {
        goHome(false);
      }
    });
    window.addEventListener("beforeunload", closeStream);
  }

  async function init() {
    bind();
    setMode(state.mode, false);
    await loadCapabilities();
    await loadRecent();
    const path = decodeURIComponent(location.pathname);
    const legacyTaskId = new URLSearchParams(location.search).get("task");
    if (path.startsWith("/projects/")) {
      const id = path.slice("/projects/".length);
      if (id) loadTask(id);
      else setView("projects"), loadProjects();
    } else if (path === "/projects") {
      setView("projects");
      loadProjects();
    } else if (legacyTaskId && legacyTaskId !== "creating") {
      history.replaceState({}, "", "/projects/" + encodeURIComponent(legacyTaskId));
      loadTask(legacyTaskId);
    } else {
      setView("home");
      setTimeout(() => els.prompt.focus(), 300);
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
