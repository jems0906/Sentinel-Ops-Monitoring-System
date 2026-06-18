export type Status = 'up' | 'degraded' | 'down';

export interface Summary {
  total_targets: number;
  up_targets: number;
  degraded_targets: number;
  down_targets: number;
  open_incidents: number;
  recent_alerts: number;
  uptime_percent_24h: number;
  ext_firing: number;
  ext_unacked: number;
  ext_auto_acked: number;
}

export interface Target {
  id: number;
  name: string;
  target_type: 'ping' | 'http' | 'dns';
  address: string;
  interval_seconds: number;
  enabled: boolean;
  extra: Record<string, unknown>;
}

export interface CheckResult {
  id: number;
  target_id: number;
  status: Status;
  latency_ms: number | null;
  message: string;
  details: Record<string, unknown>;
  created_at: string;
}

export interface IncidentNote {
  id: number;
  incident_id: number;
  note: string;
  created_at: string;
}

export interface Incident {
  id: number;
  target_id: number;
  title: string;
  severity: 'low' | 'medium' | 'high';
  status: 'open' | 'resolved';
  root_cause: string | null;
  created_at: string;
  resolved_at: string | null;
  notes: IncidentNote[];
}

export interface AlertEvent {
  id: number;
  incident_id: number;
  channel: 'dashboard' | 'email';
  subject: string;
  body: string;
  created_at: string;
}

export interface ExternalAlertEvent {
  id: number;
  source: string;
  status: 'firing' | 'resolved' | 'unknown' | string;
  alert_name: string;
  severity: 'critical' | 'warning' | 'info' | 'unknown' | string;
  summary: string;
  repeat_count: number;
  last_seen_at: string;
  acknowledged: boolean;
  acknowledged_at: string | null;
  acknowledged_by: string | null;
  created_at: string;
}
