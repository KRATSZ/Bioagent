"""
PyFluent Protocol Simulation Utilities (CommandCatcher minimal viable version)

This module provides a dry-run simulator for pyFluent-style protocols by injecting
a CommandCatcher implementation that validates basic workflow constraints and
captures a structured log of operations. It mirrors the structured return shape
used elsewhere in the project to ease integration.
"""

from __future__ import annotations

import re
import sys
import types
import traceback
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union


# -----------------------------------------------------------------------------
# CommandCatcher protocol and FCA wrapper
# -----------------------------------------------------------------------------


class _InvalidStateException(Exception):
    pass


@dataclass
class _LabwareDefinition:
    label: str
    type: str
    location: str
    position: int


class CatcherFCA:
    """
    Minimal FCA wrapper that validates basic state machine:
    - Must get_tips before aspirate/dispense
    - Labware referenced must exist
    - Volumes must be positive
    - Wells string is parsed and validated for basic format (A1..H12)
    """

    def __init__(self, protocol: "CatcherProtocol") -> None:
        self._protocol = protocol
        self._has_tip: bool = False
        self._current_channels: Optional[List[int]] = None

    def _require_labware(self, label: str) -> None:
        if label not in self._protocol._defined_labware:
            raise ValueError(f"Labware '{label}' not defined. Use protocol.add_labware() first.")

    def _parse_wells(self, wells: Optional[str]) -> List[str]:
        if not wells:
            return []
        parsed: List[str] = []
        for w in wells.split(','):
            w = w.strip()
            if not re.match(r"^[A-Ha-h][1-9][0-2]?$", w):
                raise ValueError(f"Invalid well format: {w}")
            parsed.append(w.upper())
        return parsed

    def _validate_volumes(self, volume: Union[int, float]) -> float:
        if not isinstance(volume, (int, float)):
            raise TypeError("Volume must be a number")
        if volume <= 0:
            raise ValueError("Volume must be positive")
        if volume > 1000:
            # soft cap for demo safety
            raise ValueError("Volume exceeds 1000 uL limit for demo")
        return float(volume)

    def get_tips(self, tip_type: str, channels: List[int]) -> "CatcherFCA":
        if self._has_tip:
            raise _InvalidStateException("Tip already attached. Drop tips before picking up new ones.")
        if not channels or not all(isinstance(c, int) and c >= 0 for c in channels):
            raise ValueError("Channels must be a non-empty list of non-negative integers")
        self._has_tip = True
        self._current_channels = list(channels)
        self._protocol._events.append({
            "op": "get_tips", "tip_type": tip_type, "channels": list(channels)
        })
        return self

    # Aliased to uppercase method for compatibility if needed
    GetTips = get_tips

    def aspirate(
        self,
        volume: Union[int, float],
        labware: str,
        wells: Optional[str] = None,
        liquid_class: Optional[str] = None,
        channels: Optional[List[int]] = None,
        fluent_sn: Optional[str] = None,
    ) -> "CatcherFCA":
        if not self._has_tip:
            raise _InvalidStateException("No tip attached before aspirate")
        self._require_labware(labware)
        volume = self._validate_volumes(volume)
        use_channels = channels or self._current_channels or []
        if not use_channels:
            raise ValueError("No channels specified for aspirate")
        parsed_wells = self._parse_wells(wells)
        self._protocol._events.append({
            "op": "aspirate", "vol": float(volume), "labware": labware,
            "wells": parsed_wells, "channels": list(use_channels), "liquid_class": liquid_class or ""
        })
        return self

    # Uppercase alias
    Aspirate = aspirate

    def dispense(
        self,
        volume: Union[int, float],
        labware: str,
        wells: Optional[str] = None,
        liquid_class: Optional[str] = None,
        channels: Optional[List[int]] = None,
        fluent_sn: Optional[str] = None,
    ) -> "CatcherFCA":
        if not self._has_tip:
            raise _InvalidStateException("No tip attached before dispense")
        self._require_labware(labware)
        volume = self._validate_volumes(volume)
        use_channels = channels or self._current_channels or []
        if not use_channels:
            raise ValueError("No channels specified for dispense")
        parsed_wells = self._parse_wells(wells)
        self._protocol._events.append({
            "op": "dispense", "vol": float(volume), "labware": labware,
            "wells": parsed_wells, "channels": list(use_channels), "liquid_class": liquid_class or ""
        })
        return self

    # Uppercase alias
    Dispense = dispense

    def drop_tips(self, channels: Optional[List[int]] = None, fluent_sn: Optional[str] = None) -> "CatcherFCA":
        if not self._has_tip:
            raise _InvalidStateException("No tip attached to drop")
        use_channels = channels or self._current_channels or []
        if not use_channels:
            raise ValueError("No channels specified for drop_tips")
        self._protocol._events.append({
            "op": "drop_tips", "channels": list(use_channels)
        })
        self._has_tip = False
        self._current_channels = None
        return self

    # Uppercase alias
    DropTips = drop_tips


class CatcherProtocol:
    """
    Minimal Protocol compatible with the Fluent chain-style API surface area the LLM will use.
    Only captures commands and validates labware definitions.
    """

    def __init__(self, fluent_sn: str = "19905", output_file: str = "catcher_output.gwl") -> None:
        self.fluent_sn = fluent_sn
        self.output_file = output_file
        self._defined_labware: Dict[str, _LabwareDefinition] = {}
        self._events: List[Dict[str, Any]] = []

    # Fluent-friendly: return self for chaining
    def add_labware(self, labware_type: Any, labware_label: str, location: Any, position: int, **kwargs) -> "CatcherProtocol":
        self._defined_labware[labware_label] = _LabwareDefinition(
            label=labware_label, type=str(labware_type), location=str(location), position=int(position)
        )
        self._events.append({
            "op": "add_labware", "label": labware_label, "type": str(labware_type),
            "location": str(location), "position": int(position)
        })
        return self

    def get_defined_labware(self) -> List[str]:
        return list(self._defined_labware.keys())

    def fca(self) -> CatcherFCA:
        # Lazy single instance to preserve channel/tip state within a protocol
        if not hasattr(self, "_fca_instance") or self._fca_instance is None:
            self._fca_instance = CatcherFCA(self)
        return self._fca_instance

    # Optional compatibility methods used in demos
    def save(self) -> None:
        # No-op for simulation; still record an event
        self._events.append({"op": "save", "path": self.output_file})

    def get_events(self) -> List[Dict[str, Any]]:
        return list(self._events)


# -----------------------------------------------------------------------------
# Simulation driver
# -----------------------------------------------------------------------------


def _install_protocol_stub_module() -> None:
    """Install a stub 'Protocol' module into sys.modules for import-compatibility."""
    mod = types.ModuleType("Protocol")
    setattr(mod, "Protocol", CatcherProtocol)
    # Common exceptions/types used by FCACommand might be referenced
    setattr(mod, "InvalidStateException", _InvalidStateException)
    sys.modules["Protocol"] = mod


def get_pyfluent_error_recommendations(error_output: str) -> List[str]:
    if not error_output:
        return ["无详细错误输出，可检查函数入口或基本语法。"]
    recs: List[str] = []
    low = error_output.lower()
    if "invalid well" in low or "well format" in low:
        recs.append("孔位格式错误：仅支持 A1–H12，多个孔用逗号分隔，例如 'A1,B1'")
    if "no tip" in low or "tip" in low and "before" in low:
        recs.append("请在 aspirate/dispense 之前调用 get_tips，并在结束后 drop_tips")
    if "labware" in low and "not defined" in low:
        recs.append("请先使用 protocol.add_labware 定义耗材标签，再在 FCA 操作中引用该标签")
    if "volume" in low and ("negative" in low or "must be positive" in low or "exceeds" in low):
        recs.append("移液体积必须为正数，且应在仪器容量范围内（示例：1–1000 µL）")
    if "syntaxerror" in low:
        recs.append("Python 语法错误：检查括号、缩进、逗号等")
    if not recs:
        recs.append("通用建议：检查入口函数签名、链式调用顺序与耗材是否已定义。")
    return recs


def run_pyfluent_simulation(protocol_code: str, return_structured: bool = False) -> Union[str, Dict[str, Any]]:
    """
    Execute pyFluent-style protocol code in a dry-run CommandCatcher environment.

    Expected entry point in the code: def protocol(protocol): ...
    """
    result: Dict[str, Any] = {
        "success": False,
        "raw_output": "",
        "error_details": None,
        "has_warnings": False,
        "warning_details": None,
        "final_status": "Unknown",
        "recommendations": None,
    }

    # Basic syntax check
    try:
        compile(protocol_code, "<pyfluent_protocol>", "exec")
    except SyntaxError as e:
        err = f"SyntaxError: {e.msg} at line {e.lineno}"
        result.update({
            "success": False,
            "error_details": err,
            "final_status": "Syntax error",
            "recommendations": get_pyfluent_error_recommendations(err),
        })
        return result if return_structured else err

    # Install stub module for `from Protocol import Protocol`
    _install_protocol_stub_module()

    # Prepare execution context
    exec_globals: Dict[str, Any] = {
        "Protocol": CatcherProtocol,  # direct reference if code uses `Protocol(...)`
        "print": print,
        "__builtins__": __builtins__,
    }

    try:
        # Define code and get entry function
        exec(protocol_code, exec_globals)
        entry = exec_globals.get("protocol")
        if not callable(entry):
            raise ValueError("Required entry function 'protocol(protocol)' not found.")

        # Create catcher instance and run
        catcher = CatcherProtocol()
        entry(catcher)

        events = catcher.get_events()
        stdout_output = "pyFluent dry-run completed successfully\n"
        if events:
            stdout_output += "Captured Events:\n" + "\n".join([f"  - {e}" for e in events])

        result.update({
            "success": True,
            "raw_output": stdout_output,
            "final_status": "PyFluent dry-run completed successfully",
        })
        return result if return_structured else stdout_output

    except Exception as e:
        tb = traceback.format_exc()
        err = f"Exception during pyFluent simulation: {e}\n\n{tb}"
        result.update({
            "success": False,
            "error_details": err,
            "final_status": "PyFluent simulation failed",
            "recommendations": get_pyfluent_error_recommendations(err),
        })
        return result if return_structured else err


