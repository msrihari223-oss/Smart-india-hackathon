/**
 * AETHERIA Client-Side Authentication & Session Controller
 * Manages operator login state, profile badges, clearance verification, and logout workflows.
 */

function resolveAuthApiBase() {
  if (typeof window === 'undefined') return 'http://127.0.0.1:8000';
  const loc = window.location;
  if (!loc || loc.protocol === 'file:' || loc.origin === 'null' || !loc.origin) {
    return 'http://127.0.0.1:8000';
  }
  if (loc.port === '8000' || (!loc.port && (loc.protocol === 'http:' || loc.protocol === 'https:'))) {
    return loc.origin;
  }
  if (loc.hostname === 'localhost' || loc.hostname === '127.0.0.1') {
    return `http://${loc.hostname}:8000`;
  }
  return loc.origin;
}

const AUTH_API_BASE = resolveAuthApiBase();

class AuthController {
  constructor() {
    this.token = localStorage.getItem('aetheria_token');
    this.user = null;
    try {
      const stored = localStorage.getItem('aetheria_user');
      if (stored) this.user = JSON.parse(stored);
    } catch (e) {
      this.user = null;
    }
  }

  async init() {
    this.renderUserBadge();
    if (this.token) {
      await this.validateSession();
    }
  }

  async validateSession() {
    try {
      const res = await fetch(`${AUTH_API_BASE}/api/auth/me?token=${encodeURIComponent(this.token)}`);
      const data = await res.json();
      if (data.authenticated && data.user) {
        this.user = data.user;
        localStorage.setItem('aetheria_user', JSON.stringify(data.user));
        this.renderUserBadge();
      } else {
        // Invalidate stale token
        this.token = null;
        this.user = null;
        localStorage.removeItem('aetheria_token');
        localStorage.removeItem('aetheria_user');
        this.renderUserBadge();
      }
    } catch (err) {
      console.warn('[AUTH] Validation request failed, using cached profile:', err);
    }
  }

  renderUserBadge() {
    const container = document.getElementById('header-user-profile');
    if (!container) return;

    if (this.user) {
      const name = this.user.full_name || this.user.username;
      const role = this.user.role || 'Analyst';
      const clearance = this.user.clearance_level || 'Level 3';
      const avatar = this.user.avatar || `https://api.dicebear.com/7.x/bottts/svg?seed=${this.user.username}`;

      container.innerHTML = `
        <div class="user-profile-badge" title="Active Security Clearance: ${clearance}">
          <img src="${avatar}" alt="${name}" class="user-avatar" />
          <div class="user-info">
            <span class="user-name">${name}</span>
            <span class="user-role"><i class="fas fa-shield-halved"></i> ${role} (${clearance})</span>
          </div>
          <button class="btn-logout" onclick="authController.logout()" title="Sign out / End Operator Session">
            <i class="fas fa-power-off"></i>
          </button>
        </div>
      `;
    } else {
      container.innerHTML = `
        <a href="/login" class="btn-login-gate" title="Operator Sign In & Clearance Verification">
          <i class="fas fa-user-shield"></i>
          <span>Sign In / Clearance</span>
        </a>
      `;
    }
  }

  logout() {
    if (this.token) {
      fetch(`${AUTH_API_BASE}/api/auth/logout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: this.token })
      }).catch(() => {});
    }

    localStorage.removeItem('aetheria_token');
    localStorage.removeItem('aetheria_user');
    this.token = null;
    this.user = null;
    window.location.href = '/login';
  }
}

// Global instance & robust initialization
window.authController = new AuthController();
function initAuth() {
  window.authController.init();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initAuth);
} else {
  initAuth();
}
