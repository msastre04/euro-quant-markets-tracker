const STORAGE_TRACKING_KEY = "eqmt_user_tracking_v1";
const STORAGE_CUSTOM_JOBS_KEY = "eqmt_custom_jobs_v1";

let allInternships = [];
let allCompanies = [];
let userTracking = JSON.parse(localStorage.getItem(STORAGE_TRACKING_KEY) || "{}");
let customJobs = JSON.parse(localStorage.getItem(STORAGE_CUSTOM_JOBS_KEY) || "[]");

const STATUS_OPTIONS = [
  "À postuler",
  "Postulé",
  "Test en ligne (OA)",
  "Entretien",
  "Offre",
  "Refusé"
];

function getStatusClass(status) {
  switch (status) {
    case "Postulé": return "status-applied";
    case "Test en ligne (OA)": return "status-oa";
    case "Entretien": return "status-interview";
    case "Offre": return "status-offer";
    case "Refusé": return "status-rejected";
    default: return "status-todo";
  }
}

function saveTracking() {
  localStorage.setItem(STORAGE_TRACKING_KEY, JSON.stringify(userTracking));
  updateKPIs();
}

function saveCustomJobs() {
  localStorage.setItem(STORAGE_CUSTOM_JOBS_KEY, JSON.stringify(customJobs));
}

async function init() {
  try {
    const [resJobs, resComps] = await Promise.all([
      fetch("data/internships.json"),
      fetch("data/companies.json")
    ]);
    const baseJobs = await resJobs.json();
    allCompanies = await resComps.json();
    allInternships = [...customJobs, ...baseJobs];
  } catch (err) {
    console.error("Erreur de chargement des données JSON:", err);
    allInternships = [...customJobs];
  }

  document.getElementById("tab-count-companies").textContent = allCompanies.length;
  renderInternships();
  renderCompanies();
  updateKPIs();
  bindEvents();
}

function updateKPIs() {
  const merged = getMergedInternships();
  let todo = 0, applied = 0, interview = 0, offer = 0;

  merged.forEach(job => {
    const st = (userTracking[job.id]?.status) || "À postuler";
    if (st === "À postuler") todo++;
    else if (st === "Postulé" || st === "Test en ligne (OA)") applied++;
    else if (st === "Entretien") interview++;
    else if (st === "Offre") offer++;
  });

  document.getElementById("kpi-total").textContent = merged.length;
  document.getElementById("kpi-todo").textContent = todo;
  document.getElementById("kpi-applied").textContent = applied;
  document.getElementById("kpi-interview").textContent = interview;
  document.getElementById("kpi-offer").textContent = offer;
}

function getMergedInternships() {
  return allInternships.sort((a, b) => (b.posted_date || "").localeCompare(a.posted_date || ""));
}

function renderInternships() {
  const tbody = document.getElementById("internships-tbody");
  const search = document.getElementById("filter-search").value.toLowerCase().trim();
  const city = document.getElementById("filter-city").value;
  const role = document.getElementById("filter-role").value;
  const category = document.getElementById("filter-category").value;
  const duration = document.getElementById("filter-duration").value;
  const myStatus = document.getElementById("filter-my-status").value;

  const filtered = getMergedInternships().filter(job => {
    const currentStatus = (userTracking[job.id]?.status) || "À postuler";
    const currentNote = (userTracking[job.id]?.note) || "";
    const haystack = `${job.company} ${job.title} ${job.role} ${job.city} ${currentNote}`.toLowerCase();

    if (search && !haystack.includes(search)) return false;
    if (city && job.city !== city) return false;
    if (role && job.role !== role) return false;
    if (category && job.category !== category) return false;
    if (duration && job.duration !== duration) return false;
    if (myStatus && currentStatus !== myStatus) return false;
    return true;
  });

  document.getElementById("tab-count-internships").textContent = filtered.length;

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" class="empty-state">Aucune offre ne correspond à ces filtres.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map(job => {
    const track = userTracking[job.id] || { status: "À postuler", note: "" };
    const optionsHtml = STATUS_OPTIONS.map(opt =>
      `<option value="${opt}" ${track.status === opt ? "selected" : ""}>${opt}</option>`
    ).join("");

    return `
      <tr>
        <td>
          <div class="company-cell">
            <span class="company-name">${escapeHtml(job.company)}</span>
            <span class="badge badge-cat">${escapeHtml(job.category)}</span>
          </div>
        </td>
        <td class="job-title">${escapeHtml(job.title)}</td>
        <td><span class="badge badge-role">${escapeHtml(job.role)}</span></td>
        <td><span class="badge badge-city">${escapeHtml(job.city)}</span></td>
        <td>${escapeHtml(job.duration)}</td>
        <td class="mono-date">${escapeHtml(job.posted_date || "-")}</td>
        <td>
          <select class="status-select ${getStatusClass(track.status)}" data-id="${escapeHtml(job.id)}">
            ${optionsHtml}
          </select>
        </td>
        <td>
          <input type="text" class="note-input" data-id="${escapeHtml(job.id)}"
                 value="${escapeHtml(track.note)}" placeholder="Contact, desk, notes..." />
        </td>
        <td>
          <a href="${escapeHtml(job.url)}" target="_blank" rel="noopener noreferrer" class="apply-link">
            Postuler ↗
          </a>
        </td>
      </tr>
    `;
  }).join("");

  tbody.querySelectorAll(".status-select").forEach(sel => {
    sel.addEventListener("change", (e) => {
      const id = e.target.dataset.id;
      const val = e.target.value;
      userTracking[id] = { ...(userTracking[id] || {}), status: val };
      e.target.className = `status-select ${getStatusClass(val)}`;
      saveTracking();
    });
  });

  tbody.querySelectorAll(".note-input").forEach(inp => {
    inp.addEventListener("input", (e) => {
      const id = e.target.dataset.id;
      userTracking[id] = { ...(userTracking[id] || { status: "À postuler" }), note: e.target.value };
      saveTracking();
    });
  });
}

function renderCompanies() {
  const grid = document.getElementById("companies-grid");
  const search = document.getElementById("comp-search").value.toLowerCase().trim();
  const city = document.getElementById("comp-city").value;
  const category = document.getElementById("comp-category").value;

  const filtered = allCompanies.filter(c => {
    if (search && !c.name.toLowerCase().includes(search)) return false;
    if (city && !(c.hubs || []).includes(city)) return false;
    if (category && c.category !== category) return false;
    return true;
  });

  grid.innerHTML = filtered.map(c => `
    <div class="company-card">
      <div>
        <div class="company-card-top">
          <h3>${escapeHtml(c.name)}</h3>
          <span class="badge badge-cat">${escapeHtml(c.category)}</span>
        </div>
        <div class="hubs-list" style="margin-top: 10px;">
          ${(c.hubs || []).map(h => `<span class="badge badge-city">${escapeHtml(h)}</span>`).join("")}
        </div>
      </div>
      <div class="company-card-footer">
        <span class="ats-tag">Portail: ${escapeHtml(c.ats || "direct")}</span>
        <a href="${escapeHtml(c.careers_url)}" target="_blank" rel="noopener noreferrer" class="apply-link">
          Page Carrières ↗
        </a>
      </div>
    </div>
  `).join("");
}

function bindEvents() {
  // Tabs
  document.querySelectorAll(".tab").forEach(tab => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
      document.querySelectorAll(".tab-view").forEach(v => v.classList.remove("active"));
      tab.classList.add("active");
      document.getElementById(`view-${tab.dataset.tab}`).classList.add("active");
    });
  });

  // Internship filters
  ["filter-search", "filter-city", "filter-role", "filter-category", "filter-duration", "filter-my-status"].forEach(id => {
    document.getElementById(id).addEventListener("input", renderInternships);
    document.getElementById(id).addEventListener("change", renderInternships);
  });

  document.getElementById("btn-reset-filters").addEventListener("click", () => {
    ["filter-search", "filter-city", "filter-role", "filter-category", "filter-duration", "filter-my-status"].forEach(id => {
      document.getElementById(id).value = "";
    });
    renderInternships();
  });

  // Company filters
  ["comp-search", "comp-city", "comp-category"].forEach(id => {
    document.getElementById(id).addEventListener("input", renderCompanies);
    document.getElementById(id).addEventListener("change", renderCompanies);
  });

  // Modal
  const modal = document.getElementById("modal-add");
  document.getElementById("btn-open-modal").addEventListener("click", () => modal.classList.remove("hidden"));
  document.getElementById("btn-close-modal").addEventListener("click", () => modal.classList.add("hidden"));
  modal.addEventListener("click", (e) => { if (e.target === modal) modal.classList.add("hidden"); });

  function buildNewJobFromForm() {
    const company = document.getElementById("add-company").value.trim();
    const title = document.getElementById("add-title").value.trim();
    const today = new Date().toISOString().slice(0, 10);
    return {
      id: `${company.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-${Date.now()}`,
      company,
      category: document.getElementById("add-category").value,
      title,
      role: document.getElementById("add-role").value,
      city: document.getElementById("add-city").value,
      duration: document.getElementById("add-duration").value,
      posted_date: today,
      status: "Ouvert",
      url: document.getElementById("add-url").value.trim()
    };
  }

  document.getElementById("form-add-internship").addEventListener("submit", (e) => {
    e.preventDefault();
    const newJob = buildNewJobFromForm();
    customJobs.unshift(newJob);
    saveCustomJobs();
    allInternships.unshift(newJob);
    renderInternships();
    updateKPIs();
    e.target.reset();
    modal.classList.add("hidden");
  });

  document.getElementById("btn-copy-json").addEventListener("click", () => {
    const newJob = buildNewJobFromForm();
    if (!newJob.company || !newJob.title) {
      alert("Remplis au moins l'entreprise et l'intitulé du poste.");
      return;
    }
    navigator.clipboard.writeText(JSON.stringify(newJob, null, 2));
    alert("Bloc JSON copié dans le presse-papiers ! Tu peux le coller dans data/internships.json.");
  });

  // Export / Import personal tracking
  document.getElementById("btn-export").addEventListener("click", () => {
    const payload = {
      exported_at: new Date().toISOString(),
      tracking: userTracking,
      custom_jobs: customJobs
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `mon-suivi-stages-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
  });

  document.getElementById("input-import").addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const data = JSON.parse(ev.target.result);
        if (data.tracking) {
          userTracking = data.tracking;
          saveTracking();
        }
        if (Array.isArray(data.custom_jobs)) {
          customJobs = data.custom_jobs;
          saveCustomJobs();
        }
        init();
        alert("Suivi restauré avec succès !");
      } catch (err) {
        alert("Fichier JSON invalide.");
      }
    };
    reader.readAsText(file);
  });
}

function escapeHtml(str) {
  return String(str || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

init();
