const API_BASE='https://task-management-api-ombp.onrender.com/api';
const $=id=>document.getElementById(id);
let accessToken=localStorage.getItem('task_access');

function toast(message,error=false){const t=$('toast');t.textContent=message;t.className='toast '+(error?'error':'');setTimeout(()=>t.className='',3000)}
async function api(path,options={}){const headers={'Content-Type':'application/json',...(options.headers||{})};if(accessToken)headers.Authorization=`Bearer ${accessToken}`;const res=await fetch(API_BASE+path,{...options,headers});let data={};try{data=await res.json()}catch{}if(!res.ok){if(res.status===401){logout();}throw new Error(data.detail||data.message||JSON.stringify(data)||'Request failed')}return data}
function showAuth(){ $('authView').classList.remove('hidden');$('appView').classList.add('hidden') }
function showApp(){ $('authView').classList.add('hidden');$('appView').classList.remove('hidden');loadDashboard();loadTasks() }
function logout(){localStorage.removeItem('task_access');localStorage.removeItem('task_refresh');accessToken=null;showAuth()}

if(accessToken)showApp();else showAuth();

document.querySelectorAll('.tab').forEach(btn=>btn.onclick=()=>{document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));btn.classList.add('active');const login=btn.dataset.auth==='login';$('loginForm').classList.toggle('hidden',!login);$('registerForm').classList.toggle('hidden',login)})
$('logoutBtn').onclick=logout;

$('loginForm').onsubmit=async e=>{e.preventDefault();try{const d=await api('/login/',{method:'POST',body:JSON.stringify({username:$('loginUsername').value,password:$('loginPassword').value})});accessToken=d.access;localStorage.setItem('task_access',d.access);if(d.refresh)localStorage.setItem('task_refresh',d.refresh);showApp();toast('Login successful')}catch(err){toast(err.message,true)}};
$('registerForm').onsubmit=async e=>{e.preventDefault();try{await api('/register/',{method:'POST',body:JSON.stringify({username:$('regUsername').value,email:$('regEmail').value,password:$('regPassword').value})});toast('Account created. Please login.');document.querySelector('[data-auth="login"]').click();$('loginUsername').value=$('regUsername').value}catch(err){toast(err.message,true)}};

async function loadDashboard(){try{const d=await api('/tasks/dashboard/');$('total').textContent=d.total??0;$('completed').textContent=d.completed??0;$('pending').textContent=d.pending??0;$('inProgress').textContent=d.in_progress??0;$('overdue').textContent=d.overdue??0;$('completionRate').textContent=`${d.completion_rate??0}%`}catch(e){toast(e.message,true)}}
function query(){const p=new URLSearchParams();if($('statusFilter').value)p.set('status',$('statusFilter').value);if($('priorityFilter').value)p.set('priority',$('priorityFilter').value);if($('categoryFilter').value.trim())p.set('category',$('categoryFilter').value.trim());if($('search').value.trim())p.set('search',$('search').value.trim());p.set('ordering',$('ordering').value);return '?'+p.toString()}
async function loadTasks(){try{const d=await api('/tasks/'+query());const tasks=d.results||d;renderTasks(tasks)}catch(e){toast(e.message,true)}}
function renderTasks(tasks){const list=$('taskList');list.innerHTML='';$('emptyState').classList.toggle('hidden',tasks.length>0);tasks.forEach(t=>{const card=document.createElement('article');card.className='task-card';const due=t.due_date?new Date(t.due_date).toLocaleDateString('en-IN'):'No due date';card.innerHTML=`<h3>${escapeHtml(t.title)}</h3><p>${escapeHtml(t.description||'No description')}</p><div class="badges"><span class="badge">${escapeHtml(t.priority)}</span><span class="badge">${escapeHtml(t.status)}</span>${t.category?`<span class="badge">${escapeHtml(t.category)}</span>`:''}${t.is_overdue?'<span class="badge overdue">Overdue</span>':''}${t.status==='Completed'?'<span class="badge completed">Done</span>':''}</div><div class="meta">Due: ${due} · Priority score: ${t.priority_score??0}</div><div class="actions"><button onclick="editTask(${t.id})">Edit</button><button onclick="deleteTask(${t.id})">Delete</button></div>`;list.appendChild(card)})}
function escapeHtml(v){return String(v).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}
['search','statusFilter','priorityFilter','categoryFilter','ordering'].forEach(id=>$(id).addEventListener('input',loadTasks));
$('clearFilters').onclick=()=>{$('search').value='';$('statusFilter').value='';$('priorityFilter').value='';$('categoryFilter').value='';$('ordering').value='-created_at';loadTasks()};
$('newTaskBtn').onclick=()=>openModal();$('closeModal').onclick=()=>closeModal();$('taskModal').onclick=e=>{if(e.target.id==='taskModal')closeModal()};
function openModal(task=null){$('taskModal').classList.remove('hidden');$('modalTitle').textContent=task?'Edit Task':'New Task';$('taskId').value=task?.id||'';$('title').value=task?.title||'';$('description').value=task?.description||'';$('status').value=task?.status||'Pending';$('priority').value=task?.priority||'Medium';$('category').value=task?.category||'';$('dueDate').value=task?.due_date||''}
function closeModal(){$('taskModal').classList.add('hidden')}
async function editTask(id){try{const t=await api(`/tasks/${id}/`);openModal(t)}catch(e){toast(e.message,true)}}
async function deleteTask(id){if(!confirm('Delete this task?'))return;try{await api(`/tasks/${id}/`,{method:'DELETE'});toast('Task deleted');loadTasks();loadDashboard()}catch(e){toast(e.message,true)}}
$('taskForm').onsubmit=async e=>{e.preventDefault();const id=$('taskId').value;const body={title:$('title').value,description:$('description').value,status:$('status').value,priority:$('priority').value,category:$('category').value,due_date:$('dueDate').value||null};try{await api(id?`/tasks/${id}/`:'/tasks/',{method:id?'PUT':'POST',body:JSON.stringify(body)});closeModal();toast(id?'Task updated':'Task created');loadTasks();loadDashboard()}catch(e){toast(e.message,true)}};
