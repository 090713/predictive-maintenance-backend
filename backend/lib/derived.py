"""
Derived parameter calculations for the frontend/backend shared logic.
"""
from dataclasses import dataclass


@dataclass
class DerivedParams:
    temp_difference: float
    mechanical_power: float
    overstrain: float


def derive(machine_input) -> DerivedParams:
    """Calculate derived parameters from raw sensor inputs."""
    temp_difference = machine_input.process_temperature - machine_input.air_temperature
    mechanical_power = (machine_input.torque * machine_input.rotational_speed * 2 * 3.14159) / 60
    overstrain = machine_input.tool_wear * machine_input.torque

    return DerivedParams(
        temp_difference=round(temp_difference, 2),
        mechanical_power=round(mechanical_power, 1),
        overstrain=round(overstrain, 1),
    )


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))