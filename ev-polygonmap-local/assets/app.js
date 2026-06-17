// Shared app module: data normalization, settings, reviews.
// Stored in localStorage (single-device). Swap with API calls to share across users.

window.EVApp = (function () {
  const KEY_LOGO = 'evmap.logo';
  const KEY_BRAND = 'evmap.brand';
  const KEY_ADMIN_PASS = 'evmap.admin.pass';
  const KEY_ADMIN_SESSION = 'evmap.admin.session';
  const KEY_REVIEWS_PREFIX = 'evmap.reviews.';   // approved
  const KEY_PENDING_PREFIX = 'evmap.pending.';   // awaiting approval
  const KEY_THEME = 'evmap.theme';
  const KEY_BRAND_LOGO_PREFIX = 'evmap.brand.logo.';
  const KEY_STATION_OVERRIDE_PREFIX = 'evmap.station.override.';
  const KEY_ABOUT = 'evmap.about';
  const KEY_SUBMISSIONS_PREFIX = 'evmap.sub.';
  const KEY_TRAFFIC = 'evmap.traffic';
  const KEY_STATION_VIEWS_PREFIX = 'evmap.sv.';
  const DEFAULT_BRAND = 'ev.polygonmap.com';
  const DEFAULT_PASS = 'admin'; // user prompted to change on first login

  // ── Station overrides (admin edits applied on top of static data) ──
  function getStationOverride(stationId) {
    try { return JSON.parse(localStorage.getItem(KEY_STATION_OVERRIDE_PREFIX + stationId) || 'null'); }
    catch { return null; }
  }
  function setStationOverride(stationId, data) {
    if (data && Object.keys(data).length) {
      localStorage.setItem(KEY_STATION_OVERRIDE_PREFIX + stationId, JSON.stringify(data));
    } else {
      localStorage.removeItem(KEY_STATION_OVERRIDE_PREFIX + stationId);
    }
  }

  function totalHeads(chargers, type) {
    return (chargers || []).reduce((n, c) => {
      const heads = c.heads ?? (Array.isArray(c.guns) ? c.guns.length : 0);
      return n + (c.type === type ? (heads || 0) : 0);
    }, 0);
  }

  function priceFrom(source, fallback) {
    const src = source || {};
    const srcPrice = src.price || src.pricing || {};
    const fb = fallback || {};
    const fbPrice = fb.price || fb.pricing || {};
    return {
      day: srcPrice.day ?? src.day ?? src.priceDay ?? src.price_day ?? src.dayPrice ?? src.day_price ??
        fbPrice.day ?? fb.day ?? fb.priceDay ?? fb.price_day ?? fb.dayPrice ?? fb.day_price ?? null,
      night: srcPrice.night ?? src.night ?? src.priceNight ?? src.price_night ?? src.nightPrice ?? src.night_price ??
        fbPrice.night ?? fb.night ?? fb.priceNight ?? fb.price_night ?? fb.nightPrice ?? fb.night_price ?? null,
      currency: srcPrice.currency || src.currency || fbPrice.currency || fb.currency || 'THB',
      unit: srcPrice.unit || src.unit || fbPrice.unit || fb.unit || 'kWh',
    };
  }

  function normalizeCharger(charger) {
    const c = { ...(charger || {}) };
    const explicitGuns = Array.isArray(c.guns) ? c.guns : [];
    const heads = Math.max(parseInt(c.heads || 0, 10), explicitGuns.length, 1);
    c.heads = heads;
    c.guns = Array.from({ length: heads }, (_, i) => {
      const gun = explicitGuns[i] || {};
      return {
        ...gun,
        label: gun.label || gun.name || String(i + 1),
        price: priceFrom(gun, c),
      };
    });
    return c;
  }

  function normalizeChargers(chargers) {
    return (chargers || []).map(normalizeCharger);
  }

  function slugify(str) {
    return (str || '')
      .replace(/\s*\([^)]*\)/g, '')   // strip parenthetical suffixes
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')    // non-alphanumeric → hyphen
      .replace(/^-+|-+$/g, '')         // trim leading/trailing hyphens
      .substring(0, 80) || 'station';
  }

  function loadStations() {
    const stations = [];
    const slugCount = {};
    function makeId(provider, name) {
      const base = provider + '-' + slugify(name);
      const n = (slugCount[base] = (slugCount[base] || 0) + 1);
      return n === 1 ? base : `${base}-${n}`;
    }

    (window.SPARK_DATA || []).forEach(s => stations.push({
      id: makeId('spark', s.name), provider: 'spark', providerLabel: 'Spark / BCP',
      name: s.name, lat: s.lat, lon: s.lon,
      province: s.province || '', district: s.district || '', address: s.address || '',
      chargers: normalizeChargers(s.chargers),
      dc: s.dc_total_heads ?? totalHeads(s.chargers, 'DC'),
      ac: s.ac_total_heads ?? totalHeads(s.chargers, 'AC'),
    }));
    (window.IGREEN_DATA || []).forEach(s => stations.push({
      id: makeId('igreen', s.name), provider: 'igreen', providerLabel: 'iGreen+',
      name: s.name, lat: s.lat, lon: s.lon,
      province: '', district: '', address: '',
      chargers: normalizeChargers(s.chargers),
      dc: totalHeads(s.chargers, 'DC'), ac: totalHeads(s.chargers, 'AC'),
    }));
    (window.PTT_DATA || []).forEach(s => stations.push({
      id: makeId('ptt', s.name), provider: 'ptt', providerLabel: 'PTT EV',
      name: s.name, lat: s.lat, lon: s.lon,
      province: '', district: '', address: '',
      chargers: normalizeChargers(s.chargers),
      dc: totalHeads(s.chargers, 'DC'), ac: totalHeads(s.chargers, 'AC'),
    }));
    return stations.filter(s =>
      typeof s.lat === 'number' && typeof s.lon === 'number' &&
      s.lat > 5 && s.lat < 25 && s.lon > 95 && s.lon < 110
    ).map(s => {
      const ov = getStationOverride(s.id);
      return ov ? { ...s, ...ov, id: s.id, provider: s.provider, providerLabel: s.providerLabel, lat: s.lat, lon: s.lon } : s;
    });
  }

  // ---------- Theme ----------
  function getTheme() { return localStorage.getItem(KEY_THEME) || 'light'; }
  function setTheme(v) {
    localStorage.setItem(KEY_THEME, v);
    document.documentElement.setAttribute('data-theme', v);
  }

  // ---------- Branding ----------
  function getLogo()  { return localStorage.getItem(KEY_LOGO) || 'assets/logo-icon.svg'; }
  function setLogo(v) {
    try {
      if (v) localStorage.setItem(KEY_LOGO, v); else localStorage.removeItem(KEY_LOGO);
      return true;
    } catch (e) { return false; }
  }
  function getBrand() { return localStorage.getItem(KEY_BRAND) || DEFAULT_BRAND; }
  function setBrand(v){ localStorage.setItem(KEY_BRAND, v || DEFAULT_BRAND); }

  function getBrandLogo(provider) { return localStorage.getItem(KEY_BRAND_LOGO_PREFIX + provider) || ''; }
  function setBrandLogo(provider, v) {
    try {
      if (v) localStorage.setItem(KEY_BRAND_LOGO_PREFIX + provider, v);
      else localStorage.removeItem(KEY_BRAND_LOGO_PREFIX + provider);
      return true;
    } catch (e) { return false; }
  }
  function storageUsedKB() {
    try {
      return Math.round(Object.keys(localStorage)
        .filter(k => k.startsWith('evmap.'))
        .reduce((n, k) => n + (localStorage.getItem(k) || '').length, 0) / 1024);
    } catch (e) { return 0; }
  }

  // ── Traffic & station view tracking (localStorage, per-device) ──
  function recordPageView(page) {
    const sessionKey = 'evmap.session';
    const isNewSession = !sessionStorage.getItem(sessionKey);
    if (isNewSession) sessionStorage.setItem(sessionKey, '1');

    const today = new Date().toISOString().slice(0, 10);
    let t;
    try { t = JSON.parse(localStorage.getItem(KEY_TRAFFIC) || 'null') || { total: 0, sessions: 0, weekly: [] }; }
    catch { t = { total: 0, sessions: 0, weekly: [] }; }

    t.total = (t.total || 0) + 1;
    if (isNewSession) t.sessions = (t.sessions || 0) + 1;

    const weekEntry = (t.weekly || []).find(e => e.d === today);
    if (weekEntry) weekEntry.c++;
    else t.weekly = [...(t.weekly || []), { d: today, c: 1 }];
    const cutoff = new Date(); cutoff.setDate(cutoff.getDate() - 7);
    t.weekly = t.weekly.filter(e => new Date(e.d) >= cutoff);

    try { localStorage.setItem(KEY_TRAFFIC, JSON.stringify(t)); } catch {}
  }

  function getTrafficStats() {
    try { return JSON.parse(localStorage.getItem(KEY_TRAFFIC) || 'null') || { total: 0, sessions: 0, weekly: [] }; }
    catch { return { total: 0, sessions: 0, weekly: [] }; }
  }

  function recordStationView(stationId) {
    const key = KEY_STATION_VIEWS_PREFIX + stationId;
    const n = parseInt(localStorage.getItem(key) || '0', 10) + 1;
    try { localStorage.setItem(key, String(n)); } catch {}
    recordPageView('station');
  }

  function getStationViews(stationId) {
    return parseInt(localStorage.getItem(KEY_STATION_VIEWS_PREFIX + stationId) || '0', 10);
  }

  function getTopStations(stations, n) {
    return stations
      .map(s => ({ ...s, views: getStationViews(s.id) }))
      .filter(s => s.views > 0)
      .sort((a, b) => b.views - a.views)
      .slice(0, n || 10);
  }

  // ── About page content ──
  function getAbout() {
    try { return JSON.parse(localStorage.getItem(KEY_ABOUT) || 'null'); }
    catch { return null; }
  }
  function setAbout(data) {
    try { localStorage.setItem(KEY_ABOUT, JSON.stringify(data)); return true; }
    catch { return false; }
  }

  // ── Form submissions (interested / add-station) ──
  function addSubmission(type, data) {
    const list = getSubmissions(type);
    const item = { id: 'sub_' + Date.now() + '_' + Math.floor(Math.random() * 1e4), ...data, t: Date.now() };
    list.unshift(item);
    try { localStorage.setItem(KEY_SUBMISSIONS_PREFIX + type, JSON.stringify(list)); return item; }
    catch { return null; }
  }
  function getSubmissions(type) {
    try { return JSON.parse(localStorage.getItem(KEY_SUBMISSIONS_PREFIX + type) || '[]'); }
    catch { return []; }
  }
  function deleteSubmission(type, id) {
    const list = getSubmissions(type).filter(s => s.id !== id);
    try { localStorage.setItem(KEY_SUBMISSIONS_PREFIX + type, JSON.stringify(list)); }
    catch {}
  }

  function renderBrand(el, opts = {}) {
    if (!el) return;
    const logo = getLogo();
    const brand = getBrand();
    el.innerHTML = '';
    if (logo) {
      const img = document.createElement('img');
      img.src = logo; img.alt = brand;
      img.className = 'brand-logo';
      img.onerror = () => { img.src = 'assets/logo-icon.svg'; };
      el.appendChild(img);
    } else {
      const dot = document.createElement('span');
      dot.className = 'brand-dot';
      el.appendChild(dot);
    }
    if (opts.showText !== false) {
      const txt = document.createElement('span');
      txt.className = 'brand-text';
      txt.textContent = brand;
      el.appendChild(txt);
    }
    document.title = document.title.includes('—')
      ? document.title.replace(/—.*$/, '— ' + brand)
      : brand;
  }

  // ---------- Admin auth ----------
  function getPass() { return localStorage.getItem(KEY_ADMIN_PASS) || DEFAULT_PASS; }
  function setPass(v){ localStorage.setItem(KEY_ADMIN_PASS, v); }
  function isAdmin() { return sessionStorage.getItem(KEY_ADMIN_SESSION) === '1'; }
  function login(p)  {
    if (p === getPass()) { sessionStorage.setItem(KEY_ADMIN_SESSION, '1'); return true; }
    return false;
  }
  function logout()  { sessionStorage.removeItem(KEY_ADMIN_SESSION); }

  // ---------- Reviews ----------
  function _read(key) { try { return JSON.parse(localStorage.getItem(key) || '[]'); } catch { return []; } }
  function _write(key, v) { localStorage.setItem(key, JSON.stringify(v)); }

  function getApproved(stationId) { return _read(KEY_REVIEWS_PREFIX + stationId); }
  function getPending(stationId)  { return _read(KEY_PENDING_PREFIX + stationId); }

  function submitReview(stationId, review) {
    const list = getPending(stationId);
    const item = { id: 'r_' + Date.now() + '_' + Math.floor(Math.random()*1e4), ...review, t: Date.now() };
    list.unshift(item);
    _write(KEY_PENDING_PREFIX + stationId, list);
    return item;
  }
  function approveReview(stationId, reviewId) {
    const pending = getPending(stationId);
    const idx = pending.findIndex(r => r.id === reviewId);
    if (idx === -1) return false;
    const [item] = pending.splice(idx, 1);
    item.approvedAt = Date.now();
    const approved = getApproved(stationId);
    approved.unshift(item);
    _write(KEY_PENDING_PREFIX + stationId, pending);
    _write(KEY_REVIEWS_PREFIX + stationId, approved);
    return true;
  }
  function rejectReview(stationId, reviewId) {
    const pending = getPending(stationId);
    const next = pending.filter(r => r.id !== reviewId);
    _write(KEY_PENDING_PREFIX + stationId, next);
    return true;
  }
  function deleteApproved(stationId, reviewId) {
    const approved = getApproved(stationId);
    const next = approved.filter(r => r.id !== reviewId);
    _write(KEY_REVIEWS_PREFIX + stationId, next);
    return true;
  }

  function allPendingByStation() {
    const out = [];
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k && k.startsWith(KEY_PENDING_PREFIX)) {
        const sid = k.slice(KEY_PENDING_PREFIX.length);
        const list = _read(k);
        if (list.length) out.push({ stationId: sid, reviews: list });
      }
    }
    return out;
  }
  function allApprovedByStation() {
    const out = [];
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k && k.startsWith(KEY_REVIEWS_PREFIX)) {
        const sid = k.slice(KEY_REVIEWS_PREFIX.length);
        const list = _read(k);
        if (list.length) out.push({ stationId: sid, reviews: list });
      }
    }
    return out;
  }

  // ---------- Util ----------
  function cleanName(name) {
    return (name || '').replace(/\s*\([^)]*\)/g, '').trim();
  }

  function escapeHtml(v) {
    return (v ?? '').toString().replace(/[&<>"']/g, c => ({
      '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
    }[c]));
  }
  function googleMapsUrl(s) {
    return `https://www.google.com/maps/search/?api=1&query=${s.lat},${s.lon}`;
  }
  function stationUrl(s) {
    return `station.html?id=${encodeURIComponent(s.id)}`;
  }
  function timeAgo(t) {
    const sec = Math.floor((Date.now() - t) / 1000);
    const tr = window.EVi18n ? window.EVi18n.t.bind(window.EVi18n) : null;
    if (sec < 60)     return tr ? tr('time_just_now') : 'just now';
    if (sec < 3600)   return tr ? tr('time_m_ago', { n: Math.floor(sec/60) })   : Math.floor(sec/60) + 'm ago';
    if (sec < 86400)  return tr ? tr('time_h_ago', { n: Math.floor(sec/3600) }) : Math.floor(sec/3600) + 'h ago';
    if (sec < 604800) return tr ? tr('time_d_ago', { n: Math.floor(sec/86400) }): Math.floor(sec/86400) + 'd ago';
    return new Date(t).toLocaleDateString();
  }

  return {
    loadStations, renderBrand,
    getLogo, setLogo, getBrand, setBrand,
    getBrandLogo, setBrandLogo,
    getTheme, setTheme,
    getPass, setPass, isAdmin, login, logout,
    submitReview, getApproved, getPending,
    approveReview, rejectReview, deleteApproved,
    allPendingByStation, allApprovedByStation,
    getStationOverride, setStationOverride,
    getAbout, setAbout,
    addSubmission, getSubmissions, deleteSubmission,
    recordPageView, getTrafficStats, recordStationView, getStationViews, getTopStations,
    escapeHtml, cleanName, googleMapsUrl, stationUrl, timeAgo,
    storageUsedKB,
    DEFAULT_PASS,
  };
})();

// ─── Cookie / PDPA Consent Banner ────────────────────────────────────────────
(function () {
  const KEY = 'evmap.consent';
  if (localStorage.getItem(KEY)) return;

  function init() {
    const banner = document.createElement('div');
    banner.className = 'cookie-banner';
    banner.id = 'evCookieBanner';
    banner.innerHTML =
      '<div class="cookie-banner-inner">' +
        '<span class="cookie-icon">🛡️</span>' +
        '<div class="cookie-text" data-i18n-html="cookie_text">' +
          (window.EVi18n ? window.EVi18n.t('cookie_text') : 'This site uses Local Storage to remember settings and store reviews on your device.') +
        '</div>' +
        '<div class="cookie-actions">' +
          '<button class="btn btn-ghost btn-sm" id="evCookieDecline" data-i18n="cookie_decline">' + (window.EVi18n ? window.EVi18n.t('cookie_decline') : 'Decline') + '</button>' +
          '<button class="btn btn-primary btn-sm" id="evCookieAccept" data-i18n="cookie_accept">' + (window.EVi18n ? window.EVi18n.t('cookie_accept') : 'Accept') + '</button>' +
        '</div>' +
      '</div>';

    function dismiss(value) {
      localStorage.setItem(KEY, value);
      banner.classList.add('hiding');
      setTimeout(function () { banner.remove(); }, 260);
    }

    document.body.appendChild(banner);
    document.getElementById('evCookieAccept').addEventListener('click', function () { dismiss('accepted'); });
    document.getElementById('evCookieDecline').addEventListener('click', function () { dismiss('declined'); });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

