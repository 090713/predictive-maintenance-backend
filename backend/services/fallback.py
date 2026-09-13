"""
Fallback prediction service - deterministic simulated engine for demo purposes.
"""
from datetime import datetime, timezone
from typing import Dict, List, Any

from backend.schemas import MachineInput, PredictionResponse


# Product type risk factors
PRODUCT_FACTOR = {"L": 0.0, "M": 0.06, "H": 0.14}


def clamp01(x: float) -> float:
    """Clamp value to [0, 1]."""
    return max(0.0, min(1.0, x))


def simulate_assessment(machine: MachineInput) -> PredictionResponse:
    """
    Deterministic simulated physics engine.
    Produces realistic failure probabilities based on sensor inputs.
    """
    from backend.lib.derived import derive

    d = derive(machine)
    product = PRODUCT_FACTOR[machine.product_type]

    # Failure mode scores (0-1)
    twf = clamp01((machine.tool_wear - 170) / 85) * (1 + product * 1.2)
    hdf = clamp01((18 - d.temp_difference) / 26) * (1 + abs(machine.process_temperature - 310) * 0.008)
    pwf = clamp01((d.mechanical_power - 4800) / 5200) * (1 + product * 0.8)
    osf = clamp01((d.overstrain - 5000) / 11000) * (1 + product * 0.6)
    rnf = 0.03

    # Weighted max blend (more realistic than union)
    ranked = sorted([twf, hdf, pwf, osf, rnf], reverse=True)
    failure_probability = clamp01(
        0.72 * ranked[0] + 0.22 * ranked[1] + 0.06 * ranked[2] + 0.02 + product * 0.05
    )
    failure_probability = min(failure_probability, 0.96)  # Cap at 96%

    # Determine health status
    if failure_probability >= 0.8:
        health_status = "Critical"
    elif failure_probability >= 0.6:
        health_status = "High Risk"
    elif failure_probability >= 0.35:
        health_status = "Warning"
    else:
        health_status = "Normal"

    # Risk level mapping
    risk_map = {"Critical": "Critical", "High Risk": "High", "Warning": "Medium", "Normal": "Low"}
    risk_level = risk_map[health_status]

    # Determine failure mode
    scores = {"TWF": twf, "HDF": hdf, "PWF": pwf, "OSF": osf, "RNF": rnf}
    top_mode = max(scores, key=scores.get)
    mode_code = top_mode if scores[top_mode] > 0.3 else "NONE"

    mode_names = {
        "TWF": "Tool Wear Failure",
        "HDF": "Heat Dissipation Failure",
        "PWF": "Power Failure",
        "OSF": "Overstrain Failure",
        "RNF": "Random Failure",
        "NONE": "No Failure",
    }

    return PredictionResponse(
        failure_probability=failure_probability,
        predicted_failure=failure_probability >= 0.5,
        anomaly_score=failure_probability * 100,
        anomaly_percentile=min(clamp01(failure_probability + 0.22) * 100, 99.0),
        is_anomaly=failure_probability >= 0.35,
        failure_modes=scores,
        health_status=health_status,
        failure_mode=mode_code if mode_code != "NONE" else None,
        failure_mode_name=mode_names.get(mode_code, "No Failure"),
        explanation=generate_explanation(health_status, mode_code, machine, d),
        maintenance_recommendation=generate_recommendation(mode_code, health_status),
        predicted_class=mode_code if mode_code != "NONE" else "NO FAILURE",
        recommended_maintenance_action=generate_recommendation(mode_code, health_status),
        decision_threshold=0.5,
        risk_level=risk_level,
        urgency=get_urgency(health_status),
        likely_failure_modes=[
            {"mode": k, "name": mode_names[k], "probability": v, "score": v, "score_kind": "simulated"}
            for k, v in scores.items() if v > 0.05
        ],
        contributing_features=generate_contributing(machine, d, scores),
        condition_evidence=generate_evidence(mode_code, machine, d),
        model_version="fathom-sim-v1",
        prediction_id=f"sim_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        prediction_timestamp=datetime.now(timezone.utc).isoformat(),
        latency_ms=10,
        decision_support_notice="Simulated physics engine — not a calibrated model. For demonstration only.",
    )


def generate_explanation(health_status: str, mode_code: str, machine: MachineInput, d) -> str:
    """Generate human-readable explanation."""
    if mode_code == "NONE":
        return "All monitored parameters and derived measures sit inside the nominal envelope. Failure probability is below the alert threshold; no dominant degradation driver is present."

    mode_explanations = {
        "TWF": f"Tool wear at {machine.tool_wear:.0f} minutes is the dominant degradation driver, indicating progressive cutting tool wear.",
        "HDF": f"Temperature difference of {d.temp_difference:.1f}K suggests degraded heat dissipation or cooling system performance.",
        "PWF": f"Mechanical power of {d.mechanical_power:.0f}W indicates abnormal load conditions.",
        "OSF": f"Overstrain index of {d.overstrain:.0f} indicates combined tool wear and torque stress.",
        "RNF": "No single sensor dominates; stochastic failure pattern detected.",
    }
    base = mode_explanations.get(mode_code, "Degradation detected in sensor readings.")
    return f"{base} Current risk level: {health_status}."


def generate_recommendation(mode_code: str, health_status: str) -> str:
    """Generate maintenance recommendation."""
    base_recommendations = {
        "TWF": "Inspect or replace the tool and recalibrate feed rates.",
        "HDF": "Check coolant flow; verify thermal isolation and airflow.",
        "PWF": "Inspect drive and motor; reduce load until verified.",
        "OSF": "Reduce torque and schedule spindle inspection.",
        "RNF": "Schedule diagnostic inspection; monitor trend closely.",
        "NONE": "Continue routine monitoring; no intervention required.",
    }
    base = base_recommendations.get(mode_code, "Monitor and investigate.")

    urgency_map = {
        "Critical": "Perform immediate inspection before next production cycle.",
        "High Risk": "Schedule within the next operating window.",
        "Warning": "Add to next inspection batch.",
        "Normal": "Continue routine monitoring.",
    }
    return f"{base} {urgency_map.get(health_status, '')}"


def get_urgency(health_status: str) -> str:
    """Map health status to urgency."""
    return {
        "Critical": "Immediate",
        "High Risk": "Urgent",
        "Warning": "Scheduled",
        "Normal": "Routine",
    }.get(health_status, "Routine")


def generate_contributing(machine: MachineInput, d, scores: Dict[str, float]) -> List[Dict[str, Any]]:
    """Generate contributing features."""
    features = []
    if scores["TWF"] > 0.3:
        features.append({
            "feature": "tool_wear",
            "label": "Tool wear",
            "value": machine.tool_wear,
            "magnitude": round(scores["TWF"], 3),
            "sign": 1,
            "direction": "increases",
            "method": "leave_one_out_replacement_with_training_baseline",
        })
    if scores["HDF"] > 0.3:
        features.append({
            "feature": "temp_difference",
            "label": "Temperature difference",
            "value": round(d.temp_difference, 1),
            "magnitude": round(scores["HDF"], 3),
            "sign": -1,
            "direction": "decreases",
            "method": "leave_one_out_replacement_with_training_baseline",
        })
    if scores["PWF"] > 0.3:
        features.append({
            "feature": "mechanical_power",
            "label": "Mechanical power",
            "value": round(d.mechanical_power, 0),
            "magnitude": round(scores["PWF"], 3),
            "sign": 1,
            "direction": "increases",
            "method": "leave_one_out_replacement_with_training_baseline",
        })
    if scores["OSF"] > 0.3:
        features.append({
            "feature": "overstrain",
            "label": "Overstrain",
            "value": round(d.overstrain, 0),
            "magnitude": round(scores["OSF"], 3),
            "sign": 1,
            "direction": "increases",
            "method": "leave_one_out_replacement_with_training_baseline",
        })
    return sorted(features, key=lambda x: x["magnitude"], reverse=True)


def generate_evidence(mode_code: str, machine: MachineInput, d) -> List[str]:
    """Generate condition evidence."""
    if mode_code == "NONE":
        return ["No condition evidence triggered — all monitored signals within bounds."]

    evidence_map = {
        "TWF": f"Tool wear ({machine.tool_wear:.0f} min) approaching critical threshold.",
        "HDF": f"Temperature differential ({d.temp_difference:.1f}K) below safe operating band.",
        "PWF": f"Mechanical power ({d.mechanical_power:.0f}W) exceeds normal operating range.",
        "OSF": f"Overstrain index ({d.overstrain:.0f}) indicates excessive combined stress.",
        "RNF": "Anomalous pattern without clear deterministic driver.",
    }
    return [evidence_map.get(mode_code, "Degradation detected.")]