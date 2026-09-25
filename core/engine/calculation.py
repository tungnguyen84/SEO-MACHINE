"""
Engineering & Physics Calculation Engine
Performs ground-truth physics formulas for battery runtimes, thermal loss, solar input, and dimensional clearances.
"""
from typing import Dict, Any, Optional, List
from enum import Enum

class InputProvenance(str, Enum):
    MEASURED = "MEASURED"
    SOURCE_VERIFIED = "SOURCE_VERIFIED"
    USER_INPUT = "USER_INPUT"
    MANUFACTURER_SPEC = "MANUFACTURER_SPEC"
    ASSUMPTION = "ASSUMPTION"
    MODELLED = "MODELLED"
    DEFAULT = "DEFAULT"

class CalculationProvenance(str, Enum):
    VERIFIED_CALCULATION = "VERIFIED_CALCULATION"
    ESTIMATED_CALCULATION = "ESTIMATED_CALCULATION"
    MODELLED_CALCULATION = "MODELLED_CALCULATION"

class ProvenanceFloat(float):
    def __new__(cls, value, provenance=InputProvenance.DEFAULT.value, unit=None):
        instance = super().__new__(cls, float(value))
        instance.provenance = provenance
        instance.unit = unit
        return instance

class CalculationEngine:
    """Scientific calculations for electrical systems, battery banks, and vehicle installations."""

    @staticmethod
    def _log_calculation(calc_type: str, inputs: dict, assumptions: dict, output: dict, entity_id: Optional[str] = None):
        try:
            from core.database import get_connection
            import json
            # Ensure float serialization
            def clean_dict(d):
                return {k: float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v for k, v in d.items()}

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO calculation_logs (entity_id, calculation_type, inputs_json, formula_version, assumptions_json, output_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                entity_id,
                calc_type,
                json.dumps(clean_dict(inputs)),
                "v1.2-physics",
                json.dumps(clean_dict(assumptions)),
                json.dumps(clean_dict(output))
            ))
            conn.commit()
            conn.close()
        except Exception:
            pass

    @staticmethod
    def calculate_runtime(
        battery_wh: float,
        device_watts: float,
        is_ac_load: bool = True,
        inverter_efficiency: float = 0.85,
        depth_of_discharge: float = 0.90,
        entity_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculates standard runtime for constant loads.
        - AC loads incur 15% inverter conversion loss (85% eff).
        - DC 12V loads avoid inverter loss (~95% eff).
        """
        if battery_wh <= 0 or device_watts <= 0:
            return {"error": "Battery capacity and device watts must be greater than zero."}

        eff = inverter_efficiency if is_ac_load else 0.95
        usable_wh = battery_wh * depth_of_discharge * eff
        runtime_hours = usable_wh / device_watts
        days = runtime_hours / 24.0

        p_batt = ProvenanceFloat(battery_wh, InputProvenance.MANUFACTURER_SPEC.value, "Wh")
        p_dev = ProvenanceFloat(device_watts, InputProvenance.MANUFACTURER_SPEC.value, "W")
        p_eff = ProvenanceFloat(eff, InputProvenance.ASSUMPTION.value)
        p_dod = ProvenanceFloat(depth_of_discharge, InputProvenance.ASSUMPTION.value)

        inputs = {
            "battery_wh": p_batt,
            "device_watts": p_dev,
            "is_ac_load": is_ac_load
        }
        input_provenance = {
            "battery_wh": InputProvenance.MANUFACTURER_SPEC.value,
            "device_watts": InputProvenance.MANUFACTURER_SPEC.value,
            "is_ac_load": InputProvenance.USER_INPUT.value
        }
        assumptions = {
            "depth_of_discharge": p_dod,
            "inverter_efficiency": p_eff,
            "voltage_decay_loss": "factored into DoD",
            "ambient_temp_factor": "nominal 77F"
        }
        assumption_provenance = {
            "depth_of_discharge": InputProvenance.ASSUMPTION.value,
            "inverter_efficiency": InputProvenance.ASSUMPTION.value,
            "voltage_decay_loss": InputProvenance.ASSUMPTION.value,
            "ambient_temp_factor": InputProvenance.DEFAULT.value
        }

        has_modelled = any(
            p in [InputProvenance.MODELLED.value, InputProvenance.ASSUMPTION.value]
            for p in list(input_provenance.values()) + list(assumption_provenance.values())
        )
        provenance_class = CalculationProvenance.ESTIMATED_CALCULATION.value if has_modelled else CalculationProvenance.VERIFIED_CALCULATION.value
        confidence = 0.90 if has_modelled else 0.99

        display_str = (
            f"Estimated runtime: ~{round(runtime_hours, 1)} hours "
            f"({round(days, 1)} days)" if days >= 1.0 else f"Estimated runtime: ~{round(runtime_hours, 1)} hours"
        )

        output = {
            "value": round(runtime_hours, 1),
            "unit": "hours",
            "confidence": confidence,
            "provenance_class": provenance_class,
            "battery_nominal_wh": battery_wh,
            "device_watts": device_watts,
            "usable_wh": round(usable_wh, 1),
            "efficiency_factor": round(eff, 2),
            "runtime_hours": round(runtime_hours, 1),
            "runtime_days": round(days, 2),
            "display_str": display_str
        }

        CalculationEngine._log_calculation("power_runtime", inputs, assumptions, output, entity_id)

        return {
            "value": round(runtime_hours, 1),
            "unit": "hours",
            "confidence": confidence,
            "provenance_class": provenance_class,
            "formula_version": "v1.2-physics",
            "inputs": inputs,
            "input_provenance": input_provenance,
            "assumptions": assumptions,
            "assumption_provenance": assumption_provenance,
            "output": output,
            **output
        }

    @staticmethod
    def calculate_fridge_runtime(
        battery_wh: float,
        fridge_rated_watts: float = 45.0,
        ambient_temp_f: float = 77.0,
        fridge_target_temp_f: float = 38.0,
        is_dc_12v: bool = True,
        entity_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculates 12V compressor fridge runtime with duty cycle modeling.
        Compressors do NOT run continuously; they cycle on and off depending on ambient heat.
        - Ambient 70°F (mild): ~20% duty cycle
        - Ambient 77°F (room temp): ~28% duty cycle
        - Ambient 90°F (warm car): ~45% duty cycle
        - Ambient 100°F (baking vehicle): ~65% duty cycle
        """
        delta_t = max(5.0, ambient_temp_f - fridge_target_temp_f)
        duty_cycle = min(0.90, max(0.15, (delta_t / 100.0) * 0.70))

        eff = 0.95 if is_dc_12v else 0.85
        usable_wh = battery_wh * 0.90 * eff

        avg_continuous_watts = fridge_rated_watts * duty_cycle
        daily_wh_consumption = avg_continuous_watts * 24.0
        runtime_hours = usable_wh / avg_continuous_watts
        runtime_days = runtime_hours / 24.0

        p_batt = ProvenanceFloat(battery_wh, InputProvenance.MANUFACTURER_SPEC.value, "Wh")
        p_watts = ProvenanceFloat(fridge_rated_watts, InputProvenance.MANUFACTURER_SPEC.value, "W")
        p_ambient = ProvenanceFloat(ambient_temp_f, InputProvenance.USER_INPUT.value if ambient_temp_f != 77.0 else InputProvenance.DEFAULT.value, "deg_F")
        p_target = ProvenanceFloat(fridge_target_temp_f, InputProvenance.DEFAULT.value, "deg_F")
        p_duty = ProvenanceFloat(round(duty_cycle * 100, 1), InputProvenance.MODELLED.value, "percent")

        inputs = {
            "battery_wh": p_batt,
            "fridge_rated_watts": p_watts,
            "ambient_temp_f": p_ambient,
            "fridge_target_temp_f": p_target,
            "is_dc_12v": is_dc_12v
        }
        input_provenance = {
            "battery_wh": InputProvenance.MANUFACTURER_SPEC.value,
            "fridge_rated_watts": InputProvenance.MANUFACTURER_SPEC.value,
            "ambient_temp_f": InputProvenance.USER_INPUT.value if ambient_temp_f != 77.0 else InputProvenance.DEFAULT.value,
            "fridge_target_temp_f": InputProvenance.DEFAULT.value,
            "is_dc_12v": InputProvenance.ASSUMPTION.value
        }
        assumptions = {
            "cooling_duty_cycle_formula": "min(0.90, max(0.15, (ambient - target)/100 * 0.70))",
            "duty_cycle": p_duty,
            "dc_conversion_efficiency": eff,
            "usable_capacity_dod": 0.90
        }
        assumption_provenance = {
            "cooling_duty_cycle_formula": InputProvenance.MODELLED.value,
            "duty_cycle": InputProvenance.MODELLED.value,
            "dc_conversion_efficiency": InputProvenance.ASSUMPTION.value,
            "usable_capacity_dod": InputProvenance.ASSUMPTION.value
        }

        # Uncertainty inheritance: any critical MODELLED or ASSUMPTION forces MODELLED_CALCULATION
        has_modelled = any(
            p in [InputProvenance.MODELLED.value, InputProvenance.ASSUMPTION.value]
            for p in list(input_provenance.values()) + list(assumption_provenance.values())
        )
        provenance_class = CalculationProvenance.MODELLED_CALCULATION.value if has_modelled else CalculationProvenance.VERIFIED_CALCULATION.value
        confidence = 0.88 if has_modelled else 0.98

        display_str = (
            f"Estimated runtime: ~{round(runtime_hours, 1)} hours "
            f"(~{round(runtime_days, 1)} days at {ambient_temp_f}°F ambient, duty cycle ~{round(duty_cycle * 100, 1)}%) "
            f"under stated thermodynamic assumptions."
        )

        output = {
            "value": round(runtime_hours, 1),
            "unit": "hours",
            "battery_nominal_wh": battery_wh,
            "fridge_rated_watts": fridge_rated_watts,
            "ambient_temp_f": ambient_temp_f,
            "estimated_duty_cycle_pct": round(duty_cycle * 100, 1),
            "average_watts_draw": round(avg_continuous_watts, 1),
            "daily_wh_consumption": round(daily_wh_consumption, 1),
            "runtime_hours": round(runtime_hours, 1),
            "runtime_days": round(runtime_days, 2),
            "confidence": confidence,
            "provenance_class": provenance_class,
            "display_str": display_str
        }

        CalculationEngine._log_calculation("fridge_runtime", inputs, assumptions, output, entity_id)

        return {
            "value": round(runtime_hours, 1),
            "unit": "hours",
            "confidence": confidence,
            "provenance_class": provenance_class,
            "formula_version": "v1.2-physics",
            "inputs": inputs,
            "input_provenance": input_provenance,
            "assumptions": assumptions,
            "assumption_provenance": assumption_provenance,
            "output": output,
            **output
        }
        confidence = 0.88 if has_modelled else 0.98

        display_str = (
            f"Estimated runtime: ~{round(runtime_hours, 1)} hours "
            f"(~{round(runtime_days, 1)} days at {ambient_temp_f}°F ambient, duty cycle ~{round(duty_cycle * 100, 1)}%) "
            f"under stated thermodynamic assumptions."
        )

        output = {
            "value": round(runtime_hours, 1),
            "unit": "hours",
            "battery_nominal_wh": battery_wh,
            "fridge_rated_watts": fridge_rated_watts,
            "ambient_temp_f": ambient_temp_f,
            "estimated_duty_cycle_pct": round(duty_cycle * 100, 1),
            "average_watts_draw": round(avg_continuous_watts, 1),
            "daily_wh_consumption": round(daily_wh_consumption, 1),
            "runtime_hours": round(runtime_hours, 1),
            "runtime_days": round(runtime_days, 2),
            "confidence": confidence,
            "provenance_class": provenance_class,
            "display_str": display_str
        }

        CalculationEngine._log_calculation("fridge_runtime", inputs, assumptions, output, entity_id)

        return {
            "value": round(runtime_hours, 1),
            "unit": "hours",
            "confidence": confidence,
            "provenance_class": provenance_class,
            "formula_version": "v1.2-physics",
            "inputs": inputs,
            "assumptions": assumptions,
            "output": output,
            **output
        }

    @staticmethod
    def calculate_car_charging(
        battery_wh: float,
        outlet_amps: float = 10.0,
        vehicle_voltage: float = 12.0,
        efficiency: float = 0.88
    ) -> Dict[str, Any]:
        """
        Calculates time required to recharge a portable power station via vehicle 12V auxiliary socket.
        """
        watts_in = vehicle_voltage * outlet_amps * efficiency
        hours = battery_wh / watts_in if watts_in > 0 else 0

        return {
            "vehicle_outlet": f"{vehicle_voltage}V / {outlet_amps}A",
            "effective_charge_watts": round(watts_in, 1),
            "full_charge_hours": round(hours, 1),
            "display_str": f"{round(hours, 1)} hours of continuous driving"
        }

    @staticmethod
    def calculate_solar_charging(
        battery_wh: float,
        solar_rated_watts: float = 200.0,
        peak_sun_hours_per_day: float = 5.0,
        mppt_efficiency: float = 0.82
    ) -> Dict[str, Any]:
        """
        Calculates solar recharge time factoring in real-world MPPT and angle derating (~82%).
        """
        real_watts = solar_rated_watts * mppt_efficiency
        daily_yield_wh = real_watts * peak_sun_hours_per_day
        days_to_full = battery_wh / daily_yield_wh if daily_yield_wh > 0 else 0
        hours_peak_sun = battery_wh / real_watts if real_watts > 0 else 0

        return {
            "solar_rated_watts": solar_rated_watts,
            "real_world_watts": round(real_watts, 1),
            "daily_yield_wh": round(daily_yield_wh, 1),
            "hours_of_direct_sun": round(hours_peak_sun, 1),
            "days_to_full_charge": round(days_to_full, 2),
            "display_str": f"{round(hours_peak_sun, 1)} peak sun hours (~{round(days_to_full, 1)} days)"
        }
