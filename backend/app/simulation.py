from dataclasses import dataclass


@dataclass
class SimulationState:
    mode: str = "none"
    latency_ms: int | None = None


class SimulationRegistry:
    def __init__(self) -> None:
        self._states: dict[int, SimulationState] = {}

    def set(self, target_id: int, mode: str, latency_ms: int | None = None) -> None:
        self._states[target_id] = SimulationState(mode=mode, latency_ms=latency_ms)

    def clear(self, target_id: int) -> None:
        self._states.pop(target_id, None)

    def get(self, target_id: int) -> SimulationState:
        return self._states.get(target_id, SimulationState())

    def snapshot(self) -> dict[int, SimulationState]:
        return dict(self._states)


simulation_registry = SimulationRegistry()
