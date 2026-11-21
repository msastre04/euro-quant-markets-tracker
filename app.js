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

// Known email domain patterns for major banks, brokers & commodities houses
const COMPANY_DOMAINS = {
  "Société Générale (SG CIB)": ["sgcib.com", "socgen.com"],
  "BNP Paribas (CIB)": ["bnpparibas.com", "uk.bnpparibas.com"],
  "Crédit Agricole CIB": ["ca-cib.com"],
  "Natixis CIB (Groupe BPCE)": ["natixis.com"],
  "ODDO BHF": ["oddo-bhf.com"],
  "CIC Market Solutions": ["cic.fr"],
  "LCL (Banque des Entreprises / Marchés)": ["lcl.fr"],
  "TotalEnergies (Trading & Shipping)": ["totalenergies.com"],
  "ENGIE Global Markets": ["engie.com"],
  "EDF Trading": ["edftrading.com"],
  "Marex (Marex Solutions)": ["marex.com"],
  "Vitol": ["vitol.com"],
  "Trafigura": ["trafigura.com"],
  "Gunvor Group": ["gunvorgroup.com"],
  "Mercuria": ["mercuria.com"],
  "Glencore": ["glencore.com"],
  "RWE Supply & Trading": ["rwe.com"],
  "Deutsche Bank": ["db.com"],
  "Goldman Sachs": ["gs.com"],
  "J.P. Morgan": ["jpmorgan.com", "jpmchase.com"],
  "Morgan Stanley": ["morganstanley.com"],
  "Bank of America": ["bofa.com"],
  "Citigroup": ["citi.com"],
  "UBS": ["ubs.com"],
  "Barclays": ["barclays.com"],
  "HSBC": ["hsbc.com"],
  "UniCredit": ["unicredit.eu"],
  "Intesa Sanpaolo (IMI CIB)": ["intesasanpaolo.com"],
  "TP ICAP": ["tpicap.com"],
  "Compagnie Financière Tradition": ["tradition.com"],
  "Kepler Cheuvreux": ["keplercheuvreux.com"],
  "Optiver": ["optiver.com"],
  "IMC Trading": ["imc.com"],
  "Flow Traders": ["flowtraders.com"],
  "Jane Street": ["janestreet.com"],
  "Citadel Securities": ["citadelsecurities.com"],
  "Jump Trading": ["jumptrading.com"],
  "Hudson River Trading": ["hudsonrivertrading.com"],
  "Susquehanna (SIG)": ["sig.com"],
  "Da Vinci Derivatives": ["davinciderivatives.com"],
  "Qube Research & Technologies (QRT)": ["qube-rt.com"],
  "Capital Fund Management (CFM)": ["cfm.fr"],
  "Squarepoint Capital": ["squarepoint-capital.com"],
  "Millennium Management": ["mlp.com"],
  "Point72": ["point72.com"],
  "Balyasny Asset Management": ["bamfunds.com"]
};

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
  initOutreachTab();
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
            Offre ↗
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

/* OUTREACH / COLD EMAIL TAB LOGIC */
function initOutreachTab() {
  const select = document.getElementById("outreach-company");
  if (!select) return;
  select.innerHTML = allCompanies
    .map(c => `<option value="${escapeHtml(c.name)}">${escapeHtml(c.name)}</option>`)
    .join("");
  updateOutreachTools();
}

function normalizeStr(s) {
  return (s || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9-]/g, "");
}

function updateOutreachTools() {
  const company = document.getElementById("outreach-company").value;
  const city = document.getElementById("outreach-city").value;
  const desk = document.getElementById("outreach-desk").value;
  const first = normalizeStr(document.getElementById("outreach-firstname").value);
  const last = normalizeStr(document.getElementById("outreach-lastname").value);
  const lang = document.getElementById("outreach-lang").value;

  const cleanCompany = company.replace(/\(.*?\)/g, "").trim();
  const cityQuery = city === "Londres" ? "London" : city === "Genève" ? "Geneva" : city === "Francfort" ? "Frankfurt" : city;

  const qGeneral = `site:linkedin.com/in/ "${cleanCompany}" "${cityQuery}" (${desk})`;
  const qAlumni = `site:linkedin.com/in/ "${cleanCompany}" "CentraleSupélec" (${desk})`;

  document.getElementById("btn-xray-linkedin").href = `https://www.google.com/search?q=${encodeURIComponent(qGeneral)}`;
  document.getElementById("btn-xray-alumni").href = `https://www.google.com/search?q=${encodeURIComponent(qAlumni)}`;

  // Email generation
  const resultsBox = document.getElementById("email-results");
  if (!first || !last) {
    resultsBox.innerHTML = `<span class="empty-hint">Entre un prénom et un nom pour générer les formats exacts de ${escapeHtml(company)}.</span>`;
  } else {
    const domains = COMPANY_DOMAINS[company] || [cleanCompany.toLowerCase().replace(/[^a-z0-9]/g, "") + ".com"];
    const patterns = [];
    domains.forEach(dom => {
      patterns.push(`${first}.${last}@${dom}`);
      patterns.push(`${first[0]}${last}@${dom}`);
      if (dom === "bnpparibas.com" || dom === "ca-cib.com") {
        patterns.push(`${first}.${last}@${dom}`);
      }
    });
    const uniqueEmails = [...new Set(patterns)];
    resultsBox.innerHTML = uniqueEmails.map(em => `
      <div class="email-pill-row">
        <span>${escapeHtml(em)}</span>
        <button type="button" class="btn btn-secondary" style="padding: 3px 8px; font-size: 11px;"
                onclick="navigator.clipboard.writeText('${em}'); this.textContent='Copié !';">
          Copier
        </button>
      </div>
    `).join("");
  }

  // Template update
  const deskLabel = document.getElementById("outreach-desk").selectedOptions[0]?.text || "Trading / Structuring";
  const greetingName = document.getElementById("outreach-firstname").value.trim() || "[Prénom]";
  const subjEl = document.getElementById("tpl-subject");
  const bodyEl = document.getElementById("tpl-body");

  if (lang === "fr") {
    subjEl.value = `Candidature stage 6 mois — Desk ${deskLabel} (${city}) — CentraleSupélec`;
    bodyEl.value = `Bonjour ${greetingName},

Actuellement étudiant en 2e année du cycle ingénieur à CentraleSupélec (spécialisation mathématiques appliquées / finance de marché), je suis à la recherche d'un stage de 6 mois en ${deskLabel} à ${city}.

Votre parcours au sein du desk chez ${cleanCompany} a particulièrement retenu mon attention. Passionné par les produits dérivés, les matières premières et la modélisation quantitative (Python, C++, probabilités), je serais ravi d'échanger 5 minutes avec vous ou de vous transmettre mon CV si votre équipe envisage de recruter un stagiaire prochainement.

Bien cordialement,
Maxime
CentraleSupélec — +33 6 XX XX XX XX`;
  } else {
    subjEl.value = `Off-Cycle Internship Inquiry — ${deskLabel} (${cityQuery}) — CentraleSupélec`;
    bodyEl.value = `Hi ${greetingName},

I am currently a 2nd-year engineering student at CentraleSupélec (Applied Mathematics & Quantitative Finance track) looking for a 6-month off-cycle internship on the ${deskLabel} desk in ${cityQuery}.

I have been closely following ${cleanCompany}'s activity in this space and would welcome the opportunity to share my resume or have a brief 5-minute chat if your team is considering taking on an intern in the coming months.

Best regards,
Maxime
CentraleSupélec — +33 6 XX XX XX XX`;
  }
}

window.copyField = function(id) {
  const el = document.getElementById(id);
  navigator.clipboard.writeText(el.value);
};

function bindEvents() {
  document.querySelectorAll(".tab").forEach(tab => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
      document.querySelectorAll(".tab-view").forEach(v => v.classList.remove("active"));
      tab.classList.add("active");
      document.getElementById(`view-${tab.dataset.tab}`).classList.add("active");
    });
  });

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

  ["comp-search", "comp-city", "comp-category"].forEach(id => {
    document.getElementById(id).addEventListener("input", renderCompanies);
    document.getElementById(id).addEventListener("change", renderCompanies);
  });

  ["outreach-company", "outreach-city", "outreach-desk", "outreach-firstname", "outreach-lastname", "outreach-lang"].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener("input", updateOutreachTools);
      el.addEventListener("change", updateOutreachTools);
    }
  });

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
