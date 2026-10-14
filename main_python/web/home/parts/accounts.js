// ---- accounts --------------------------------------------------------
// Only ever shows NAMES: the hub never sends a hash anywhere.
async function loadUsers(){
  const box = $('userBox');
  if (!authed) { box.hidden = true; return; }
  box.hidden = false;
  const a = await Mice.Api.get('/api/users');
  const list = $('userList');
  if (!a.ok) { list.textContent = 'could not read the accounts: ' + a.says; return; }
  const r = a.data;
  list.innerHTML = '';
  const byName = {};
  (r.accounts || []).forEach(function(x){ byName[x.name] = x; });
  const boss = window.miceLogin && miceLogin.role() === 'super_admin';
  (r.users || []).forEach(function(u){
    const chip = document.createElement('span');
    chip.className = 'port';
    const info = byName[u] || {};
    // role and "still on the default password", in words
    chip.textContent = u + (info.role === 'super_admin' ? ' · super_admin' : '') +
                       (info.mustChange ? ' · default password' : '');
    if (boss) {
      const rn = document.createElement('button');
      rn.className = 'icon'; rn.textContent = '✎'; rn.title = 'rename ' + u;
      rn.onclick = function(){ userAction('/api/users/rename', u,
        {'new': (prompt('New username for ' + u) || '').trim()}); };
      chip.appendChild(rn);
      const pw = document.createElement('button');
      pw.className = 'icon'; pw.textContent = '🔑'; pw.title = 'set a new password for ' + u;
      pw.onclick = function(){ const np = prompt('New password for ' + u + ' (8 or more)');
        if (np) userAction('/api/users/password', u, {password: np}); };
      chip.appendChild(pw);
    }
    // The last account has no remove button at all, rather than one that
    // fails: offering an action that cannot work is its own bug.
    if ((r.users || []).length > 1) {
      // A control that ACTS is a button, not a link, and its danger comes
      // from the shared sheet rather than an inline style nobody updates.
      const x = document.createElement('button');
      x.className = 'danger icon';
      x.textContent = '✕';
      x.title = 'remove ' + u;
      x.onclick = function(){ removeUser(u); };
      chip.appendChild(x);
    }
    list.appendChild(chip);
  });
  if (!(r.users || []).length) list.textContent = 'no accounts yet';
}

// One status line for every account action: the hub's reason on the surface,
// the technical part behind the switch (Mice.Status).
let _uStat = null;
function uSay(){ return _uStat || (_uStat = new Mice.Status('uStat')); }

async function addUser(){
  const name = $('uName').value.trim(), pass = $('uPass').value;
  uSay().loading('adding…');
  const a = await Mice.Api.post('/api/users/add',
                                {user: name, password: pass, role: $('uRole').value});
  // The hub's reason says what to fix, so show it rather than a generic no.
  if (!a.ok) return uSay().error(a.says, a.tech);
  uSay().ready('');
  $('uName').value = ''; $('uPass').value = ''; loadUsers();
}

// super_admin edits someone's name or password; the hub says why if not
async function userAction(path, name, body){
  if (body['new'] === '') return;
  uSay().from(await Mice.Api.post(path, Object.assign({user: name}, body)), 'saved');
  loadUsers();
}

async function removeUser(name){
  if (!confirm('Remove ' + name + '? They are logged out straight away.')) return;
  uSay().from(await Mice.Api.post('/api/users/remove', {user: name}), '');
  loadUsers();
}

