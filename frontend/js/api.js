/**
 * API Client for Social Media Analytics Framework
 */

const API_BASE = window.location.origin;

export const ApiClient = {
  async getKPIs() {
    const res = await fetch(`${API_BASE}/api/kpis`);
    return await res.json();
  },

  async getFeed(limit = 40, platform = 'all', emotion = 'all', search = '') {
    const params = new URLSearchParams({ limit, platform, emotion, search });
    const res = await fetch(`${API_BASE}/api/feed?${params.toString()}`);
    return await res.json();
  },

  async getTimeline(buckets = 15) {
    const res = await fetch(`${API_BASE}/api/timeline?buckets=${buckets}`);
    return await res.json();
  },

  async getDemographics() {
    const res = await fetch(`${API_BASE}/api/demographics`);
    return await res.json();
  },

  async getTrends() {
    const res = await fetch(`${API_BASE}/api/trends`);
    return await res.json();
  },

  async getNetwork() {
    const res = await fetch(`${API_BASE}/api/network`);
    return await res.json();
  },

  async getCascade(seedUser = '', steps = 4) {
    const params = new URLSearchParams({ seed_user: seedUser, steps });
    const res = await fetch(`${API_BASE}/api/network/cascade?${params.toString()}`);
    return await res.json();
  },

  async analyzeCustomPost(payload) {
    const res = await fetch(`${API_BASE}/api/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return await res.json();
  },

  async checkToxicity(payload) {
    const res = await fetch(`${API_BASE}/api/check-toxicity`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return await res.json();
  },


  async controlStreamSpeed(speedSeconds) {
    const res = await fetch(`${API_BASE}/api/stream/control`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ speed_seconds: speedSeconds })
    });
    return await res.json();
  },

  async getDbHealth() {
    try {
      const res = await fetch(`${API_BASE}/api/db/health`);
      return await res.json();
    } catch (e) {
      return { status: 'offline', database: 'PostgreSQL', error: e.message };
    }
  },

  async reconnectDb(url = '') {
    const param = url ? `?db_url=${encodeURIComponent(url)}` : '';
    const res = await fetch(`${API_BASE}/api/db/reconnect${param}`, { method: 'POST' });
    return await res.json();
  },

  async getRealUsers(platform = 'all', search = '', limit = 60) {
    const params = new URLSearchParams({ platform, search, limit });
    const res = await fetch(`${API_BASE}/api/real-users?${params.toString()}`);
    return await res.json();
  },

  async triggerRealCollection() {
    const res = await fetch(`${API_BASE}/api/real-users/collect-now`, { method: 'POST' });
    return await res.json();
  },

  async exportRealUsers(format = 'json') {
    window.open(`${API_BASE}/api/real-users/export?format=${format}`, '_blank');
  },

  async createPost(payload) {
    const res = await fetch(`${API_BASE}/api/posts/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return await res.json();
  },

  async getComments(postId) {
    const res = await fetch(`${API_BASE}/api/posts/${encodeURIComponent(postId)}/comments`);
    return await res.json();
  },

  async addComment(postId, payload) {
    const res = await fetch(`${API_BASE}/api/posts/${encodeURIComponent(postId)}/comments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return await res.json();
  },

  async likePost(postId, liked = true, username = 'operator') {
    const res = await fetch(`${API_BASE}/api/posts/${encodeURIComponent(postId)}/like`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ liked, username })
    });
    return await res.json();
  },

  async repostPost(postId, payload = {}) {
    const res = await fetch(`${API_BASE}/api/posts/${encodeURIComponent(postId)}/repost`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return await res.json();
  }
};
