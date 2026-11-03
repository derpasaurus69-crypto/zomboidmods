"use strict";
const $ = (id) => document.getElementById(id);
const PRESETS = [
  ["downtown", "Downtown", "about 1 km²"],
  ["town", "Town", "about 9 km², the real outline"],
  ["city_core", "City core", "about 25 km², needs a strong PC"],
];
let chosen = null;      // the Place picked from the search
let preset = "downtown";
let lastPlan = null;

async function api(path, body) {
  const r = await fetch(path, body === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  const data = await r.json().catch(() => ({ error: "Portal did not answer." }));
  if (!r.ok) throw new Error(data.error || `Error ${r.status}`);
  return data;
}

function show(id, on = true) { $(id).hidden = !on; }

function showEngine(e) {
  $("engine").textContent = e.ok ? "" : e.problem;
  $("engine").classList.toggle("bad", !e.ok);
  show("knoxmap-form", !e.ok && /not found/.test(e.problem || ""));
}

async function checkEngine() {
  showEngine(await api("/api/engine").catch((err) => ({ ok: false, problem: err.message })));
}

$("knoxmap-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  showEngine(await api("/api/settings", { knoxmap_dir: $("knoxmap-dir").value })
    .catch((err) => ({ ok: false, problem: err.message + " (not found)" })));
});

$("search-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();  // search only on submit: Nominatim's rules, and KnoxMap's
  const q = $("q").value.trim();
  $("results").innerHTML = "";
  $("search-note").textContent = "Searching…";
  try {
    const { results } = await api(`/api/search?q=${encodeURIComponent(q)}`);
    $("search-note").textContent = results.length ? "" : "No places found. Try adding the state or country.";
    for (const place of results) {
      const li = document.createElement("li");
      const b = document.createElement("button");
      b.innerHTML = `${escapeHtml(place.display_name)} <span class="kind">${escapeHtml(place.kind)}</span>`;
      b.addEventListener("click", () => pick(place));
      li.append(b);
      $("results").append(li);
    }
  } catch (err) {
    $("search-note").textContent = err.message;
  }
});

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function pick(place) {
  chosen = place;
  $("size-title").textContent = place.display_name;
  $("presets").innerHTML = "";
  for (const [key, label, hint] of PRESETS) {
    const b = document.createElement("button");
    b.dataset.preset = key;
    b.innerHTML = `${label}<small>${hint}</small>`;
    b.addEventListener("click", () => choosePreset(key));
    $("presets").append(b);
  }
  show("size");
  choosePreset("downtown");
}

async function choosePreset(key) {
  preset = key;
  for (const b of $("presets").children) b.setAttribute("aria-pressed", String(b.dataset.preset === key));
  $("plan-note").textContent = "Checking…";
  try {
    lastPlan = await api("/api/plan", { place: chosen, preset });
    const p = lastPlan.plan, e = lastPlan.estimate;
    let note = `${p.cells} map cells, about ${p.est_minutes} minutes.`;
    if (e.impossible) note = e.impossible;
    else if (e.tight) note += ` ${e.tight}`;
    $("plan-note").textContent = note;
    $("generate").disabled = Boolean(e.impossible);
    $("generate").textContent = lastPlan.existing ? "Regenerate" : "Generate & Play";
    show("play-existing", lastPlan.existing);
  } catch (err) {
    $("plan-note").textContent = err.message;
  }
}

$("generate").addEventListener("click", async () => {
  try {
    await api("/api/generate", { place: chosen, preset, spawn_address: $("spawn-address").value,
                                fill_gaps: $("fill-gaps").checked });
    $("job-title").textContent = lastPlan.title;
    show("size", false); show("done", false); show("job");
    poll();
  } catch (err) {
    $("plan-note").textContent = err.message;
  }
});

$("play-existing").addEventListener("click", () => finished(lastPlan.mod_id, lastPlan.title));
$("cancel").addEventListener("click", () => api("/api/cancel", {}));

async function poll() {
  const s = await api("/api/job");
  $("bar").value = s.pct;
  $("job-step").textContent = s.message;
  if (s.state === "running") return setTimeout(poll, 1000);
  show("job", false);
  if (s.state === "done") finished(s.mod_id, lastPlan.title);
  else { show("size"); $("plan-note").textContent = s.message; }
  loadTowns();
}

let current = null;
function finished(modId, title) {
  current = modId;
  $("done-title").textContent = title;
  $("done-mod").textContent = title;
  $("done-spawn").textContent = title;
  show("publish-note", false);
  show("done");
}

$("launch").addEventListener("click", () => api("/api/launch", {}));
$("publish").addEventListener("click", async () => {
  const r = await api("/api/publish", { mod_id: current }).catch((err) => ({ error: err.message }));
  const note = $("publish-note");
  note.hidden = false;
  note.textContent = r.error ? r.error :
    `${r.reminder} Ready in ${r.folder}. In Project Zomboid: Workshop → Create and Upload, then pick that folder.`;
});

async function loadTowns() {
  const { towns } = await api("/api/towns");
  $("towns").innerHTML = towns.length ? "" : "<li class='note'>None yet.</li>";
  for (const t of towns) {
    const li = document.createElement("li");
    li.textContent = t.title;
    li.addEventListener("click", () => finished(t.mod_id, t.title));
    $("towns").append(li);
  }
}

checkEngine();
loadTowns();
