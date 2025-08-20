from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol
import os

from .config import get_settings


try:
    from MomentumPyClient import Momentum as RealMomentum
except Exception:  # pragma: no cover - when not installed
    RealMomentum = None  # type: ignore


class MomentumLike(Protocol):
    """A structural type for Momentum methods used by the app."""

    def get_status(self) -> Dict[str, Any]: ...

    def get_version(self) -> Dict[str, Any]: ...

    def start(self) -> Optional[Dict[str, Any]]: ...

    def simulate(self) -> Optional[Dict[str, Any]]: ...

    def stop(self) -> Optional[Dict[str, Any]]: ...

    def get_devices(self) -> List[Dict[str, Any]]: ...

    def get_nests(self) -> List[Dict[str, Any]]: ...

    def get_processes(self) -> List[Dict[str, Any]]: ...

    def get_workqueue(self) -> List[Dict[str, Any]]: ...

    # Optional advanced
    def run_process(self, *args, **kwargs): ...


class MockMomentum(MomentumLike):
    def __init__(self) -> None:
        self._state = {
            "Simulated": True,
            "Attended": True,
            "State": {"Status": "Idle"},
        }

    def get_status(self) -> Dict[str, Any]:
        return self._state

    def get_version(self) -> Dict[str, Any]:
        return {"Version": "0.0.0-mock"}

    def start(self) -> None:
        self._state["State"] = {"Status": "Running"}
        return None

    def simulate(self) -> None:
        self._state["State"] = {"Status": "SimulateRunning"}
        return None

    def stop(self) -> None:
        self._state["State"] = {"Status": "Stopped"}
        return None

    def get_devices(self) -> List[Dict[str, Any]]:
        return [
            {
                "Id": "dev-1",
                "Name": "Hotel_1",
                "IsInstrument": True,
                "IsSimulated": True,
                "State": "Online",
            }
        ]

    def get_nests(self) -> List[Dict[str, Any]]:
        return [
            {
                "Name": "Hotel_1:Nests:Nest 1",
                "DeviceName": "Hotel_1",
                "Content": None,
                "IsStack": False,
                "StackContents": [],
            }
        ]

    def get_processes(self) -> List[Dict[str, Any]]:
        return [{"Id": "proc-1", "Name": "MockProcess"}]

    def get_workqueue(self) -> List[Dict[str, Any]]:
        return []

    def run_process(self, *args, **kwargs):
        return {"Details": "mock run_process accepted", "args": args, "kwargs": kwargs}


def create_momentum_client() -> MomentumLike:
    """Factory that returns either real Momentum or a mock, based on settings."""
    settings = get_settings()

    if settings.momentum_mock or RealMomentum is None:
        return MockMomentum()

    verify: bool | str
    v = str(settings.momentum_verify).strip().lower()
    if v in {"false", "0", "no"}:
        verify = False
    elif v in {"true", "1", "yes"}:
        verify = True
    else:
        verify = v

    return RealMomentum(
        url=settings.momentum_url,
        user_name=settings.momentum_user,
        password=settings.momentum_passwd,
        verify=verify,
        timeout=settings.momentum_timeout,
    )


