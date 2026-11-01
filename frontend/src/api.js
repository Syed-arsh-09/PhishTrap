/**
 * API client for PhishTrap FastAPI backend.
 */

const API_BASE = '/api/v1';

export async function fetchHealth() {
  const res = await fetch('/health');
  if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
  return res.json();
}

export async function fetchQueue(limit = 100, offset = 0) {
  const res = await fetch(`${API_BASE}/queue?limit=${limit}&offset=${offset}`);
  if (!res.ok) throw new Error(`Failed to fetch queue: ${res.statusText}`);
  return res.json();
}

export async function fetchMessage(id) {
  const res = await fetch(`${API_BASE}/messages/${id}`);
  if (!res.ok) throw new Error(`Failed to fetch message ${id}: ${res.statusText}`);
  return res.json();
}

export async function submitOverride(id, { reviewerId, action, reason }) {
  const res = await fetch(`${API_BASE}/messages/${id}/override`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      reviewer_id: reviewerId,
      action: action, // "RELEASE", "CONFIRM_PHISH", "RELABEL"
      reason: reason
    })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Override failed');
  }
  return res.json();
}

export async function fetchAuditLog(limit = 100, offset = 0) {
  const res = await fetch(`${API_BASE}/audit?limit=${limit}&offset=${offset}`);
  if (!res.ok) throw new Error(`Failed to fetch audit log: ${res.statusText}`);
  return res.json();
}

export async function fetchMetrics() {
  const res = await fetch(`${API_BASE}/metrics`);
  if (!res.ok) throw new Error(`Failed to fetch metrics: ${res.statusText}`);
  return res.json();
}

export async function ingestEmail(payload) {
  const res = await fetch(`${API_BASE}/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Ingestion failed');
  }
  return res.json();
}

