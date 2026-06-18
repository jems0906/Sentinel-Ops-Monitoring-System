import axios from 'axios';
import { AlertEvent, CheckResult, ExternalAlertEvent, Incident, Summary, Target } from './types';

const apiBase = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

const client = axios.create({
  baseURL: apiBase,
  timeout: 10000,
});

export async function fetchSummary(): Promise<Summary> {
  const { data } = await client.get<Summary>('/api/summary');
  return data;
}

export async function fetchTargets(): Promise<Target[]> {
  const { data } = await client.get<Target[]>('/api/targets');
  return data;
}

export async function fetchChecks(limit = 50): Promise<CheckResult[]> {
  const { data } = await client.get<CheckResult[]>('/api/checks', { params: { limit } });
  return data;
}

export async function fetchIncidents(): Promise<Incident[]> {
  const { data } = await client.get<Incident[]>('/api/incidents');
  return data;
}

export async function fetchAlerts(limit = 50): Promise<AlertEvent[]> {
  const { data } = await client.get<AlertEvent[]>('/api/alerts', { params: { limit } });
  return data;
}

export async function fetchExternalAlerts(limit = 50): Promise<ExternalAlertEvent[]> {
  const { data } = await client.get<ExternalAlertEvent[]>('/api/external-alerts', { params: { limit } });
  return data;
}

export async function acknowledgeExternalAlert(eventId: number, acknowledgedBy = 'ops-user'): Promise<void> {
  await client.patch(`/api/external-alerts/${eventId}/acknowledge`, { acknowledged_by: acknowledgedBy });
}

export async function unacknowledgeExternalAlert(eventId: number): Promise<void> {
  await client.patch(`/api/external-alerts/${eventId}/unacknowledge`);
}

export async function toggleSimulation(target_id: number, mode: string, latency_ms?: number): Promise<void> {
  await client.post('/api/simulations/toggle', { target_id, mode, latency_ms });
}

export async function restartService(target_id: number): Promise<void> {
  await client.post(`/api/simulations/restart-service/${target_id}`);
}

export async function updateIncident(
  incidentId: number,
  payload: { status?: string; root_cause?: string },
): Promise<void> {
  await client.patch(`/api/incidents/${incidentId}`, payload);
}

export async function addIncidentNote(incidentId: number, note: string): Promise<void> {
  await client.post(`/api/incidents/${incidentId}/notes`, { note });
}
