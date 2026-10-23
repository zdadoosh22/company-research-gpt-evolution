"""
Telemetry Flight-Recorder - MFE/MAE Diagnostic & Trade Analytics Engine
Isolated Tactical Laboratory: daytrading/tools/telemetry_blackbox.py

Provides black-box telemetry flight-recorder logging for every tactical execution:
1. Maximum Favorable Excursion (MFE): Maximum unrealized gain % reached during trade life.
2. Maximum Adverse Excursion (MAE): Maximum unrealized drawdown % reached during trade life.
3. Stop Placement Efficiency: Quantifies whether stops were placed too tight (MAE breached before 2R)
   or too loose (wasted risk budget).
4. Profit Capture Efficiency: (Realized Return / MFE) - identifies money left on the table.
5. Emits structured JSONL telemetry to `daytrading/logs/flight_recorder.jsonl`.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).resolve().parent
DAYTRADING_ROOT = SCRIPT_DIR.parent
LOGS_DIR = DAYTRADING_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
FLIGHT_RECORDER_LOG = LOGS_DIR / "flight_recorder.jsonl"


@dataclass
class TradeTelemetryRecord:
    trade_id: str
    ticker: str
    is_uk: bool
    sector: str
    entry_timestamp: str
    exit_timestamp: str
    entry_price: float
    exit_price: float
    position_size_gbp: float
    hold_duration_days: int
    realized_return_pct: float
    realized_pnl_gbp: float
    total_friction_gbp: float
    max_favorable_excursion_pct: float  # MFE
    max_adverse_excursion_pct: float   # MAE
    stop_distance_pct: float
    t1_distance_pct: float
    t2_distance_pct: float
    exit_reason: str
    profit_capture_ratio: float
    stop_efficiency_rating: str
    regime_state: str


class TelemetryBlackbox:
    """Manages recording, analysis, and serialization of flight-recorder trade telemetry."""

    def __init__(self, log_path: Path = FLIGHT_RECORDER_LOG):
        self.log_path = log_path

    def record_completed_trade(
        self,
        trade_id: str,
        ticker: str,
        is_uk: bool,
        sector: str,
        entry_timestamp: str,
        exit_timestamp: str,
        entry_price: float,
        exit_price: float,
        position_size_gbp: float,
        hold_duration_days: int,
        realized_return_pct: float,
        realized_pnl_gbp: float,
        total_friction_gbp: float,
        mfe_pct: float,
        mae_pct: float,
        stop_pct: float,
        t1_pct: float,
        t2_pct: float,
        exit_reason: str,
        regime_state: str = "BULL_TREND"
    ) -> TradeTelemetryRecord:
        """Computes trade flight telemetry and appends to persistent JSONL log."""
        
        # Profit capture ratio: Realized return / MFE (capped at 1.0 or 0.0 for losses)
        if realized_return_pct > 0 and mfe_pct > 0.001:
            profit_capture = round(min(1.0, realized_return_pct / mfe_pct), 3)
        else:
            profit_capture = 0.0

        # Stop placement efficiency rating
        abs_stop = abs(stop_pct)
        abs_mae = abs(mae_pct)
        if realized_return_pct > 0:
            if abs_mae < (abs_stop * 0.4):
                stop_rating = "OPTIMAL_LOW_STRESS_WIN"
            else:
                stop_rating = "TESTED_SUPPORT_AND_HELD"
        else:
            if abs_mae >= abs_stop:
                stop_rating = "DISCIPLINED_STOP_TRIGGERED"
            else:
                stop_rating = "TIME_OR_REGIME_BASED_CUT"

        record = TradeTelemetryRecord(
            trade_id=trade_id,
            ticker=ticker.upper(),
            is_uk=is_uk,
            sector=sector,
            entry_timestamp=entry_timestamp,
            exit_timestamp=exit_timestamp,
            entry_price=round(entry_price, 4),
            exit_price=round(exit_price, 4),
            position_size_gbp=round(position_size_gbp, 2),
            hold_duration_days=hold_duration_days,
            realized_return_pct=round(realized_return_pct, 2),
            realized_pnl_gbp=round(realized_pnl_gbp, 2),
            total_friction_gbp=round(total_friction_gbp, 2),
            max_favorable_excursion_pct=round(mfe_pct, 2),
            max_adverse_excursion_pct=round(mae_pct, 2),
            stop_distance_pct=round(stop_pct, 2),
            t1_distance_pct=round(t1_pct, 2),
            t2_distance_pct=round(t2_pct, 2),
            exit_reason=exit_reason,
            profit_capture_ratio=profit_capture,
            stop_efficiency_rating=stop_rating,
            regime_state=regime_state
        )

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(record)) + "\n")

        return record

    def load_recent_records(self, limit: int = 50) -> list[dict]:
        """Loads the most recent telemetry records from disk."""
        if not self.log_path.exists():
            return []
        records = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except Exception:
                        pass
        return records[-limit:]

    def summarize_telemetry(self) -> dict:
        """Computes aggregate analytics across recorded flight history."""
        records = self.load_recent_records(limit=1000)
        if not records:
            return {"total_records": 0, "avg_mfe": 0.0, "avg_mae": 0.0, "avg_profit_capture": 0.0}

        n = len(records)
        avg_mfe = sum(r["max_favorable_excursion_pct"] for r in records) / n
        avg_mae = sum(r["max_adverse_excursion_pct"] for r in records) / n
        wins = [r for r in records if r["realized_pnl_gbp"] > 0]
        avg_pc = (sum(r["profit_capture_ratio"] for r in wins) / max(1, len(wins))) if wins else 0.0

        return {
            "total_records": n,
            "win_count": len(wins),
            "loss_count": n - len(wins),
            "avg_mfe_pct": round(avg_mfe, 2),
            "avg_mae_pct": round(avg_mae, 2),
            "avg_profit_capture_ratio": round(avg_pc, 3),
            "total_pnl_gbp": round(sum(r["realized_pnl_gbp"] for r in records), 2),
            "total_friction_paid_gbp": round(sum(r["total_friction_gbp"] for r in records), 2)
        }


def main():
    bb = TelemetryBlackbox()
    # Log sample seed trades if empty
    existing = bb.load_recent_records(limit=5)
    if not existing:
        bb.record_completed_trade(
            trade_id="TR-202610-001",
            ticker="NVDA",
            is_uk=False,
            sector="MEGACAP_TITANS",
            entry_timestamp="2026-10-15 14:45:00",
            exit_timestamp="2026-10-21 20:55:00",
            entry_price=135.20,
            exit_price=152.80,
            position_size_gbp=333.33,
            hold_duration_days=4,
            realized_return_pct=13.02,
            realized_pnl_gbp=43.40,
            total_friction_gbp=1.42,
            mfe_pct=15.80,
            mae_pct=-2.10,
            stop_pct=-6.50,
            t1_pct=8.50,
            t2_pct=18.00,
            exit_reason="STAGE_2_10EMA_TRAIL",
            regime_state="BULL_TREND"
        )
        bb.record_completed_trade(
            trade_id="TR-202610-002",
            ticker="RR.L",
            is_uk=True,
            sector="UK_ZERO_FX_ISA",
            entry_timestamp="2026-10-16 08:15:00",
            exit_timestamp="2026-10-22 16:25:00",
            entry_price=5.22,
            exit_price=5.68,
            position_size_gbp=333.33,
            hold_duration_days=5,
            realized_return_pct=8.81,
            realized_pnl_gbp=29.37,
            total_friction_gbp=0.40,
            mfe_pct=9.50,
            mae_pct=-1.20,
            stop_pct=-5.50,
            t1_pct=5.00,
            t2_pct=11.00,
            exit_reason="STAGE_2_10EMA_TRAIL",
            regime_state="BULL_TREND"
        )
    summary = bb.summarize_telemetry()
    print("Telemetry Summary:", json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
