const mark = (key, value) => qcMark('TOOLS~' + key + '=' + Boolean(value));
window.addEventListener('load', async () => {
  try {
    const frame = document.getElementById('hub');
    frame.width = 1280; frame.height = 900; frame.src = '/';
    if (!await qcWaitFor(() => frame.contentDocument && frame.contentDocument.querySelector('#tools .tool-open'), 18000))
      throw Error('launcher did not become ready');
    const w = frame.contentWindow, d = frame.contentDocument;
    w.showTab('tools');
    const actual = await fetch('/api/apps').then(r => r.json());
    const ids = box => [...box.querySelectorAll('.tool-open')].map(a => a.getAttribute('href'));
    await mark('registry_count', d.querySelectorAll('#tools .tool-open').length === actual.apps.length);
    await mark('home_parity', JSON.stringify(ids(d.getElementById('tools'))) === JSON.stringify(ids(d.getElementById('homeTools'))));
    await mark('no_help_duplicates', !d.querySelector('#tools a[href*="help"], #homeTools a[href*="help"]') && !actual.apps.some(a => a.id === 'help'));
    const globalHelp = d.getElementById('helpLink');
    globalHelp.focus();
    await mark('global_help_keyboard', d.activeElement === globalHelp && globalHelp.getAttribute('href') === '/help#hub');
    const nativeLink = d.querySelector('#tools .tool-open');
    nativeLink.focus();
    await mark('native_keyboard_link', d.activeElement === nativeLink && nativeLink.tagName === 'A' && nativeLink.target === '_blank' && nativeLink.rel.includes('noopener') && nativeLink.getAttribute('aria-label').includes('แท็บใหม่'));
    const odd = {id: 'brand-new', name: '<img src=x onerror=alert(1)>', icon: '<svg/onload=alert(2)>', blurb: '<script>bad()</script>', path: '/app/brand-new/'};
    w.miceTools.boxes().forEach(box => w.miceTools.render(box, [...actual.apps, odd]));
    await mark('unknown_app_visible', d.querySelectorAll('#tools .tool-open').length === actual.apps.length + 1);
    await mark('registry_text_safe', !d.querySelector('#tools img, #tools svg, #tools script') && d.getElementById('tools').textContent.includes(odd.name));
    const realFetch = w.fetch;
    const answer = (data, status = 200) => { w.fetch = (url, opts) => url === '/api/apps' ? Promise.resolve(new w.Response(JSON.stringify(data), {status})) : realFetch.call(w, url, opts); };
    answer({ok: true, apps: []}); await w.loadApps();
    await mark('empty_truthful', d.querySelector('#tools [data-state="empty"]') && !d.getElementById('tools').querySelector('a'));
    answer({ok: false, apps: [], error: 'registry broken'}); await w.loadApps();
    await mark('registry_failure_not_empty', d.querySelector('#tools [data-state="error"]') && !d.querySelector('#tools [data-state="empty"]'));
    answer({ok: true}); await w.loadApps();
    await mark('malformed_not_empty', d.querySelector('#tools [data-state="error"]'));
    answer({ok: true, apps: actual.apps}, 503); await w.loadApps();
    await mark('http_failure', d.querySelector('#tools [data-state="error"]'));
    answer({ok: true, apps: [{...odd, path: 'javascript:alert(1)'}]}); await w.loadApps();
    await mark('unsafe_url_rejected', d.querySelector('#tools [data-state="error"]') && !d.querySelector('#tools a'));
    let resolve;
    w.fetch = (url, opts) => url === '/api/apps' ? new Promise(r => {resolve = r;}) : realFetch.call(w, url, opts);
    const retry = d.querySelector('#tools button'); retry.focus(); retry.click();
    await mark('retry_loading', d.getElementById('tools').getAttribute('aria-busy') === 'true' && d.querySelector('#tools [data-state="loading"]'));
    resolve(new w.Response(JSON.stringify(actual), {status: 200}));
    await qcWaitFor(() => d.querySelector('#tools .tool-open'), 4000);
    await mark('retry_focus_recovered', d.activeElement === d.querySelector('#tools .tool-open') && d.getElementById('tools').getAttribute('aria-busy') === 'false');
    w.fetch = realFetch;
    for (const theme of THEMES) {
      d.documentElement.setAttribute('data-theme', theme);
      for (const width of [360, 768, 1280, 1920]) {
        frame.width = width;
        await new Promise(r => setTimeout(r, 25));
        const box = d.getElementById('tools'), cards = [...box.children];
        const over = Math.max(d.documentElement.scrollWidth, d.body.scrollWidth) - width;
        const minTarget = Math.min(...[...box.querySelectorAll('.tool-open')].map(a => a.getBoundingClientRect().height));
        const first = cards[0].getBoundingClientRect(), next = cards[1].getBoundingClientRect();
        const flat = !box.querySelector('.tool-grid') && cards.every(c => c.classList.contains('tool-tile'));
        await mark('layout_' + theme + '_' + width, over <= 1 && minTarget >= 44 && flat && (width < 768 || Math.abs(first.top - next.top) < 2));
      }
    }
  } catch(error) { await qcMark('TOOLS~error=' + String(error)); }
  await qcMark('done');
});
