import { useState } from 'react';
import { Incident } from '../types';

interface Props {
  incidents: Incident[];
  onAddNote: (incidentId: number, note: string) => Promise<void>;
  onUpdateRootCause: (incidentId: number, rootCause: string) => Promise<void>;
  onResolve: (incidentId: number) => Promise<void>;
}

export function IncidentsPanel({ incidents, onAddNote, onUpdateRootCause, onResolve }: Props) {
  const [noteDraft, setNoteDraft] = useState<Record<number, string>>({});
  const [rootCauseDraft, setRootCauseDraft] = useState<Record<number, string>>({});

  return (
    <section className="card">
      <h2>Incident Timeline + Root Cause Notes</h2>
      <div className="incident-list">
        {incidents.length === 0 && <p>No incidents yet. Trigger a simulation to test alerting and diagnostics.</p>}
        {incidents.map((incident) => (
          <article key={incident.id} className="incident-item">
            <header>
              <h3>{incident.title}</h3>
              <span className={`pill ${incident.status === 'open' ? 'down' : 'up'}`}>{incident.status}</span>
            </header>
            <p className="muted">
              Severity: {incident.severity} | Opened: {new Date(incident.created_at).toLocaleString()}
            </p>
            <div className="notes">
              {incident.notes.map((note) => (
                <div key={note.id} className="note-item">
                  <span>{new Date(note.created_at).toLocaleTimeString()}</span> - {note.note}
                </div>
              ))}
            </div>
            <textarea
              placeholder="Add incident timeline note"
              value={noteDraft[incident.id] || ''}
              onChange={(e) => setNoteDraft((prev) => ({ ...prev, [incident.id]: e.target.value }))}
            />
            <div className="button-row">
              <button
                onClick={async () => {
                  const value = (noteDraft[incident.id] || '').trim();
                  if (!value) return;
                  await onAddNote(incident.id, value);
                  setNoteDraft((prev) => ({ ...prev, [incident.id]: '' }));
                }}
              >
                Add Note
              </button>
            </div>
            <textarea
              placeholder="Root cause analysis notes"
              value={rootCauseDraft[incident.id] ?? incident.root_cause ?? ''}
              onChange={(e) => setRootCauseDraft((prev) => ({ ...prev, [incident.id]: e.target.value }))}
            />
            <div className="button-row">
              <button
                onClick={async () => {
                  const value = (rootCauseDraft[incident.id] ?? '').trim();
                  await onUpdateRootCause(incident.id, value);
                }}
              >
                Save Root Cause
              </button>
              {incident.status === 'open' && <button onClick={() => onResolve(incident.id)}>Mark Resolved</button>}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
