// ---- accounts --------------------------------------------------------
// Only ever shows NAMES: the hub never sends a hash anywhere.
async function loadUsers(){
  const box = $('userBox');
  if (!authed) { box.hidden = true; return; }
  box.hidden = false;
  try{
    const r = await fetch('/api/users').then(x => x.json());
    const list = $('userList');
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
  }catch(e){ $('userList').textContent = 'could not read the accounts'; }
}

async function addUser(){
  const name = $('uName').value.trim(), pass = $('uPass').value;
  $('uStat').textContent = 'adding…';
  try{
    const r = await fetch('/api/users/add', {method:'POST',
      body: JSON.stringify({user:name, password:pass, role:$('uRole').value})}).then(x => x.json());
    // The hub's reason says what to fix, so show it rather than a generic no.
    $('uStat').textContent = r.ok ? '' : (r.error || 'refused');
    if (r.ok) { $('uName').value = ''; $('uPass').value = ''; loadUsers(); }
  }catch(e){ $('uStat').textContent = 'the hub did not answer'; }
}

// super_admin edits someone's name or password; the hub says why if not
async function userAction(path, name, body){
  if (body['new'] === '') return;
  try{
    const r = await fetch(path, {method:'POST',
      body: JSON.stringify(Object.assign({user:name}, body))}).then(x => x.json());
    $('uStat').textContent = r.ok ? 'saved' : (r.error || 'refused');
    loadUsers();
  }catch(e){ $('uStat').textContent = 'the hub did not answer'; }
}

async function removeUser(name){
  if (!confirm('Remove ' + name + '? They are logged out straight away.')) return;
  try{
    const r = await fetch('/api/users/remove', {method:'POST',
      body: JSON.stringify({user:name})}).then(x => x.json());
    $('uStat').textContent = r.ok ? '' : (r.error || 'refused');
    loadUsers();
  }catch(e){ $('uStat').textContent = 'the hub did not answer'; }
}

