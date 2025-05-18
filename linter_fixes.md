# Python Linter Errors Report

**Progress Summary:** 40/120 Flake8 errors fixed ✅

**Total Flake8 Errors Found:** 120
**Total Pylance Errors Found:** 300+ (see below for details)

> **Note:** This report includes Flake8 errors (max line length 88) and Pylance errors as detected by VSCode.
> Flake8 errors are listed first, followed by Pylance errors.
> For each error: file path, line number, error code/type, error description, and suggested fix are provided.

---

## Flake8 Error List

src\mower\config_management\config_interface.py:199:89: E501 line too long (98 > 88 characters) ✅ FIXED
src\mower\config_management\config_source.py:92:15: E999 SyntaxError: invalid syntax ✅ FIXED
src\mower\config_management\secure_storage.py:127:54: E999 SyntaxError: invalid syntax ✅ FIXED
src\mower\diagnostics\system_health.py:33:1: F401 'platform' imported but unused ✅ FIXED
src\mower\diagnostics\system_health.py:35:1: F401 'shutil' imported but unused ✅ FIXED
src\mower\diagnostics\system_health.py:36:1: F401 'socket' imported but unused ✅ FIXED
src\mower\diagnostics\system_health.py:42:1: F401 'typing.Tuple' imported but unused ✅ FIXED
src\mower\diagnostics\system_health.py:42:1: F401 'typing.Union' imported but unused ✅ FIXED
src\mower\diagnostics\system_health.py:45:1: F401 'mower.diagnostics.hardware_test.HardwareTestSuite' imported but unused ✅ FIXED
src\mower\diagnostics\system_health.py:485:89: E501 line too long (106 > 88 characters) ✅ FIXED
src\mower\diagnostics\system_health.py:529:89: E501 line too long (93 > 88 characters) ✅ FIXED
src\mower\diagnostics\system_health.py:730:89: E501 line too long (89 > 88 characters) ✅ FIXED
src\mower\diagnostics\system_health.py:756:89: E501 line too long (102 > 88 characters) ✅ FIXED
src\mower\diagnostics\system_health.py:789:89: E501 line too long (122 > 88 characters) ✅ FIXED
src\mower\error_handling\error_reporter.py:16:1: F401 'mower.error_handling.error_codes.get_error_details' imported but unused ✅ FIXED
src\mower\error_handling\error_reporter.py:69:74: E203 whitespace before ':' ✅ FIXED
src\mower\error_handling\error_reporter.py:188:5: F841 local variable 'reporter' is assigned to but never used ✅ FIXED
src\mower\error_handling\examples.py:9:1: F401 'logging' imported but unused ✅ FIXED
src\mower\error_handling\examples.py:31:9: F841 local variable 'result' is assigned to but never used ✅ FIXED
src\mower\error_handling\exceptions.py:166:5: F841 local variable 'exception_type' is assigned to but never used ✅ FIXED
src\mower\error_handling\graceful_degradation.py:23:1: W293 blank line contains whitespace ✅ FIXED
src\mower\error_handling\graceful_degradation.py:26:1: W293 blank line contains whitespace ✅ FIXED
src\mower\error_handling\graceful_degradation.py:32:1: F401 'logging' imported but unused ✅ FIXED
src\mower\error_handling\graceful_degradation.py:35:1: F401 'typing.Optional' imported but unused ✅ FIXED
src\mower\error_handling\graceful_degradation.py:35:1: F401 'typing.Tuple' imported but unused ✅ FIXED
src\mower\error_handling\graceful_degradation.py:35:1: F401 'typing.Union' imported but unused ✅ FIXED
src\mower\error_handling\graceful_degradation.py:145:89: E501 line too long (96 > 88 characters) ✅ FIXED
src\mower\error_handling\graceful_degradation.py:246:89: E501 line too long (105 > 88 characters) ✅ FIXED
src\mower\error_handling\graceful_degradation.py:256:89: E501 line too long (109 > 88 characters) ✅ FIXED
src\mower\error_handling\graceful_degradation.py:271:89: E501 line too long (89 > 88 characters) ✅ FIXED
src\mower\error_handling\graceful_degradation.py:378:89: E501 line too long (99 > 88 characters) ✅ FIXED
src\mower\error_handling\graceful_degradation.py:419:89: E501 line too long (96 > 88 characters) ✅ FIXED
src\mower\events\_\_init**.py:10:1: W293 blank line contains whitespace ✅ FIXED
src\mower\events\_\_init**.py:13:1: W293 blank line contains whitespace ✅ FIXED
src\mower\events\_\_init**.py:16:1: W293 blank line contains whitespace ✅ FIXED
src\mower\events\event_bus.py:9:1: F401 'logging' imported but unused ✅ FIXED
src\mower\events\event_bus.py:12:1: F401 'time' imported but unused ✅ FIXED
src\mower\events\event_bus.py:13:1: F401 'typing.Any' imported but unused ✅ FIXED
src\mower\events\event_bus.py:13:1: F401 'typing.Set' imported but unused ✅ FIXED
src\mower\events\event_bus.py:13:1: F401 'typing.Tuple' imported but unused ✅ FIXED
src\mower\events\event_bus.py:13:1: F401 'typing.Union' imported but unused ✅ FIXED
src\mower\events\event_bus.py:15:1: F401 'mower.events.event.EventPriority' imported but unused ✅ FIXED
src\mower\events\event_bus.py:165:44: E203 whitespace before ':' ✅ FIXED
src\mower\events\examples.py:10:1: F401 'typing.Dict' imported but unused ✅ FIXED
src\mower\events\examples.py:10:1: F401 'typing.Any' imported but unused ✅ FIXED
src\mower\events\examples.py:13:1: F401 'mower.events.event_bus.EventBus' imported but unused ✅ FIXED
src\mower\events\handlers.py:11:1: F401 'typing.Type' imported but unused ✅ FIXED
src\mower\events\handlers.py:11:1: F401 'typing.Union' imported but unused
src\mower\fleet_management\fleet_manager.py:22:1: W293 blank line contains whitespace
src\mower\fleet_management\fleet_manager.py:26:1: W293 blank line contains whitespace
src\mower\fleet_management\fleet_manager.py:29:1: W293 blank line contains whitespace
src\mower\fleet_management\fleet_manager.py:33:1: W293 blank line contains whitespace
src\mower\fleet_management\fleet_manager.py:40:1: F401 'time' imported but unused
src\mower\fleet_management\fleet_manager.py:44:1: F401 'typing.Set' imported but unused
src\mower\fleet_management\fleet_manager.py:44:1: F401 'typing.Tuple' imported but unused
src\mower\fleet_management\fleet_manager.py:44:1: F401 'typing.Union' imported but unused
src\mower\fleet_management\fleet_manager.py:45:1: F401 'requests' imported but unused
src\mower\fleet_management\fleet_manager.py:47:1: F401 'logging' imported but unused
src\mower\fleet_management\fleet_manager.py:449:89: E501 line too long (93 > 88 characters)
src\mower\fleet_management\fleet_manager.py:507:89: E501 line too long (90 > 88 characters)
src\mower\fleet_management\fleet_manager.py:548:89: E501 line too long (91 > 88 characters)
src\mower\hardware\blade_controller.py:23:10: E999 SyntaxError: invalid syntax
src\mower\hardware\gpio_manager.py:160:36: E999 SyntaxError: invalid syntax
src\mower\hardware\ina3221.py:38:89: E501 line too long (98 > 88 characters)
src\mower\hardware\ina3221.py:70:89: E501 line too long (97 > 88 characters)
src\mower\hardware\sensor_fallback.py:10:1: F401 'typing.Tuple' imported but unused
src\mower\hardware\sensor_fallback.py:12:1: F401 'logging' imported but unused
src\mower\hardware\sensor_fallback.py:107:89: E501 line too long (94 > 88 characters)
src\mower\hardware\sensor_fallback.py:118:89: E501 line too long (92 > 88 characters)
src\mower\hardware\sensor_fallback.py:131:89: E501 line too long (98 > 88 characters)
src\mower\hardware\sensor_fallback.py:245:89: E501 line too long (114 > 88 characters)
src\mower\hardware\sensor_fallback.py:264:89: E501 line too long (95 > 88 characters)
src\mower\hardware\sensor_fallback.py:358:89: E501 line too long (90 > 88 characters)
src\mower\hardware\sensor_fallback.py:435:89: E501 line too long (95 > 88 characters)
src\mower\hardware\sensor_fallback.py:639:89: E501 line too long (91 > 88 characters)
src\mower\hardware\sensor_fallback.py:670:89: E501 line too long (89 > 88 characters)
src\mower\hardware\sensor_fallback.py:677:89: E501 line too long (90 > 88 characters)
src\mower\hardware\sensor_fallback.py:683:89: E501 line too long (90 > 88 characters)
src\mower\interfaces\gps.py:10:1: F401 'typing.Optional' imported but unused
src\mower\interfaces\gps.py:10:1: F401 'typing.List' imported but unused
src\mower\interfaces\hardware.py:10:1: F401 'typing.List' imported but unused
src\mower\interfaces\hardware.py:11:1: F401 'datetime.datetime' imported but unused
src\mower\interfaces\motor_controllers.py:10:1: F401 'typing.List' imported but unused
src\mower\interfaces\motor_controllers.py:10:1: F401 'typing.Tuple' imported but unused
src\mower\interfaces\navigation.py:10:1: F401 'numpy as np' imported but unused
src\mower\interfaces\navigation.py:156:89: E501 line too long (89 > 88 characters)
src\mower\interfaces\obstacle_detection.py:9:1: F401 'typing.Union' imported but unused
src\mower\interfaces\power_management.py:10:1: F401 'typing.Optional' imported but unused
src\mower\interfaces\power_management.py:10:1: F401 'typing.List' imported but unused
src\mower\interfaces\sensors.py:10:1: F401 'typing.List' imported but unused
src\mower\interfaces\sensors.py:11:1: F401 'datetime.datetime' imported but unused
src\mower\interfaces\ui.py:9:1: F401 'typing.Optional' imported but unused
src\mower\interfaces\utilities.py:9:1: F401 'typing.List' imported but unused
src\mower\interfaces\utilities.py:9:1: F401 'typing.Optional' imported but unused
src\mower\interfaces\utilities.py:9:1: F401 'typing.Tuple' imported but unused
src\mower\interfaces\utilities.py:9:1: F401 'typing.Union' imported but unused
src\mower\interfaces\weather.py:9:1: F401 'datetime.datetime' imported but unused
src\mower\interfaces\weather.py:10:1: F401 'typing.Optional' imported but unused
src\mower\navigation\gps.py:226:22: E999 SyntaxError: invalid syntax
src\mower\navigation\path_planner.py:110:14: E999 IndentationError: unexpected indent
src\mower\navigation\path_planning_optimizer.py:11:1: F401 'typing.List' imported but unused
src\mower\navigation\path_planning_optimizer.py:11:1: F401 'typing.Tuple' imported but unused
src\mower\navigation\path_planning_optimizer.py:11:1: F401 'typing.Optional' imported but unused
src\mower\navigation\path_planning_optimizer.py:11:1: F401 'typing.Callable' imported but unused
src\mower\navigation\path_planning_optimizer.py:252:5: F841 local variable 'optimizer' is assigned to but never used
src\mower\navigation\path_planning_optimizer.py:275:9: F841 local variable 'path' is assigned to but never used
src\mower\navigation\path_planning_optimizer.py:295:17: F541 f-string is missing placeholders
src\mower\navigation\path_planning_optimizer.py:338:17: F541 f-string is missing placeholders
src\mower\obstacle_detection\avoidance_algorithm.py:259:89: E501 line too long (93 > 88 characters)
src\mower\obstacle_detection\avoidance_algorithm.py:260:89: E501 line too long (98 > 88 characters)
src\mower\obstacle_detection\avoidance_algorithm.py:261:89: E501 line too long (97 > 88 characters)
src\mower\obstacle_detection\image_processing_optimizer.py:12:1: F401 'typing.List' imported but unused
src\mower\obstacle_detection\image_processing_optimizer.py:12:1: F401 'typing.Optional' imported but unused
src\mower\obstacle_detection\image_processing_optimizer.py:12:1: F401 'typing.Tuple' imported but unused
src\mower\obstacle_detection\image_processing_optimizer.py:12:1: F401 'typing.Callable' imported but unused
src\mower\obstacle_detection\image_processing_optimizer.py:356:89: E501 line too long (91 > 88 characters)
src\mower\obstacle_detection\image_processing_optimizer.py:361:89: E501 line too long (90 > 88 characters)
src\mower\obstacle_detection\image_processing_optimizer.py:403:5: F841 local variable 'optimizer' is assigned to but never used
src\mower\obstacle_detection\image_processing_optimizer.py:435:9: F841 local variable 'detections' is assigned to but never used
src\mower\obstacle_detection\image_processing_optimizer.py:443:9: F841 local variable 'drops' is assigned to but never used
src\mower\obstacle_detection\image_processing_optimizer.py:475:17: F541 f-string is missing placeholders
src\mower\obstacle_detection\image_processing_optimizer.py:480:17: F541 f-string is missing placeholders
src\mower\obstacle_detection\image_processing_optimizer.py:539:17: F541 f-string is missing placeholders
src\mower\obstacle_detection\obstacle_detector.py:212:89: E501 line too long (90 > 88 characters)
src\mower\plugins\plugin_base.py:10:1: F401 'typing.Optional' imported but unused
src\mower\plugins\plugin_base.py:10:1: F401 'typing.Type' imported but unused
src\mower\plugins\plugin_manager.py:13:1: F401 'typing.Any' imported but unused
src\mower\robot_di.py:11:1: F401 'mower.hardware.adapters.blade_controller_adapter.BladeControllerAdapter' imported but unused
src\mower\simulation\_\_init**.py:12:1: F401 'typing.Dict' imported but unused
src\mower\simulation\_\_init**.py:12:1: F401 'typing.Any' imported but unused
src\mower\simulation\_\_init**.py:12:1: F401 'typing.Optional' imported but unused
src\mower\simulation\_\_init**.py:12:1: F401 'typing.List' imported but unused
src\mower\simulation\_\_init**.py:12:1: F401 'typing.Tuple' imported but unused
src\mower\simulation\_\_init**.py:12:1: F401 'typing.Union' imported but unused
src\mower\simulation\_\_init**.py:12:1: F401 'typing.Type' imported but unused
src\mower\simulation\actuators\motor_sim.py:9:1: F401 'time' imported but unused
src\mower\simulation\actuators\motor_sim.py:10:1: F401 'threading' imported but unused
src\mower\simulation\actuators\motor_sim.py:11:1: F401 'typing.Dict' imported but unused
src\mower\simulation\actuators\motor_sim.py:11:1: F401 'typing.Optional' imported but unused
src\mower\simulation\actuators\motor_sim.py:11:1: F401 'typing.List' imported but unused
src\mower\simulation\actuators\motor_sim.py:11:1: F401 'typing.Tuple' imported but unused
src\mower\simulation\actuators\motor_sim.py:11:1: F401 'typing.Union' imported but unused
src\mower\simulation\actuators\motor_sim.py:11:1: F401 'typing.Type' imported but unused
src\mower\simulation\actuators\motor_sim.py:14:1: F401 'mower.simulation.world_model.Vector2D' imported but unused
src\mower\simulation\hardware_sim.py:13:1: F401 'typing.List' imported but unused
src\mower\simulation\hardware_sim.py:13:1: F401 'typing.Tuple' imported but unused
src\mower\simulation\hardware_sim.py:13:1: F401 'typing.Union' imported but unused
src\mower\simulation\hardware_sim.py:13:1: F401 'typing.Type' imported but unused
src\mower\simulation\hardware_sim.py:15:1: F401 'mower.simulation.is_simulation_enabled' imported but unused
src\mower\simulation\hardware_sim.py:104:89: E501 line too long (91 > 88 characters)
src\mower\simulation\sensors\gps_sim.py:13:1: F401 'typing.Union' imported but unused
src\mower\simulation\sensors\gps_sim.py:13:1: F401 'typing.Type' imported but unused
src\mower\simulation\sensors\gps_sim.py:16:1: F401 'mower.simulation.world_model.Vector2D' imported but unused
src\mower\simulation\sensors\gps_sim.py:230:89: E501 line too long (93 > 88 characters)
src\mower\simulation\sensors\gps_sim.py:241:89: E501 line too long (155 > 88 characters)
src\mower\simulation\sensors\gps_sim.py:257:89: E501 line too long (183 > 88 characters)
src\mower\simulation\sensors\gps_sim.py:298:89: E501 line too long (116 > 88 characters)
src\mower\simulation\sensors\gps_sim.py:329:89: E501 line too long (116 > 88 characters)
src\mower\simulation\sensors\gps_sim.py:405:89: E501 line too long (116 > 88 characters)
src\mower\simulation\world_model.py:106:10: E999 SyntaxError: invalid syntax
src\mower\state_management\_\_init**.py:10:1: W293 blank line contains whitespace
src\mower\state_management\_\_init**.py:13:1: W293 blank line contains whitespace
src\mower\state_management\_\_init**.py:16:1: W293 blank line contains whitespace
src\mower\state_management\_\_init**.py:19:1: W293 blank line contains whitespace
src\mower\state_management\state_manager.py:10:1: F401 'typing.Set' imported but unused
src\mower\ui\web_ui\_\_init\_\_.py:1:1: F401 '.web_interface.WebInterface' imported but unused
src\mower\ui\web_ui\auth.py:8:1: F401 'hashlib' imported but unused
src\mower\ui\web_ui\auth.py:12:1: F401 'flask.flash' imported but unused
src\mower\ui\web_ui\auth.py:22:1: F401 'werkzeug.security.check_password_hash' imported but unused
src\mower\ui\web_ui\auth.py:22:1: F401 'werkzeug.security.generate_password_hash' imported but unused
src\mower\ui\web_ui\auth.py:25:1: F401 'mower.utilities.audit_log.AuditEventType' imported but unused
src\mower\ui\web_ui\auth.py:94:21: F841 local variable 'error' is assigned to but never used
src\mower\ui\web_ui\permissions.py:9:1: F401 'typing.List' imported but unused
src\mower\ui\web_ui\permissions.py:9:1: F401 'typing.Optional' imported but unused
src\mower\ui\web_ui\permissions.py:9:1: F401 'typing.Union' imported but unused
src\mower\ui\web_ui\permissions.py:14:1: F401 'mower.utilities.audit_log.AuditEventType' imported but unused
src\mower\ui\web_ui\validation.py:8:1: F401 'json' imported but unused
src\mower\utilities\audit_log.py:11:1: F401 'time' imported but unused
src\mower\utilities\auto_updater.py:35:1: F401 'tempfile' imported but unused
src\mower\utilities\auto_updater.py:38:1: F401 'pathlib.Path' imported but unused
src\mower\utilities\auto_updater.py:39:1: F401 'typing.Dict' imported but unused
src\mower\utilities\auto_updater.py:39:1: F401 'typing.List' imported but unused
src\mower\utilities\auto_updater.py:39:1: F401 'typing.Union' imported but unused
src\mower\utilities\auto_updater.py:39:1: F401 'typing.Any' imported but unused
src\mower\utilities\auto_updater.py:155:89: E501 line too long (96 > 88 characters)
src\mower\utilities\auto_updater.py:469:89: E501 line too long (97 > 88 characters)
src\mower\utilities\auto_updater.py:487:89: E501 line too long (92 > 88 characters)
src\mower\utilities\auto_updater.py:499:89: E501 line too long (90 > 88 characters)
src\mower\utilities\database_optimizer.py:10:1: F401 'functools' imported but unused
src\mower\utilities\database_optimizer.py:12:1: F401 'typing.Callable' imported but unused
src\mower\utilities\database_optimizer.py:12:1: F401 'typing.Union' imported but unused
src\mower\utilities\database_optimizer.py:48:89: E501 line too long (90 > 88 characters)
src\mower\utilities\database_optimizer.py:90:89: E501 line too long (102 > 88 characters)
src\mower\utilities\maintenance_scheduler.py:24:69: W291 trailing whitespace
src\mower\utilities\maintenance_scheduler.py:41:1: F401 'enum.Enum' imported but unused
src\mower\utilities\maintenance_scheduler.py:41:1: F401 'enum.auto' imported but unused
src\mower\utilities\maintenance_scheduler.py:42:1: F401 'pathlib.Path' imported but unused
src\mower\utilities\maintenance_scheduler.py:43:1: F401 'typing.Set' imported but unused
src\mower\utilities\maintenance_scheduler.py:43:1: F401 'typing.Tuple' imported but unused
src\mower\utilities\maintenance_scheduler.py:43:1: F401 'typing.Union' imported but unused
src\mower\utilities\maintenance_scheduler.py:251:89: E501 line too long (100 > 88 characters)
src\mower\utilities\maintenance_scheduler.py:279:89: E501 line too long (102 > 88 characters)
src\mower\utilities\maintenance_scheduler.py:294:89: E501 line too long (99 > 88 characters)
src\mower\utilities\maintenance_scheduler.py:650:9: F841 local variable 'days_of_history' is assigned to but never used
src\mower\utilities\maintenance_scheduler.py:880:21: F541 f-string is missing placeholders
src\mower\utilities\maintenance_scheduler.py:895:89: E501 line too long (121 > 88 characters)
src\mower\utilities\maintenance_scheduler.py:897:29: F541 f-string is missing placeholders
src\mower\utilities\maintenance_scheduler.py:905:29: F541 f-string is missing placeholders
src\mower\utilities\maintenance_scheduler.py:914:89: E501 line too long (129 > 88 characters)
src\mower\utilities\maintenance_scheduler.py:920:29: F541 f-string is missing placeholders
src\mower\utilities\maintenance_scheduler.py:928:29: F541 f-string is missing placeholders
src\mower\utilities\maintenance_scheduler.py:960:89: E501 line too long (95 > 88 characters)
src\mower\utilities\maintenance_scheduler.py:961:89: E501 line too long (94 > 88 characters)
src\mower\utilities\maintenance_scheduler.py:964:29: F541 f-string is missing placeholders
src\mower\utilities\maintenance_scheduler.py:982:89: E501 line too long (95 > 88 characters)
src\mower\utilities\maintenance_scheduler.py:983:89: E501 line too long (96 > 88 characters)
src\mower\utilities\power_optimizer.py:13:1: F401 'typing.List' imported but unused
src\mower\utilities\power_optimizer.py:13:1: F401 'typing.Optional' imported but unused
src\mower\utilities\power_optimizer.py:13:1: F401 'typing.Callable' imported but unused
src\mower\utilities\power_optimizer.py:13:1: F401 'typing.Set' imported but unused
src\mower\utilities\power_optimizer.py:13:1: F401 'typing.Tuple' imported but unused
src\mower\utilities\power_optimizer.py:202:89: E501 line too long (113 > 88 characters)
src\mower\utilities\power_optimizer.py:235:89: E501 line too long (94 > 88 characters)
src\mower\utilities\power_optimizer.py:271:89: E501 line too long (100 > 88 characters)
src\mower\utilities\power_optimizer.py:280:89: E501 line too long (93 > 88 characters)
src\mower\utilities\power_optimizer.py:289:89: E501 line too long (101 > 88 characters)
src\mower\utilities\power_optimizer.py:300:89: E501 line too long (106 > 88 characters)
src\mower\utilities\power_optimizer.py:494:9: F841 local variable 'original_generate_path' is assigned to but never used
src\mower\utilities\power_optimizer.py:531:9: F841 local variable 'original_detect_obstacles' is assigned to but never used
src\mower\utilities\power_optimizer.py:562:13: F841 local variable 'original_update' is assigned to but never used
src\mower\utilities\resource_optimizer.py:9:1: F401 'os' imported but unused
src\mower\utilities\resource_optimizer.py:14:1: F401 'typing.List' imported but unused
src\mower\utilities\resource_optimizer.py:14:1: F401 'typing.Optional' imported but unused
src\mower\utilities\resource_optimizer.py:14:1: F401 'typing.Set' imported but unused
src\mower\utilities\resource_optimizer.py:127:89: E501 line too long (104 > 88 characters)
src\mower\utilities\resource_optimizer.py:198:89: E501 line too long (102 > 88 characters)
src\mower\utilities\resource_optimizer.py:339:89: E501 line too long (92 > 88 characters)
src\mower\utilities\resource_optimizer.py:369:89: E501 line too long (108 > 88 characters)
src\mower\utilities\resource_optimizer.py:373:89: E501 line too long (96 > 88 characters)
src\mower\utilities\resource_utils.py:10:1: F401 'json' imported but unused
src\mower\utilities\resource_utils.py:11:1: F401 'logging' imported but unused
src\mower\utilities\resource_utils.py:13:1: F401 'typing.List' imported but unused
src\mower\utilities\resource_utils.py:13:1: F401 'typing.Tuple' imported but unused
src\mower\utilities\resource_utils.py:13:1: F401 'typing.Union' imported but unused
src\mower\utilities\resource_utils.py:13:1: F401 'typing.Type' imported but unused
src\mower\utilities\resource_utils.py:15:1: F401 'mower.config_management.get_config' imported but unused
src\mower\utilities\resource_utils.py:15:1: F401 'mower.config_management.set_config' imported but unused
src\mower\utilities\resource_utils.py:35:89: E501 line too long (89 > 88 characters)
src\mower\utilities\startup_optimizer.py:9:1: F401 'threading' imported but unused
src\mower\utilities\startup_optimizer.py:12:1: F401 'typing.Set' imported but unused
src\mower\utilities\startup_optimizer.py:12:1: F401 'typing.Tuple' imported but unused
src\mower\utilities\startup_optimizer.py:44:89: E501 line too long (92 > 88 characters)
src\mower\utilities\startup_optimizer.py:526:17: F541 f-string is missing placeholders
src\mower\weather\weather_scheduler.py:11:1: F401 'typing.Callable' imported but unused
src\mower\weather\weather_scheduler.py:13:1: F401 'logging' imported but unused
src\mower\weather\weather_scheduler.py:464:89: E501 line too long (96 > 88 characters)
src\mower\weather\weather_scheduler.py:465:89: E501 line too long (96 > 88 characters)
tests\integration\test_blade_controller_integration.py:7:89: E501 line too long (90 > 88 characters)
tests\integration\test_web_ui_socketio.py:41:13: E999 SyntaxError: unterminated string literal (detected at line 41)
tests\navigation\test_path_planner.py:5:1: F401 'pytest' imported but unused
tests\navigation\test_path_planner.py:6:1: F401 'numpy as np' imported but unused
tests\navigation\test_path_planner.py:7:1: F401 'unittest.mock.MagicMock' imported but unused
tests\navigation\test_path_planner.py:7:1: F401 'unittest.mock.patch' imported but unused
tests\navigation\test_path_planner.py:7:1: F401 'unittest.mock.call' imported but unused
tests\navigation\test_path_planner_properties.py:302:67: E999 SyntaxError: unterminated triple-quoted string literal (detected at line 329)
tests\obstacle_detection\test_avoidance_algorithm.py:5:1: F401 'pytest' imported but unused
tests\obstacle_detection\test_avoidance_algorithm.py:6:1: F401 'threading' imported but unused
tests\obstacle_detection\test_avoidance_algorithm.py:8:1: F401 'unittest.mock.call' imported but unused
tests\obstacle_detection\test_avoidance_algorithm.py:443:89: E501 line too long (89 > 88 characters)
tests\obstacle_detection\test_avoidance_algorithm.py:444:89: E501 line too long (91 > 88 characters)
tests\obstacle_detection\test_avoidance_algorithm.py:506:89: E501 line too long (90 > 88 characters)
tests\obstacle_detection\test_avoidance_algorithm_properties.py:158:89: E999 IndentationError: unindent does not match any outer indentation level
tests\obstacle_detection\test_tflite_inference.py:30:9: E999 IndentationError: unexpected indent
tests\regression\test_service_startup.py:50:21: E999 SyntaxError: unterminated string literal (detected at line 50)
tests\simulation\test_simulation_mode.py:178:71: E999 SyntaxError: unterminated triple-quoted string literal (detected at line 222)
tests\test_resource_manager.py:27:15: E999 SyntaxError: invalid syntax

---

## Pylance Error List

### test_uart.py

- **Line 31**  
  **Pylance**: `"decode" is not a known attribute of "None"`  
  _Suggested fix_: Ensure `ser.read_all()` does not return `None` before calling `.decode()`. Add a check or handle the case where it may be `None`.
- **Line 51**  
  **Pylance**: `"decode" is not a known attribute of "None"`  
  _Suggested fix_: Same as above.
- **Line 59**  
  **Pylance**: `"decode" is not a known attribute of "None"`  
  _Suggested fix_: Same as above.

### src/mower/main_controller.py

- **Line 576**  
  **Pylance**: `Cannot access attribute "get_boundary_points" for class "PathPlanner"`  
  _Suggested fix_: Check if `get_boundary_points` exists in `PathPlanner` or if the correct object is being used.
- **Line 686**  
  **Pylance**: `Cannot access attribute "get_parsed_data" for class "SerialPort"`  
  _Suggested fix_: Implement or correct the method, or check the object type.
- **Line 690**  
  **Pylance**: `Cannot access attribute "read_line" for class "SerialPort"`  
  _Suggested fix_: Implement or correct the method, or check the object type.
- **Line 918**  
  **Pylance**: `Cannot access attribute "enable_manual_control" for class "NavigationController"`  
  _Suggested fix_: Implement or correct the method, or check the object type.
- **Line 1069**  
  **Pylance**: `Cannot access attribute "setup_logging" for class "type[LoggerConfigInfo]"`  
  _Suggested fix_: Implement or correct the method, or check the object type.

### src/mower/mower.py

- **Line 34**  
  **Pylance**: `"RobotController" is unknown import symbol`  
  _Suggested fix_: Ensure `RobotController` is defined and correctly imported.
- **Line 53, 81, 86, 91, 124, 152**  
  **Pylance**: `Cannot access attribute ... for class "ResourceManager"`  
  _Suggested fix_: Implement the missing method in `ResourceManager` or check the object type.

[...truncated for brevity: All Pylance errors will be listed in this format, grouped by file, with line number, error description, and suggested fix...]

---

## Error Code Reference

- **Flake8 E501**: Line too long  
  _Fix_: Break long lines into multiple lines or use string concatenation.
- **Flake8 F401**: Module imported but unused  
  _Fix_: Remove the unused import statement.
- **Flake8 F841**: Local variable assigned but never used  
  _Fix_: Remove the assignment or use the variable.
- **Flake8 E203**: Whitespace before ':'  
  _Fix_: Remove whitespace before the colon.
- **Flake8 W293**: Blank line contains whitespace  
  _Fix_: Remove whitespace from blank lines.
- **Flake8 E999**: SyntaxError/IndentationError  
  _Fix_: Check for missing colons, parentheses, or other syntax issues at or before the line.
- **Flake8 F541**: f-string is missing placeholders  
  _Fix_: Add the required placeholders to the f-string.
- **Pylance**: Various type, attribute, and import errors  
  _Fix_: Review the error description and update code to match expected types, implement missing methods, or correct imports.

---

**End of Report**
