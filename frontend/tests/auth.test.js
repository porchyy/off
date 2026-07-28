import test from 'node:test';
import assert from 'node:assert/strict';

// Mock localStorage for Node test runner
if (!globalThis.localStorage) {
  const store = new Map();
  globalThis.localStorage = {
    getItem: key => store.get(key) || null,
    setItem: (key, val) => store.set(key, String(val)),
    removeItem: key => store.delete(key),
    clear: () => store.clear()
  };
}

// Mock fetch before importing auth module
globalThis.fetch = async (url, opts = {}) => {
  const urlStr = String(url);
  if (urlStr.includes('/api/auth/demo')) {
    const body = JSON.parse(opts.body || '{}');
    return {
      ok: true,
      json: async () => ({
        accessToken: 'mock-jwt-token-123',
        user: { id: 'demo_user_1', email: body.email || 'employee@company.com', name: body.name || 'Somchai', provider: 'demo' }
      })
    };
  }
  if (urlStr.includes('/api/auth/me')) {
    return {
      ok: true,
      json: async () => ({ id: 'demo_user_1', email: 'employee@company.com', name: 'Somchai', provider: 'demo' })
    };
  }
  return { ok: false, status: 404 };
};

const { initAuth, loginAsDemo, logout, getUser, getToken } = await import('../auth.js');

test('auth state manages session storage correctly', async () => {
  logout();
  assert.equal(getUser(), null);
  assert.equal(getToken(), null);

  const user = await loginAsDemo('somchai@company.com', 'Somchai Employee');
  assert.equal(user.email, 'somchai@company.com');
  assert.equal(getToken(), 'mock-jwt-token-123');
  assert.equal(getUser().email, 'somchai@company.com');

  // Verify re-initialization restores saved session
  initAuth();
  assert.equal(getToken(), 'mock-jwt-token-123');
  assert.equal(getUser().email, 'somchai@company.com');

  logout();
  assert.equal(getUser(), null);
  assert.equal(getToken(), null);
});
