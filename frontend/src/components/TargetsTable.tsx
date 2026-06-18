import { CheckResult, Target } from '../types';

interface Props {
  targets: Target[];
  checks: CheckResult[];
  onSimulate: (targetId: number, mode: string) => Promise<void>;
  onHighLatency: (targetId: number) => Promise<void>;
  onRestartService: (targetId: number) => Promise<void>;
}

function latestStatus(checks: CheckResult[], targetId: number) {
  return checks.find((item) => item.target_id === targetId);
}

export function TargetsTable({ targets, checks, onSimulate, onHighLatency, onRestartService }: Props) {
  return (
    <section className="card">
      <h2>Monitored Targets</h2>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>Address</th>
              <th>Status</th>
              <th>Latency</th>
              <th>Failure Sim</th>
            </tr>
          </thead>
          <tbody>
            {targets.map((target) => {
              const current = latestStatus(checks, target.id);
              return (
                <tr key={target.id}>
                  <td>{target.name}</td>
                  <td>{target.target_type}</td>
                  <td>{target.address}</td>
                  <td>
                    <span className={`pill ${current?.status || 'down'}`}>{current?.status || 'unknown'}</span>
                  </td>
                  <td>{current?.latency_ms ? `${current.latency_ms} ms` : '-'}</td>
                  <td>
                    <div className="button-row">
                      <button onClick={() => onSimulate(target.id, 'server_down')}>Server Down</button>
                      <button onClick={() => onHighLatency(target.id)}>High Latency</button>
                      <button onClick={() => onSimulate(target.id, 'dns_failure')}>DNS Fail</button>
                      <button onClick={() => onSimulate(target.id, 'service_crash')}>Service Crash</button>
                      <button onClick={() => onRestartService(target.id)}>Restart</button>
                      <button onClick={() => onSimulate(target.id, 'none')}>Clear</button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
