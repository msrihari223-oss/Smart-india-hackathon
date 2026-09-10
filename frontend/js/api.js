/**
 * API Client for Social Media Analytics Framework
 * Automatically resolves the correct backend host across same-origin, Live Server, custom dev ports, or file protocols.
 */

export function resolveApiBase() {
  if (typeof window === 'undefined') return 'http://127.0.0.1:8000';
  const loc = window.location;
  if (!loc || loc.protocol === 'file:' || loc.origin === 'null' || !loc.origin) {
    return 'http://127.0.0.1:8000';
  }
  // When running directly from the FastAPI backend server (port 8000) or standard 80/443 in production
  if (loc.port === '8000' || (!loc.port && (loc.protocol === 'http:' || loc.protocol === 'https:'))) {
    return loc.origin;
  }
  // When running from a frontend dev server (e.g. Live Server on 5500, Vite on 5173, Next on 3000, etc.)
  if (loc.hostname === 'localhost' || loc.hostname === '127.0.0.1') {
    return `http://${loc.hostname}:8000`;
  }
  return loc.origin;
}

export function resolveWsUrl() {
  if (typeof window === 'undefined') return 'ws://127.0.0.1:8000/ws/stream';
  const loc = window.location;
  if (!loc || loc.protocol === 'file:' || loc.origin === 'null') {
    return 'ws://127.0.0.1:8000/ws/stream';
  }
  const wsProto = loc.protocol === 'https:' ? 'wss:' : 'ws:';
  if (loc.port === '8000' || (!loc.port && (loc.protocol === 'http:' || loc.protocol === 'https:'))) {
    return `${wsProto}//${loc.host}/ws/stream`;
  }
  if (loc.hostname === 'localhost' || loc.hostname === '127.0.0.1') {
    return `ws://${loc.hostname}:8000/ws/stream`;
  }
  return `${wsProto}//${loc.host}/ws/stream`;
}

export const API_BASE = resolveApiBase();
export const WS_URL = resolveWsUrl();

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

  async getInfluencerRankings(platform = 'all', country = 'all', category = 'all', search = '', sortBy = 'influence_score') {
    const params = new URLSearchParams({ platform, country, category, search, sort_by: sortBy });
    const res = await fetch(`${API_BASE}/api/influencers/rankings?${params.toString()}`);
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
    const body = typeof payload === 'string' ? { text: payload } : payload;
    const res = await fetch(`${API_BASE}/api/check-toxicity`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    return await res.json();
  },

  async uploadMedia(file) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/api/media/upload`, {
      method: 'POST',
      body: formData
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

  async syncRealUsersToDb() {
    const res = await fetch(`${API_BASE}/api/real-users/sync-db`, { method: 'POST' });
    return await res.json();
  },

  async exportRealUsers(format = 'json') {
    window.open(`${API_BASE}/api/real-users/export?format=${format}`, '_blank');
  },

  async getDangerWordsDataset() {
    const res = await fetch(`${API_BASE}/api/moderation/danger-words`);
    return await res.json();
  },

  async checkDangerWords(payload) {
    const res = await fetch(`${API_BASE}/api/moderation/check-danger-words`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return await res.json();
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
