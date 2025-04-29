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

## ISSUE-006
**Timestamp:** 2025-04-29T10:17:28Z

**Files Affected:**
- `src/mower/ui/web_ui/app.py`
- `src/mower/hardware/ina3221.py`
- `src/mower/navigation/path_planner.py`
- `src/mower/obstacle_detection/obstacle_detector.py`

**Description:**
Multiple errors were identified in the `JOURNALCTLOUTPUT.md` log:
1. `ResourceManager` object lacks `get_safety_status` and `get_status` methods.
2. INA3221 sensor initialization fails due to missing arguments.
3. `PathPlanner` initialization requires a `pattern_config` argument.
4. Undefined `_` function in Jinja2 templates for translations.
5. TensorFlow Lite interpreter initialization fails due to invalid model identifier.

**Error Messages:**
- `'ResourceManager' object has no attribute 'get_safety_status'`
- `'ResourceManager' object has no attribute 'get_status'`
- `INA3221Sensor() takes no arguments`
- `PathPlanner.__init__() missing 1 required positional argument: 'pattern_config'`
- `jinja2.exceptions.UndefinedError: '_' is undefined`
- `Failed to initialize interpreter: Model provided has model identifier 'onb', should be 'TFL3'`

**Attempted Fixes:**
1. Added `get_safety_status` and `get_status` methods to `ResourceManager`.
2. Updated `init_ina3221` method to correctly initialize the INA3221 sensor.
3. Ensured `PathPlanner` is initialized with the required `pattern_config` argument.
4. Added Flask-Babel initialization for translations in `app.py`.
5. Fixed `_initialize_interpreter` method to handle invalid model identifiers.

**Resolution:**
All issues were resolved by implementing the fixes listed above.

**Status:** Resolved

**Related Issues:** None

## ISSUE-007
**Timestamp:** 2025-04-29T12:50:10Z

**Files Affected:**
- `src/mower/ui/web_ui/app.py`
- `src/mower/navigation/path_planner.py`
- `src/mower/hardware/ina3221.py`

**Description:**
New and recurring errors were identified in the `JOURNALCTLOUTPUT.md` log:
1. `ResourceManager` object lacks `get_status` method.
2. INA3221 sensor initialization fails due to `name 'logger' is not defined`.
3. `PathPlanner` initialization requires a `pattern_config` argument.
4. Flask-Babel `localeselector` attribute is missing, causing web interface startup failure.

**Error Messages:**
- `'ResourceManager' object has no attribute 'get_status'`
- `Error initializing INA3221 sensor: name 'logger' is not defined`
- `PathPlanner.__init__() missing 1 required positional argument: 'pattern_config'`
- `AttributeError: 'Babel' object has no attribute 'localeselector'`

**Attempted Fixes:**
1. Added `get_status` method to `ResourceManager`.
2. Corrected logger initialization in `ina3221.py`.
3. Ensured `PathPlanner` is initialized with the required `pattern_config` argument.
4. Updated Flask-Babel usage to resolve `localeselector` attribute error.

**Resolution:**
Fixes have been implemented in the respective files.

**Status:** Resolved

**Related Issues:** ISSUE-006
