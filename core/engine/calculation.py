"""
Engineering & Physics Calculation Engine
Performs ground-truth physics formulas for battery runtimes, thermal loss, solar input, and dimensional clearances.
"""
from typing import Dict, Any, Optional

class CalculationEngine:
    """Scientific calculations for electrical systems, battery banks, and vehicle installations."""

    @staticmethod
    def _log_calculation(calc_type: str, inputs: dict, assumptions: dict, output: dict, entity_id: Optional[str] = None):
        try:
            from core.database import get_connection
            import json
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO calculation_logs (entity_id, calculation_type, inputs_json, formula_version, assumptions_json, output_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                entity_id,
                calc_type,
                json.dumps(inputs),
                "v1.2-physics",
                json.dumps(assumptions),
                json.dumps(output)
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

        inputs = {
            "battery_wh": battery_wh,
            "device_watts": device_watts,
            "is_ac_load": is_ac_load
        }
        assumptions = {
            "depth_of_discharge": depth_of_discharge,
            "inverter_efficiency": eff,
            "voltage_decay_loss": "factored into DoD",
            "ambient_temp_factor": "nominal 77F"
        }
        output = {
            "battery_nominal_wh": battery_wh,
            "device_watts": device_watts,
            "usable_wh": round(usable_wh, 1),
            "efficiency_factor": round(eff, 2),
            "runtime_hours": round(runtime_hours, 1),
            "runtime_days": round(days, 2),
            "display_str": f"{round(runtime_hours, 1)} hours ({round(days, 1)} days)" if days >= 1.0 else f"{round(runtime_hours, 1)} hours"
        }

        CalculationEngine._log_calculation("power_runtime", inputs, assumptions, output, entity_id)

        return {
            "formula_version": "v1.2-physics",
            "inputs": inputs,
            "assumptions": assumptions,
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
        # Linear approximation of duty cycle based on ambient temperature
        delta_t = max(5.0, ambient_temp_f - fridge_target_temp_f)
        duty_cycle = min(0.90, max(0.15, (delta_t / 100.0) * 0.70))

        eff = 0.95 if is_dc_12v else 0.85
        usable_wh = battery_wh * 0.90 * eff

        # Average continuous power draw
        avg_continuous_watts = fridge_rated_watts * duty_cycle
        daily_wh_consumption = avg_continuous_watts * 24.0
        runtime_hours = usable_wh / avg_continuous_watts
        runtime_days = runtime_hours / 24.0

        inputs = {
            "battery_wh": battery_wh,
            "fridge_rated_watts": fridge_rated_watts,
            "ambient_temp_f": ambient_temp_f,
            "fridge_target_temp_f": fridge_target_temp_f,
            "is_dc_12v": is_dc_12v
        }
        assumptions = {
            "cooling_duty_cycle_formula": "min(0.90, max(0.15, (ambient - target)/100 * 0.70))",
            "dc_conversion_efficiency": eff,
            "usable_capacity_dod": 0.90
        }
        output = {
            "battery_nominal_wh": battery_wh,
            "fridge_rated_watts": fridge_rated_watts,
            "ambient_temp_f": ambient_temp_f,
            "estimated_duty_cycle_pct": round(duty_cycle * 100, 1),
            "average_watts_draw": round(avg_continuous_watts, 1),
            "daily_wh_consumption": round(daily_wh_consumption, 1),
            "runtime_hours": round(runtime_hours, 1),
            "runtime_days": round(runtime_days, 2),
            "display_str": f"{round(runtime_hours, 1)} hours ({round(runtime_days, 1)} days at {ambient_temp_f}°F ambient)"
        }

        CalculationEngine._log_calculation("fridge_runtime", inputs, assumptions, output, entity_id)

        return {
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
