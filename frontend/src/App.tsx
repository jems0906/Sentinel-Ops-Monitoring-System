import { useCallback, useEffect, useState } from 'react';
import {
  acknowledgeExternalAlert,
  addIncidentNote,
  fetchAlerts,
  fetchChecks,
  fetchExternalAlerts,
  fetchIncidents,
  fetchSummary,
  fetchTargets,
  restartService,
  toggleSimulation,
  unacknowledgeExternalAlert,
  updateIncident,
} from './api';
import { AlertsPanel } from './components/AlertsPanel';
import { ExternalAlertsPanel } from './components/ExternalAlertsPanel';
import { IncidentsPanel } from './components/IncidentsPanel';
import { SummaryCards } from './components/SummaryCards';
import { TargetsTable } from './components/TargetsTable';
import { AlertEvent, CheckResult, ExternalAlertEvent, Incident, Summary, Target } from './types';

function App() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [targets, setTargets] = useState<Target[]>([]);
  const [checks, setChecks] = useState<CheckResult[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [alerts, setAlerts] = useState<AlertEvent[]>([]);
  const [externalAlerts, setExternalAlerts] = useState<ExternalAlertEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setError(null);
      const [summaryData, targetData, checkData, incidentData, alertData, externalAlertData] = await Promise.all([
        fetchSummary(),
        fetchTargets(),
        fetchChecks(100),
        fetchIncidents(),
        fetchAlerts(50),
        fetchExternalAlerts(50),
      ]);
      setSummary(summaryData);
      setTargets(targetData);
      setChecks(checkData);
      setIncidents(incidentData);
      setAlerts(alertData);
      setExternalAlerts(externalAlertData);
    } catch {
      setError('Failed to load monitoring data. Check backend connectivity.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const timer = window.setInterval(loadData, 10000);
    return () => window.clearInterval(timer);
  }, [loadData]);

  async function handleSimulation(targetId: number, mode: string) {
    await toggleSimulation(targetId, mode);
    await loadData();
  }

  async function handleHighLatency(targetId: number) {
    await toggleSimulation(targetId, 'high_latency', 950);
    await loadData();
  }

  async function handleRestart(targetId: number) {
    await restartService(targetId);
    await loadData();
  }

  async function handleAddNote(incidentId: number, note: string) {
    await addIncidentNote(incidentId, note);
    await loadData();
  }

  async function handleUpdateRootCause(incidentId: number, rootCause: string) {
    await updateIncident(incidentId, { root_cause: rootCause });
    await loadData();
  }

  async function handleResolve(incidentId: number) {
    await updateIncident(incidentId, { status: 'resolved' });
    await loadData();
  }

  async function handleSetExternalAlertAcknowledged(eventId: number, acknowledged: boolean) {
    if (acknowledged) {
      await acknowledgeExternalAlert(eventId);
    } else {
      await unacknowledgeExternalAlert(eventId);
    }
    await loadData();
  }

  return (
    <div className="layout">
      <header className="hero">
        <div>
          <h1>Sentinel Ops Monitoring System</h1>
          <p>Network, service, and DNS monitoring with incident diagnostics and operational response workflows.</p>
        </div>
        <button onClick={loadData}>Refresh Now</button>
      </header>

      {loading && <p>Loading dashboard...</p>}
      {error && <p className="error">{error}</p>}

      <SummaryCards summary={summary} />
      <TargetsTable
        targets={targets}
        checks={checks}
        onSimulate={handleSimulation}
        onHighLatency={handleHighLatency}
        onRestartService={handleRestart}
      />
      <div className="grid split-grid">
        <IncidentsPanel
          incidents={incidents}
          onAddNote={handleAddNote}
          onUpdateRootCause={handleUpdateRootCause}
          onResolve={handleResolve}
        />
        <div className="grid stack-grid">
          <AlertsPanel alerts={alerts} />
          <ExternalAlertsPanel alerts={externalAlerts} onSetAcknowledged={handleSetExternalAlertAcknowledged} />
        </div>
      </div>
    </div>
  );
}

export default App;
