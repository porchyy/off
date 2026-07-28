/**
 * Auth & SSO module for PostureAI (Google, Microsoft 365, & Local Demo User)
 */

const TOKEN_KEY = 'postureai_access_token';
const USER_KEY = 'postureai_user';

let currentUser = null;
let currentToken = null;
const listeners = [];

export function initAuth() {
  const savedToken = localStorage.getItem(TOKEN_KEY);
  const savedUser = localStorage.getItem(USER_KEY);
  if (savedToken && savedUser) {
    try {
      currentToken = savedToken;
      currentUser = JSON.parse(savedUser);
    } catch {
      logout();
    }
  }
  notifyListeners();
  checkAuthMe();
}

export function subscribeAuth(callback) {
  listeners.push(callback);
  callback(currentUser, currentToken);
}

function notifyListeners() {
  listeners.forEach(cb => cb(currentUser, currentToken));
}

function getApiUrl(endpoint) {
  if (typeof window !== 'undefined' && window.location) {
    return endpoint;
  }
  return `http://localhost:8000${endpoint}`;
}

export async function checkAuthMe() {
  if (!currentToken) return;
  try {
    const resp = await fetch(getApiUrl('/api/auth/me'), {
      headers: { 'Authorization': `Bearer ${currentToken}` }
    });
    if (resp.ok) {
      currentUser = await resp.json();
      localStorage.setItem(USER_KEY, JSON.stringify(currentUser));
      notifyListeners();
    } else {
      logout();
    }
  } catch {
    // Offline or server unavailable - keep saved user
  }
}

export async function loginWithOAuth(provider, idToken) {
  const resp = await fetch(getApiUrl('/api/auth/oauth'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ provider, idToken })
  });
  if (!resp.ok) throw new Error('OAuth login failed');
  const data = await resp.json();
  setSession(data.accessToken, data.user);
  return data.user;
}

export async function loginAsDemo(email = 'employee@company.com', name = 'Somchai Employee') {
  const resp = await fetch(getApiUrl('/api/auth/demo'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, name })
  });
  if (!resp.ok) throw new Error('Demo login failed');
  const data = await resp.json();
  setSession(data.accessToken, data.user);
  return data.user;
}

function setSession(token, user) {
  currentToken = token;
  currentUser = user;
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
  notifyListeners();
}

export function logout() {
  currentToken = null;
  currentUser = null;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  notifyListeners();
}

export function getToken() {
  return currentToken;
}

export function getUser() {
  return currentUser;
}
