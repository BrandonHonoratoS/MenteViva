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
    const esEmpresa = () => !resp.contexto || resp.contexto === 'Trabajo en una empresa' || resp.contexto === 'Otra';
    const visibles = () => vars.filter(v => !(grupoVentas.includes(v.id) && !vende()) && !(v.grupo === 'Ruta DM' && !esEmpresa()));
    function vende() { const f = resp.funciones || []; return f.includes('Vendo o asesoro a clientes') || f.includes('Atiendo clientes en mi negocio u oficio') || f.includes('Genero negocio nuevo') || f.includes('Otro') || resp.contexto === 'Tengo mi negocio u oficio'; }
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
      if (m.lab && $('#lab-caso')) { $('#lab-caso').textContent = m.lab.caso + ' / ' + m.lab.casos; $('#lab-evento').textContent = m.lab.evento + ' / ' + m.lab.eventos; $('#lab-bar i').style.width = Math.round((m.lab.respondidos / (m.lab.total || 10)) * 100) + '%'; if (m.lab.titulo) $('#lab-titulo').textContent = m.lab.titulo; }
    }
    setInterval(() => { if (fin) return; const s = Math.max(0, Math.floor((Date.now() - inicio) / 1000)); const m = Math.floor(s / 60); $('#timer').textContent = m + ':' + String(s % 60).padStart(2, '0'); $('#timer').classList.toggle('down', m >= dur); }, 1000);
    let pendiente = false;   // hay un mensaje del usuario (o la apertura) sin respuesta del avatar
    function errorConReintento(msg) {
      const d = add('sistema', msg); const b = document.createElement('button'); b.className = 'btn sm'; b.style.marginLeft = '8px'; b.textContent = 'Reintentar';
      b.onclick = () => { d.remove(); continuar(); }; d.appendChild(b);
    }
    function aplicar(r) {
      orb.classList.add('talking'); setTimeout(() => orb.classList.remove('talking'), 2500);
      if (r.mensaje) add('avatar', r.mensaje, ses.dataset.avatar);
      meta(r.meta || {}); if (r.turnos != null) { turnos = r.turnos; $('#turnos').textContent = turnos + ' / ' + r.turnos_max; }
      if (r.escenario && r.escenario.titulo && $('#esc-titulo')) { $('#esc-titulo').textContent = r.escenario.titulo; $('#esc-encuadre').textContent = r.escenario.encuadre || ''; $('#esc-situacion').textContent = r.escenario.situacion || ''; $('#esc-box').style.display = 'block'; }
      pendiente = false;
      if (r.fin) finalizar();
    }
    async function continuar(auto) {
      if (fin) return; btn.disabled = true; typing(true);
      try { const r = await api('/api/sesiones/' + id + '/continuar'); typing(false); aplicar(r); }
      catch (e) {
        typing(false);
        if (auto && /satur|límite|demanda/i.test(e.message)) { add('sistema', 'La IA está saturada; reintento en 6 segundos…'); setTimeout(() => continuar(false), 6000); }
        else errorConReintento(e.message);
        if (/agotó|presupuesto/i.test(e.message)) fin = true;
      }
      btn.disabled = false;
    }
    async function enviar(txt) {
      const texto = (txt ?? ta.value).trim(); if (!texto || fin) return;
      if (pendiente) { continuar(); return; }
      ta.value = ''; btn.disabled = true; add('usuario', texto); typing(true); pendiente = true;
      $$('[data-rapido^="Estoy listo"]').forEach(b => b.remove());
      try {
        const r = await api('/api/sesiones/' + id + '/mensaje', { texto });
        typing(false); aplicar(r);
      } catch (e) {
        typing(false);
        if (/agotó|presupuesto/i.test(e.message)) { add('sistema', e.message); fin = true; }
        else if (/Escribe algo|ya terminó/i.test(e.message)) { add('sistema', e.message); pendiente = false; }
        else errorConReintento(e.message);
      }
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
    /* ── grabación de voz (MediaRecorder → /audio) y foto (/foto) ── */
    async function subirAdjunto(url, form, etiqueta) {
      if (fin || pendiente) { toast('Espera la respuesta anterior.'); return; }
      btn.disabled = true; pendiente = true; add('usuario', etiqueta); typing(true);
      try {
        form.append('csrf', CSRF);
        const r = await fetch(url, { method: 'POST', headers: { 'X-CSRF': CSRF }, body: form });
        let js = {}; try { js = await r.json(); } catch (e) { js = {}; }
        if (!r.ok) throw new Error(js.error || ('Error ' + r.status));
        typing(false);
        const ult = $$('#msgs .msg.usuario').pop();
        if (ult && js.transcripcion) { const a = js.audio || {}; ult.innerHTML = '<span class="who">Tú</span><span class="adj">🎙️ ' + Math.floor(a.duracion_s / 60) + ':' + String(a.duracion_s % 60).padStart(2, '0') + ' · ' + a.ppm + ' ppm · ' + a.muletillas + ' muletillas</span>' + esc(js.transcripcion); }
        if (ult && js.foto) { ult.innerHTML = '<span class="who">Tú</span><span class="adj">📷 foto · ' + esc(js.foto.codigo_detectado) + '</span>' + esc(js.foto.es_outfit ? 'Te envío una foto de mi outfit.' : 'Te envié una imagen.'); }
        aplicar(js);
      } catch (e) {
        typing(false); pendiente = false;
        const ult = $$('#msgs .msg.usuario').pop(); if (ult) ult.remove();
        if (/agotó|presupuesto/i.test(e.message)) { add('sistema', e.message); fin = true; } else add('sistema', e.message);
      }
      btn.disabled = false;
    }
    const grabar = $('#grabar');
    if (grabar && ses.dataset.audio === '1') {
      let rec = null, chunks = [], t0 = 0, tick = null, cancelado = false; const MAX = 420;
      const estado = $('#adjunto-estado');
      function parar(cancel) { cancelado = !!cancel; if (rec && rec.state !== 'inactive') rec.stop(); }
      grabar.onclick = async () => {
        if (rec && rec.state === 'recording') { parar(false); return; }
        if (!navigator.mediaDevices || !window.MediaRecorder) { toast('Tu navegador no permite grabar; escribe tu respuesta.'); return; }
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          const tipo = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg'].find(t => MediaRecorder.isTypeSupported(t)) || '';
          rec = new MediaRecorder(stream, tipo ? { mimeType: tipo } : undefined); chunks = []; cancelado = false;
          rec.ondataavailable = e => { if (e.data && e.data.size) chunks.push(e.data); };
          rec.onstop = () => {
            stream.getTracks().forEach(t => t.stop()); clearInterval(tick); estado.style.display = 'none'; grabar.classList.remove('on'); $('#composer').style.display = 'flex';
            const dur = Math.round((Date.now() - t0) / 1000);
            if (cancelado || !chunks.length || dur < 2) { if (!cancelado) toast('La grabación quedó demasiado corta.'); return; }
            const blob = new Blob(chunks, { type: rec.mimeType || tipo || 'audio/webm' });
            const form = new FormData(); form.append('archivo', blob, 'grabacion.' + ((blob.type.includes('mp4')) ? 'mp4' : (blob.type.includes('ogg') ? 'ogg' : 'webm'))); form.append('duracion', String(dur));
            subirAdjunto('/api/sesiones/' + id + '/audio', form, '🎙️ Grabación de ' + Math.floor(dur / 60) + ':' + String(dur % 60).padStart(2, '0') + ' (transcribiendo…)');
          };
          rec.start(1000); t0 = Date.now(); grabar.classList.add('on'); estado.style.display = 'flex'; $('#composer').style.display = 'none';
          tick = setInterval(() => { const s = Math.floor((Date.now() - t0) / 1000); $('#rec-tiempo').textContent = Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); if (s >= MAX) parar(false); }, 500);
        } catch (e) { toast('No se pudo acceder al micrófono: revisa el permiso del navegador.'); }
      };
      $('#rec-stop').onclick = () => parar(false);
      $('#rec-cancel').onclick = () => parar(true);
    }
    const foto = $('#foto');
    if (foto && ses.dataset.foto === '1') {
      foto.onchange = () => {
        const f = foto.files && foto.files[0]; if (!f) return;
        const img = new Image(); const url = URL.createObjectURL(f);
        img.onload = () => {
          // se reduce a máx. 1280 px (menos bytes, mismo análisis) y se envía como JPEG
          const esc_ = Math.min(1, 1280 / Math.max(img.width, img.height)); const c = document.createElement('canvas'); c.width = Math.round(img.width * esc_); c.height = Math.round(img.height * esc_);
          c.getContext('2d').drawImage(img, 0, 0, c.width, c.height); URL.revokeObjectURL(url);
          c.toBlob(blob => { const form = new FormData(); form.append('archivo', blob, 'outfit.jpg'); form.append('comentario', ta.value.trim()); ta.value = ''; subirAdjunto('/api/sesiones/' + id + '/foto', form, '📷 Foto enviada (analizando la vestimenta…)'); foto.value = ''; }, 'image/jpeg', 0.86);
        };
        img.onerror = () => { toast('No se pudo leer la imagen.'); foto.value = ''; };
        img.src = url;
      };
    }
    if (ses.dataset.estado === 'analizando') finalizar();
    if (ses.dataset.estado === 'error') { finalizar(); }
    // Sin apertura del avatar (o último mensaje del usuario sin respuesta): pedirla ahora, con reintento automático.
    if (ses.dataset.estado === 'en_curso') { const ms = $$('#msgs .msg'); const ultimo = ms[ms.length - 1]; if (!ultimo || ultimo.classList.contains('usuario')) { pendiente = !!ultimo; continuar(true); } }
    scroll(); ta?.focus();
    // modalidad "Prepárate 5 minutos": cuenta un bloque y avisa que se puede pausar
    const bloque = $('#bloque');
    if (bloque) {
      const total = (+bloque.dataset.min || 5) * 60; const t0 = Date.now(); let hecho = false;
      const tick = setInterval(async () => {
        const s = Math.max(0, total - Math.floor((Date.now() - t0) / 1000)); $('#bloque-v').textContent = Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); $('#bloque-bar').style.width = Math.round(((total - s) / total) * 100) + '%';
        if (s === 0 && !hecho) { hecho = true; clearInterval(tick); try { const r = await api('/api/actividad/bloque'); $('#bloque-msg').innerHTML = '<b>Bloque completado 🔥</b> Racha: ' + r.racha + ' día' + (r.racha === 1 ? '' : 's') + ' · hoy ' + r.bloques_hoy + ' bloques. Puedes continuar o volver más tarde: la sesión se queda abierta.'; toast('¡Bloque de 5 minutos completado!'); } catch (e) { } }
      }, 1000);
    }
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

  /* ── Sócrates: pestañas, mapa Mermaid y espera de generación ───── */
  const tabs = $('#lec-tabs');
  if (tabs) {
    $$('button', tabs).forEach(b => b.onclick = () => { $$('button', tabs).forEach(x => x.classList.toggle('on', x === b)); $$('.tab-pane').forEach(p => p.style.display = p.dataset.pane === b.dataset.tab ? 'block' : 'none'); window.scrollTo({ top: tabs.offsetTop - 80, behavior: 'smooth' }); });
  }
  const mapa = $('#mapa');
  if (mapa) {
    const src = $('.mermaid-src', mapa).textContent.trim();
    const s = document.createElement('script'); s.src = 'https://cdnjs.cloudflare.com/ajax/libs/mermaid/11.12.0/mermaid.min.js';
    s.onload = async () => {
      try {
        mermaid.initialize({ startOnLoad: false, theme: 'base', securityLevel: 'strict', themeVariables: { primaryColor: '#EDE9FE', primaryBorderColor: '#7C3AED', primaryTextColor: '#1E1B4B', lineColor: '#06B6D4', fontFamily: 'Instrument Sans, system-ui, sans-serif', fontSize: '14px' }, flowchart: { curve: 'basis', padding: 12 } });
        const { svg } = await mermaid.render('mapa-svg', src);
        mapa.innerHTML = svg;
      } catch (e) { mapa.innerHTML = '<div class="muted small">El mapa no se pudo dibujar; aquí está su estructura:</div><pre class="small" style="white-space:pre-wrap">' + esc(src) + '</pre>'; }
    };
    s.onerror = () => { mapa.innerHTML = '<pre class="small" style="white-space:pre-wrap">' + esc(src) + '</pre>'; };
    document.head.appendChild(s);
    setTimeout(() => { if ($('.mermaid-src', mapa)) s.onerror(); }, 15000);   // si la librería no carga en 15 s, se muestra la estructura en texto
  }
  const espera = $('#lec-espera');
  if (espera) {
    const id = espera.dataset.id;
    (async function poll() {
      try { const r = await fetch('/api/socrates/' + id + '/estado').then(x => x.json()); if (r.estado !== 'generando') { location.reload(); return; } } catch (e) { }
      setTimeout(poll, 4000);
    })();
  }

  /* filas clicables y confirmaciones */
  $$('tr[data-href]').forEach(tr => tr.onclick = () => location.href = tr.dataset.href);
  $$('form[data-confirm]').forEach(f => f.addEventListener('submit', e => { if (!confirm(f.dataset.confirm)) e.preventDefault(); }));
})();
