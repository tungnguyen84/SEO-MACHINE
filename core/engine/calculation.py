"""
Engineering & Physics Calculation Engine
Performs ground-truth scientific formulas for electrical loads, duty cycles,
solar generation, and dimensional clearances across diverse niches.
"""
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
import json
from pydantic import BaseModel, Field

from core.niche_adapters.base_adapter import ProvenanceClass, CalculationDefinition


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


class CalculationRegistry:
    """Central registry of mathematical and physics calculations across all niches."""
    _definitions: Dict[str, CalculationDefinition] = {}

    @classmethod
    def register(cls, definition: CalculationDefinition):
        cls._definitions[definition.calculation_id] = definition

    @classmethod
    def get(cls, calculation_id: str) -> Optional[CalculationDefinition]:
        return cls._definitions.get(calculation_id)

    @classmethod
    def list_all(cls) -> List[CalculationDefinition]:
        return list(cls._definitions.values())

    @classmethod
    def list_for_adapter(cls, adapter_id: str) -> List[CalculationDefinition]:
        return [d for d in cls._definitions.values() if d.adapter_id == adapter_id]

    @classmethod
    def execute(cls, calculation_id: str, **kwargs) -> Dict[str, Any]:
        defn = cls.get(calculation_id)
        if not defn:
            raise KeyError(f"Calculation '{calculation_id}' not found in CalculationRegistry.")
        if not defn.executor:
            raise ValueError(f"Calculation '{calculation_id}' has no registered executor.")
        return defn.executor(**kwargs)

    @classmethod
    def clear(cls):
        cls._definitions.clear()


class CalculationEngine:
    """Scientific calculations for electrical systems, battery banks, and equipment installations."""

    @staticmethod
    def _log_calculation(calc_type: str, inputs: dict, assumptions: dict, output: dict, entity_id: Optional[str] = None):
        try:
            from core.database import get_connection
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
        Calculates standard runtime for constant electrical loads.
        - AC loads incur conversion loss (~85% eff).
        - DC loads avoid inverter loss (~95% eff).
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
        Calculates compressor appliance runtime with duty cycle thermal modeling.
        Compressors cycle on/off according to ambient heat differentials:
        - Ambient 70°F (mild indoor): ~20% duty cycle
        - Ambient 77°F (room temp): ~28% duty cycle
        - Ambient 90°F (warm environment): ~45% duty cycle
        - Ambient 100°F (enclosed space heat): ~65% duty cycle
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
        p_amb = ProvenanceFloat(ambient_temp_f, InputProvenance.ASSUMPTION.value, "°F")
        p_target = ProvenanceFloat(fridge_target_temp_f, InputProvenance.USER_INPUT.value, "°F")
        p_duty = ProvenanceFloat(duty_cycle, InputProvenance.MODELLED.value)

        inputs = {
            "battery_wh": p_batt,
            "fridge_rated_watts": p_watts,
            "ambient_temp_f": p_amb,
            "fridge_target_temp_f": p_target,
            "is_dc_12v": is_dc_12v
        }
        input_provenance = {
            "battery_wh": InputProvenance.MANUFACTURER_SPEC.value,
            "fridge_rated_watts": InputProvenance.MANUFACTURER_SPEC.value,
            "ambient_temp_f": InputProvenance.ASSUMPTION.value,
            "fridge_target_temp_f": InputProvenance.USER_INPUT.value,
            "is_dc_12v": InputProvenance.USER_INPUT.value
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
            "confidence": 0.88,
            "provenance_class": CalculationProvenance.MODELLED_CALCULATION.value,
            "display_str": display_str,
            "model_disclosure": "Modelled duty cycle based on ambient thermal differential. Real-world consumption varies by sun exposure and ventilation."
        }

        CalculationEngine._log_calculation("fridge_runtime", inputs, assumptions, output, entity_id)

        return {
            "value": round(runtime_hours, 1),
            "unit": "hours",
            "confidence": 0.88,
            "provenance_class": CalculationProvenance.MODELLED_CALCULATION.value,
            "formula_version": "v1.2-physics",
            "inputs": inputs,
            "input_provenance": input_provenance,
            "assumptions": assumptions,
            "assumption_provenance": assumption_provenance,
            "output": output,
            **output
        }

    @staticmethod
    def calculate_fit_clearance(
        enclosure_height_inches: float,
        appliance_height_inches: float,
        lid_open_clearance_inches: float = 6.0
    ) -> Dict[str, Any]:
        """
        Calculates physical enclosure vertical clearance.
        - Clearance > 6.0 in: Full opening without obstruction.
        - Clearance 0.0 - 6.0 in: Fits closed, requires extension/slide for 90° open.
        - Clearance < 0.0 in: Does not fit.
        """
        clearance = enclosure_height_inches - appliance_height_inches
        lid_clearance = clearance - lid_open_clearance_inches

        if clearance < 0:
            status = "FAIL"
            detail = f"Appliance height ({appliance_height_inches}\") exceeds enclosure opening height ({enclosure_height_inches}\") by {abs(round(clearance, 1))}\"."
        elif lid_clearance < 0:
            status = "PASS_WITH_CONDITIONS"
            detail = (
                f"Fits inside enclosure ({round(clearance, 1)}\" vertical clearance), "
                f"but lid requires {lid_open_clearance_inches}\" clearance. Requires slide-out tray for full access."
            )
        else:
            status = "PASS"
            detail = f"Fits comfortably with {round(clearance, 1)}\" overhead clearance allowing complete opening."

        return {
            "enclosure_height_in": enclosure_height_inches,
            "appliance_height_in": appliance_height_inches,
            "remaining_clearance_in": round(clearance, 1),
            "lid_clearance_margin_in": round(lid_clearance, 1),
            "status": status,
            "detail": detail
        }

    @staticmethod
    def calculate_dc_charge_time(
        battery_wh: float,
        dc_voltage: float = 12.0,
        outlet_amps: float = 10.0,
        efficiency: float = 0.88
    ) -> Dict[str, Any]:
        """Calculates recharge duration via regulated DC auxiliary outlet."""
        watts_in = dc_voltage * outlet_amps * efficiency
        hours = battery_wh / watts_in if watts_in > 0 else 0

        return {
            "dc_outlet": f"{dc_voltage}V / {outlet_amps}A",
            "effective_charge_watts": round(watts_in, 1),
            "full_charge_hours": round(hours, 1),
            "display_str": f"{round(hours, 1)} hours of continuous charging"
        }

    # Backward compatibility aliases
    calculate_fridge_runtime_hours = calculate_fridge_runtime
    calculate_solar_charge_time_hours = lambda *args, **kwargs: CalculationEngine.calculate_solar_charging(*args, **kwargs)
    calculate_12v_charge_time_hours = lambda *args, **kwargs: CalculationEngine.calculate_dc_charge_time(*args, **kwargs)

    @staticmethod
    def calculate_solar_charging(
        battery_wh: float,
        solar_rated_watts: float = 200.0,
        peak_sun_hours_per_day: float = 5.0,
        mppt_efficiency: float = 0.82
    ) -> Dict[str, Any]:
        """Calculates solar recharge duration factoring in MPPT conversion and solar angle derating (~82%)."""
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


# Register core calculators into CalculationRegistry
CalculationRegistry.register(CalculationDefinition(
    calculation_id="power_runtime",
    adapter_id="core",
    name="Electrical Constant Load Runtime",
    required_inputs=["battery_wh", "device_watts"],
    optional_inputs=["is_ac_load", "inverter_efficiency", "depth_of_discharge"],
    formula_version="v1.2-physics",
    executor=CalculationEngine.calculate_runtime,
    output_schema={"runtime_hours": "float", "usable_wh": "float"}
))

CalculationRegistry.register(CalculationDefinition(
    calculation_id="solar_charging",
    adapter_id="core",
    name="Solar Array MPPT Charge Time",
    required_inputs=["battery_wh", "solar_rated_watts"],
    optional_inputs=["peak_sun_hours_per_day", "mppt_efficiency"],
    formula_version="v1.2-physics",
    executor=CalculationEngine.calculate_solar_charging,
    output_schema={"hours_of_direct_sun": "float", "days_to_full_charge": "float"}
))

CalculationRegistry.register(CalculationDefinition(
    calculation_id="dc_charging",
    adapter_id="core",
    name="Auxiliary DC Outlet Charging Time",
    required_inputs=["battery_wh"],
    optional_inputs=["dc_voltage", "outlet_amps", "efficiency"],
    formula_version="v1.2-physics",
    executor=CalculationEngine.calculate_dc_charge_time,
    output_schema={"full_charge_hours": "float", "effective_charge_watts": "float"}
))

CalculationRegistry.register(CalculationDefinition(
    calculation_id="enclosure_fit_clearance",
    adapter_id="core",
    name="Enclosure Dimensional Clearance",
    required_inputs=["enclosure_height_inches", "appliance_height_inches"],
    optional_inputs=["lid_open_clearance_inches"],
    formula_version="v1.0-geometry",
    executor=CalculationEngine.calculate_fit_clearance,
    output_schema={"remaining_clearance_in": "float", "status": "str"}
))
