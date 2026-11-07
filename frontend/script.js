const API_BASE = (window.API_BASE_URL || "https://task-management-api-ombp.onrender.com/api").replace(/\/+$/, "");

const $ = (id) => document.getElementById(id);
let accessToken = localStorage.getItem("task_access");
let currentUsername = localStorage.getItem("task_username");
let currentTasks = [];
let currentView = "list";
let calendarCursor = new Date();

function showLanding() {
  $("landingView").classList.remove("hidden");
  $("appView").classList.add("hidden");
  closeAuth();
}

function openAuth(mode = "login") {
  $("authModal").classList.remove("hidden");
  if (mode === "signup") $("registerTab").click();
  else $("loginTab").click();
}

function closeAuth() {
  $("authModal").classList.add("hidden");
}

$("navLoginBtn").onclick = () => openAuth("login");
$("navSignupBtn").onclick = () => openAuth("signup");
$("heroSignupBtn").onclick = () => openAuth("signup");
$("heroLoginBtn").onclick = () => openAuth("login");
$("bottomSignupBtn").onclick = () => openAuth("signup");
$("closeAuth").onclick = closeAuth;
$("authOverlay").onclick = closeAuth;

function showApp() {
  if (accessToken) {
    $("landingView").classList.add("hidden");
    $("authModal").classList.add("hidden");
    $("appView").classList.remove("hidden");
    $("welcome").textContent = currentUsername ? `Hi, ${currentUsername}` : "";
    refresh();
  } else {
    showLanding();
  }
}

function headers(json=true) {
  const h = {};
  if (json) h["Content-Type"] = "application/json";
  if (accessToken) h.Authorization = `Bearer ${accessToken}`;
  return h;
}

async function api(url, options={}) {
  const res = await fetch(API_BASE + url, {...options, headers: {...headers(!!options.body), ...(options.headers||{})}});
  if (res.status === 401) logout();
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || data.message || Object.values(data).flat().join(" ") || "Request failed");
  return data;
}

$("loginTab").onclick = () => {
  $("loginTab").classList.add("active"); $("registerTab").classList.remove("active");
  $("loginForm").classList.remove("hidden"); $("registerForm").classList.add("hidden");
};

$("registerTab").onclick = () => {
  $("registerTab").classList.add("active"); $("loginTab").classList.remove("active");
  $("registerForm").classList.remove("hidden"); $("loginForm").classList.add("hidden");
};

$("loginForm").onsubmit = async (e) => {
  e.preventDefault(); $("loginMsg").textContent = "";
  try {
    const data = await api("/login/", {method:"POST", body:JSON.stringify({
      username:$("loginUsername").value, password:$("loginPassword").value
    })});
    accessToken = data.access; localStorage.setItem("task_access", accessToken);
    currentUsername = $("loginUsername").value; localStorage.setItem("task_username", currentUsername);
    showApp();
  } catch(err) { $("loginMsg").textContent = err.message; }
};

$("registerForm").onsubmit = async (e) => {
  e.preventDefault(); $("registerMsg").textContent = "";
  try {
    const data = await api("/register/", {method:"POST", body:JSON.stringify({
      username:$("registerUsername").value, email:$("registerEmail").value, password:$("registerPassword").value
    })});
    accessToken = data.access;
    localStorage.setItem("task_access", accessToken);
    currentUsername = data.user?.username || $("registerUsername").value;
    localStorage.setItem("task_username", currentUsername);
    $("registerForm").reset();
    showApp();
  } catch(err) { $("registerMsg").textContent = err.message; }
};

function logout() {
  accessToken = null; currentUsername = null;
  localStorage.removeItem("task_access"); localStorage.removeItem("task_username");
  showLanding();
}
$("logoutBtn").onclick = logout;

async function refresh() {
  await Promise.all([loadDashboard(), loadTasks(), loadReminders()]);
  checkBrowserReminders();
}

async function loadDashboard() {
  try {
    const d = await api("/tasks/dashboard/");
    $("totalStat").textContent=d.total; $("completedStat").textContent=d.completed;
    $("pendingStat").textContent=d.pending; $("progressStat").textContent=d.in_progress;
    $("overdueStat").textContent=d.overdue; $("rateStat").textContent=d.completion_rate+"%";
  } catch {}
}

async function loadTasks() {
  const params = new URLSearchParams();
  if ($("searchInput").value) params.set("search",$("searchInput").value);
  if ($("statusFilter").value) params.set("status",$("statusFilter").value);
  if ($("priorityFilter").value) params.set("priority",$("priorityFilter").value);
  if ($("categoryFilter").value) params.set("category",$("categoryFilter").value);
  params.set("ordering",$("sortFilter").value); params.set("page_size", "50");
  try {
    const data = await api("/tasks/?"+params.toString());
    const tasks = data.results || data;
    currentTasks = tasks;
    renderCurrentView();
    $("emptyState").classList.toggle("hidden", tasks.length !== 0);
  } catch(err) {
    $("taskGrid").innerHTML = "";
    $("emptyState").textContent = err.message;
    $("emptyState").classList.remove("hidden");
  }
}

function taskCard(t) {
  return `<article class="task-card">
    <h3>${escapeHtml(t.title)}</h3>
    <p>${escapeHtml(t.description || "No description")}</p>
    <div class="badges">
      <span class="badge">${escapeHtml(t.status)}</span>
      <span class="badge">${escapeHtml(t.priority)}</span>
      ${t.category ? `<span class="badge">${escapeHtml(t.category)}</span>` : ""}
      ${t.is_overdue ? `<span class="badge overdue">Overdue</span>` : ""}
      ${t.status==="Completed" ? `<span class="badge completed">Done</span>` : ""}
    </div>
    <div class="meta">Due: ${t.due_date || "No due date"} · Score: ${t.priority_score}</div>
    ${t.dependencies?.length ? `<div class="dependency-note">↳ Depends on: ${t.dependencies.map(d => escapeHtml(d.title)).join(", ")}</div>` : ""}
    ${t.blocked_by?.length ? `<div class="dependency-note">→ Blocks: ${t.blocked_by.map(d => escapeHtml(d.title)).join(", ")}</div>` : ""}
    ${t.subtask_progress?.total ? `<div class="subtask-progress">Subtasks: ${t.subtask_progress.completed}/${t.subtask_progress.total} <span><i style="width:${t.subtask_progress.percent}%"></i></span></div>` : ""}
    ${t.parent_task_id ? `<div class="dependency-note">↳ Subtask of another task</div>` : ""}
    <div class="actions">
      <button onclick="editTask(${t.id})">Edit</button>
      <button onclick="deleteTask(${t.id})">Delete</button>
      <button onclick="setReminderFor(${t.id})">🔔</button>
      ${t.status!=="Completed" ? `<button onclick="completeTask(${t.id})">Complete</button>` : ""}
    </div>
  </article>`;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
}

$("newTaskBtn").onclick = () => openModal();
$("closeModal").onclick = () => $("taskModal").classList.add("hidden");

$("taskForm").onsubmit = async (e) => {
  e.preventDefault(); $("taskMsg").textContent="";
  const id = $("taskId").value;
  const body = {
    title:$("taskTitle").value, description:$("taskDescription").value,
    status:$("taskStatus").value, priority:$("taskPriority").value,
    category:$("taskCategory").value, due_date:$("taskDueDate").value || null,
    parent_task_id:$("taskParent").value ? Number($("taskParent").value) : null,
    dependency_ids:Array.from($("taskDependencies").selectedOptions).map(o => Number(o.value))
  };
  try {
    await api(id ? `/tasks/${id}/` : "/tasks/", {method:id?"PUT":"POST", body:JSON.stringify(body)});
    $("taskModal").classList.add("hidden"); await refresh();
  } catch(err) { $("taskMsg").textContent=err.message; }
};

function openModal(task=null) {
  $("taskId").value = task?.id || "";
  $("modalTitle").textContent = task ? "Edit Task" : "Create Task";
  $("taskTitle").value = task?.title || "";
  $("taskDescription").value = task?.description || "";
  $("taskStatus").value = task?.status || "Pending";
  $("taskPriority").value = task?.priority || "Medium";
  $("taskCategory").value = task?.category || "";
  $("taskDueDate").value = task?.due_date || "";
  populateParentOptions(task?.id, task?.parent_task_id);
  populateDependencyOptions(task?.id, task?.dependencies || []);
  $("taskMsg").textContent="";
  $("taskModal").classList.remove("hidden");
}

async function editTask(id) { openModal(await api(`/tasks/${id}/`)); }

async function deleteTask(id) {
  if (!confirm("Delete this task?")) return;
  await api(`/tasks/${id}/`, {method:"DELETE"}); await refresh();
}

async function completeTask(id) {
  const task = await api(`/tasks/${id}/`);
  await api(`/tasks/${id}/`, {method:"PUT", body:JSON.stringify({
    title:task.title, description:task.description, status:"Completed",
    priority:task.priority, category:task.category, due_date:task.due_date, parent_task_id:task.parent_task_id || null, dependency_ids:(task.dependencies||[]).map(d=>d.id)
  })});
  await refresh();
}

["searchInput","statusFilter","priorityFilter","categoryFilter","sortFilter"].forEach(id => {
  $(id).addEventListener("input", loadTasks);
  $(id).addEventListener("change", loadTasks);
});

$("clearFilters").onclick = () => {
  ["searchInput","categoryFilter"].forEach(id => $(id).value="");
  ["statusFilter","priorityFilter"].forEach(id => $(id).value="");
  $("sortFilter").value="-created_at"; loadTasks();
};


// Subtasks
async function populateParentOptions(excludeId, selectedId) {
  const select = $("taskParent");
  if (!select) return;
  try {
    const data = await api("/tasks/?page_size=50&ordering=title");
    const tasks = data.results || data;
    select.innerHTML = '<option value="">No parent task</option>' + tasks.filter(t => Number(t.id) !== Number(excludeId)).map(t => `<option value="${t.id}" ${Number(selectedId)===Number(t.id)?"selected":""}>${escapeHtml(t.title)}</option>`).join("");
  } catch { select.innerHTML = '<option value="">No parent task</option>'; }
}

// Task dependencies
async function populateDependencyOptions(excludeId, selectedDeps=[]) {
  const select = $("taskDependencies");
  if (!select) return;
  try {
    const data = await api("/tasks/?page_size=50&ordering=title");
    const tasks = data.results || data;
    const selected = new Set(selectedDeps.map(d => Number(d.id)));
    select.innerHTML = tasks.filter(t => Number(t.id) !== Number(excludeId)).map(t =>
      `<option value="${t.id}" ${selected.has(Number(t.id)) ? "selected" : ""}>${escapeHtml(t.title)}${t.status === "Completed" ? " ✓" : ""}</option>`
    ).join("");
  } catch { select.innerHTML = ""; }
}

// Task templates
let templateItemCount = 0;
function addTemplateItem(data={}) {
  templateItemCount += 1;
  const id = templateItemCount;
  const div = document.createElement("div");
  div.className = "template-item";
  div.dataset.itemId = id;
  div.innerHTML = `
    <div class="template-item-head"><strong>Task ${id}</strong><button type="button" class="template-item-remove">Remove</button></div>
    <div class="template-item-grid">
      <label>Title<input class="tpl-title" maxlength="200" value="${escapeHtml(data.title || "")}" required></label>
      <label>Priority<select class="tpl-priority"><option ${data.priority === "Low" ? "selected" : ""}>Low</option><option ${!data.priority || data.priority === "Medium" ? "selected" : ""}>Medium</option><option ${data.priority === "High" ? "selected" : ""}>High</option><option ${data.priority === "Urgent" ? "selected" : ""}>Urgent</option></select></label>
      <label>Due in (days)<input class="tpl-days" type="number" min="0" value="${data.relative_due_days ?? ""}" placeholder="e.g. 1"></label>
    </div>
    <label>Description<textarea class="tpl-description" rows="2">${escapeHtml(data.description || "")}</textarea></label>
    <label>Category<input class="tpl-category" value="${escapeHtml(data.category || "")}" placeholder="Work, Study..."></label>`;
  div.querySelector(".template-item-remove").onclick = () => div.remove();
  $("templateItems").appendChild(div);
}

async function loadTemplates() {
  const list = $("templateList");
  try {
    const templates = await api("/templates/");
    list.innerHTML = templates.length ? templates.map(t => `
      <div class="template-row">
        <div><h4>${escapeHtml(t.name)}</h4><p>${t.items.length} task${t.items.length === 1 ? "" : "s"}${t.description ? " · " + escapeHtml(t.description) : ""}</p></div>
        <div class="template-actions"><button onclick="applyTemplate(${t.id})">Use Template</button><button onclick="deleteTemplate(${t.id})">Delete</button></div>
      </div>`).join("") : `<div class="empty">No templates yet. Create your first reusable workflow below.</div>`;
  } catch (err) { list.innerHTML = `<div class="message">${escapeHtml(err.message)}</div>`; }
}

function openTemplates() {
  $("templateModal").classList.remove("hidden");
  $("templateForm").reset();
  $("templateItems").innerHTML = "";
  templateItemCount = 0;
  addTemplateItem();
  loadTemplates();
}

$("templatesBtn").onclick = openTemplates;
$("closeTemplateModal").onclick = () => $("templateModal").classList.add("hidden");
$("addTemplateItem").onclick = () => addTemplateItem();

$("templateForm").onsubmit = async (e) => {
  e.preventDefault();
  $("templateMsg").textContent = "";
  const items = Array.from(document.querySelectorAll(".template-item")).map((el, index) => ({
    title: el.querySelector(".tpl-title").value,
    description: el.querySelector(".tpl-description").value,
    priority: el.querySelector(".tpl-priority").value,
    category: el.querySelector(".tpl-category").value,
    relative_due_days: el.querySelector(".tpl-days").value === "" ? null : Number(el.querySelector(".tpl-days").value),
    position: index
  }));
  if (!items.length) { $("templateMsg").textContent = "Add at least one task."; return; }
  try {
    await api("/templates/", {method:"POST", body:JSON.stringify({
      name:$("templateName").value, description:$("templateDescription").value, items
    })});
    $("templateForm").reset(); $("templateItems").innerHTML = ""; templateItemCount = 0; addTemplateItem();
    $("templateMsg").textContent = "Template saved successfully.";
    await loadTemplates();
  } catch (err) { $("templateMsg").textContent = err.message; }
};

async function applyTemplate(id) {
  try {
    const data = await api(`/templates/${id}/apply/`, {method:"POST", body:JSON.stringify({})});
    alert(data.message);
    await refresh();
  } catch (err) { alert(err.message); }
}

async function deleteTemplate(id) {
  if (!confirm("Delete this template?")) return;
  try { await api(`/templates/${id}/`, {method:"DELETE"}); await loadTemplates(); }
  catch (err) { alert(err.message); }
}

function setView(view) {
  currentView = view;
  ["listViewBtn","kanbanViewBtn","calendarViewBtn"].forEach(id => $(id)?.classList.remove("active"));
  const active = {list:"listViewBtn",kanban:"kanbanViewBtn",calendar:"calendarViewBtn"}[view];
  $(active)?.classList.add("active");
  renderCurrentView();
}
function renderCurrentView() {
  $("taskGrid").classList.toggle("hidden", currentView !== "list");
  $("kanbanBoard").classList.toggle("hidden", currentView !== "kanban");
  $("calendarView").classList.toggle("hidden", currentView !== "calendar");
  if (currentView === "list") $("taskGrid").innerHTML = currentTasks.map(taskCard).join("");
  if (currentView === "kanban") renderKanban();
  if (currentView === "calendar") renderCalendar();
}
function renderKanban() {
  const cols = ["Pending","In Progress","Completed"];
  $("kanbanBoard").innerHTML = cols.map(status => {
    const tasks = currentTasks.filter(t => t.status === status);
    return `<div class="kanban-column" data-status="${status}"><div class="kanban-head"><h3>${status}</h3><span>${tasks.length}</span></div><div class="kanban-dropzone">${tasks.map(t => `<article class="kanban-card" draggable="true" data-id="${t.id}"><strong>${escapeHtml(t.title)}</strong><small>${escapeHtml(t.priority)}${t.due_date ? " · " + t.due_date : ""}</small><div class="badges"><span class="badge">${escapeHtml(t.category || "General")}</span>${t.is_overdue?'<span class="badge overdue">Overdue</span>':''}</div><button onclick="editTask(${t.id})">Edit</button></article>`).join("")}</div></div>`;
  }).join("");
  document.querySelectorAll(".kanban-column").forEach(col => {
    col.addEventListener("dragover", e => { e.preventDefault(); col.classList.add("drag-over"); });
    col.addEventListener("dragleave", () => col.classList.remove("drag-over"));
    col.addEventListener("drop", async e => {
      e.preventDefault(); col.classList.remove("drag-over");
      const id = Number(e.dataTransfer.getData("text/plain")); const task = currentTasks.find(t => t.id === id);
      if (!task || task.status === col.dataset.status) return;
      await updateTaskStatus(task, col.dataset.status);
    });
  });
  document.querySelectorAll(".kanban-card").forEach(card => card.addEventListener("dragstart", e => e.dataTransfer.setData("text/plain", card.dataset.id)));
}
async function updateTaskStatus(task, status) {
  try {
    await api(`/tasks/${task.id}/`, {method:"PUT", body:JSON.stringify({title:task.title,description:task.description,status,priority:task.priority,category:task.category,due_date:task.due_date,parent_task_id:task.parent_task_id||null,dependency_ids:(task.dependencies||[]).map(d=>d.id)})});
    await refresh();
  } catch (err) { alert(err.message); }
}
function renderCalendar() {
  const y = calendarCursor.getFullYear(), m = calendarCursor.getMonth();
  const first = new Date(y,m,1); const start = new Date(y,m,1-first.getDay()); const days=[];
  for(let i=0;i<42;i++){ const d=new Date(start); d.setDate(start.getDate()+i); days.push(d); }
  const monthName = first.toLocaleString(undefined,{month:"long",year:"numeric"});
  $("calendarView").innerHTML = `<div class="calendar-head"><button class="secondary" onclick="changeMonth(-1)">←</button><h2>${monthName}</h2><button class="secondary" onclick="changeMonth(1)">→</button></div><div class="calendar-grid calendar-week"><b>Sun</b><b>Mon</b><b>Tue</b><b>Wed</b><b>Thu</b><b>Fri</b><b>Sat</b></div><div class="calendar-grid">${days.map(d=>{const key=d.toISOString().slice(0,10);const items=currentTasks.filter(t=>t.due_date===key);return `<div class="calendar-day ${d.getMonth()!==m?'muted-day':''}"><span>${d.getDate()}</span>${items.map(t=>`<button class="calendar-task" onclick="editTask(${t.id})">${escapeHtml(t.title)}</button>`).join("")}</div>`}).join("")}</div>`;
}
function changeMonth(delta){calendarCursor.setMonth(calendarCursor.getMonth()+delta);renderCalendar();}
async function openInsights(){
  $("insightsModal").classList.remove("hidden"); $("insightsContent").innerHTML='<div class="empty">Analyzing your productivity...</div>';
  try { const d=await api("/ai/insights/"); $("insightsContent").innerHTML=`<div class="insight-summary">${escapeHtml(d.ai_insight || d.summary)}</div><div class="insight-metrics"><div><b>${d.metrics.completion_rate}%</b><span>Completion</span></div><div><b>${d.metrics.overdue}</b><span>Overdue</span></div><div><b>${d.metrics.urgent_open}</b><span>Urgent</span></div></div><h3>Recommendations</h3><ul>${d.recommendations.map(x=>`<li>${escapeHtml(x)}</li>`).join("")}</ul>`; } catch(e){$("insightsContent").innerHTML=`<div class="message">${escapeHtml(e.message)}</div>`;}
}
async function loadReminders(){
  if(!accessToken || !$("reminderList")) return;
  try{ const rs=await api("/reminders/"); $("reminderList").innerHTML=rs.length?rs.map(r=>`<div class="reminder-row"><div><strong>${escapeHtml(r.task_title)}</strong><small>${new Date(r.remind_at).toLocaleString()}${r.message?" · "+escapeHtml(r.message):""}</small></div><button onclick="deleteReminder(${r.id})">Delete</button></div>`).join(""):'<div class="empty">No reminders yet.</div>'; }catch(e){}
}
function openReminders(){$("reminderModal").classList.remove("hidden");populateReminderTasks();loadReminders();}
function populateReminderTasks(){const s=$("reminderTask");s.innerHTML=currentTasks.map(t=>`<option value="${t.id}">${escapeHtml(t.title)}</option>`).join("");}
function setReminderFor(id){openReminders();setTimeout(()=>{$("reminderTask").value=String(id);},50);}
async function deleteReminder(id){await api(`/reminders/${id}/`,{method:"DELETE"});loadReminders();}
async function checkBrowserReminders(){
  if(!("Notification" in window)||!accessToken)return;
  try{if(Notification.permission==="default") await Notification.requestPermission(); const rs=await api("/reminders/"); const now=Date.now(); rs.filter(r=>!r.is_sent && new Date(r.remind_at).getTime()<=now).forEach(r=>{if(Notification.permission==="granted")new Notification("Task Reminder",{body:r.message||r.task_title}); api(`/reminders/${r.id}/`,{method:"PATCH",body:JSON.stringify({is_sent:true})}).catch(()=>{});});}catch(e){}
}
$("listViewBtn").onclick=()=>setView("list"); $("kanbanViewBtn").onclick=()=>setView("kanban"); $("calendarViewBtn").onclick=()=>setView("calendar");
$("insightsBtn").onclick=openInsights; $("closeInsights").onclick=()=>$("insightsModal").classList.add("hidden");
$("remindersBtn").onclick=openReminders; $("closeReminders").onclick=()=>$("reminderModal").classList.add("hidden");
$("reminderForm").onsubmit=async e=>{e.preventDefault();$("reminderMsg").textContent="";try{await api("/reminders/",{method:"POST",body:JSON.stringify({task:Number($("reminderTask").value),remind_at:new Date($("reminderAt").value).toISOString(),message:$("reminderMessage").value})});$("reminderForm").reset();$("reminderMsg").textContent="Reminder created.";loadReminders();}catch(err){$("reminderMsg").textContent=err.message;}};

showApp();


// AI Task Assistant
const aiChat = $("aiChat");
const aiMessages = $("aiMessages");
const aiInput = $("aiInput");
const aiForm = $("aiForm");
const aiSendBtn = $("aiSendBtn");

function openGeminiChat() {
  if (!accessToken) return openAuth("login");
  aiChat.classList.remove("hidden");
  if (!aiMessages.children.length) {
    addAiMessage("Tell me what you need to get done. I can turn one message into multiple tasks, understand dates like tomorrow/Friday/next week, and set priorities for you.");
  }
  aiInput.focus();
}
function closeAiChat() { aiChat.classList.add("hidden"); }

$("aiAssistantBtn").onclick = openGeminiChat;
$("closeAiChat").onclick = closeAiChat;
aiChat.addEventListener("click", (e) => { if (e.target === aiChat) closeAiChat(); });

document.querySelectorAll(".ai-suggestions button").forEach(btn => {
  btn.onclick = () => { aiInput.value = btn.dataset.prompt; aiInput.focus(); };
});

function addAiMessage(text, type="bot") {
  const div = document.createElement("div");
  div.className = `ai-message ${type}`;
  div.innerHTML = escapeHtml(text).replace(/\n/g, "<br>");
  aiMessages.appendChild(div);
  aiMessages.scrollTop = aiMessages.scrollHeight;
}

aiForm.onsubmit = async (e) => {
  e.preventDefault();
  const message = aiInput.value.trim();
  if (!message || !accessToken) return;
  addAiMessage(message, "user");
  aiInput.value = "";
  aiSendBtn.disabled = true;
  aiSendBtn.textContent = "Creating...";
  $("aiMsg").textContent = "";
  const typing = document.createElement("div");
  typing.className = "ai-message bot typing";
  typing.textContent = "AI is creating your tasks...";
  aiMessages.appendChild(typing);
  aiMessages.scrollTop = aiMessages.scrollHeight;
  try {
    const data = await api("/ai/create-tasks/", {method:"POST", body:JSON.stringify({message})});
    typing.remove();
    const titles = (data.tasks || []).map(t => `• ${t.title}`).join("\n");
    addAiMessage(`${data.message}\n${titles}`, "bot");
    await refresh();
  } catch (err) {
    typing.remove();
    addAiMessage(`I couldn't create the tasks. ${err.message}`, "bot");
  } finally {
    aiSendBtn.disabled = false;
    aiSendBtn.textContent = "Create Tasks";
    aiInput.focus();
  }
};
