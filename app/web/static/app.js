/* Mente Viva · lógica de interfaz (sin dependencias, salvo Chart.js para gráficas) */
(function () {
  const CSRF = document.querySelector('meta[name="csrf"]')?.content || '';
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));

  async function api(url, body) {
    const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF': CSRF }, body: JSON.stringify({ ...(body || {}), csrf: CSRF }) });
    let js = {};
    try { js = await r.json(); } catch (e) { js = {}; }
    if (!r.ok) throw new Error(js.error || ('Error ' + r.status));
    return js;
  }
  function toast(t, ms) { const d = document.createElement('div'); d.className = 'toast'; d.textContent = t; document.body.appendChild(d); setTimeout(() => d.remove(), ms || 3200); }
  function esc(s) { return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }
  window.MV = { api, toast, esc };

  /* ── onboarding (chips) ─────────────────────────────────────────── */
  const ob = $('#onboarding');
  if (ob) {
    const vars = JSON.parse(ob.dataset.vars);
    const grupoVentas = JSON.parse(ob.dataset.grupoVentas);
    const previo = JSON.parse(ob.dataset.previo || '{}');
    const resp = { ...previo };
    let i = 0;
    const visibles = () => vars.filter(v => !(grupoVentas.includes(v.id) && !vende()));
    function vende() { const f = resp.funciones || []; return f.includes('Vendo o asesoro a clientes') || f.includes('Genero negocio nuevo') || f.includes('Otro'); }
    function render() {
      const lista = visibles(); if (i >= lista.length) { i = lista.length - 1; }
      const v = lista[i];
      $('#ob-grupo').textContent = v.grupo; $('#ob-q').textContent = v.pregunta;
      $('#ob-prog').style.width = Math.round((i / lista.length) * 100) + '%';
      $('#ob-n').textContent = (i + 1) + ' / ' + lista.length;
      const box = $('#ob-chips'); box.innerHTML = '';
      v.opciones.forEach(o => {
        const b = document.createElement('button'); b.type = 'button'; b.textContent = o;
        const sel = v.multiple ? (resp[v.id] || []).includes(o) : resp[v.id] === o;
        if (sel) b.classList.add('on');
        b.onclick = () => {
          if (v.multiple) { const a = new Set(resp[v.id] || []); a.has(o) ? a.delete(o) : a.add(o); resp[v.id] = Array.from(a); render(); }
          else { resp[v.id] = o; setTimeout(next, 160); render(); }
        };
        box.appendChild(b);
      });
      $('#ob-prod').style.display = v.id === 'tipo_producto' ? 'block' : 'none';
      $('#ob-next').style.display = v.multiple ? 'inline-flex' : 'none';
      $('#ob-prev').disabled = i === 0;
      $('#ob-done').style.display = (i === lista.length - 1 && resp[v.id]) ? 'inline-flex' : 'none';
    }
    function next() { const lista = visibles(); const v = lista[i]; if (!resp[v.id] || (v.multiple && !resp[v.id].length)) return; if (i < lista.length - 1) { i++; render(); } else render(); }
    $('#ob-next').onclick = next; $('#ob-prev').onclick = () => { if (i > 0) { i--; render(); } };
    $('#ob-done').onclick = async () => {
      $('#ob-done').disabled = true;
      try { await api('/api/diagnostico/onboarding', { respuestas: resp, producto_concreto: $('#ob-prod input').value }); location.reload(); }
      catch (e) { toast(e.message); $('#ob-done').disabled = false; }
    };
    render();
  }

  /* ── sesión con avatar ──────────────────────────────────────────── */
  const ses = $('#sesion');
  if (ses) {
    const id = ses.dataset.id; let turnos = +ses.dataset.turnos; const max = +ses.dataset.max; let fin = ses.dataset.estado !== 'en_curso';
    const msgs = $('#msgs'), ta = $('#texto'), btn = $('#enviar'), orb = $('#orb');
    const inicio = new Date(ses.dataset.inicio); const dur = +ses.dataset.duracion;
    const fases = ['rapport', 'encuadre', 'desarrollo', 'profundizacion', 'cierre', 'fin'];
    function scroll() { msgs.scrollTop = msgs.scrollHeight; }
    function add(rol, texto, who) { const d = document.createElement('div'); d.className = 'msg ' + rol; d.innerHTML = (who ? '<span class="who">' + esc(who) + '</span>' : '') + esc(texto); msgs.appendChild(d); scroll(); return d; }
    function typing(on) { let t = $('#typing'); if (on && !t) { t = document.createElement('div'); t.id = 'typing'; t.className = 'typing'; t.innerHTML = '<i></i><i></i><i></i>'; msgs.appendChild(t); scroll(); } if (!on && t) t.remove(); orb.classList.toggle('thinking', on); }
    function meta(m) {
      if (m.tension != null) { $('#tension i').style.width = m.tension + '%'; $('#tension-v').textContent = m.tension; }
      if (m.fase) { const k = fases.indexOf(m.fase); $$('#fases span').forEach((s, j) => s.classList.toggle('on', j <= k)); $('#fase-v').textContent = m.fase; }
      if (m.etapa) $('#etapa-v').textContent = m.etapa;
      if (m.historias != null) $('#hist-v').textContent = m.historias;
    }
    setInterval(() => { if (fin) return; const s = Math.max(0, Math.floor((Date.now() - inicio) / 1000)); const m = Math.floor(s / 60); $('#timer').textContent = m + ':' + String(s % 60).padStart(2, '0'); $('#timer').classList.toggle('down', m >= dur); }, 1000);
    async function enviar(txt) {
      const texto = (txt ?? ta.value).trim(); if (!texto || fin) return;
      ta.value = ''; btn.disabled = true; add('usuario', texto); typing(true);
      try {
        const r = await api('/api/sesiones/' + id + '/mensaje', { texto });
        typing(false); orb.classList.add('talking'); setTimeout(() => orb.classList.remove('talking'), 2500);
        add('avatar', r.mensaje, ses.dataset.avatar); meta(r.meta || {}); turnos = r.turnos; $('#turnos').textContent = turnos + ' / ' + r.turnos_max;
        if (r.fin) { finalizar(); }
      } catch (e) { typing(false); add('sistema', e.message); if (/agotó|presupuesto/i.test(e.message)) fin = true; }
      btn.disabled = false; ta.focus();
    }
    function finalizar() { fin = true; ses.dataset.estado = 'analizando'; $('#composer').style.display = 'none'; $('#analizando').style.display = 'flex'; orb.classList.add('thinking'); poll(); }
    async function poll() {
      try {
        const r = await fetch('/api/sesiones/' + id + '/estado').then(x => x.json());
        if (r.estado === 'completada' && r.destino) { location.href = r.destino; return; }
        if (r.estado === 'error') { $('#analizando').innerHTML = '<div class="alert err">' + esc(r.error || 'No se pudo analizar la sesión.') + '</div><button class="btn mt" id="reintentar">Reintentar análisis</button>'; $('#reintentar').onclick = async () => { await api('/api/sesiones/' + id + '/reintentar'); $('#analizando').innerHTML = '<div class="orb thinking"></div><p>Analizando…</p>'; poll(); }; return; }
        if (r.estado === 'descartada') { location.href = '/hoy'; return; }
      } catch (e) { }
      setTimeout(poll, 2500);
    }
    btn.onclick = () => enviar();
    ta.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); enviar(); } });
    $$('[data-rapido]').forEach(b => b.onclick = () => enviar(b.dataset.rapido));
    $('#terminar')?.addEventListener('click', async () => { if (!confirm('¿Terminar la práctica y pasar al análisis?')) return; try { await api('/api/sesiones/' + id + '/terminar'); finalizar(); } catch (e) { toast(e.message); } });
    $('#descartar')?.addEventListener('click', async () => { if (!confirm('¿Descartar esta sesión? No se analizará.')) return; try { await api('/api/sesiones/' + id + '/descartar'); location.href = ses.dataset.salida || '/hoy'; } catch (e) { toast(e.message); } });
    if (ses.dataset.estado === 'analizando') finalizar();
    if (ses.dataset.estado === 'error') { finalizar(); }
    scroll(); ta?.focus();
  }

  /* ── chats simples (analista / coach) ───────────────────────────── */
  $$('[data-chat]').forEach(box => {
    const url = box.dataset.chat, msgs = $('.msgs', box), ta = $('textarea', box), btn = $('button.enviar', box), quien = box.dataset.quien || 'Analista';
    function add(rol, texto, extra) { const d = document.createElement('div'); d.className = 'msg ' + rol; d.innerHTML = '<span class="who">' + esc(rol === 'usuario' ? 'Tú' : quien) + '</span>' + esc(texto) + (extra || ''); msgs.appendChild(d); msgs.scrollTop = msgs.scrollHeight; }
    async function enviar(txt) {
      const texto = (txt ?? ta.value).trim(); if (!texto) return; ta.value = ''; btn.disabled = true; add('usuario', texto);
      const t = document.createElement('div'); t.className = 'typing'; t.innerHTML = '<i></i><i></i><i></i>'; msgs.appendChild(t); msgs.scrollTop = msgs.scrollHeight;
      try {
        const r = await api(url, { texto }); t.remove();
        let extra = '';
        if (r.fuentes && r.fuentes.length) extra = '<span class="src">Fuentes: ' + r.fuentes.map(f => '<a href="' + esc(f.url) + '" target="_blank" rel="noopener">' + esc(f.dominio || f.titulo) + '</a>').join('') + '</span>';
        if (r.herramientas && r.herramientas.length) extra += '<span class="src soft">Consultó: ' + esc(r.herramientas.join(', ')) + '</span>';
        add('avatar', r.texto, extra);
      } catch (e) { t.remove(); add('sistema', e.message); }
      btn.disabled = false; ta.focus();
    }
    btn.onclick = () => enviar(); ta.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); enviar(); } });
    $$('[data-sugerencia]', box.parentElement).forEach(b => b.onclick = () => enviar(b.dataset.sugerencia));
    msgs.scrollTop = msgs.scrollHeight;
  });
  $('#limpiar-chat')?.addEventListener('click', async () => { await api('/api/analista/chat/limpiar'); location.reload(); });

  /* ── gráficas ───────────────────────────────────────────────────── */
  if (window.Chart) {
    Chart.defaults.font.family = "'Instrument Sans', system-ui, sans-serif"; Chart.defaults.color = '#6B6690'; Chart.defaults.plugins.legend.display = false;
    const grad = ctx => { const g = ctx.createLinearGradient(0, 0, 0, 220); g.addColorStop(0, 'rgba(124,58,237,.35)'); g.addColorStop(1, 'rgba(6,182,212,.02)'); return g; };
    $$('canvas[data-line]').forEach(c => {
      const d = JSON.parse(c.dataset.line); const ctx = c.getContext('2d');
      new Chart(c, { type: 'line', data: { labels: d.labels, datasets: [{ data: d.values, borderColor: '#7C3AED', backgroundColor: grad(ctx), fill: true, tension: .4, pointRadius: 4, pointBackgroundColor: '#fff', pointBorderColor: '#7C3AED', pointBorderWidth: 2, spanGaps: true }] },
        options: { responsive: true, maintainAspectRatio: false, scales: { y: { min: 0, max: 100, grid: { color: '#EEEBFA' } }, x: { grid: { display: false } } }, plugins: { tooltip: { callbacks: { label: x => ' ' + x.formattedValue + (d.unidad || '') } } } } });
    });
    $$('canvas[data-bar]').forEach(c => {
      const d = JSON.parse(c.dataset.bar);
      new Chart(c, { type: 'bar', data: { labels: d.labels, datasets: [{ data: d.values, backgroundColor: d.colors || '#A855F7', borderRadius: 8, maxBarThickness: 34 }] },
        options: { responsive: true, maintainAspectRatio: false, indexAxis: d.horizontal ? 'y' : 'x', scales: { y: { grid: { color: '#EEEBFA' }, beginAtZero: true, max: d.max }, x: { grid: { display: false } } } } });
    });
    $$('canvas[data-radar]').forEach(c => {
      const d = JSON.parse(c.dataset.radar);
      new Chart(c, { type: 'radar', data: { labels: d.labels, datasets: [{ data: d.values, borderColor: '#06B6D4', backgroundColor: 'rgba(6,182,212,.18)', pointBackgroundColor: '#06B6D4' }].concat(d.values2 ? [{ data: d.values2, borderColor: '#A855F7', backgroundColor: 'rgba(168,85,247,.12)', pointBackgroundColor: '#A855F7' }] : []) },
        options: { responsive: true, maintainAspectRatio: false, layout: { padding: 6 }, scales: { r: { min: 0, max: d.max || 100, ticks: { display: false }, grid: { color: '#E9E6F7' }, pointLabels: { font: { size: 10 }, callback: l => l.length > 18 ? l.slice(0, 17) + '…' : l } } } } });
    });
    $$('canvas[data-donut]').forEach(c => {
      const d = JSON.parse(c.dataset.donut);
      new Chart(c, { type: 'doughnut', data: { labels: d.labels, datasets: [{ data: d.values, backgroundColor: d.colors || ['#7C3AED', '#A855F7', '#06B6D4', '#10B981', '#F59E0B', '#F43F5E', '#3B82F6'], borderWidth: 0 }] },
        options: { responsive: true, maintainAspectRatio: false, cutout: '70%', plugins: { legend: { display: true, position: 'right' } } } });
    });
  }

  /* filas clicables y confirmaciones */
  $$('tr[data-href]').forEach(tr => tr.onclick = () => location.href = tr.dataset.href);
  $$('form[data-confirm]').forEach(f => f.addEventListener('submit', e => { if (!confirm(f.dataset.confirm)) e.preventDefault(); }));
})();
