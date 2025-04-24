# Issues Summary
Date: 2025-04-24

## 1. Missing get_status in ResourceManager
**Symptom**: `AttributeError: 'ResourceManager' object has no attribute 'get_status'` in the web UI update loop.
**Cause**: The UI was attempting to call `resource_manager.get_status()`, but no such method exists.
**Fix**: Either add a `get_status()` method to `ResourceManager` that proxies to `Mower.get_status()`, or update the web interface code to call `mower.get_status()` directly.

## 2. Incorrect battery voltage method in INA3221Sensor
**Symptom**: `AttributeError: 'INA3221Sensor' object has no attribute 'get_battery_voltage'` in `Mower.get_battery_level()`.
**Cause**: `Mower.get_battery_level()` calls a non-existent `get_battery_voltage()` on the sensor class, which only defines `battery_charge()` and `read()` methods.
**Fix**: Implement a `get_battery_voltage()` method in `INA3221Sensor` (e.g. wrap `read_ina3221(sensor, 3)['bus_voltage']`) or modify `Mower.get_battery_level()` to use the existing `battery_charge()` or `read()` methods.

## 3. Obstacle detection NoneType error
**Symptom**: `NoneType` error when checking obstacle detection status in `Mower.get_safety_status()`.
**Cause**: `ResourceManager.get_obstacle_detection()` returned `None`—likely due to a naming mismatch or initialization failure in `_initialize_software()`.
**Fix**: Ensure `ResourceManager._initialize_software()` sets the key exactly as used by the getter (`"obstacle_detection"`) and that all getters match resource keys.

## Next Steps
- Implement the missing methods and update callers.
- Run the full test suite and manual web UI tests to verify fixes.
- Update documentation and code comments to reflect these changes.
