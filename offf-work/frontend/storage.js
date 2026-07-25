// PostureAI storage layer — talks to the real FastAPI backend only.
// (Demo/localStorage fallback removed: this build always requires a live backend.)

export const defaultSettings = {
  riskThreshold: 60,
  riskSeconds: 45,
  dataDir: '',
  soundEnabled: true,
  desktopEnabled: false
};

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

export class BackendUnavailableError extends Error {
  constructor(cause) {
    super('PostureAI backend ไม่ตอบสนอง — ตรวจสอบว่า backend รันอยู่ (docker compose up หรือ python -m app)');
    this.cause = cause;
  }
}

export class BackendStorage {
  mode = 'backend';

  async health() {
    return requestJson('/api/health');
  }

  async getSettings() {
    return requestJson('/api/settings');
  }

  async saveSettings(settings) {
    return requestJson('/api/settings', {
      method: 'PUT',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(settings)
    });
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

  async export(format) {
    if (format === 'json') return JSON.stringify(await requestJson('/api/export?format=json'), null, 2);
    return requestText('/api/export?format=csv');
  }

  async clear() {
    return requestJson('/api/data', { method: 'DELETE' });
  }
}

/**
 * Creates the storage client and confirms the backend is reachable.
 * Throws BackendUnavailableError if /api/health fails — the caller
 * (app.js) is responsible for showing a retry UI. There is no
 * silent localStorage fallback anymore: this build is "real backend or bust".
 */
export async function createStorage() {
  const backend = new BackendStorage();
  try {
    await backend.health();
  } catch (err) {
    throw new BackendUnavailableError(err);
  }
  return backend;
}
