const state = {
  user: null,
  token: localStorage.getItem("uc_token"),
  config: null,
  defaults: null,
  section: "dashboard",
  modpacks: [],
  mods: [],
  theme: "glass",
};

const sections = {
  dashboard: renderDashboard,
  modpacks: renderModpacks,
  mods: renderMods,
  console: renderConsole,
  profile: renderProfile,
  publish: renderPublish,
  installer: renderInstaller,
  admin: renderAdmin,
};

function api(path, options = {}) {
  const headers = options.headers || {};
  if (state.token) {
    headers.Authorization = `Bearer ${state.token}`;
  }
  return fetch(path, { ...options, headers })
    .then(async (res) => {
      const data = await res.json();
      if (!res.ok || !data.ok) {
        throw new Error(data.error || "Request failed");
      }
      return data;
    });
}

function showToast(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.remove("hidden");
  setTimeout(() => toast.classList.add("hidden"), 2500);
}

function setSection(section) {
  state.section = section;
  document.getElementById("sectionTitle").textContent = sectionLabel(section);
  document.getElementById("sectionSubtitle").textContent = sectionSubtitle(section);
  sections[section]();
}

function sectionLabel(section) {
  const labels = {
    dashboard: "Dashboard",
    modpacks: "Modpacks",
    mods: "Mods",
    console: "Console",
    profile: "Profile Settings",
    publish: "Publish Mods",
    installer: "Installer / Paths",
    admin: "Admin",
  };
  return labels[section] || "Dashboard";
}

function sectionSubtitle(section) {
  const subtitles = {
    dashboard: "Overview",
    modpacks: "Profiles",
    mods: "Modrinth",
    console: "Logs",
    profile: "Profile",
    publish: "Workspace",
    installer: "Paths",
    admin: "Management",
  };
  return subtitles[section] || "";
}

function renderCard(html) {
  const card = document.createElement("div");
  card.className = "card";
  card.innerHTML = html;
  return card;
}

function renderDashboard() {
  const container = document.getElementById("sectionContent");
  container.innerHTML = "";
  const summary = renderCard(`
    <h3>Welcome ${state.user ? state.user.username : ""}</h3>
    <p>Installed modpacks: ${state.modpacks.length}</p>
  `);
  container.appendChild(summary);
}

async function renderModpacks() {
  const container = document.getElementById("sectionContent");
  container.innerHTML = "";
  await loadModpacks();
  const list = state.modpacks.map((pack) => `
    <tr>
      <td>${pack.name}</td>
      <td>${pack.loader}</td>
      <td>${pack.mc_version}</td>
      <td>${pack.mod_count}</td>
      <td><button class="ghost-button" data-pack="${pack.id}">Details</button></td>
    </tr>
  `).join("");
  container.appendChild(renderCard(`
    <div class="row">
      <h3>Modpacks</h3>
    </div>
    <table class="table">
      <thead>
        <tr><th>Name</th><th>Loader</th><th>MC</th><th>Mods</th><th></th></tr>
      </thead>
      <tbody>
        ${list || "<tr><td colspan=\"5\">No modpacks found.</td></tr>"}
      </tbody>
    </table>
  `));
  container.appendChild(renderCreatePack());
  container.querySelectorAll("button[data-pack]").forEach((btn) => {
    btn.addEventListener("click", () => openModpackDetail(btn.dataset.pack));
  });
}

function renderCreatePack() {
  const card = renderCard(`
    <h3>Create Modpack</h3>
    <div class="modal-body">
      <input id="packName" type="text" placeholder="Name" />
      <input id="packLoader" type="text" placeholder="Loader (Fabric, Forge)" />
      <input id="packVersion" type="text" placeholder="MC Version" />
      <button id="packCreate" class="primary-button">Create</button>
    </div>
  `);
  card.querySelector("#packCreate").addEventListener("click", async () => {
    const name = document.getElementById("packName").value.trim();
    const loader = document.getElementById("packLoader").value.trim();
    const mcVersion = document.getElementById("packVersion").value.trim();
    try {
      await api("/api/modpacks/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, loader, mc_version: mcVersion }),
      });
      showToast("Modpack created");
      renderModpacks();
    } catch (err) {
      showToast(err.message);
    }
  });
  return card;
}

async function openModpackDetail(packId) {
  const container = document.getElementById("sectionContent");
  container.innerHTML = "";
  try {
    const data = await api(`/api/modpacks/${packId}`);
    const rows = data.mods.map((mod) => `
      <tr>
        <td>${mod.name}</td>
        <td>${mod.filename}</td>
        <td>${(mod.size / 1024 / 1024).toFixed(2)} MB</td>
        <td>${mod.modrinth ? "Modrinth" : "Local"}</td>
      </tr>
    `).join("");
    container.appendChild(renderCard(`
      <h3>Mods</h3>
      <table class="table">
        <thead><tr><th>Name</th><th>File</th><th>Size</th><th>Source</th></tr></thead>
        <tbody>${rows || "<tr><td colspan=\"4\">No mods installed.</td></tr>"}</tbody>
      </table>
      <button class="ghost-button" id="launchPack">Launch</button>
    `));
    container.querySelector("#launchPack").addEventListener("click", async () => {
      const result = await api(`/api/modpacks/${packId}/launch`, { method: "POST" });
      if (!result.launched && result.url) {
        window.open(result.url, "_blank");
      }
      showToast(result.launched ? "Launching Modrinth" : "Opening Modrinth site");
    });
  } catch (err) {
    showToast(err.message);
  }
}

async function renderMods() {
  const container = document.getElementById("sectionContent");
  container.innerHTML = "";
  const card = renderCard(`
    <h3>Browse Modrinth</h3>
    <input id="modQuery" type="text" placeholder="Search" />
    <input id="modLoader" type="text" placeholder="Loader" />
    <input id="modVersion" type="text" placeholder="MC Version" />
    <button id="modSearch" class="primary-button">Search</button>
    <div id="modResults" class="mod-results"></div>
  `);
  container.appendChild(card);
  card.querySelector("#modSearch").addEventListener("click", async () => {
    const q = card.querySelector("#modQuery").value.trim();
    const loader = card.querySelector("#modLoader").value.trim();
    const version = card.querySelector("#modVersion").value.trim();
    try {
      const data = await api(`/api/mods/search?q=${encodeURIComponent(q)}&loader=${encodeURIComponent(loader)}&version=${encodeURIComponent(version)}`);
      state.mods = data.results;
      renderModResults();
    } catch (err) {
      showToast(err.message);
    }
  });
}

function renderModResults() {
  const results = document.getElementById("modResults");
  results.innerHTML = state.mods.map((mod) => `
    <div class="card">
      <h4>${mod.title}</h4>
      <p>${mod.description || ""}</p>
      <span class="badge">${mod.project_id}</span>
    </div>
  `).join("") || "<p>No results.</p>";
}

async function renderConsole() {
  const container = document.getElementById("sectionContent");
  container.innerHTML = "";
  try {
    const data = await api("/api/logs");
    const lines = data.logs.map((log) => `<div>[${log.level}] ${log.message}</div>`).join("");
    container.appendChild(renderCard(`<h3>Logs</h3><div class="log-stream">${lines}</div>`));
  } catch (err) {
    showToast(err.message);
  }
}

function renderProfile() {
  const container = document.getElementById("sectionContent");
  container.innerHTML = "";
  const card = renderCard(`
    <h3>Profile</h3>
    <p>Username: ${state.user.username}</p>
    <p>Role: ${state.user.role}</p>
    <textarea id="profileDescription" rows="4" placeholder="Description">${state.user.profile_description || ""}</textarea>
    <button id="profileSave" class="primary-button">Save</button>
  `);
  container.appendChild(card);
  card.querySelector("#profileSave").addEventListener("click", async () => {
    const description = document.getElementById("profileDescription").value.trim();
    try {
      await api("/api/profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description }),
      });
      showToast("Profile updated");
    } catch (err) {
      showToast(err.message);
    }
  });
}

function renderPublish() {
  const container = document.getElementById("sectionContent");
  container.innerHTML = "";
  container.appendChild(renderCard(`
    <h3>Publish Workspace</h3>
    <p>Token required in settings.</p>
    <button class="ghost-button">Open Exports</button>
  `));
}

function renderInstaller() {
  const container = document.getElementById("sectionContent");
  container.innerHTML = "";
  const config = state.config || {};
  container.appendChild(renderCard(`
    <h3>Paths</h3>
    <p>App Path: ${config.app_path || ""}</p>
    <p>Profiles Path: ${config.profiles_path || ""}</p>
    <button id="openWizard" class="ghost-button">Open Wizard</button>
  `));
  container.querySelector("#openWizard").addEventListener("click", () => {
    document.getElementById("wizard").classList.remove("hidden");
  });
}

async function renderAdmin() {
  const container = document.getElementById("sectionContent");
  container.innerHTML = "";
  const data = await api("/api/admin/users");
  const rows = data.users.map((user) => `
    <tr>
      <td>${user.username}</td>
      <td>${user.email}</td>
      <td>${user.role}</td>
      <td>${user.is_active ? "Active" : "Blocked"}</td>
    </tr>
  `).join("");
  container.appendChild(renderCard(`
    <h3>User Management</h3>
    <table class="table">
      <thead><tr><th>User</th><th>Email</th><th>Role</th><th>Status</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
  `));
}

async function loadModpacks() {
  try {
    const data = await api("/api/modpacks");
    state.modpacks = data.modpacks;
  } catch (err) {
    showToast(err.message);
  }
}

async function init() {
  try {
    const configResponse = await api("/api/config");
    state.config = configResponse.config;
    state.defaults = configResponse.defaults;
    if (!configResponse.installed) {
      document.getElementById("wizard").classList.remove("hidden");
      document.getElementById("app").classList.add("hidden");
      return;
    } else {
      document.getElementById("app").classList.remove("hidden");
    }
  } catch (err) {
    showToast(err.message);
  }

  if (state.token) {
    try {
      const data = await api("/api/session");
      state.user = data.user;
      updateUserChip();
      if (["ADMIN", "MANAGER", "OWNER"].includes(state.user.role)) {
        document.getElementById("adminNav").classList.remove("hidden");
      }
      await loadModpacks();
    } catch (err) {
      state.token = null;
      localStorage.removeItem("uc_token");
    }
  }

  if (!state.user) {
    document.getElementById("auth").classList.remove("hidden");
  }

  setSection("dashboard");
}

function updateUserChip() {
  const chip = document.getElementById("userChip");
  if (state.user) {
    chip.textContent = `${state.user.username} · ${state.config?.minecraft_name || ""}`;
  }
}

function bindEvents() {
  document.querySelectorAll(".sidebar-nav button").forEach((button) => {
    button.addEventListener("click", () => setSection(button.dataset.section));
  });

  document.getElementById("toggleSidebar").addEventListener("click", () => {
    document.getElementById("sidebar").classList.toggle("collapsed");
  });

  document.getElementById("themeToggle").addEventListener("click", async () => {
    state.theme = state.theme === "glass" ? "dark" : "glass";
    document.body.dataset.theme = state.theme;
    await api("/api/settings/theme", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ theme: state.theme }),
    });
  });

  document.getElementById("wizardAutodetect").addEventListener("click", () => {
    const defaults = state.defaults || {};
    document.getElementById("wizardAppPath").value = defaults.app_path || "";
    document.getElementById("wizardProfilesPath").value = defaults.profiles_path || "";
  });

  document.getElementById("wizardSubmit").addEventListener("click", async () => {
    const appPath = document.getElementById("wizardAppPath").value.trim();
    const profilesPath = document.getElementById("wizardProfilesPath").value.trim();
    const minecraftName = document.getElementById("wizardMinecraft").value.trim();
    const createShortcut = document.getElementById("wizardShortcut").checked;
    try {
      const data = await api("/api/wizard/setup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          app_path: appPath,
          profiles_path: profilesPath,
          minecraft_name: minecraftName,
          create_shortcut: createShortcut,
        }),
      });
      state.config = data.config;
      document.getElementById("wizard").classList.add("hidden");
      document.getElementById("app").classList.remove("hidden");
      updateUserChip();
      showToast("Setup complete");
    } catch (err) {
      showToast(err.message);
    }
  });

  document.getElementById("loginSubmit").addEventListener("click", async () => {
    const identifier = document.getElementById("loginIdentifier").value.trim();
    const password = document.getElementById("loginPassword").value.trim();
    try {
      const data = await api("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ identifier, password }),
      });
      state.user = data.user;
      state.token = data.token;
      localStorage.setItem("uc_token", data.token);
      updateUserChip();
      document.getElementById("auth").classList.add("hidden");
      showToast("Logged in");
      setSection("dashboard");
    } catch (err) {
      showToast(err.message);
    }
  });

  document.getElementById("registerSubmit").addEventListener("click", async () => {
    const email = document.getElementById("registerEmail").value.trim();
    const username = document.getElementById("registerUsername").value.trim();
    const password = document.getElementById("registerPassword").value.trim();
    const confirm = document.getElementById("registerConfirm").value.trim();
    try {
      const data = await api("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, username, password, confirm }),
      });
      state.user = data.user;
      state.token = data.token;
      localStorage.setItem("uc_token", data.token);
      updateUserChip();
      document.getElementById("auth").classList.add("hidden");
      showToast("Account created");
    } catch (err) {
      showToast(err.message);
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.ctrlKey && event.key.toLowerCase() === "k") {
      event.preventDefault();
    }
  });
}

bindEvents();
init();
