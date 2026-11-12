(() => {
  'use strict';
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const escape = value => String(value).replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const state = { view: 'desktop', wallpaper: 'rider', accent: 'frost', motion: !reduced.matches, sound: false, icons: true, folder: 'Home', settingsTab: 'wallpapers', installer: 0, avatar: 'hunter', windows: new Map(), active: null, z: 10 };
  const apps = {
    welcome: { title: 'Welcome to DhampirOS', label: 'Welcome', description: 'A little time in the half-light', icon: 'system-about', size: [530, 333], position: [.09, .08] },
    files: { title: 'Files', label: 'Files', description: 'Find your way around', icon: 'system-file-manager', size: [680, 405], position: [.12, .09] },
    settings: { title: 'Appearance', label: 'Appearance', description: 'Wallpaper, colour and movement', icon: 'preferences-desktop', size: [545, 424], position: [.19, .10] },
    terminal: { title: 'Terminal', label: 'Terminal', description: 'A small, local preview shell', icon: 'utilities-terminal', size: [575, 345], position: [.29, .21] },
    gallery: { title: 'The visual archive', label: 'Artwork', description: 'Four ways to meet the night', icon: 'image-x-generic', size: [640, 420], position: [.14, .08] },
    notes: { title: 'Field notes', label: 'Field notes', description: 'The thinking behind Nocturne', icon: 'accessories-text-editor', size: [530, 388], position: [.22, .13] },
    viewer: { title: 'Image viewer', label: 'Image viewer', description: '', icon: 'image-x-generic', size: [710, 427], position: [.11, .07] }
  };
  let manifest, iconMap, activeToast, siteToast, heroEnabled = !reduced.matches;
  const videoVisibility = new Map();
  const audio = new Audio('showcase/assets/motion/notification.wav');
  audio.preload = 'none'; audio.volume = .55;
  const icon = (name, extra = '') => `<img src="${escape(iconMap.get(name)?.src || 'showcase/assets/icons/applications-other.svg')}" alt="" ${extra}>`;
  const wallpaper = id => manifest.wallpapers.find(p => p.id === id) || manifest.wallpapers[0];

  function toast(message, site = false) {
    const el = $(site ? '#site-toast' : '#os-toast');
    clearTimeout(site ? siteToast : activeToast); el.textContent = message; el.hidden = false;
    const timer = setTimeout(() => { el.hidden = true; }, 3200);
    if (site) siteToast = timer; else { activeToast = timer; if (state.sound) { audio.currentTime = 0; audio.play().catch(() => {}); } }
  }

  function prepareVideo(video) {
    if (video.dataset.prepared) return;
    for (const source of $$('source[data-src]', video)) source.src = source.dataset.src;
    video.muted = true; video.dataset.prepared = 'true'; video.load();
    video.addEventListener('loadeddata', () => { if (!video.paused) video.classList.add('is-ready'); });
    video.addEventListener('playing', () => video.classList.add('is-ready'));
  }
  function updateVideos() {
    for (const [video, visible] of videoVisibility) {
      const wanted = video.id === 'hero-video' ? heroEnabled : state.motion && state.wallpaper === 'rider' && state.view === 'desktop';
      if (wanted && visible && !document.hidden) { prepareVideo(video); if (video.paused) video.play().catch(() => {}); }
      else video.pause();
      if (video.id === 'desktop-video' && (!state.motion || state.wallpaper !== 'rider')) video.classList.remove('is-ready');
    }
    $('#hero-motion').textContent = heroEnabled ? 'Pause motion' : 'Play motion';
    $('#hero-motion').setAttribute('aria-pressed', String(heroEnabled));
  }
  function observeVideos() {
    const observer = new IntersectionObserver(entries => { for (const entry of entries) videoVisibility.set(entry.target, entry.isIntersecting); updateVideos(); }, { threshold: .12 });
    for (const video of $$('.motion-video')) { videoVisibility.set(video, false); observer.observe(video); }
    document.addEventListener('visibilitychange', updateVideos);
    $('#hero-motion').addEventListener('click', () => { heroEnabled = !heroEnabled; $('.nocturne-hero').dataset.motionOverride = String(heroEnabled); updateVideos(); });
    reduced.addEventListener('change', event => { if (event.matches) { heroEnabled = state.motion = false; $('#view-desktop').dataset.motionOverride = 'false'; $('.nocturne-hero').dataset.motionOverride = 'false'; updateVideos(); refreshSettings(); } });
  }

  function setView(view, scroll = false) {
    if (!['desktop', 'login', 'installer', 'library'].includes(view)) return;
    state.view = view; hideLauncher(false);
    for (const button of $$('[data-view]')) { const selected = button.dataset.view === view; button.setAttribute('aria-selected', String(selected)); button.tabIndex = selected ? 0 : -1; }
    for (const panel of $$('.preview-view')) panel.hidden = panel.id !== `view-${view}`;
    updateVideos();
    if (scroll) $('#icons').scrollIntoView({ behavior: reduced.matches ? 'auto' : 'smooth', block: 'start' });
  }
  function applyWallpaper(id, announce = true) {
    const selected = wallpaper(id); state.wallpaper = selected.id;
    $('#desktop-still').src = selected.src; $('#desktop-still').alt = selected.name;
    updateVideos(); refreshSettings();
    for (const button of $$('[data-try-wallpaper]')) button.textContent = button.dataset.tryWallpaper === id ? 'On the desktop ✓' : 'Try this wallpaper ↗';
    if (announce) toast(`${selected.name} · on the desktop`);
  }
  function applyAccent(name) { state.accent = name; $('#view-desktop').dataset.accent = name; refreshSettings(); }
  function refreshSettings() { const window = state.windows.get('settings'); if (window) renderApp(window); }

  function launcherApps(query = '') {
    const names = ['files', 'settings', 'terminal', 'gallery', 'notes', 'welcome'];
    const matches = names.filter(id => `${apps[id].label} ${apps[id].description}`.toLowerCase().includes(query.toLowerCase()));
    $('#launcher-apps').innerHTML = matches.map(id => `<button class="launcher-app" type="button" data-open="${id}">${icon(apps[id].icon)}<span><strong>${apps[id].label}</strong><small>${apps[id].description}</small></span></button>`).join('') || '<p class="note">No applications match.</p>';
  }
  function hideLauncher(restore = true) { $('#launcher').hidden = true; $('#preview-start').setAttribute('aria-expanded', 'false'); if (restore) $('#preview-start').focus({ preventScroll: true }); }
  function toggleLauncher() {
    const open = $('#launcher').hidden; $('#launcher').hidden = !open; $('#preview-start').setAttribute('aria-expanded', String(open));
    if (open) { $('#launcher-search').value = ''; launcherApps(); $('#launcher-search').focus({ preventScroll: true }); }
  }

  function updateTasks() {
    $('#panel-tasks').innerHTML = [...state.windows.values()].map(win => `<button type="button" class="panel-task ${state.active === win.id && !win.minimized ? 'is-active' : ''} ${win.minimized ? 'is-minimized' : ''}" data-task="${win.id}" aria-label="${win.minimized ? 'Restore' : 'Show'} ${escape(apps[win.id].label)}" title="${escape(apps[win.id].label)}">${icon(apps[win.id].icon)}<span>${escape(apps[win.id].label)}</span></button>`).join('');
  }
  function focusWindow(win) {
    win.minimized = false; win.el.hidden = false; state.active = win.id; win.el.style.zIndex = String(++state.z);
    for (const other of state.windows.values()) other.el.classList.toggle('is-active', other === win);
    updateTasks();
  }
  function closeWindow(id) {
    const win = state.windows.get(id); if (!win) return; win.el.remove(); state.windows.delete(id);
    const next = [...state.windows.values()].filter(w => !w.minimized).pop(); state.active = null; if (next) focusWindow(next); else updateTasks();
  }
  function maximizeWindow(win) {
    if (!win.maximized) { win.geometry = { left: win.el.style.left, top: win.el.style.top, width: win.el.style.width, height: win.el.style.height }; win.maximized = true; }
    else { win.maximized = false; Object.assign(win.el.style, win.geometry); }
    win.el.classList.toggle('is-maximized', win.maximized);
    $('[data-window-action="maximize"]', win.el).setAttribute('aria-pressed', String(win.maximized));
    focusWindow(win);
  }
  function moveWindow(win, left, top) {
    const layer = $('#window-layer');
    win.el.style.left = `${Math.max(0, Math.min(left, Math.max(0, layer.clientWidth - win.el.offsetWidth)))}px`;
    win.el.style.top = `${Math.max(0, Math.min(top, Math.max(0, layer.clientHeight - win.el.offsetHeight)))}px`;
  }
  function bindWindow(win) {
    win.el.addEventListener('pointerdown', () => focusWindow(win));
    const bar = $('.os-titlebar', win.el);
    bar.addEventListener('dblclick', event => { if (!event.target.closest('button')) maximizeWindow(win); });
    bar.addEventListener('keydown', event => {
      if (event.target !== bar || win.maximized) return;
      const shift = { ArrowLeft: [-12, 0], ArrowRight: [12, 0], ArrowUp: [0, -12], ArrowDown: [0, 12] }[event.key];
      if (shift) { event.preventDefault(); moveWindow(win, win.el.offsetLeft + shift[0], win.el.offsetTop + shift[1]); }
    });
    bar.addEventListener('pointerdown', event => {
      if (event.target.closest('button') || win.maximized || innerWidth < 761 || event.button !== 0) return;
      event.preventDefault(); const start = { x: event.clientX, y: event.clientY, left: win.el.offsetLeft, top: win.el.offsetTop };
      bar.setPointerCapture(event.pointerId); win.el.classList.add('is-dragging');
      const move = e => moveWindow(win, start.left + e.clientX - start.x, start.top + e.clientY - start.y);
      const finish = () => { bar.removeEventListener('pointermove', move); bar.removeEventListener('pointerup', finish); bar.removeEventListener('pointercancel', finish); win.el.classList.remove('is-dragging'); };
      bar.addEventListener('pointermove', move); bar.addEventListener('pointerup', finish); bar.addEventListener('pointercancel', finish);
    });
  }
  function openApp(id, context = {}) {
    if (!apps[id]) return; setView('desktop'); hideLauncher(false);
    if (id === 'settings' && context.tab) state.settingsTab = context.tab;
    let win = state.windows.get(id);
    if (win) { Object.assign(win.context, context); if (Object.keys(context).length) renderApp(win); focusWindow(win); return win; }
    const app = apps[id], layer = $('#window-layer');
    const el = document.createElement('section'); el.className = 'os-window'; el.dataset.app = id; el.setAttribute('role', 'dialog'); el.setAttribute('aria-label', app.title);
    const width = Math.min(app.size[0], layer.clientWidth - 26), height = Math.min(app.size[1], layer.clientHeight - 28);
    Object.assign(el.style, { width: `${width}px`, height: `${height}px`, left: `${Math.min(layer.clientWidth * app.position[0], layer.clientWidth - width - 10)}px`, top: `${Math.min(layer.clientHeight * app.position[1], layer.clientHeight - height - 10)}px` });
    el.innerHTML = `<div class="os-titlebar" tabindex="0" aria-label="${escape(app.title)} window. Drag to move, or use arrow keys."><span class="os-title">${icon(app.icon)}<span class="window-title-text">${app.title}</span></span><div class="os-window-controls"><button type="button" data-window-action="minimize" aria-label="Minimize ${escape(app.label)}" title="Minimize">−</button><button type="button" data-window-action="maximize" aria-label="Maximize ${escape(app.label)}" aria-pressed="false" title="Maximize">□</button><button type="button" data-window-action="close" aria-label="Close ${escape(app.label)}" title="Close">×</button></div></div><div class="os-window-body"></div>`;
    layer.append(el); win = { id, el, context, minimized: false, maximized: false, history: [], historyIndex: 0 }; state.windows.set(id, win);
    bindWindow(win); renderApp(win); focusWindow(win); return win;
  }

  function welcomeContent() {
    return `<div class="welcome-app"><div><div class="welcome-tag">NOCTURNE / INTERFACE STUDY</div><img class="welcome-wordmark" src="showcase/assets/brand/dhampiros-wordmark.svg" alt="DhampirOS by potemkin"><h2>Welcome to the half-light.</h2><p>A few windows. A little weather. Explore the artwork, try a different scene and find your way around the Nocturne desktop.</p><div class="welcome-buttons"><button class="os-primary" type="button" data-open="files">Browse Files ↗</button><button class="os-secondary" type="button" data-open="settings">Make it yours</button></div></div><img src="showcase/assets/brand/dhampiros-sigil.svg" alt="DhampirOS sigil"></div>`;
  }
  const folderIcons = { Home: 'user-home', Documents: 'folder-documents', Downloads: 'folder-download', Pictures: 'folder-pictures', Music: 'folder-music', Videos: 'folder-videos', Projects: 'folder-development', Trash: 'user-trash' };
  const notes = {
    'Field notes': { title: 'At home in the half-light.', body: '<p>DhampirOS by potemkin brings a Vampire Hunter D visual language to a custom Kicksecure-based Linux project.</p><h3>The Nocturne palette</h3><p>Midnight indigo for surfaces. Silver for text. Cold blue focus. Crimson in small, deliberate moments.</p><h3>Movement with a purpose</h3><p>The camera holds still while wind works through hair, the mane, cloth and grass. Rain falls through several depths. The interface settles after each action.</p><small>Project notes · visual preview</small>' },
    'Design language': { title: 'A quiet system, after dark.', body: '<p>Readable icons, clear focus and small changes of state. Gothic science fantasy in the artwork; restraint in the controls.</p><p>The scenes, identity marks, icons and cursor artwork shown here are the actual assets prepared for DhampirOS.</p><h3>One visual world</h3><p>Rainbound Hunter, Crimson Eclipse, Silver Nocturne and Threshold share the same indigo, silver and garnet palette.</p>' },
    'About DhampirOS': { title: 'DhampirOS by potemkin', body: '<p>An independent, Vampire Hunter D-inspired project based on Kicksecure and Debian, with LXQt/labwc-oriented visual resources.</p><h3>Current stage</h3><p>Pre-alpha. The artwork package and desktop defaults are being developed; a full OS image has not yet been runtime-verified end to end.</p><p>This desktop is an interactive visual preview in your browser.</p><p><a href="https://github.com/potemkin666/DhampirOS" target="_blank" rel="noopener noreferrer">Explore the project on GitHub ↗</a></p>' }
  };
  function filesContent() {
    const folder = state.folder;
    const sidebar = ['Home', 'Documents', 'Downloads', 'Pictures', 'Trash'].map(name => `<button type="button" data-folder="${name}" class="${folder === name ? 'is-selected' : ''}" title="${name}">${icon(folderIcons[name])}<span>${name}</span></button>`).join('');
    let tiles = '';
    if (folder === 'Home') tiles = ['Documents', 'Downloads', 'Pictures', 'Music', 'Videos', 'Projects'].map(name => `<button type="button" class="file-tile" data-folder="${name}">${icon(folderIcons[name])}<span>${name}</span></button>`).join('');
    else if (folder === 'Pictures') tiles = manifest.wallpapers.map(p => `<button type="button" class="file-tile" data-image="${p.id}"><img class="file-photo" src="${p.thumb}" alt=""><span>${p.name}</span></button>`).join('');
    else if (folder === 'Documents' || folder === 'Projects') tiles = Object.keys(notes).map(name => `<button type="button" class="file-tile" data-note="${name}">${icon('text-x-generic')}<span>${name}.txt</span></button>`).join('');
    else if (folder === 'Videos') tiles = `<button type="button" class="file-tile" data-motion-file>${icon('video-x-generic')}<span>Nocturne · 24s loop</span></button>`;
    const count = folder === 'Home' ? 6 : folder === 'Pictures' ? 4 : folder === 'Documents' || folder === 'Projects' ? 3 : folder === 'Videos' ? 1 : 0;
    const empty = `<div class="empty-folder"><img src="showcase/assets/states/empty-folder.svg" alt=""><h3>${folder === 'Trash' ? 'Nothing left behind.' : 'A quiet corner.'}</h3><p>${folder === 'Trash' ? 'The preview trash is empty.' : 'No files here in the preview.'}</p></div>`;
    return `<div class="file-app"><nav class="file-sidebar" aria-label="File locations">${sidebar}</nav><div class="file-main"><div class="file-toolbar"><button type="button" data-folder="Home" aria-label="Go to Home" title="Home">⌂</button><button type="button" data-folder="Home" aria-label="Go up to Home" title="Up">↑</button><code>/home/user${folder === 'Home' ? '' : '/' + folder}</code></div>${tiles ? `<div class="file-grid">${tiles}</div>` : empty}<div class="file-status">${count} ${count === 1 ? 'item' : 'items'} · ${folder}</div></div></div>`;
  }
  function settingsContent() {
    const tabs = ['wallpapers', 'motion', 'colour'];
    let body;
    if (state.settingsTab === 'motion') body = `<h3>A little weather.</h3><p>Rain, hair, mane, cloth and grass. A fixed camera.</p><label class="settings-row"><span><strong>Scene motion</strong><small>${state.wallpaper === 'rider' ? 'The Rainbound Hunter 24-second loop' : 'Available with Rainbound Hunter'}</small></span><input class="os-switch" type="checkbox" data-motion-setting ${state.motion && state.wallpaper === 'rider' ? 'checked' : ''} ${state.wallpaper !== 'rider' ? 'disabled' : ''}></label><label class="settings-row"><span><strong>Desktop icons</strong><small>Home, Artwork and Field notes</small></span><input class="os-switch" type="checkbox" data-icons-setting ${state.icons ? 'checked' : ''}></label><label class="settings-row"><span><strong>Preview sounds</strong><small>A quiet note for wallpaper and preview notices</small></span><input class="os-switch" type="checkbox" data-sound-setting ${state.sound ? 'checked' : ''}></label><div style="margin-top:20px"><button class="os-secondary" type="button" data-test-notice>Preview a notification</button></div>`;
    else if (state.settingsTab === 'colour') body = `<h3>Cold light. Small red signals.</h3><p>Choose the focus colour for this desktop preview.</p><div class="accent-options">${[['frost', 'Frost', '#8bb8da'], ['crimson', 'Crimson', '#c54a61'], ['silver', 'Silver', '#dde5ef']].map(([id, label, colour]) => `<button type="button" class="accent-option ${state.accent === id ? 'is-selected' : ''}" data-accent="${id}" aria-pressed="${state.accent === id}"><i style="--choice:${colour}"></i>${label}</button>`).join('')}</div><div style="margin-top:27px;padding:20px;border:1px solid var(--accent);background:#090c13;border-radius:4px"><p style="color:var(--accent-soft);margin:0 0 7px;font-size:12px">A clear point of focus.</p><p style="margin:0">The artwork keeps its own palette; only the preview's focus edges change.</p></div>`;
    else body = `<h3>Find your frontier.</h3><p>Choose an original DhampirOS scene.</p><div class="wallpaper-options">${manifest.wallpapers.map(p => `<button type="button" class="wallpaper-option ${state.wallpaper === p.id ? 'is-selected' : ''}" data-wallpaper="${p.id}" aria-pressed="${state.wallpaper === p.id}"><img src="${p.thumb}" alt=""><span>${p.name}${p.motion ? ' · motion' : ''}</span></button>`).join('')}</div>`;
    return `<div class="settings-app"><div class="settings-tabs">${tabs.map(id => `<button type="button" data-settings-tab="${id}" class="${id === state.settingsTab ? 'is-selected' : ''}">${id === 'wallpapers' ? 'Wallpapers' : id === 'motion' ? 'Motion & details' : 'Colour'}</button>`).join('')}</div>${body}</div>`;
  }
  function terminalContent() { return '<div class="terminal-app"><div class="terminal-note">Visual preview shell · commands stay inside this demonstration</div><div class="terminal-output"><div class="terminal-response">DhampirOS / Nocturne<br>Type <span class="terminal-prompt">help</span> to find your way around.</div></div><form class="terminal-form"><label>user@dhampiros ~ $</label><input type="text" aria-label="Preview terminal command" autocomplete="off" spellcheck="false"></form></div>'; }
  function terminalCommand(win, command) {
    const output = $('.terminal-output', win.el), line = document.createElement('div'); line.className = 'terminal-line';
    const prompt = document.createElement('span'); prompt.className = 'terminal-prompt'; prompt.textContent = 'user@dhampiros ~ $ '; line.append(prompt, document.createTextNode(command)); output.append(line);
    const clean = command.trim(), name = clean.toLowerCase(); let response = '';
    if (name === 'clear') { output.replaceChildren(); return; }
    if (name === 'help') response = 'A few local preview commands:\n  help       this little map\n  ls         look around\n  pwd        your preview location\n  whoami     the preview user\n  about      the project\n  neofetch   the Nocturne identity\n  date       your browser clock\n  clear      a clean slate';
    else if (name === 'ls' || name === 'ls -la') response = 'Documents/   Downloads/   Pictures/\nMusic/       Videos/      Projects/';
    else if (name === 'pwd') response = '/home/user';
    else if (name === 'whoami') response = 'user · visual preview';
    else if (name === 'date') response = new Date().toLocaleString();
    else if (name === 'about' || name === 'neofetch') response = 'DhampirOS by potemkin\n────────────────────────────\nBase      Kicksecure / Debian\nDirection LXQt / labwc\nTheme     Nocturne\nArtwork   Vampire Hunter D inspired\nStage     Pre-alpha visual preview';
    else if (name === 'cat field-notes.txt') response = 'At home in the half-light.\nMidnight indigo. Silver text. Cold blue focus.\nCrimson in small, deliberate moments.';
    else if (name) response = `“${clean}” is outside this small preview shell. Try help.`;
    const result = document.createElement('div'); result.className = 'terminal-response'; result.textContent = response; output.append(result); output.scrollTop = output.scrollHeight;
  }
  function bindTerminal(win) {
    const form = $('.terminal-form', win.el), input = $('input', form);
    form.addEventListener('submit', event => { event.preventDefault(); const command = input.value; input.value = ''; if (!command.trim()) return; win.history.push(command); win.historyIndex = win.history.length; terminalCommand(win, command); });
    input.addEventListener('keydown', event => { if (event.key === 'ArrowUp' || event.key === 'ArrowDown') { event.preventDefault(); win.historyIndex = Math.max(0, Math.min(win.history.length, win.historyIndex + (event.key === 'ArrowUp' ? -1 : 1))); input.value = win.history[win.historyIndex] || ''; } });
  }
  function renderApp(win) {
    const body = $('.os-window-body', win.el);
    if (win.id === 'welcome') body.innerHTML = welcomeContent();
    if (win.id === 'files') { body.innerHTML = filesContent(); $('.window-title-text', win.el).textContent = `Files — ${state.folder}`; }
    if (win.id === 'settings') body.innerHTML = settingsContent();
    if (win.id === 'terminal') { body.innerHTML = terminalContent(); bindTerminal(win); }
    if (win.id === 'notes') { const note = notes[win.context.note || 'Field notes'] || notes['Field notes']; body.innerHTML = `<article class="notes-app"><h2>${note.title}</h2>${note.body}</article>`; $('.window-title-text', win.el).textContent = win.context.note || 'Field notes'; }
    if (win.id === 'gallery') body.innerHTML = `<div class="gallery-app">${manifest.wallpapers.map(p => `<button type="button" class="gallery-image" data-image="${p.id}"><img src="${p.thumb}" alt=""><span>${p.name}</span></button>`).join('')}</div>`;
    if (win.id === 'viewer') { const p = wallpaper(win.context.wallpaper || state.wallpaper); body.innerHTML = `<div class="image-app"><img src="${p.src}" alt="${p.name}"><div class="image-actions"><span>${p.name}</span><button class="os-primary" type="button" data-wallpaper="${p.id}">Use wallpaper</button></div></div>`; $('.window-title-text', win.el).textContent = p.name; }
  }

  function renderInstaller() {
    const stages = [['welcome', 'Welcome'], ['keyboard', 'Keyboard'], ['storage', 'Storage'], ['users', 'User'], ['finished', 'Ready']];
    $('#installer-steps').innerHTML = stages.map(([id, title], i) => `<button class="installer-step ${state.installer === i ? 'is-current' : state.installer > i ? 'is-done' : ''}" type="button" data-install-stage="${i}" aria-label="Preview ${title} stage" aria-current="${state.installer === i ? 'step' : 'false'}"><img src="showcase/assets/installer/${id}.svg" alt=""><span>${title}</span></button>`).join('');
    let body;
    if (state.installer === 0) body = '<h3 class="installer-content-title">Welcome to DhampirOS.</h3><p class="installer-content-description">A few quiet steps into your own corner of the frontier.</p><label class="installer-field">Language<select><option>English</option><option>Deutsch</option><option>Français</option><option>Polski</option></select></label>';
    if (state.installer === 1) body = `<h3 class="installer-content-title">Make yourself understood.</h3><p class="installer-content-description">A glimpse of the keyboard and language surface.</p><label class="installer-field">Keyboard layout<select><option>English (UK)</option><option>English (US)</option><option>Deutsch</option></select></label><div class="keyboard-preview" aria-label="Illustrated keyboard">${'QWERTYUIOPASDFGHJKLZXCVBNM'.split('').map(c => `<kbd>${c}</kbd>`).join('')}</div>`;
    if (state.installer === 2) body = '<h3 class="installer-content-title">Room for the night.</h3><p class="installer-content-description">An illustrative storage layout. This preview never accesses a disk.</p><div class="storage-preview"><strong>Example installation disk</strong><small>Visual layout only</small><div class="storage-bar"><i></i><i></i></div><div class="storage-legend"><span>Boot area</span><span>System & files</span></div></div>';
    if (state.installer === 3) body = '<h3 class="installer-content-title">A face at the threshold.</h3><p class="installer-content-description">The account artwork keeps its place in the same visual world.</p><div class="installer-avatar-choices"><button type="button" data-avatar="hunter" class="is-selected" aria-label="Choose the hunter avatar"><img src="showcase/assets/brand/avatar-hunter.svg" alt="Hunter"></button><button type="button" data-avatar="sigil" aria-label="Choose the DhampirOS sigil avatar"><img src="showcase/assets/brand/dhampiros-sigil.svg" alt="DhampirOS sigil"></button></div><label class="installer-field">Preview name<input value="user" maxlength="24" aria-label="Illustrative user name"></label>';
    if (state.installer === 4) body = '<img class="install-complete-icon" src="showcase/assets/states/install-complete.svg" alt=""><h3 class="installer-content-title">The frontier awaits.</h3><p class="installer-content-description">That is the visual journey. Step into the interactive desktop to explore the artwork and windows.</p>';
    $('#installer-content').innerHTML = body; $('#installer-position').textContent = `${state.installer + 1} / 5`; $('#installer-back').disabled = state.installer === 0; $('#installer-next').textContent = state.installer === 4 ? 'Enter preview ↗' : 'Continue →';
  }
  function renderLibrary() {
    const query = $('#library-search').value.trim().toLowerCase(), category = $('#library-category').value;
    const matches = manifest.icons.filter(item => `${item.id} ${item.label}`.toLowerCase().includes(query) && (category === 'all' || item.category === category));
    $('#icon-library').innerHTML = matches.map(item => `<a class="library-icon" href="${item.src}" target="_blank" rel="noopener noreferrer" title="Open ${escape(item.label)} SVG"><img src="${item.src}" alt="" loading="lazy"><span>${escape(item.label)}</span></a>`).join('');
    $('#library-count').textContent = `${matches.length} / ${manifest.icons.length}`; $('#library-empty').hidden = matches.length > 0;
  }
  function renderWallpaperGallery() {
    $('#wallpaper-gallery').innerHTML = manifest.wallpapers.map(p => `<figure class="wallpaper-card"><img src="${p.src}" alt="${p.name}" loading="lazy">${p.motion ? '<span class="motion-badge">24 SECOND MOTION STUDY</span>' : ''}<figcaption><div><h3>${p.name}</h3><p>${p.caption}</p></div><button type="button" data-try-wallpaper="${p.id}">${p.id === state.wallpaper ? 'On the desktop ✓' : 'Try this wallpaper ↗'}</button></figcaption></figure>`).join('');
  }
  function updateSoundButton() { const button = $('#sound-toggle'); button.setAttribute('aria-pressed', String(state.sound)); button.setAttribute('aria-label', `${state.sound ? 'Disable' : 'Enable'} preview notification sounds`); button.title = `Preview sounds ${state.sound ? 'on' : 'off'}`; $('img', button).src = `showcase/assets/panel/audio-volume-${state.sound ? 'high' : 'muted'}.svg`; }
  function resetPreview() { for (const win of state.windows.values()) win.el.remove(); state.windows.clear(); state.active = null; state.folder = 'Home'; state.settingsTab = 'wallpapers'; state.motion = !reduced.matches; state.accent = 'frost'; state.icons = true; state.sound = false; state.installer = 0; $('.desktop-shortcuts').hidden = false; $('#view-desktop').dataset.motionOverride = 'false'; applyAccent('frost'); applyWallpaper('rider', false); updateSoundButton(); renderInstaller(); setView('desktop'); openApp('welcome'); toast('A fresh corner of the night.'); }

  function bindEvents() {
    $('#preview-start').addEventListener('click', toggleLauncher); $('#launcher-search').addEventListener('input', event => launcherApps(event.target.value));
    document.addEventListener('pointerdown', event => { if (!$('#launcher').hidden && !event.target.closest('#launcher,#preview-start')) hideLauncher(false); });
    document.addEventListener('keydown', event => { if (event.key === 'Escape' && !$('#launcher').hidden) { hideLauncher(); event.preventDefault(); } });
    for (const tab of $$('[data-view]')) { tab.addEventListener('click', () => setView(tab.dataset.view)); tab.addEventListener('keydown', event => { if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return; event.preventDefault(); const tabs = $$('[data-view]'), index = tabs.indexOf(tab), next = tabs[(index + (event.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length]; setView(next.dataset.view); next.focus(); }); }
    document.addEventListener('click', event => {
      const button = event.target.closest('button,a'); if (!button) return;
      if (button.dataset.open) openApp(button.dataset.open, button.dataset.settingsTab ? { tab: button.dataset.settingsTab } : {});
      if (button.dataset.windowAction) { const win = state.windows.get(button.closest('.os-window').dataset.app); if (button.dataset.windowAction === 'close') closeWindow(win.id); if (button.dataset.windowAction === 'maximize') maximizeWindow(win); if (button.dataset.windowAction === 'minimize') { win.minimized = true; win.el.hidden = true; state.active = null; updateTasks(); } }
      if (button.dataset.task) { const win = state.windows.get(button.dataset.task); if (state.active === win.id && !win.minimized) { win.minimized = true; win.el.hidden = true; state.active = null; updateTasks(); } else focusWindow(win); }
      if (button.dataset.folder) { state.folder = button.dataset.folder; const win = state.windows.get('files') || openApp('files'); renderApp(win); }
      if (button.dataset.image) openApp('viewer', { wallpaper: button.dataset.image });
      if (button.dataset.note) openApp('notes', { note: button.dataset.note });
      if (button.dataset.wallpaper) applyWallpaper(button.dataset.wallpaper);
      if (button.dataset.tryWallpaper) { setView('desktop', true); applyWallpaper(button.dataset.tryWallpaper, false); const win = state.windows.get('welcome'); if (win) closeWindow('welcome'); toast(wallpaper(button.dataset.tryWallpaper).name); }
      if (button.dataset.accent) applyAccent(button.dataset.accent);
      if (button.dataset.settingsTab && !button.dataset.open) { state.settingsTab = button.dataset.settingsTab; refreshSettings(); }
      if (button.hasAttribute('data-login')) setView('login');
      if (button.hasAttribute('data-enter-desktop')) { setView('desktop'); openApp('welcome'); }
      if (button.hasAttribute('data-motion-file')) { applyWallpaper('rider', false); state.motion = true; $('#view-desktop').dataset.motionOverride = 'true'; updateVideos(); toast('Nocturne · the 24-second motion study'); }
      if (button.hasAttribute('data-test-notice')) toast('A quiet note from the Nocturne desktop.');
      if (button.dataset.installStage !== undefined) { state.installer = Number(button.dataset.installStage); renderInstaller(); }
      if (button.dataset.avatar) { state.avatar = button.dataset.avatar; for (const b of $$('[data-avatar]')) b.classList.toggle('is-selected', b === button); }
    });
    $('#desktop-shell').addEventListener('change', event => {
      if (event.target.hasAttribute('data-motion-setting')) { state.motion = event.target.checked; $('#view-desktop').dataset.motionOverride = String(state.motion); updateVideos(); }
      if (event.target.hasAttribute('data-icons-setting')) { state.icons = event.target.checked; $('.desktop-shortcuts').hidden = !state.icons; }
      if (event.target.hasAttribute('data-sound-setting')) { state.sound = event.target.checked; updateSoundButton(); }
    });
    $('#sound-toggle').addEventListener('click', () => { state.sound = !state.sound; updateSoundButton(); refreshSettings(); toast(`Preview sounds ${state.sound ? 'on' : 'off'}.`); });
    $('#installer-next').addEventListener('click', () => { if (state.installer === 4) { setView('desktop'); openApp('welcome'); } else { state.installer++; renderInstaller(); } });
    $('#installer-back').addEventListener('click', () => { state.installer = Math.max(0, state.installer - 1); renderInstaller(); });
    $('#library-search').addEventListener('input', renderLibrary); $('#library-category').addEventListener('change', renderLibrary);
    $('#reset-preview').addEventListener('click', resetPreview);
    $('#fullscreen-preview').addEventListener('click', async () => { try { if (document.fullscreenElement) await document.exitFullscreen(); else await $('#desktop-shell').requestFullscreen(); } catch { toast('Fullscreen is unavailable in this browser view.', true); } });
    window.addEventListener('resize', () => { for (const win of state.windows.values()) if (!win.maximized) moveWindow(win, win.el.offsetLeft, win.el.offsetTop); });
  }
  async function init() {
    const response = await fetch('showcase/visuals.json'); if (!response.ok) throw new Error('Visual asset manifest could not be loaded.');
    manifest = await response.json(); iconMap = new Map(manifest.icons.map(item => [item.id, item]));
    launcherApps(); renderInstaller(); renderLibrary(); renderWallpaperGallery(); bindEvents(); observeVideos(); openApp('welcome');
    const clock = () => { $('#desktop-clock').textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false }); }; clock(); setInterval(clock, 30000);
    document.documentElement.dataset.previewReady = 'true';
    window.DhampirPreview = { get view() { return state.view; }, get wallpaper() { return state.wallpaper; }, get windows() { return [...state.windows.keys()]; }, setView, openApp, reset: resetPreview };
  }
  init().catch(error => { console.error(error); toast('The preview could not load. The artwork below is still available.', true); });
})();
