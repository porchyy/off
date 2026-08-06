const SAMPLE_LIMIT = 500;
const ALERT_LIMIT = 500;
const ADMIN_TOKEN_KEY = 'postureai_admin_token';
const KEYS = {
  samples: 'postureai_samples',
  alerts: 'postureai_alerts',
  settings: 'postureai_settings'
};

export const defaultSettings = {
  riskThreshold: 60,
  riskSeconds: 45,
  dataDir: 'database',
  soundEnabled: true,
  voiceEnabled: true,
  desktopEnabled: false
};

const readJson = (key, fallback) => {
  try {
    const value = localStorage.getItem(key);
    return value ? JSON.parse(value) : fallback;
  } catch {
    return fallback;
  }
};

const writeJson = (key, value) => {
  localStorage.setItem(key, JSON.stringify(value));
};

const todayKey = () => new Date().toISOString().slice(0, 10);
const dayKey = value => value.slice(0, 10);

const csvEscape = value => {
  const text = value == null ? '' : String(value);
  return /[",\n\r]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
};

function rowsToCsv(rows) {
  const columns = ['type', 'id', 'score', 'neck', 'shoulders', 'torso', 'severity', 'message', 'created_at'];
  return [
    columns.join(','),
    ...rows.map(row => columns.map(column => csvEscape(row[column])).join(','))
  ].join('\n');
}

async function requestJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) throw Error(`HTTP ${response.status}`);
  return response.json();
}

async function requestText(url) {
  const response = await fetch(url);
  if (!response.ok) throw Error(`HTTP ${response.status}`);
  return response.text();
}

function adminHeaders() {
  const token = sessionStorage.getItem(ADMIN_TOKEN_KEY);
  return token ? { 'x-postureai-admin-token': token } : {};
}

class BackendStorage {
  mode = 'backend';
  isDemo = false;

  async health() {
    return requestJson('/api/health');
  }

  async getSettings() {
    return requestJson('/api/settings');
  }

  async saveSettings(settings) {
    return requestJson('/api/settings', {
      method: 'PUT',
      headers: { 'content-type': 'application/json', ...adminHeaders() },
      body: JSON.stringify(settings)
    });
  }

  setAdminToken(token) {
    sessionStorage.setItem(ADMIN_TOKEN_KEY, token);
  }

  async addSample(sample) {
    return requestJson('/api/samples', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(sample)
    });
  }

  async addAlert(alert) {
    return requestJson('/api/alerts', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(alert)
    });
  }

  async summary() {
    return requestJson('/api/summary');
  }

  async stats() {
    return requestJson('/api/stats');
  }

  async clientStatus() {
    return requestJson('/api/client/status');
  }

  async export(format) {
    if (format === 'json') return JSON.stringify(await requestJson('/api/export?format=json'), null, 2);
    return requestText('/api/export?format=csv');
  }

  async clear() {
    return requestJson('/api/data', { method: 'DELETE', headers: adminHeaders() });
  }
}

class LocalStorageStorage {
  mode = 'demo';
  isDemo = true;

  async health() {
    return {
      ok: true,
      dbOk: false,
      mode: 'demo',
      dataDir: 'localStorage',
      time: new Date().toISOString()
    };
  }

  async getSettings() {
    return { ...defaultSettings, ...readJson(KEYS.settings, {}) };
  }

  async saveSettings(settings) {
    const next = { ...defaultSettings, ...settings, dataDir: 'localStorage' };
    writeJson(KEYS.settings, next);
    return next;
  }

  async addSample(sample) {
    const samples = readJson(KEYS.samples, []);
    samples.push({ id: crypto.randomUUID(), ...sample, created_at: new Date().toISOString() });
    writeJson(KEYS.samples, samples.slice(-SAMPLE_LIMIT));
    return { ok: true };
  }

  async addAlert(alert) {
    const alerts = readJson(KEYS.alerts, []);
    alerts.push({ id: crypto.randomUUID(), ...alert, created_at: new Date().toISOString() });
    writeJson(KEYS.alerts, alerts.slice(-ALERT_LIMIT));
    return { ok: true };
  }

  async summary() {
    const today = todayKey();
    const samples = readJson(KEYS.samples, []).filter(sample => dayKey(sample.created_at) === today);
    const alerts = readJson(KEYS.alerts, [])
      .filter(alert => dayKey(alert.created_at) === today)
      .sort((a, b) => b.created_at.localeCompare(a.created_at))
      .slice(0, 10);
    const average = samples.length
      ? Math.round(samples.reduce((sum, sample) => sum + Number(sample.score || 0), 0) / samples.length)
      : null;
    return { samples: samples.length, average, alerts };
  }

  async stats() {
    const samplesByDay = new Map();
    for (const sample of readJson(KEYS.samples, [])) {
      const label = dayKey(sample.created_at);
      const row = samplesByDay.get(label) || { label, total: 0, samples: 0 };
      row.total += Number(sample.score || 0);
      row.samples += 1;
      samplesByDay.set(label, row);
    }
    const daily = Array.from(samplesByDay.values())
      .map(row => ({ label: row.label, average: Math.round(row.total / row.samples), samples: row.samples }))
      .sort((a, b) => a.label.localeCompare(b.label))
      .slice(-14);

    const alertsByDay = new Map();
    for (const alert of readJson(KEYS.alerts, [])) {
      const label = dayKey(alert.created_at);
      alertsByDay.set(label, (alertsByDay.get(label) || 0) + 1);
    }
    const weeklyAlerts = Array.from(new Set([...samplesByDay.keys(), ...alertsByDay.keys()]))
      .sort()
      .slice(-14)
      .map(label => ({ label, alerts: alertsByDay.get(label) || 0 }));

    return { daily, weeklyAlerts };
  }

  setAdminToken() {}

  async clientStatus() {
    return { online: false, message: 'โหมดตัวอย่างไม่เชื่อมต่อ Raspberry Pi', retentionDays: null };
  }

  async export(format) {
    const rows = this.exportRows();
    if (format === 'json') return JSON.stringify({ exportedAt: new Date().toISOString(), mode: 'demo', rows }, null, 2);
    return rowsToCsv(rows);
  }

  async clear() {
    localStorage.removeItem(KEYS.samples);
    localStorage.removeItem(KEYS.alerts);
    return { ok: true };
  }

  exportRows() {
    const samples = readJson(KEYS.samples, []).map(sample => ({
      type: 'sample',
      id: sample.id,
      score: sample.score,
      neck: sample.neck,
      shoulders: sample.shoulders,
      torso: sample.torso,
      severity: null,
      message: null,
      created_at: sample.created_at
    }));
    const alerts = readJson(KEYS.alerts, []).map(alert => ({
      type: 'alert',
      id: alert.id,
      score: null,
      neck: null,
      shoulders: null,
      torso: null,
      severity: alert.severity,
      message: alert.message,
      created_at: alert.created_at
    }));
    return [...samples, ...alerts].sort((a, b) => a.created_at.localeCompare(b.created_at));
  }
}

export async function createStorage() {
  const backend = new BackendStorage();
  try {
    await backend.health();
    return backend;
  } catch {
    return new LocalStorageStorage();
  }
}
