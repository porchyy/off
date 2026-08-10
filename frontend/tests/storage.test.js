import test from 'node:test';
import assert from 'node:assert/strict';

// Mock localStorage for Node environment
class MockLocalStorage {
  constructor() {
    this.store = new Map();
  }
  getItem(key) {
    return this.store.has(key) ? this.store.get(key) : null;
  }
  setItem(key, value) {
    this.store.set(key, String(value));
  }
  removeItem(key) {
    this.store.delete(key);
  }
  clear() {
    this.store.clear();
  }
}

globalThis.localStorage = new MockLocalStorage();

// Import storage after mocking localStorage
const { createStorage, defaultSettings } = await import('../storage.js');

test('LocalStorageStorage fallback initializes with default settings', async () => {
  localStorage.clear();
  const storage = await createStorage(); // backend health check will fail, falling back to LocalStorageStorage
  assert.equal(storage.isDemo, true);

  const settings = await storage.getSettings();
  assert.equal(settings.riskThreshold, defaultSettings.riskThreshold);
  assert.equal(settings.riskSeconds, defaultSettings.riskSeconds);
  assert.equal(settings.soundEnabled, defaultSettings.soundEnabled);
});

test('LocalStorageStorage saveSettings and getSettings', async () => {
  localStorage.clear();
  const storage = await createStorage();

  const updated = await storage.saveSettings({ riskThreshold: 75, riskSeconds: 30, soundEnabled: false });
  assert.equal(updated.riskThreshold, 75);
  assert.equal(updated.riskSeconds, 30);
  assert.equal(updated.soundEnabled, false);

  const reloaded = await storage.getSettings();
  assert.equal(reloaded.riskThreshold, 75);
  assert.equal(reloaded.riskSeconds, 30);
  assert.equal(reloaded.soundEnabled, false);
});

test('LocalStorageStorage addSample, summary, and stats', async () => {
  localStorage.clear();
  const storage = await createStorage();

  await storage.addSample({ score: 90, neck: 10, shoulders: 2, torso: 1 });
  await storage.addSample({ score: 70, neck: 15, shoulders: 5, torso: 4 });
  await storage.addAlert({ severity: 'risk', message: 'Adjust posture' });

  const summary = await storage.summary();
  assert.equal(summary.samples, 2);
  assert.equal(summary.average, 80);
  assert.equal(summary.alerts.length, 1);
  assert.equal(summary.alerts[0].message, 'Adjust posture');

  const stats = await storage.stats();
  assert.ok(stats.daily.length >= 1);
  assert.equal(stats.daily[0].samples, 2);
  assert.equal(stats.daily[0].average, 80);
});

test('LocalStorageStorage export and clear', async () => {
  localStorage.clear();
  const storage = await createStorage();

  await storage.addSample({ score: 85, neck: 10, shoulders: 2, torso: 1 });
  await storage.addAlert({ severity: 'caution', message: 'Watch out' });

  const csv = await storage.export('csv');
  assert.ok(csv.includes('type,id,score'));
  assert.ok(csv.includes('Watch out'));

  const jsonStr = await storage.export('json');
  const jsonData = JSON.parse(jsonStr);
  assert.equal(jsonData.mode, 'demo');
  assert.equal(jsonData.rows.length, 2);

  await storage.clear();
  const summaryAfter = await storage.summary();
  assert.equal(summaryAfter.samples, 0);
  assert.equal(summaryAfter.alerts.length, 0);
});
