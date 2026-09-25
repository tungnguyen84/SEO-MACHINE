"""
Deterministic Calculation Engine Tests (Section 8)
Verifies that runtime and power calculations:
1. Yield exact deterministic results based on physics laws.
2. Record inputs, formula_version, assumptions, and output.
3. Are never guessed or hallucinated by an LLM.
"""
import pytest
from core.engine.calculation import CalculationEngine
from core.database import get_connection

def test_power_runtime_deterministic_fixed_input():
    """Test standard power runtime with fixed inputs: 1056Wh, 100W load, AC inverter."""
    battery_wh = 1056.0
    device_watts = 100.0
    is_ac_load = True
    inverter_eff = 0.85
    dod = 0.90
    
    # Expected: 1056 * 0.90 * 0.85 = 807.84 usable Wh.
    # 807.84 / 100 = 8.0784 hours -> rounded to 8.1 hours.
    res = CalculationEngine.calculate_runtime(
        battery_wh=battery_wh,
        device_watts=device_watts,
        is_ac_load=is_ac_load,
        inverter_efficiency=inverter_eff,
        depth_of_discharge=dod,
        entity_id="prod_anker_solix_c1000"
    )
    
    assert res["usable_wh"] == 807.8
    assert res["runtime_hours"] == 8.1
    assert res["formula_version"] == "v1.2-physics"
    assert res["inputs"]["battery_wh"] == 1056.0
    assert res["inputs"]["device_watts"] == 100.0
    assert res["assumptions"]["inverter_efficiency"] == 0.85
    assert res["assumptions"]["depth_of_discharge"] == 0.90
    
    # Verify persisted in calculation_logs database table
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM calculation_logs 
    WHERE calculation_type = 'power_runtime' AND entity_id = 'prod_anker_solix_c1000' 
    ORDER BY id DESC LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()
    
    assert row is not None, "Calculation must be persisted in calculation_logs"
    assert row["formula_version"] == "v1.2-physics"
    assert "807.8" in row["output_json"]

def test_fridge_runtime_duty_cycle_deterministic():
    """Test 12V fridge runtime with duty cycle modeling at 77°F ambient."""
    # Jackery 1000 v2 (1070Wh) powering 45W fridge on 12V DC
    res = CalculationEngine.calculate_fridge_runtime(
        battery_wh=1070.0,
        fridge_rated_watts=45.0,
        ambient_temp_f=77.0,
        fridge_target_temp_f=38.0,
        is_dc_12v=True
    )
    
    assert res["formula_version"] == "v1.2-physics"
    assert res["ambient_temp_f"] == 77.0
    assert res["estimated_duty_cycle_pct"] == 27.3
    assert res["average_watts_draw"] == 12.3
    assert res["runtime_hours"] > 70.0  # ~74 hours on 1070Wh at 77F
    assert res["runtime_days"] >= 3.0
