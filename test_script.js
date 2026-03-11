// ═══════════════════════════════════════════════════════════════════════════════════════
// CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════════════════

function resolveApiUrl() {
  // Optional override:
  // window.__CREATOROS_API_URL__ = 'https://api.example.com/api'
  // localStorage.setItem('creatoros_api_url', 'https://api.example.com/api')
  const explicitUrl = window.__CREATOROS_API_URL__ || localStorage.getItem('creatoros_api_url');
  if (explicitUrl) {
    const cleaned = explicitUrl.replace(/\/+$/, '');
    // Auto-migrate old local override from older ports -> localhost:5004.
    if (cleaned === 'http://localhost:5000/api' || cleaned === 'http://127.0.0.1:5000/api' || 
        cleaned === 'http://localhost:5001/api' || cleaned === 'http://127.0.0.1:5001/api') {
      const migrated = 'http://localhost:5004/api';
      localStorage.setItem('creatoros_api_url', migrated);
      return migrated;
    }
    return cleaned;
  }
  
  if (window.location.protocol === 'file:') {
    return 'http://localhost:5004/api';
  }
  
  const { protocol, hostname, origin, port } = window.location;
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    if (port === '5004') return `${origin}/api`;
    return `${protocol}//${hostname}:5004/api`;
  }
  
  return `${origin}/api`;
}

const API_URL = resolveApiUrl();
let currentUser = null;
let accessToken = localStorage.getItem('access_token');
let latestConnectedPlatforms = [];
let syncInProgress = false;
let autoSyncTimer = null;
let platformAnalyticsLoading = false;
let activePlatformAnalytics = null;
let selectedUploadFiles = [];
let publishScheduleMode = 'now';
let selectedSchedulerFiles = [];
let queuePollTimer = null;
let queueStatusMap = {};
let publishedVideoStatsCache = null;

function showToast(title, message = '', type = 'info', ttlMs = 2600) {
  const wrap = document.getElementById('toast-wrap');
  if (!wrap) {
    alert(`${title}${message ? `\n${message}` : ''}`);
    return;
  }
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <div class="toast-title">${escapeHtml(title)}</div>
    ${message ? `<div class="toast-body">${escapeHtml(message)}</div>` : ''}
  `;
  wrap.appendChild(toast);
  setTimeout(() => toast.remove(), ttlMs);
}

function setButtonLoading(buttonId, loadingText, isLoading) {
  const btn = document.getElementById(buttonId);
  if (!btn) return;
  if (!btn.dataset.defaultLabel) btn.dataset.defaultLabel = btn.innerHTML;
  if (isLoading) {
    btn.disabled = true;
    btn.innerHTML = loadingText;
  } else {
    btn.disabled = false;
    btn.innerHTML = btn.dataset.defaultLabel;
  }
}

function stopQueuePolling() {
  if (queuePollTimer) {
    clearInterval(queuePollTimer);
    queuePollTimer = null;
  }
}

function startQueuePolling(durationMs = 90000, intervalMs = 3000) {
  stopQueuePolling();
  const endsAt = Date.now() + durationMs;
  queuePollTimer = setInterval(async () => {
    await loadPostQueue();
    if (Date.now() > endsAt) stopQueuePolling();
  }, intervalMs);
}

function postVideoLink(post) {
  if (!post || !post.external_post_id) return '';
  const id = String(post.external_post_id);
  if (post.platform === 'youtube' && !id.startsWith('sim_')) {
    return `https://www.youtube.com/watch?v=${encodeURIComponent(id)}`;
  }
  return '';
}

function hydrateAuthFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const token = params.get('token');
  if (!token) return;
  
  accessToken = token;
  localStorage.setItem('access_token', token);
  
  ['token', 'user', 'provider', 'auth'].forEach(key => params.delete(key));
  const nextQuery = params.toString();
  const cleanUrl = `${window.location.pathname}${nextQuery ? `?${nextQuery}` : ''}${window.location.hash || ''}`;
  window.history.replaceState({}, document.title, cleanUrl);
}

function handleOAuthResultFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const oauth = params.get('oauth');
  const platform = params.get('platform');
  const error = params.get('error');
  if (!oauth || !platform) return;
  
  if (oauth === 'success') {
    showToast('Platform Connected', `${platform} connected successfully.`, 'success');
    setTimeout(async () => {
      await refreshLiveStats({ silent: true, force: true });
    }, 200);
  } else {
    showToast('Connect Failed', error || `Failed to connect ${platform}.`, 'error', 4500);
  }
  
  ['oauth', 'platform', 'error'].forEach(key => params.delete(key));
  const nextQuery = params.toString();
  const cleanUrl = `${window.location.pathname}${nextQuery ? `?${nextQuery}` : ''}${window.location.hash || ''}`;
  window.history.replaceState({}, document.title, cleanUrl);
}

async function parseJsonSafely(response) {
  const contentType = response.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) return {};
  
  try {
    return await response.json();
  } catch (error) {
    return {};
  }
}

function getNetworkErrorMessage(error) {
  const mixedContentBlocked = window.location.protocol === 'https:' && API_URL.startsWith('http://');
  if (mixedContentBlocked) {
    return `Blocked by browser security (HTTPS page calling HTTP API). Use an HTTPS API URL instead of ${API_URL}.`;
  }
  
  if (error && error.name === 'TypeError') {
    return `Cannot reach backend at ${API_URL}. Make sure backend server is running.`;
  }
  
  return 'Network error. Please try again.';
}

// Check if user is logged in
async function checkAuth() {
  if (!accessToken) {
    showAuthScreen();
    return;
  }
  
  try {
    const response = await fetch(`${API_URL}/auth/verify-token`, {
      headers: { 'Authorization': `Bearer ${accessToken}` }
    });
    
    if (response.ok) {
      const data = await parseJsonSafely(response);
      currentUser = data.user;
      showAppScreen();
      initializeApp();
    } else {
      accessToken = null;
      localStorage.removeItem('access_token');
      showAuthScreen();
    }
  } catch (error) {
    console.error('Auth check error:', error);
    showAuthScreen();
  }
}

function showAuthScreen() {
  document.getElementById('auth-screen').classList.remove('hidden');
  document.getElementById('app').classList.add('hidden');
}

function showAppScreen() {
  document.getElementById('auth-screen').classList.add('hidden');
  document.getElementById('app').classList.remove('hidden');
}

// ═══════════════════════════════════════════════════════════════════════════════════════
// AUTHENTICATION API CALLS
// ═══════════════════════════════════════════════════════════════════════════════════════

async function handleLogin(event) {
  event.preventDefault();
  
  const email = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-pw').value;
  const errorEl = document.getElementById('login-error');
  const loginBtn = document.getElementById('login-btn');
  
  if (!email || !password) {
    showError(errorEl, 'Please fill in all fields');
    return;
  }
  
  loginBtn.disabled = true;
  loginBtn.textContent = 'Signing in...';
  
  try {
    const response = await fetch(`${API_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    
    const data = await parseJsonSafely(response);
    
    if (!response.ok) {
      showError(errorEl, data.error || 'Login failed');
      loginBtn.disabled = false;
      loginBtn.textContent = 'Sign In to CreatorOS';
      return;
    }
    
    // Store token and user
    accessToken = data.access_token;
    currentUser = data.user;
    localStorage.setItem('access_token', accessToken);
    
    showAppScreen();
    initializeApp();
    
    // Clear form
    document.getElementById('login-email').value = '';
    document.getElementById('login-pw').value = '';
  } catch (error) {
    console.error('Login error:', error);
    showError(errorEl, getNetworkErrorMessage(error));
    loginBtn.disabled = false;
    loginBtn.textContent = 'Sign In to CreatorOS';
  }
}

async function handleRegister(event) {
  event.preventDefault();
  
  const name = document.getElementById('reg-name').value.trim();
  const email = document.getElementById('reg-email').value.trim();
  const password = document.getElementById('reg-pw').value;
  const referral_code = document.getElementById('reg-ref').value.trim();
  const errorEl = document.getElementById('register-error');
  const registerBtn = document.getElementById('register-btn');
  
  if (!name || !email || !password) {
    showError(errorEl, 'Please fill in all required fields');
    return;
  }
  
  if (password.length < 10) {
    showError(errorEl, 'Password must be at least 10 characters and include upper/lowercase, number, special character');
    return;
  }
  
  registerBtn.disabled = true;
  registerBtn.textContent = 'Creating account...';
  
  try {
    const response = await fetch(`${API_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password, referral_code })
    });
    
    const data = await parseJsonSafely(response);
    
    if (!response.ok) {
      showError(errorEl, data.error || 'Registration failed');
      registerBtn.disabled = false;
      registerBtn.textContent = 'Create Account — Get 350 Credits Free';
      return;
    }
    
    // Auto-login
    accessToken = data.access_token;
    currentUser = data.user;
    localStorage.setItem('access_token', accessToken);
    
    showAppScreen();
    initializeApp();
    
    // Clear form
    document.getElementById('reg-name').value = '';
    document.getElementById('reg-email').value = '';
    document.getElementById('reg-pw').value = '';
    document.getElementById('reg-ref').value = '';
  } catch (error) {
    console.error('Registration error:', error);
    showError(errorEl, getNetworkErrorMessage(error));
    registerBtn.disabled = false;
    registerBtn.textContent = 'Create Account — Get 350 Credits Free';
  }
}

function showError(el, msg) {
  el.textContent = msg;
  el.style.display = 'block';
  setTimeout(() => el.style.display = 'none', 4000);
}

function showAuthTab(tab) {
  document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.auth-form').forEach(f => f.classList.add('hidden'));
  
  document.querySelector(`[onclick="showAuthTab('${tab}')"]`).classList.add('active');
  document.getElementById(`form-${tab}`).classList.remove('hidden');
}

function togglePw(inputId, btn) {
  const input = document.getElementById(inputId);
  if (input.type === 'password') {
    input.type = 'text';
    btn.innerHTML = '<svg width="16" height="16" fill="none" stroke="var(--lime)" stroke-width="2" viewBox="0 0 24 24"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/><line x1="1" y1="1" x2="23" y2="23"/></svg>';
  } else {
    input.type = 'password';
    btn.innerHTML = '<svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
  }
}

// ═══════════════════════════════════════════════════════════════════════════════════════
// APP FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════════════

async function initializeApp() {
  if (!currentUser) return;
  
  // Set user info
  document.getElementById('credit-count').textContent = currentUser.credits || 0;
  document.getElementById('nav-user-avatar').textContent = currentUser.name.charAt(0).toUpperCase();
  document.getElementById('hero-greeting').textContent = `Welcome back, ${currentUser.name}! 🚀 Generate content, analyze trends, and publish — all from one place.`;
  document.getElementById('setting-name').value = currentUser.name;
  document.getElementById('setting-email').value = currentUser.email;
  
  // Load connected platforms
  await loadConnectedPlatforms();
  try {
    publishedVideoStatsCache = await loadPublishedVideoAnalytics();
    updatePlatformViewSummary(publishedVideoStatsCache);
  } catch (error) {
    console.error('Initial published views load failed:', error);
  }

  // Pull latest numbers first, then paint cards
  await refreshLiveStats({ silent: true });
  await loadPostQueue();

  if (autoSyncTimer) clearInterval(autoSyncTimer);
  autoSyncTimer = setInterval(() => {
    refreshLiveStats({ silent: true });
    processDuePosts(true);
  }, 120000);
}

async function loadConnectedPlatforms() {
  try {
    const response = await fetch(`${API_URL}/platforms/connected`, {
      headers: { 'Authorization': `Bearer ${accessToken}` }
    });
    
    if (response.ok) {
      const data = await parseJsonSafely(response);
      latestConnectedPlatforms = data.platforms || [];
      const wrap = document.getElementById('dash-platform-strip');
      const platformsEl = document.getElementById('dash-platforms');
      
      if (!latestConnectedPlatforms.length) {
        platformsEl.innerHTML = '<div style="font-size:12px;color:var(--t3)">No connected platforms yet.</div>';
        wrap.style.display = 'block';
        renderPublishPlatformSelector();
        renderSchedulerPlatformSelector();
        return;
      }
      
      const platformsList = latestConnectedPlatforms.map(p => {
        const handle = p.platform_username ? `@${p.platform_username}` : '';
        const platformName = (p.platform || '').toLowerCase();
        const isLinkedIn = platformName === 'linkedin';
        const a = p.latest_analytics || {};
        const followers = Number(a.followers || 0);
        const analyticsViews = Number(a.views || 0);
        const publishedViews = Number(publishedVideoStatsCache?.summary?.[platformName]?.total_views || 0);
        const views = analyticsViews > 0 ? analyticsViews : publishedViews;
        const posts = Number(a.posts_count || 0);
        const hasSyncedAnalytics = !!p.latest_analytics;
        const hasMetrics = isLinkedIn ? (followers > 0 || posts > 0) : (followers > 0 || views > 0);
        const metricText = hasMetrics
          ? (isLinkedIn
              ? `${followers.toLocaleString()} followers · ${posts.toLocaleString()} posts`
              : `${followers.toLocaleString()} followers · ${views.toLocaleString()} views`)
          : (hasSyncedAnalytics ? 'Connected · limited metrics available' : 'Waiting for analytics sync');
        return `
          <div onclick="openPlatformAnalyticsPage('${p.platform}')" style="display:flex;align-items:center;gap:10px;padding:10px 12px;background:var(--s2);border:1px solid var(--b1);border-radius:10px;font-size:12px;min-width:250px;cursor:pointer">
            <div style="display:flex;flex-direction:column;gap:2px;min-width:0">
              <strong style="font-size:12px;line-height:1.2">${p.platform_display_name || p.platform}</strong>
              <div style="color:var(--t3);font-size:10px">${handle || p.platform}</div>
              <div style="color:var(--t2);font-size:10px">${metricText}</div>
              ${p.profile_url ? `<a href="${p.profile_url}" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation()" style="color:var(--lime);font-size:10px;text-decoration:none">Open profile ↗</a>` : ''}
            </div>
            <button class="btn btn-ghost btn-sm" style="margin-left:auto;padding:3px 8px;font-size:10px" onclick="event.stopPropagation();disconnectPlatform('${p.platform}')">Disconnect</button>
          </div>
        `;
      }).join('');
      
      platformsEl.innerHTML = platformsList;
      wrap.style.display = 'block';
      renderPublishPlatformSelector();
      renderSchedulerPlatformSelector();

      const youtubeSnapshot = document.getElementById('youtube-snapshot');
      const youtubePlatform = latestConnectedPlatforms.find(p => (p.platform || '').toLowerCase() === 'youtube');
      if (!youtubePlatform) {
        youtubeSnapshot.style.display = 'none';
      } else {
        const a = youtubePlatform.latest_analytics || {};
        const d = a.data || {};
        const ytSummaryViews = Number(publishedVideoStatsCache?.summary?.youtube?.total_views || 0);
        const ytViews = Number(a.views || 0) > 0 ? Number(a.views || 0) : ytSummaryViews;
        document.getElementById('youtube-snapshot-name').textContent =
          d.channel_title || youtubePlatform.platform_display_name || youtubePlatform.platform_username || 'YouTube channel';
        document.getElementById('youtube-snapshot-followers').textContent = Number(a.followers || 0).toLocaleString();
        document.getElementById('youtube-snapshot-views').textContent = ytViews.toLocaleString();
        document.getElementById('youtube-snapshot-posts').textContent = Number(a.posts_count || 0).toLocaleString();
        youtubeSnapshot.style.display = 'block';
      }

      const linkedinSnapshot = document.getElementById('linkedin-snapshot');
      const linkedinPlatform = latestConnectedPlatforms.find(p => (p.platform || '').toLowerCase() === 'linkedin');
      if (!linkedinPlatform) {
        linkedinSnapshot.style.display = 'none';
      } else {
        const a = linkedinPlatform.latest_analytics || {};
        const d = a.data || {};
        const followersAvailable = d.followers_available === true;
        const postsAvailable = d.posts_available === true;
        const followersText = followersAvailable ? Number(a.followers || 0).toLocaleString() : 'Not available';
        const postsText = postsAvailable ? Number(a.posts_count || 0).toLocaleString() : 'Not available';
        document.getElementById('linkedin-snapshot-name').textContent =
          linkedinPlatform.platform_display_name || linkedinPlatform.platform_username || 'LinkedIn account';
        document.getElementById('linkedin-snapshot-followers').textContent = followersText;
        document.getElementById('linkedin-snapshot-posts').textContent = postsText;
        linkedinSnapshot.style.display = 'block';
      }
    }
  } catch (error) {
    console.error('Error loading platforms:', error);
  }
}

function renderPublishPlatformSelector() {
  const el = document.getElementById('pub-plat-sel');
  if (!el) return;
  if (!latestConnectedPlatforms.length) {
    el.innerHTML = '<div style="font-size:12px;color:var(--t3)">Connect at least one platform first.</div>';
    return;
  }
  el.innerHTML = latestConnectedPlatforms.map((p, index) => `
    <button
      type="button"
      class="btn ${index === 0 ? 'btn-lime' : 'btn-ghost'} btn-xs"
      data-pub-platform="${p.platform}"
      onclick="togglePublishPlatform(this)"
      style="text-transform:capitalize"
    >${p.platform}</button>
  `).join('');
  refreshYouTubeSettingsVisibility();
}

function renderSchedulerPlatformSelector() {
  const el = document.getElementById('scheduler-plat-sel');
  if (!el) return;
  if (!latestConnectedPlatforms.length) {
    el.innerHTML = '<div style="font-size:12px;color:var(--t3)">Connect at least one platform first.</div>';
    return;
  }
  el.innerHTML = latestConnectedPlatforms.map((p, index) => `
    <button
      type="button"
      class="btn ${index === 0 ? 'btn-lime' : 'btn-ghost'} btn-xs"
      data-scheduler-platform="${p.platform}"
      onclick="toggleSchedulerPlatform(this)"
      style="text-transform:capitalize"
    >${p.platform}</button>
  `).join('');
  refreshYouTubeSettingsVisibility();
}

function togglePublishPlatform(btn) {
  const selected = btn.classList.contains('btn-lime');
  btn.classList.toggle('btn-lime', !selected);
  btn.classList.toggle('btn-ghost', selected);
  refreshYouTubeSettingsVisibility();
}

function toggleSchedulerPlatform(btn) {
  const selected = btn.classList.contains('btn-lime');
  btn.classList.toggle('btn-lime', !selected);
  btn.classList.toggle('btn-ghost', selected);
  refreshYouTubeSettingsVisibility();
}

function getSelectedPublishPlatforms() {
  const buttons = Array.from(document.querySelectorAll('[data-pub-platform]'));
  return buttons.filter(b => b.classList.contains('btn-lime')).map(b => b.dataset.pubPlatform);
}

function getSelectedSchedulerPlatforms() {
  const buttons = Array.from(document.querySelectorAll('[data-scheduler-platform]'));
  return buttons.filter(b => b.classList.contains('btn-lime')).map(b => b.dataset.schedulerPlatform);
}

function setYouTubePrivacy(prefix, btn) {
  document.querySelectorAll(`#${prefix}-youtube-settings [data-yt-privacy]`).forEach(el => {
    el.classList.remove('btn-lime');
    el.classList.add('btn-ghost');
  });
  btn.classList.remove('btn-ghost');
  btn.classList.add('btn-lime');
}

function getYouTubePrivacy(prefix) {
  const selected = document.querySelector(`#${prefix}-youtube-settings [data-yt-privacy].btn-lime`);
  return selected ? selected.dataset.ytPrivacy : 'public';
}

function refreshYouTubeSettingsVisibility() {
  const publishHasYoutube = getSelectedPublishPlatforms().includes('youtube');
  const schedulerHasYoutube = getSelectedSchedulerPlatforms().includes('youtube');
  const publishPanel = document.getElementById('pub-youtube-settings');
  const schedulerPanel = document.getElementById('scheduler-youtube-settings');
  if (publishPanel) publishPanel.style.display = publishHasYoutube ? 'block' : 'none';
  if (schedulerPanel) schedulerPanel.style.display = schedulerHasYoutube ? 'block' : 'none';
}

function handleDrop(event) {
  event.preventDefault();
  event.currentTarget.classList.remove('drag');
  if (event.dataTransfer?.files?.length) {
    handleFiles(event.dataTransfer.files);
  }
}

async function uploadMediaFiles(files) {
  const list = Array.from(files || []).slice(0, 10);
  if (!list.length) return [];
  const form = new FormData();
  list.forEach(file => form.append('media', file));
  const response = await fetch(`${API_URL}/posts/upload`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${accessToken}` },
    body: form
  });
  const data = await parseJsonSafely(response);
  if (!response.ok) {
    throw new Error(data.error || 'Media upload failed');
  }
  return data.media_items || [];
}

async function handleFiles(files) {
  const localItems = Array.from(files || []).slice(0, 10).map(file => ({
    name: file.name,
    size: file.size,
    type: file.type
  }));
  selectedUploadFiles = localItems;
  const preview = document.getElementById('media-preview');
  if (!localItems.length) {
    preview.style.display = 'none';
    preview.innerHTML = '';
    return;
  }
  preview.style.display = 'grid';
  preview.innerHTML = localItems.map(item => `
    <div style="padding:8px;background:var(--s2);border:1px solid var(--b1);border-radius:8px;font-size:11px">
      <div style="font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${item.name}</div>
      <div style="color:var(--t3)">${Math.max(1, Math.round(item.size / 1024))} KB</div>
    </div>
  `).join('');
  try {
    const uploaded = await uploadMediaFiles(files);
    selectedUploadFiles = uploaded;
  } catch (error) {
    console.error('Upload media error:', error);
    alert(error.message || 'Failed to upload media files');
  }
}

function handleSchedulerDrop(event) {
  event.preventDefault();
  event.currentTarget.classList.remove('drag');
  if (event.dataTransfer?.files?.length) {
    handleSchedulerFiles(event.dataTransfer.files);
  }
}

async function handleSchedulerFiles(files) {
  const localItems = Array.from(files || []).slice(0, 10).map(file => ({
    name: file.name,
    size: file.size,
    type: file.type
  }));
  selectedSchedulerFiles = localItems;
  const preview = document.getElementById('scheduler-media-preview');
  if (!preview) return;
  if (!localItems.length) {
    preview.style.display = 'none';
    preview.innerHTML = '';
    return;
  }
  preview.style.display = 'grid';
  preview.innerHTML = localItems.map(item => `
    <div style="padding:8px;background:var(--s2);border:1px solid var(--b1);border-radius:8px;font-size:11px">
      <div style="font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${item.name}</div>
      <div style="color:var(--t3)">${Math.max(1, Math.round(item.size / 1024))} KB</div>
    </div>
  `).join('');
  try {
    const uploaded = await uploadMediaFiles(files);
    selectedSchedulerFiles = uploaded;
  } catch (error) {
    console.error('Upload scheduler media error:', error);
    alert(error.message || 'Failed to upload media files');
  }
}

function onSchedulerTypeChange(type) {
  const dt = document.getElementById('scheduler-dt');
  if (!dt) return;
  dt.style.display = type === 'custom' ? 'block' : 'none';
}

function setSched(el) {
  document.querySelectorAll('.sched-opt').forEach(x => x.classList.remove('sel'));
  el.classList.add('sel');
  publishScheduleMode = el.dataset.sched || 'now';
  const custom = document.getElementById('custom-sched');
  custom.style.display = publishScheduleMode === 'custom' ? 'block' : 'none';
}

function extractHashtagsFromCaption(caption) {
  return (caption.match(/#[A-Za-z0-9_]+/g) || []).join(' ');
}

function hasUploadedYoutubeVideo(mediaItems) {
  return Array.isArray(mediaItems) && mediaItems.some(item => {
    const path = (item && item.path) || '';
    const name = (item && item.name) || '';
    const file = `${path} ${name}`.toLowerCase();
    return ['.mp4', '.mov', '.m4v', '.avi', '.mkv'].some(ext => file.includes(ext));
  });
}

async function loadPublishedVideoAnalytics(platform = '') {
  if (!accessToken) return null;
  const suffix = platform ? `?platform=${encodeURIComponent(platform)}` : '';
  const response = await fetch(`${API_URL}/analytics/published-videos${suffix}`, {
    headers: { 'Authorization': `Bearer ${accessToken}` }
  });
  const data = await parseJsonSafely(response);
  if (!response.ok) {
    throw new Error(data.error || 'Failed to fetch published video analytics');
  }
  return data;
}

function updatePlatformViewSummary(summaryPayload) {
  const container = document.getElementById('platform-view-summary');
  if (!container) return;
  const summary = (summaryPayload && summaryPayload.summary) || {};
  const platforms = Object.keys(summary);
  if (!platforms.length) {
    container.innerHTML = '<div style="font-size:12px;color:var(--t3)">No platform data yet.</div>';
    return;
  }
  container.innerHTML = platforms.map(platform => {
    let pViews = Number(summary[platform]?.total_views || 0);
    let pLabel = "Combined views of published videos";
    const connectedP = latestConnectedPlatforms.find(p => p.platform === platform);
    if (connectedP && connectedP.latest_analytics && connectedP.latest_analytics.views > 0) {
        pViews = Math.max(pViews, connectedP.latest_analytics.views);
        pLabel = "Total channel views";
    }
    return `
    <div style="padding:10px;border:1px solid var(--b1);border-radius:10px;background:var(--s2)">
      <div style="display:flex;justify-content:space-between;gap:8px">
        <strong style="text-transform:capitalize">${platform}</strong>
        <span style="font-size:10px;color:var(--t3)">Published: ${Number(summary[platform]?.published_count || 0)}</span>
      </div>
      <div style="font-family:var(--font-head);font-size:18px;margin-top:6px">${pViews.toLocaleString()}</div>
      <div style="font-size:10px;color:var(--t3)">${pLabel}</div>
    </div>
  `}).join('');
}

function notifyQueueStatusChanges(posts) {
  (posts || []).forEach(post => {
    const prev = queueStatusMap[post.id];
    if (!prev) {
      queueStatusMap[post.id] = post.status;
      return;
    }
    if (prev === post.status) return;
    queueStatusMap[post.id] = post.status;
    if (post.status === 'published') {
      showToast('Published', `${post.platform} post published successfully.`, 'success');
    } else if (post.status === 'failed') {
      showToast('Publish Failed', post.error_message || `${post.platform} publish failed.`, 'error', 4200);
    } else if (post.status === 'processing') {
      showToast('Processing', `${post.platform} post is being processed.`, 'info');
    }
  });
}

function renderQueueCards(posts) {
  if (!posts.length) {
    return '<div style="color:var(--t3);font-size:12px;padding:20px;text-align:center">No posts queued yet.</div>';
  }
  return posts.map(post => {
    const when = post.status === 'published' ? post.published_at : post.scheduled_for;
    const whenText = when ? new Date(when).toLocaleString() : '—';
    const badgeClass = post.status === 'published' ? 'published' : (post.status === 'failed' ? 'failed' : 'scheduled');
    const errorHtml = post.error_message ? `<div style="font-size:10px;color:#ff7b7b">${post.error_message}</div>` : '';
    const mediaCount = Array.isArray(post.media_items) ? post.media_items.length : 0;
    const earn = Number(post.credits_earned || 0);
    const spend = Number(post.credits_spent || 0);
    const creditLine = `<div style="font-size:10px;color:var(--t3)">Credits: -${spend}${earn > 0 ? ` / +${earn}` : ''}</div>`;
    return `
      <div class="queue-item">
        <div style="flex:1;min-width:0">
          <div style="display:flex;align-items:center;gap:8px">
            <strong style="text-transform:capitalize">${post.platform}</strong>
            <span class="qi-status ${badgeClass}">${post.status}</span>
          </div>
          <div style="font-size:11px;color:var(--t2);margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${post.caption || ''}</div>
          <div style="font-size:10px;color:var(--t3)">At: ${whenText} · Media: ${mediaCount}</div>
          ${creditLine}
          ${errorHtml}
        </div>
        ${(post.status === 'scheduled' || post.status === 'failed') ? `<button class="btn btn-ghost btn-xs" onclick="cancelPost('${post.id}')">Cancel</button>` : ''}
      </div>
    `;
  }).join('');
}

async function loadPostQueue() {
  if (!accessToken) return;
  try {
    const response = await fetch(`${API_URL}/posts`, {
      headers: { 'Authorization': `Bearer ${accessToken}` }
    });
    const data = await parseJsonSafely(response);
    if (!response.ok) return;
    const posts = data.posts || [];
    notifyQueueStatusChanges(posts);
    const html = renderQueueCards(posts);
    const queueA = document.getElementById('upload-queue');
    const queueB = document.getElementById('scheduler-queue');
    if (queueA) queueA.innerHTML = html;
    if (queueB) queueB.innerHTML = html;

    const scheduled = Number(data?.summary?.scheduled || 0);
    document.getElementById('ds-scheduled').textContent = scheduled.toLocaleString();
    document.getElementById('ds-sched-p').style.width = `${Math.min(100, scheduled * 10)}%`;
    if (typeof data.credits === 'number') {
      document.getElementById('credit-count').textContent = data.credits.toLocaleString();
      if (currentUser) currentUser.credits = data.credits;
    }
    try {
      publishedVideoStatsCache = await loadPublishedVideoAnalytics();
      updatePlatformViewSummary(publishedVideoStatsCache);
    } catch (error) {
      console.error('Published video analytics summary error:', error);
    }
  } catch (error) {
    console.error('Load post queue error:', error);
  }
}

async function processDuePosts(silent = false) {
  if (!accessToken) return;
  try {
    const response = await fetch(`${API_URL}/posts/process-due`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${accessToken}` }
    });
    const data = await parseJsonSafely(response);
    if (!response.ok) {
      if (!silent) alert(data.error || 'Failed to process due posts');
      return;
    }
    await loadPostQueue();
  } catch (error) {
    console.error('Process due posts error:', error);
    if (!silent) alert('Failed to process due posts');
  }
}

async function cancelPost(postId) {
  try {
    const response = await fetch(`${API_URL}/posts/${postId}/cancel`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${accessToken}` }
    });
    const data = await parseJsonSafely(response);
    if (!response.ok) {
      alert(data.error || 'Failed to cancel post');
      return;
    }
    await loadPostQueue();
  } catch (error) {
    console.error('Cancel post error:', error);
  }
}

function updateStatCard(id, subId, barId, value, label, maxForBar = 1) {
  const numEl = document.getElementById(id);
  const subEl = document.getElementById(subId);
  const barEl = document.getElementById(barId);
  
  if (value === null || value === undefined) {
    numEl.textContent = '—';
    if (subEl) subEl.textContent = label || 'No data';
    if (barEl) barEl.style.width = '0%';
    return;
  }
  
  numEl.textContent = Number(value).toLocaleString();
  if (subEl) subEl.textContent = label || 'Live data';
  if (barEl) {
    const pct = Math.max(0, Math.min(100, (Number(value) / Math.max(1, maxForBar)) * 100));
    barEl.style.width = `${pct}%`;
  }
}

async function loadDashboardAnalytics() {
  try {
    const response = await fetch(`${API_URL}/analytics/dashboard`, {
      headers: { 'Authorization': `Bearer ${accessToken}` }
    });
    
      if (response.ok) {
        const data = await parseJsonSafely(response);
        let totalViews = Number(data?.summary?.total_views || 0);
        let totalFollowers = Number(data?.summary?.total_followers || 0);
        let totalPosts = Number(data?.summary?.total_posts || 0);
        
        // Force channel views from all connected accounts (YouTube total views, etc)
        let cViews = 0, cFollowers = 0, cPosts = 0;
        latestConnectedPlatforms.forEach(p => {
          const a = p.latest_analytics || {};
          cViews += Number(a.views || 0);
          cFollowers += Number(a.followers || 0);
          cPosts += Number(a.posts_count || 0);
        });
        
        totalViews = Math.max(totalViews, cViews);
        totalFollowers = Math.max(totalFollowers, cFollowers);
        totalPosts = Math.max(totalPosts, cPosts);
      
      const hasConnected = latestConnectedPlatforms.length > 0;
      if (totalViews === 0) {
        const publishedFallback = Object.values((publishedVideoStatsCache?.summary || {}))
          .reduce((sum, item) => sum + Number(item?.total_views || 0), 0);
        if (publishedFallback > 0) totalViews = publishedFallback;
      }
      const hasData = (totalViews + totalFollowers + totalPosts) > 0;
      const statusText = hasData ? 'Live synced data' : (hasConnected ? 'Connected. Waiting for first sync' : 'Connect platforms');
      
      const maxRef = Math.max(totalViews, totalFollowers, totalPosts, 1);
      updateStatCard('ds-posts', 'ds-posts-sub', 'ds-posts-p', hasData ? totalPosts : (hasConnected ? 0 : null), statusText, maxRef);
      updateStatCard('ds-reach', 'ds-reach-sub', 'ds-reach-p', hasData ? totalViews : (hasConnected ? 0 : null), statusText, maxRef);
      updateStatCard('ds-followers', 'ds-followers-sub', 'ds-followers-p', hasData ? totalFollowers : (hasConnected ? 0 : null), statusText, maxRef);
    }
  } catch (error) {
    console.error('Error loading analytics:', error);
  }
}

async function refreshLiveStats(options = {}) {
  const { silent = false, force = false } = options;
  if (!accessToken) return;
  if (syncInProgress && !force) return;
  if (!latestConnectedPlatforms.length && !force) {
    await loadDashboardAnalytics();
    return;
  }

  try {
    syncInProgress = true;
    const response = await fetch(`${API_URL}/platforms/sync-all`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${accessToken}` }
    });

    const data = await parseJsonSafely(response);

    if (!response.ok) {
      if (!silent) alert(data.error || 'Failed to sync live stats');
      return;
    }

    await loadConnectedPlatforms();
    await loadDashboardAnalytics();

    const syncErrors = Array.isArray(data.errors) ? data.errors.filter(Boolean) : [];
    if (syncErrors.length > 0) {
      const summary = syncErrors.map(err => `${err.platform}: ${err.error}`).join('\n');
      if (!silent) alert(`Partial sync completed:\n${summary}`);
      return;
    }

    if (!silent) alert('Live stats refreshed');
  } catch (error) {
    console.error('Error refreshing live stats:', error);
    if (!silent) alert('Failed to refresh live stats');
  } finally {
    syncInProgress = false;
  }
}

function closePlatformAnalyticsModal() {
  document.getElementById('platform-analytics-modal').style.display = 'none';
}

function renderPlatformVideoRows(platform, analyticsPayload) {
  const list = document.getElementById('pa-videos');
  if (!list) return;
  const filtered = ((analyticsPayload && analyticsPayload.videos) || [])
    .filter(v => v.platform === platform)
    .sort((a, b) => new Date(b.published_at || 0) - new Date(a.published_at || 0))
    .slice(0, 25);
  if (!filtered.length) {
    list.innerHTML = '<div style="font-size:12px;color:var(--t3)">No published videos/posts yet for this platform.</div>';
    return;
  }
  list.innerHTML = filtered.map(video => {
    const title = video.title || 'Published content';
    const link = video.url || '';
    const when = video.published_at;
    const viewsText = Number.isFinite(Number(video.views)) ? `${Number(video.views).toLocaleString()} views` : 'Views: not available';
    return `
      <div class="video-row">
        <div class="video-meta">
          <div class="video-title">${escapeHtml(title)}</div>
          <div class="video-sub">${escapeHtml((video.platform || '').toUpperCase())} · ${when ? new Date(when).toLocaleString() : '—'} · ${viewsText}</div>
        </div>
        <div style="display:flex;gap:6px">
          ${link
            ? `<a class="btn btn-ghost btn-xs" href="${link}" target="_blank" rel="noopener noreferrer">Open</a>`
            : '<span class="btn btn-ghost btn-xs" style="pointer-events:none;opacity:.65">No Link</span>'}
          <button class="btn btn-danger btn-xs" onclick="deletePublishedVideo('${video.post_id}', '${video.platform}')">Delete</button>
        </div>
      </div>
    `;
  }).join('');
}

async function deletePublishedVideo(postId, platform) {
  if (!postId) return;
  try {
    showToast('Deleting', 'Deleting selected post...', 'info');
    const response = await fetch(`${API_URL}/posts/${postId}/delete`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      }
    });
    const data = await parseJsonSafely(response);
    if (!response.ok) {
      showToast('Delete Failed', data.error || 'Failed to delete post', 'error', 4200);
      return;
    }
    if (data.warning) {
      showToast('Deleted (App Only)', data.warning, 'warn', 5200);
    } else {
      showToast('Deleted', `${platform} post deleted successfully.`, 'success');
    }
    await loadPostQueue();
    if (activePlatformAnalytics) await loadPlatformAnalyticsPage(activePlatformAnalytics);
  } catch (error) {
    console.error('Delete published post error:', error);
    showToast('Delete Failed', 'Network error while deleting post.', 'error');
  }
}

function renderLineGraph(svgId, points) {
  const svg = document.getElementById(svgId);
  if (!svg) return;

  const width = 640;
  const height = 220;
  const pad = 24;
  const safePoints = (points || [])
    .map((p, idx) => ({
      label: p?.label || String(idx + 1),
      value: Number(p?.value || 0)
    }))
    .filter(p => Number.isFinite(p.value));

  if (!safePoints.length) {
    svg.innerHTML = `<text x="50%" y="50%" fill="var(--t3)" text-anchor="middle" dominant-baseline="middle">No analytics history yet</text>`;
    return;
  }

  const values = safePoints.map(p => Number(p.value || 0));
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = Math.max(max - min, 1);
  const stepX = safePoints.length > 1 ? (width - pad * 2) / (safePoints.length - 1) : 0;
  const toY = (v) => height - pad - (((v - min) / range) * (height - pad * 2));

  const polyline = safePoints.map((p, i) => `${pad + stepX * i},${toY(p.value)}`).join(' ');
  const grid = [0.25, 0.5, 0.75].map(r => {
    const y = pad + (height - pad * 2) * r;
    return `<line x1="${pad}" y1="${y}" x2="${width - pad}" y2="${y}" stroke="var(--b1)" stroke-width="1"/>`;
  }).join('');

  svg.innerHTML = `
    <rect x="0" y="0" width="${width}" height="${height}" fill="transparent"/>
    ${grid}
    <polyline points="${polyline}" fill="none" stroke="var(--lime)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
  `;
}

async function openPlatformAnalyticsPage(platform) {
  activePlatformAnalytics = (platform || '').toLowerCase();
  if (!activePlatformAnalytics) return;
  tab('platform-analytics');
  await loadPlatformAnalyticsPage(activePlatformAnalytics);
}

async function reloadPlatformAnalyticsPage() {
  if (!activePlatformAnalytics) return;
  await loadPlatformAnalyticsPage(activePlatformAnalytics);
}

async function loadPlatformAnalyticsPage(platform) {
  const normalized = (platform || '').toLowerCase();
  document.getElementById('pa-title').textContent = `${normalized.charAt(0).toUpperCase()}${normalized.slice(1)} Analytics`;
  document.getElementById('pa-sub').textContent = 'Loading live analytics and trend graph...';
  document.getElementById('pa-meta').innerHTML = '';
  const videosEl = document.getElementById('pa-videos');
  if (videosEl) videosEl.innerHTML = '<div style="font-size:12px;color:var(--t3)">Loading published videos...</div>';

  try {
    const [liveResp, histResp, videosResp] = await Promise.all([
      fetch(`${API_URL}/platforms/${normalized}/analytics-live`, {
        headers: { 'Authorization': `Bearer ${accessToken}` }
      }),
      fetch(`${API_URL}/analytics/platform/${normalized}?days=30`, {
        headers: { 'Authorization': `Bearer ${accessToken}` }
      }),
      fetch(`${API_URL}/analytics/published-videos?platform=${encodeURIComponent(normalized)}`, {
        headers: { 'Authorization': `Bearer ${accessToken}` }
      })
    ]);

    const liveData = await parseJsonSafely(liveResp);
    const histData = await parseJsonSafely(histResp);
    const videoData = await parseJsonSafely(videosResp);
    if (!liveResp.ok) {
      document.getElementById('pa-sub').textContent = liveData.error || 'Failed to load platform analytics';
      renderLineGraph('pa-graph', []);
      return;
    }

    const latest = liveData.latest_analytics || {};
    const raw = latest.data || {};
    const summaryViews = Number(videoData?.summary?.[normalized]?.total_views || 0);
    const liveViews = Number(latest.views || 0);
    const displayViews = liveViews > 0 ? liveViews : summaryViews;
    document.getElementById('pa-followers').textContent = Number(latest.followers || 0).toLocaleString();
    document.getElementById('pa-views').textContent = displayViews.toLocaleString();
    document.getElementById('pa-posts').textContent = Number(latest.posts_count || 0).toLocaleString();
    document.getElementById('pa-engagement').textContent = Number(latest.engagement || 0).toLocaleString();

    const historyRows = Array.isArray(histData?.data) ? histData.data : [];
    const graphMetric = normalized === 'linkedin' ? 'followers' : 'views';
    let points = [];
    if (Array.isArray(videoData?.daily_series) && videoData.daily_series.length) {
      points = videoData.daily_series.map((row, idx) => ({
        label: row.date || String(idx + 1),
        value: Number(row.views || 0)
      }));
      document.getElementById('pa-graph-title').textContent = '30-Day Daily View Change';
    } else {
      points = historyRows.map((row, idx) => ({
        label: row.metric_date || String(idx + 1),
        value: Number(row[graphMetric] || 0)
      }));
      document.getElementById('pa-graph-title').textContent = `30-Day Trend (${graphMetric})`;
    }
    if (!points.length) {
      const videoPoints = (videoData?.videos || [])
        .filter(v => v.platform === normalized && Number.isFinite(Number(v.views)))
        .sort((a, b) => new Date(a.published_at || 0) - new Date(b.published_at || 0))
        .slice(-30)
        .map((v, idx) => ({
          label: v.published_at ? new Date(v.published_at).toLocaleDateString() : `Video ${idx + 1}`,
          value: Number(v.views || 0)
        }));
      if (videoPoints.length) {
        points = videoPoints;
      }
    }
    if (!points.length) {
      // Last-resort fallback so chart always renders something meaningful.
      const fallbackValue = Number.isFinite(displayViews) ? displayViews : 0;
      points = [
        { label: 'Prev', value: Math.max(0, fallbackValue) },
        { label: 'Now', value: Math.max(0, fallbackValue) }
      ];
    }
    renderLineGraph('pa-graph', points);
    document.getElementById('pa-sub').textContent = liveData.sync_error ? `Loaded with warning: ${liveData.sync_error}` : 'Live synced data with historical trend';

    const extra = [];
    if (normalized === 'youtube') {
      extra.push(['Channel', raw.channel_title || liveData.platform?.platform_display_name || 'Connected channel']);
      extra.push(['Channel ID', raw.channel_id || liveData.platform?.platform_user_id || '—']);
      extra.push(['Profile URL', liveData.platform?.profile_url || '—']);
    }
    if (normalized === 'linkedin') {
      extra.push(['Name', raw.name || liveData.platform?.platform_display_name || '—']);
      extra.push(['Email', raw.email || 'Not available']);
      extra.push(['Locale', raw.locale || 'Not available']);
    }
    document.getElementById('pa-meta').innerHTML = extra.map(([k, v]) => `
      <div style="display:flex;justify-content:space-between;gap:12px;padding:8px 10px;border:1px solid var(--b1);border-radius:10px;background:var(--s2);font-size:12px">
        <span style="color:var(--t3)">${k}</span>
        <span style="text-align:right;word-break:break-word">${v}</span>
      </div>
    `).join('');
    renderPlatformVideoRows(normalized, videoData);
  } catch (error) {
    console.error('Platform analytics page error:', error);
    document.getElementById('pa-sub').textContent = 'Failed to load analytics';
    renderLineGraph('pa-graph', []);
  }
}

function renderPlatformAnalyticsHtml(platformName, payload) {
  const platform = payload?.platform || {};
  const latest = payload?.latest_analytics || {};
  const raw = latest?.data || {};
  const baseRows = [
    ['Platform', platformName],
    ['Profile', platform.platform_display_name || platform.platform_username || 'Connected account'],
    ['Last sync', platform.last_sync || 'Just now']
  ];
  let metricRows = [
    ['Followers', Number(latest.followers || 0).toLocaleString()],
    ['Views', Number(latest.views || 0).toLocaleString()],
    ['Posts', Number(latest.posts_count || 0).toLocaleString()],
    ['Engagement', Number(latest.engagement || 0).toLocaleString()]
  ];
  if (platformName === 'linkedin') {
    metricRows = [
      ['Followers', Number(latest.followers || 0).toLocaleString()],
      ['Posts', Number(latest.posts_count || 0).toLocaleString()]
    ];
  } else if (platformName === 'youtube') {
    metricRows = [
      ['Subscribers', Number(latest.followers || 0).toLocaleString()],
      ['Views', Number(latest.views || 0).toLocaleString()],
      ['Videos', Number(latest.posts_count || 0).toLocaleString()],
      ['Engagement', Number(latest.engagement || 0).toLocaleString()],
      ['Channel', raw.channel_title || platform.platform_display_name || 'Connected channel'],
      ['Channel ID', raw.channel_id || platform.platform_user_id || '—'],
      ['Hidden subscribers', raw.hidden_subscriber_count ? 'Yes' : 'No']
    ];
  }
  const rows = [...baseRows, ...metricRows];

  if (platformName === 'linkedin') {
    rows.push(['Name', raw.name || raw.given_name || platform.platform_display_name || 'Not available']);
    rows.push(['Email', raw.email || 'Not available with current LinkedIn access']);
    rows.push(['Locale', raw.locale || 'Not available']);
  }

  const rowsHtml = rows.map(([k, v]) => `
    <div style="display:flex;justify-content:space-between;gap:12px;padding:8px 10px;border:1px solid var(--b1);border-radius:10px;background:var(--s2)">
      <span style="color:var(--t3)">${k}</span>
      <span style="text-align:right;word-break:break-word">${v ?? '—'}</span>
    </div>
  `).join('');

  const extraInfo = platformName === 'linkedin'
    ? `<div style="font-size:11px;color:var(--t3);line-height:1.5">LinkedIn personal profile analytics are limited by LinkedIn API permissions. For full org/page analytics, Marketing/Community API access is required.</div>`
    : '';

  return `${rowsHtml}${extraInfo}`;
}

async function openPlatformAnalytics(platform) {
  if (!accessToken || platformAnalyticsLoading) return;
  const platformName = (platform || '').toLowerCase();
  if (!platformName) return;

  const title = `${platformName.charAt(0).toUpperCase()}${platformName.slice(1)} Analytics`;
  document.getElementById('platform-analytics-title').textContent = title;
  document.getElementById('platform-analytics-sub').textContent = 'Fetching latest live profile analytics...';
  document.getElementById('platform-analytics-body').innerHTML = '<div style="color:var(--t3)">Loading...</div>';
  document.getElementById('platform-analytics-modal').style.display = 'flex';

  try {
    platformAnalyticsLoading = true;
    const response = await fetch(`${API_URL}/platforms/${platformName}/analytics-live`, {
      headers: { 'Authorization': `Bearer ${accessToken}` }
    });
    const data = await parseJsonSafely(response);
    if (!response.ok) {
      document.getElementById('platform-analytics-sub').textContent = 'Unable to load analytics';
      document.getElementById('platform-analytics-body').innerHTML = `<div style="color:#ff7b7b">${data.error || 'Failed to fetch platform analytics'}</div>`;
      return;
    }

    document.getElementById('platform-analytics-sub').textContent = data.sync_error ? `Synced with warnings: ${data.sync_error}` : 'Live synced analytics';
    document.getElementById('platform-analytics-body').innerHTML = renderPlatformAnalyticsHtml(platformName, data);
    await loadConnectedPlatforms();
    await loadDashboardAnalytics();
  } catch (error) {
    console.error('Error loading platform analytics:', error);
    document.getElementById('platform-analytics-sub').textContent = 'Unable to load analytics';
    document.getElementById('platform-analytics-body').innerHTML = '<div style="color:#ff7b7b">Network error while fetching platform analytics.</div>';
  } finally {
    platformAnalyticsLoading = false;
  }
}

async function logout() {
  if (confirm('Are you sure you want to log out?')) {
    try {
      await fetch(`${API_URL}/auth/logout`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${accessToken}` }
      });
    } catch (error) {
      console.error('Logout error:', error);
    }
    
    accessToken = null;
    currentUser = null;
    stopQueuePolling();
    localStorage.removeItem('access_token');
    location.reload();
  }
}

function tab(name) {
  document.querySelectorAll('.content').forEach(c => c.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  
  const tabEl = document.getElementById(`tab-${name}`);
  if (!tabEl) return;
  tabEl.classList.add('active');
  const navEl = document.getElementById(`nav-${name}`);
  if (navEl) navEl.classList.add('active');
  
  const titles = {
    dashboard: 'Dashboard — CreatorOS',
    writer: 'AI Content Studio',
    publish: 'Upload & Publish',
    ideas: 'Idea Board',
    analytics: 'Analytics',
    trends: 'Trend Radar',
    repurpose: 'Content Multiplier',
    scheduler: 'Scheduler',
    connect: 'Connect Platforms',
    'platform-analytics': 'Platform Analytics',
    admin: 'Admin Dashboard',
    settings: 'Settings'
  };
  const title = titles[name] || 'CreatorOS';
  document.getElementById('topbar-title').innerHTML = `${title} <span class="dim">— CreatorOS</span>`;
  
  if (name === 'admin') {
    loadAdminData();
  }
}

// --- FEEDBACK & ADMIN LOGIC --- //
let currentFeedbackRating = 0;
let adminToken = null;

function openFeedbackModal() {
  currentFeedbackRating = 0;
  updateFeedbackStars();
  document.getElementById('feedback-msg').value = '';
  document.getElementById('feedback-modal').classList.add('open');
}

function closeFeedbackModal() {
  document.getElementById('feedback-modal').classList.remove('open');
}

function setFeedbackRating(r) {
  currentFeedbackRating = r;
  updateFeedbackStars();
}

function updateFeedbackStars() {
  const stars = document.getElementById('feedback-stars').children;
  for(let i=0; i<stars.length; i++) {
    stars[i].style.color = i < currentFeedbackRating ? 'var(--lime)' : 'var(--t3)';
  }
}

async function submitFeedback() {
  if (currentFeedbackRating === 0) {
    showToast('Rating Required', 'Please select a star rating (1-5) before submitting.', 'warn');
    return;
  }
  const msg = document.getElementById('feedback-msg').value;
  const btn = document.getElementById('btn-submit-feedback');
  const ogText = btn.innerHTML;
  btn.innerHTML = 'Submitting...';
  btn.disabled = true;
  
  try {
    const res = await fetch(`${API_URL}/feedback`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ rating: currentFeedbackRating, message: msg })
    });
    if (res.ok) {
      showToast('Feedback Sent', 'Thank you for your feedback! We appreciate it.', 'success');
      closeFeedbackModal();
    } else {
      const data = await res.json();
      showToast('Error', data.error || 'Failed to submit feedback.', 'error');
    }
  } catch (err) {
    console.error(err);
    showToast('Network Error', 'Check your connection and try again.', 'error');
  } finally {
    btn.innerHTML = ogText;
    btn.disabled = false;
  }
}

function promptAdminLogin() {
  if (adminToken) {
    tab('admin');
  } else {
    document.getElementById('admin-secret').value = '';
    document.getElementById('admin-login-modal').classList.add('open');
  }
}

function closeAdminLoginModal() {
  document.getElementById('admin-login-modal').classList.remove('open');
}

async function submitAdminLogin() {
  const code = document.getElementById('admin-secret').value;
  if (!code) {
    showToast('Required', 'Please enter the secret code.', 'warn');
    return;
  }
  const btn = document.getElementById('btn-admin-login');
  const ogText = btn.innerHTML;
  btn.innerHTML = 'Verifying...';
  btn.disabled = true;
  
  try {
    const res = await fetch(`${API_URL}/admin/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code })
    });
    if (res.ok) {
      const data = await res.json();
      adminToken = data.access_token;
      document.getElementById('nav-admin').style.display = 'flex';
      closeAdminLoginModal();
      
      const adminLoginTime = new Date().toLocaleString();
      const adminDevice = navigator.userAgent;
      document.getElementById('admin-session-info').textContent = `Session: ${adminLoginTime} | Device: ${adminDevice}`;
      showToast('Admin Access Granted', `Session started: ${adminLoginTime}`, 'success');
      
      tab('admin');
    } else {
      showToast('Access Denied', 'Invalid secret code.', 'error');
    }
  } catch (err) {
    console.error(err);
    showToast('Network Error', 'Failed to connect to admin servers.', 'error');
  } finally {
    btn.innerHTML = ogText;
    btn.disabled = false;
  }
}

let adminUsers = [];
let adminFeedback = [];
let adminUsersPage = 1;
let adminFeedbackPage = 1;
const ADMIN_PAGE_SIZE = 10;

function renderAdminUsers() {
  const uBody = document.getElementById('admin-users-body');
  uBody.innerHTML = '';
  const start = (adminUsersPage - 1) * ADMIN_PAGE_SIZE;
  const end = start + ADMIN_PAGE_SIZE;
  const paged = adminUsers.slice(start, end);
  
  paged.forEach(u => {
    let joined = u.created_at ? new Date(u.created_at).toLocaleDateString() : '-';
    let login = u.last_login ? new Date(u.last_login).toLocaleDateString() : 'Never';
    let status = u.premium ? '<span style="color:var(--gold)">Premium</span>' : '<span style="color:var(--t3)">Free</span>';
    uBody.innerHTML += `
      <tr style="border-bottom:1px solid var(--b1);font-size:12px">
        <td style="padding:12px;font-weight:600">${escapeHtml(u.name || 'Unknown')}<br><span style="color:var(--t3);font-weight:400">${escapeHtml(u.email)}</span></td>
        <td style="padding:12px;color:var(--t3)">${joined}</td>
        <td style="padding:12px;color:var(--t3)">${login}</td>
        <td style="padding:12px;color:var(--lime);font-family:var(--font-mono)">${u.credits}</td>
        <td style="padding:12px">${status}</td>
      </tr>
    `;
  });
  
  const totalPages = Math.max(1, Math.ceil(adminUsers.length / ADMIN_PAGE_SIZE));
  document.getElementById('admin-users-pagination').innerHTML = `
    <button class="btn btn-ghost btn-xs" onclick="adminUsersPage--; renderAdminUsers()" ${adminUsersPage === 1 ? 'disabled' : ''}>&larr; Prev</button>
    <span style="font-size:11px;color:var(--t2)">Page ${adminUsersPage} of ${totalPages}</span>
    <button class="btn btn-ghost btn-xs" onclick="adminUsersPage++; renderAdminUsers()" ${adminUsersPage >= totalPages ? 'disabled' : ''}>Next &rarr;</button>
  `;
}

function renderAdminFeedback() {
  const fBody = document.getElementById('admin-feedback-body');
  fBody.innerHTML = '';
  const start = (adminFeedbackPage - 1) * ADMIN_PAGE_SIZE;
  const end = start + ADMIN_PAGE_SIZE;
  const paged = adminFeedback.slice(start, end);
  
  paged.forEach(f => {
    let starStr = '⭐'.repeat(f.rating || 0);
    let date = new Date(f.created_at).toLocaleDateString();
    fBody.innerHTML += `
      <tr style="border-bottom:1px solid var(--b1);font-size:12px">
        <td style="padding:12px"><b>${escapeHtml(f.user_name)}</b><br><span style="color:var(--t3)">${escapeHtml(f.user_email)}</span></td>
        <td style="padding:12px">${starStr}</td>
        <td style="padding:12px;max-width:300px;word-break:break-word">${escapeHtml(f.message || '-')}</td>
        <td style="padding:12px;color:var(--t3)">${date}</td>
      </tr>
    `;
  });
  
  const totalPages = Math.max(1, Math.ceil(adminFeedback.length / ADMIN_PAGE_SIZE));
  document.getElementById('admin-feedback-pagination').innerHTML = `
    <button class="btn btn-ghost btn-xs" onclick="adminFeedbackPage--; renderAdminFeedback()" ${adminFeedbackPage === 1 ? 'disabled' : ''}>&larr; Prev</button>
    <span style="font-size:11px;color:var(--t2)">Page ${adminFeedbackPage} of ${totalPages}</span>
    <button class="btn btn-ghost btn-xs" onclick="adminFeedbackPage++; renderAdminFeedback()" ${adminFeedbackPage >= totalPages ? 'disabled' : ''}>Next &rarr;</button>
  `;
}

async function loadAdminData() {
  if (!adminToken) return;
  try {
    const [resU, resF] = await Promise.all([
      fetch(`${API_URL}/admin/users`, { headers: { 'Authorization': `Bearer ${adminToken}` } }),
      fetch(`${API_URL}/admin/feedback`, { headers: { 'Authorization': `Bearer ${adminToken}` } })
    ]);
    if (resU.ok) {
      const dU = await resU.json();
      document.getElementById('admin-user-count').textContent = dU.count;
      adminUsers = dU.users || [];
      adminUsersPage = 1;
      renderAdminUsers();
    }
    if (resF.ok) {
      const dF = await resF.json();
      document.getElementById('admin-feedback-count').textContent = dF.count;
      adminFeedback = dF.feedback || [];
      adminFeedbackPage = 1;
      renderAdminFeedback();
    }
  } catch(err) {
    console.error('Failed to load admin data:', err);
  }
}

function setMode(mode) {
  document.querySelectorAll('.tb').forEach(b => b.classList.remove('active'));
  document.querySelector(`[data-mode="${mode}"]`).classList.add('active');
  
  const modes = {
    hook: { name: 'Hook Generator', desc: 'Generate viral opening lines that stop the scroll and force viewers to keep watching.' },
    script: { name: 'Script Architect', desc: 'Full scripts with hooks, sections, b-roll cues, and CTAs.' },
    thread: { name: 'Thread Weaver', desc: 'Viral threads with narrative tension and punchy CTAs.' },
    caption: { name: 'Caption Generator', desc: 'Engaging captions that boost engagement.' },
    email: { name: 'Newsletter Writer', desc: 'Compelling newsletter content.' },
    bio: { name: 'Bio Creator', desc: 'Profile bio that converts.' },
    ideas: { name: 'Idea Generator', desc: 'Endless content ideas.' }
  };
  
  if (modes[mode]) {
    document.getElementById('mode-name').textContent = modes[mode].name;
    document.getElementById('mode-desc').textContent = modes[mode].desc;
  }
}

function setPlatform(el, platform) {
  document.querySelectorAll('.pchip').forEach(c => c.classList.remove('active'));
  el.classList.add('active');
}

function setTone(el) {
  document.querySelectorAll('.tone-btn').forEach(c => c.classList.remove('active'));
  el.classList.add('active');
}

function escapeHtml(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

async function aiGenerate(task, prompt, extra = {}) {
  if (!accessToken) {
    alert('Please sign in first.');
    return null;
  }
  const platform = document.querySelector('.pchip.active')?.textContent?.trim() || 'YouTube';
  const tone = document.querySelector('.tone-btn.active')?.dataset?.tone || 'Educational';
  const response = await fetch(`${API_URL}/ai/generate`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      task,
      prompt,
      platform,
      tone,
      ...extra
    })
  });
  const data = await parseJsonSafely(response);
  if (!response.ok) {
    throw new Error(data.error || 'AI request failed');
  }
  return data;
}

let chatHistory = [];

async function sendChatMessage() {
  const inputEl = document.getElementById('chat-input');
  const prompt = inputEl.value.trim();
  if (!prompt) return;
  
  if (!accessToken) {
    alert('Please sign in first.');
    return;
  }

  const chatMessages = document.getElementById('chat-messages');
  
  const msgDiv = document.createElement('div');
  msgDiv.style.alignSelf = 'flex-end';
  msgDiv.style.background = 'var(--lime)';
  msgDiv.style.color = '#000';
  msgDiv.style.padding = '12px 16px';
  msgDiv.style.borderRadius = '16px 16px 0 16px';
  msgDiv.style.maxWidth = '80%';
  msgDiv.textContent = prompt;
  chatMessages.appendChild(msgDiv);
  
  inputEl.value = '';
  const sendBtn = document.getElementById('chat-send-btn');
  sendBtn.disabled = true;
  
  const aiMsgDiv = document.createElement('div');
  aiMsgDiv.style.alignSelf = 'flex-start';
  aiMsgDiv.style.background = 'var(--s2)';
  aiMsgDiv.style.padding = '12px 16px';
  aiMsgDiv.style.borderRadius = '16px 16px 16px 0';
  aiMsgDiv.style.maxWidth = '80%';
  aiMsgDiv.style.whiteSpace = 'pre-wrap';
  aiMsgDiv.style.lineHeight = '1.5';
  aiMsgDiv.textContent = '...';
  chatMessages.appendChild(aiMsgDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  
  try {
    const response = await fetch(`${API_URL}/ai/chat`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ prompt, history: chatHistory })
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || 'Failed to connect to AI');
    }
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let aiText = "";
    aiMsgDiv.textContent = "";
    
    while(true) {
      const {done, value} = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.substring(6);
          if (dataStr === '[DONE]') break;
          try {
            const data = JSON.parse(dataStr);
            if (data.error) {
              aiMsgDiv.textContent += '\nError: ' + data.error;
            } else if (data.text) {
              aiText += data.text;
              aiMsgDiv.textContent = aiText;
              chatMessages.scrollTop = chatMessages.scrollHeight;
            }
          } catch(e) {}
        }
      }
    }
    
    chatHistory.push({role: "user", content: prompt});
    chatHistory.push({role: "model", content: aiText});
    
  } catch (error) {
    aiMsgDiv.textContent = "Error: " + error.message;
  } finally {
    sendBtn.disabled = false;
    inputEl.focus();
  }
}

async function sendMsg() {
  const inputEl = document.getElementById('user-input');
  const input = inputEl.value.trim();
  if (!input) return;

  const sendBtn = document.getElementById('send-btn');
  const activeMode = document.querySelector('.tb.active')?.dataset?.mode || 'hook';
  const output = document.getElementById('ai-output');
  const msgDiv = document.createElement('div');
  msgDiv.className = 'ai-msg';
  msgDiv.innerHTML = `<div class="msg-lbl">You</div><span>${escapeHtml(input)}</span>`;
  output.appendChild(msgDiv);

  sendBtn.disabled = true;
  sendBtn.textContent = 'Generating...';
  try {
    const data = await aiGenerate('writer', input, { mode: activeMode });
    const aiMsgDiv = document.createElement('div');
    aiMsgDiv.className = 'ai-msg';
    const provider = (data.provider || 'ai').toUpperCase();
    aiMsgDiv.innerHTML = `<div class="msg-lbl">✦ CreatorOS AI · ${escapeHtml(provider)}</div><span style="white-space:pre-line">${escapeHtml(data.text || 'No response')}</span>`;
    output.appendChild(aiMsgDiv);
    inputEl.value = '';
    inputEl.style.height = 'auto';
  } catch (error) {
    console.error('AI writer error:', error);
    alert(error.message || 'Failed to generate AI content.');
  } finally {
    sendBtn.disabled = false;
    sendBtn.textContent = 'Generate';
  }
}

async function aiCaption() {
  const captionEl = document.getElementById('pub-caption');
  const basePrompt = captionEl.value.trim() || 'Create a high-performing social media caption about creator growth.';
  try {
    const data = await aiGenerate('caption', basePrompt);
    captionEl.value = data.text || '';
    autoResize(captionEl);
  } catch (error) {
    console.error('AI caption error:', error);
    alert(error.message || 'Failed to generate caption.');
  }
}

async function aiOptimize() {
  const captionEl = document.getElementById('pub-caption');
  const basePrompt = captionEl.value.trim();
  if (!basePrompt) {
    alert('Write or generate a caption first.');
    return;
  }
  try {
    const data = await aiGenerate('optimize', basePrompt);
    captionEl.value = data.text || basePrompt;
    autoResize(captionEl);
  } catch (error) {
    console.error('AI optimize error:', error);
    alert(error.message || 'Failed to optimize caption.');
  }
}

async function aiHashtags() {
  const caption = document.getElementById('pub-caption').value.trim();
  const prompt = caption || 'Generate hashtags for creator growth and social media content.';
  const strip = document.getElementById('hashtag-strip');
  const btn = document.getElementById('hashtag-btn');
  btn.disabled = true;
  btn.textContent = 'Generating...';
  try {
    const data = await aiGenerate('hashtags', prompt);
    const tags = (data.hashtags || []).slice(0, 15);
    if (!tags.length) {
      strip.innerHTML = '<span style="font-size:12px;color:var(--t3);align-self:center">No hashtags returned.</span>';
      return;
    }
    strip.innerHTML = tags.map(tag => (
      `<span class="htag" onclick="copyH('${escapeHtml(tag)}')">${escapeHtml(tag)}</span>`
    )).join('');
  } catch (error) {
    console.error('AI hashtag error:', error);
    alert(error.message || 'Failed to generate hashtags.');
  } finally {
    btn.disabled = false;
    btn.textContent = '# AI Hashtags';
  }
}

async function aiViralityScore() {
  const caption = document.getElementById('pub-caption').value.trim();
  if (!caption) {
    alert('Add caption first to score virality.');
    return;
  }
  const box = document.getElementById('virality-box');
  try {
    const data = await aiGenerate('virality', caption);
    const score = Number.isFinite(data.score) ? data.score : 70;
    box.style.display = 'block';
    box.innerHTML = `<strong>Virality Score: ${score}/100</strong><br><br>${escapeHtml(data.analysis || data.text || '')}`;
  } catch (error) {
    console.error('AI virality error:', error);
    alert(error.message || 'Failed to calculate virality score.');
  }
}

async function genIdeas() {
  const niche = document.getElementById('trend-niche')?.value || 'content creation';
  try {
    const data = await aiGenerate('ideas', `Generate ideas in niche: ${niche}`);
    const ideas = (data.ideas || []).slice(0, 6);
    if (!ideas.length) return;
    const col = document.getElementById('col-ideas');
    col.innerHTML = ideas.map((idea, index) => `
      <div class="idea-card" draggable="true">
        <div class="ip">AI Idea ${index + 1}</div>
        <div class="ititle">${escapeHtml(idea)}</div>
        <div class="idesc">Generated for your current niche and platform.</div>
        <div class="itags"><span class="itag">ai</span><span class="itag">fresh</span></div>
      </div>
    `).join('');
    document.getElementById('cnt-ideas').textContent = String(ideas.length);
  } catch (error) {
    console.error('AI ideas error:', error);
    alert(error.message || 'Failed to generate ideas.');
  }
}

function copyH(tag) {
  navigator.clipboard.writeText(tag);
}

function useTrend(el) {
  const trend = el.querySelector('.tname')?.textContent?.trim();
  if (!trend) return;
  tab('writer');
  document.getElementById('user-input').value = `Create a post about: ${trend}`;
  autoResize(document.getElementById('user-input'));
}

async function refreshHashtags() {
  const niche = document.getElementById('trend-niche')?.value || 'content creation';
  try {
    const data = await aiGenerate('hashtags', `Trending hashtags for niche: ${niche}`);
    const cloud = document.getElementById('hashtag-cloud');
    const tags = (data.hashtags || []).slice(0, 15);
    cloud.innerHTML = tags.map(tag => `<span class="htag" onclick="copyH('${escapeHtml(tag)}')">${escapeHtml(tag)}</span>`).join('');
  } catch (error) {
    console.error('Refresh hashtag error:', error);
    alert(error.message || 'Failed to refresh hashtags.');
  }
}

async function refreshTrends() {
  const niche = document.getElementById('trend-niche')?.value || 'content creation';
  const button = document.getElementById('trend-refresh-btn');
  button.disabled = true;
  button.textContent = 'Refreshing...';
  try {
    const data = await aiGenerate('trends', `Find trending creator topics in niche: ${niche}`);
    const lines = (data.text || '').split('\n').map(line => line.trim()).filter(Boolean).slice(0, 5);
    const hot = document.getElementById('trend-list-hot');
    if (lines.length) {
      hot.innerHTML = lines.map((line, i) => `
        <div class="trend-item" onclick="useTrend(this)">
          <div class="trank">${String(i + 1).padStart(2, '0')}</div>
          <div class="tinfo"><div class="tname">${escapeHtml(line.replace(/^\d+[\).\-\s]*/, ''))}</div><div class="tmeta">${escapeHtml(niche)} · AI refresh</div></div>
          <div class="tscore">${(9 - i * 0.3).toFixed(1)}</div>
        </div>
      `).join('');
    }
    if (Array.isArray(data.hashtags) && data.hashtags.length) {
      const cloud = document.getElementById('hashtag-cloud');
      cloud.innerHTML = data.hashtags.slice(0, 12).map(tag => `<span class="htag" onclick="copyH('${escapeHtml(tag)}')">${escapeHtml(tag)}</span>`).join('');
    }
  } catch (error) {
    console.error('Refresh trends error:', error);
    alert(error.message || 'Failed to refresh trends.');
  } finally {
    button.disabled = false;
    button.textContent = 'Refresh';
  }
}

function copyLast() {
  const msgs = document.querySelectorAll('.ai-msg');
  if (msgs.length > 0) {
    const lastMsg = msgs[msgs.length - 1].innerText;
    navigator.clipboard.writeText(lastMsg);
    alert('Copied!');
  }
}

function dlLast() {
  const msgs = document.querySelectorAll('.ai-msg');
  if (msgs.length > 0) {
    const lastMsg = msgs[msgs.length - 1].innerText;
    const blob = new Blob([lastMsg], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'creatorOS-content.txt';
    a.click();
  }
}

function clearChat() {
  const output = document.getElementById('ai-output');
  output.innerHTML = '<div class="ai-msg"><div class="msg-lbl">✦ CreatorOS AI</div><span>Chat cleared. Ready for new content!</span></div>';
}

async function scheduleFromSchedulerTab() {
  const platforms = getSelectedSchedulerPlatforms();
  const caption = document.getElementById('scheduler-caption').value.trim();
  const scheduleType = document.getElementById('scheduler-schedule-type').value;
  const dt = document.getElementById('scheduler-dt').value;
  const hashtags = extractHashtagsFromCaption(caption);

  if (!platforms.length) {
    showToast('Missing Platform', 'Select at least one platform.', 'warn');
    return;
  }
  if (!caption) {
    showToast('Missing Caption', 'Caption is required.', 'warn');
    return;
  }
  if (platforms.includes('youtube') && !hasUploadedYoutubeVideo(selectedSchedulerFiles)) {
    showToast('Video Required', 'YouTube requires uploaded video. Wait for upload preview, then schedule.', 'warn', 4200);
    return;
  }
  if (scheduleType === 'custom' && !dt) {
    showToast('Missing Time', 'Pick custom date and time.', 'warn');
    return;
  }

  const payload = {
    platforms,
    caption,
    hashtags,
    media_items: selectedSchedulerFiles,
    schedule_type: scheduleType,
    scheduled_for: scheduleType === 'custom' ? new Date(dt).toISOString() : null,
    youtube_settings: {
      title: document.getElementById('scheduler-yt-title')?.value?.trim() || '',
      description: document.getElementById('scheduler-yt-desc')?.value?.trim() || '',
      privacy: getYouTubePrivacy('scheduler')
    }
  };

  try {
    setButtonLoading('scheduler-submit-btn', 'Scheduling...', true);
    showToast('Submitting', 'Scheduling post request sent...', 'info');
    const response = await fetch(`${API_URL}/posts`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });
    const data = await parseJsonSafely(response);
    if (!response.ok) {
      const msg = data.exception
        ? `${data.error || 'Failed to schedule post'}\n${data.details || ''}\nException: ${data.exception}`
        : (data.details || data.error || 'Failed to schedule post');
      showToast('Schedule Failed', msg, 'error', 5000);
      return;
    }
    if (typeof data.remaining_credits === 'number') {
      document.getElementById('credit-count').textContent = data.remaining_credits;
      if (currentUser) currentUser.credits = data.remaining_credits;
    }
    showToast('Scheduled', `${data.created_count} post(s) queued successfully.`, 'success');
    await loadPostQueue();
    startQueuePolling();
  } catch (error) {
    console.error('Scheduler create post error:', error);
    showToast('Schedule Failed', 'Failed to schedule post.', 'error');
  } finally {
    setButtonLoading('scheduler-submit-btn', 'Scheduling...', false);
  }
}

async function publishContent() {
  const platforms = getSelectedPublishPlatforms();
  const caption = document.getElementById('pub-caption').value.trim();
  const hashtags = extractHashtagsFromCaption(caption);
  const dt = document.getElementById('sched-dt').value;
  const viralityBox = document.getElementById('virality-box').textContent || '';
  const scoreMatch = viralityBox.match(/(\d{1,3})\/100/);
  const viralityScore = scoreMatch ? Number(scoreMatch[1]) : null;

  if (!platforms.length) {
    showToast('Missing Platform', 'Select at least one connected platform.', 'warn');
    return;
  }
  if (!caption) {
    showToast('Missing Caption', 'Caption is required.', 'warn');
    return;
  }
  if (platforms.includes('youtube') && !hasUploadedYoutubeVideo(selectedUploadFiles)) {
    showToast('Video Required', 'YouTube requires uploaded video. Wait for upload preview, then publish.', 'warn', 4200);
    return;
  }
  if (publishScheduleMode === 'custom' && !dt) {
    showToast('Missing Time', 'Select custom date/time.', 'warn');
    return;
  }

  const payload = {
    platforms,
    caption,
    hashtags,
    media_items: selectedUploadFiles,
    schedule_type: publishScheduleMode,
    scheduled_for: publishScheduleMode === 'custom' ? new Date(dt).toISOString() : null,
    virality_score: viralityScore,
    youtube_settings: {
      title: document.getElementById('pub-yt-title')?.value?.trim() || '',
      description: document.getElementById('pub-yt-desc')?.value?.trim() || '',
      privacy: getYouTubePrivacy('pub')
    }
  };

  try {
    setButtonLoading('publish-submit-btn', 'Submitting...', true);
    showToast('Submitting', 'Publish request sent...', 'info');
    const response = await fetch(`${API_URL}/posts`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });
    const data = await parseJsonSafely(response);
    if (!response.ok) {
      const msg = data.exception
        ? `${data.error || 'Failed to queue post'}\n${data.details || ''}\nException: ${data.exception}`
        : (data.details || data.error || 'Failed to queue post');
      showToast('Publish Failed', msg, 'error', 5000);
      return;
    }
    if (typeof data.remaining_credits === 'number') {
      document.getElementById('credit-count').textContent = data.remaining_credits;
      if (currentUser) currentUser.credits = data.remaining_credits;
    }
    showToast('Queued', `${data.created_count} post(s) queued successfully.`, 'success');
    await loadPostQueue();
    startQueuePolling();
  } catch (error) {
    console.error('Publish content error:', error);
    showToast('Publish Failed', 'Failed to queue post.', 'error');
  } finally {
    setButtonLoading('publish-submit-btn', 'Submitting...', false);
  }
}

function openShopModal() {
  document.getElementById('shop-modal').style.display = 'flex';
}

function closeShopModal() {
  document.getElementById('shop-modal').style.display = 'none';
}

function openPremiumModal() {
  document.getElementById('premium-modal').style.display = 'flex';
}

function closePremiumModal() {
  document.getElementById('premium-modal').style.display = 'none';
}

function upgradeToPremium() {
  alert('Premium upgrade would connect to Stripe in production.');
}

function toggleAdmin() {
  const adminBtn = document.getElementById('admin-btn');
  if (currentUser?.email === 'admin@creator.os') {
    alert('Admin mode simulated. In production, this triggers admin dashboard.');
    tab('admin');
  }
}

async function saveProfile() {
  try {
    const name = document.getElementById('setting-name').value;
    const bio = document.getElementById('setting-bio').value;
    
    const response = await fetch(`${API_URL}/user/profile`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ name, bio })
    });
    
    if (response.ok) {
      const data = await response.json();
      currentUser = data.user;
      alert('Profile saved successfully!');
    } else {
      alert('Failed to save profile');
    }
  } catch (error) {
    console.error('Error saving profile:', error);
    alert('Error saving profile');
  }
}

async function changePassword() {
  const oldPassword = prompt('Enter your current password:');
  if (!oldPassword) return;
  
  const newPassword = prompt('Enter your new password (min 8 characters):');
  if (!newPassword || newPassword.length < 8) {
    alert('Password must be at least 8 characters');
    return;
  }
  
  try {
    const response = await fetch(`${API_URL}/user/password`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ old_password: oldPassword, new_password: newPassword })
    });
    
    const data = await response.json();
    
    if (response.ok) {
      alert('Password changed successfully!');
    } else {
      alert(data.error || 'Failed to change password');
    }
  } catch (error) {
    console.error('Error changing password:', error);
    alert('Error changing password');
  }
}

function toggle2FA(el) {
  el.classList.toggle('on');
}

function toggleNotif(el) {
  el.classList.toggle('on');
}

function toggleMarketing(el) {
  el.classList.toggle('on');
}

async function disconnectPlatform(platform) {
  if (!confirm(`Disconnect ${platform}?`)) return;
  
  try {
    const response = await fetch(`${API_URL}/platforms/disconnect`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ platform })
    });
    
    if (response.ok) {
      alert(`${platform} disconnected`);
      await loadConnectedPlatforms();
      await loadDashboardAnalytics();
    }
  } catch (error) {
    console.error('Error disconnecting platform:', error);
  }
}

async function connectPlatform(platform) {
  try {
    const response = await fetch(`${API_URL}/platforms/${platform}/auth`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ redirect_url: window.location.href })
    });
    
    if (response.ok) {
      const data = await response.json();
      window.location.href = data.auth_url;
    } else {
      const data = await parseJsonSafely(response);
      alert(data.error || `Failed to connect ${platform}`);
    }
  } catch (error) {
    console.error('Error connecting platform:', error);
    alert(`Error connecting ${platform}`);
  }
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 200) + 'px';
}

function handleKey(e) {
  if (e.key === 'Enter' && e.ctrlKey) {
    sendMsg();
  }
}

function repurpose() {
  alert('Repurposing content... (AI would generate multiple formats)');
}

function downloadApp() {
  alert('App download would be available as PWA/Electron in production.');
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 200) + 'px';
}

function handleKey(e) {
  if (e.key === 'Enter' && e.ctrlKey) {
    sendMsg();
  }
}

function repurpose() {
  alert('Repurposing content... (AI would generate multiple formats)');
}

// Initialize on load
hydrateAuthFromUrl();
handleOAuthResultFromUrl();
checkAuth();
