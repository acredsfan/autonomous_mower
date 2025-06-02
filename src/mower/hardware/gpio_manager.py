"""
GPIO Manager module.

This module provides a unified interface for GPIO access, using the gpiozero
library for hardware interaction and simulation.
@hardware_interface
"""

import logging
from typing import Optional, Dict, Union

# Attempt to import gpiozero and specific device types
try:
    from gpiozero import (
        Device,
        OutputDevice,
        InputDevice,
        Button,
        PWMOutputDevice
    )
    from gpiozero.pins.mock import MockFactory, MockPin
    from gpiozero.exc import (
        GPIOZeroError,
        PinInvalidFunction,
        PinSetInput,
        PinFixedPull,
        BadPinFactory,
        PinUnsupportedVCN,
    )

    # Attempt to set a pin factory. If it fails, we assume we're not on a Pi
    # or a compatible environment for gpiozero's default factories.
    try:
        _ = Device.pin_factory  # Access to check if it's configured
        GPIOZERO_AVAILABLE = True
    except BadPinFactory:
        logging.warning(
            "gpiozero default pin factory failed to load. Trying MockFactory."
        )
        try:
            Device.pin_factory = MockFactory()
            GPIOZERO_AVAILABLE = True  # Technically available, but mocked
            logging.info("gpiozero running with MockFactory for simulation.")
        except Exception as e_mock:
            GPIOZERO_AVAILABLE = False
            logging.error(
                f"Failed to initialize gpiozero with MockFactory: {e_mock}")
    except Exception as e_factory:  # Catch any other Device.pin_factory access issues
        GPIOZERO_AVAILABLE = False
        logging.warning(
            f"gpiozero not fully available or not on a Pi: {e_factory}. "
            "Will use simulation."
        )


except ImportError:
    GPIOZERO_AVAILABLE = False
    logging.warning(
        "gpiozero library not found. "
        "GPIO operations will be simulated using a basic dictionary."
    )

    # Define dummy exception classes if gpiozero is not available for type
    # hinting
    class GPIOZeroError(Exception):  # type: ignore
        pass

    class PinInvalidFunction(GPIOZeroError):  # type: ignore
        pass

    class PinSetInput(GPIOZeroError):  # type: ignore
        pass

    class PinFixedPull(GPIOZeroError):  # type: ignore
        pass

    class PinUnsupportedVCN(GPIOZeroError):  # type: ignore
        pass

    class BadPinFactory(GPIOZeroError):  # type: ignore
        pass

    # Define dummy device classes for type hinting if gpiozero is not available

    class MockPin:  # type: ignore
        def __init__(self, number):
            self.number = number
            self._value = 0  # For digital
            self._frequency = None
            self._duty_cycle = 0.0  # For PWM

        def drive_low(self):
            self._value = 0
            self._duty_cycle = 0.0

        def drive_high(self):
            self._value = 1
            self._duty_cycle = 1.0

        @property
        def state(self):
            return self._value

        @property
        def frequency(self):
            return self._frequency

        @frequency.setter
        def frequency(self, freq):
            self._frequency = freq

    class MockFactory:  # type: ignore
        def __init__(self):
            self.pins: Dict[int, MockPin] = {}

        def pin(self, number) -> MockPin:
            if number not in self.pins:
                self.pins[number] = MockPin(number)
            return self.pins[number]

        def close(self):
            self.pins.clear()

        @property
        def name(self):
            return "mock"

    class Device:  # type: ignore
        pin_factory: Optional[MockFactory] = None  # Add class attribute

        def __init__(self, pin=None, pin_factory=None):  # pin_factory arg for consistency
            self.pin = pin  # Stores the pin number
            self._value = 0  # Use _value for internal storage (digital state or PWM duty cycle)
            # If a specific pin_factory is provided, use it. Otherwise, use
            # class default.
            if pin_factory is not None:
                self._pin_factory = pin_factory
            elif Device.pin_factory is None and not GPIOZERO_AVAILABLE:  # Auto-init for dummy
                Device.pin_factory = MockFactory()
                self._pin_factory = Device.pin_factory
            else:
                self._pin_factory = Device.pin_factory

            # Simulate pin object creation if factory exists
            if self.pin is not None and self._pin_factory is not None:
                self._mock_pin_obj = self._pin_factory.pin(self.pin)

        def close(self):
            pass

        @property
        def value(self):
            if hasattr(self, '_mock_pin_obj') and isinstance(self, PWMOutputDevice):  # Check if PWM type
                return self._mock_pin_obj._duty_cycle
            elif hasattr(self, '_mock_pin_obj'):
                return self._mock_pin_obj.state
            return self._value

        @value.setter
        def value(self, val):
            # This setter is used by OutputDevice (0/1) and PWMOutputDevice (0.0-1.0)
            self._value = val
            if hasattr(self, '_mock_pin_obj'):
                if isinstance(self, PWMOutputDevice):  # Check if PWM type
                    self._mock_pin_obj._duty_cycle = float(val)
                elif val:
                    self._mock_pin_obj.drive_high()
                else:
                    self._mock_pin_obj.drive_low()

    class OutputDevice(Device):  # type: ignore
        def __init__(
                self,
                pin=None,
                active_high: bool = True,
                initial_value: bool = False,  # bool for OutputDevice
                pin_factory=None):
            super().__init__(pin, pin_factory=pin_factory)
            self.active_high = active_high
            effective_initial_value = initial_value if initial_value is not None else False
            if effective_initial_value:
                self.on()
            else:
                self.off()

        def on(self):
            self.value = 1 if self.active_high else 0

        def off(self):
            self.value = 0 if self.active_high else 1

    class PWMOutputDevice(Device):  # type: ignore
        def __init__(
            self,
            pin=None,
            active_high: bool = True,
            initial_value: float = 0.0,
            frequency: int = 100,
            pin_factory=None
        ):
            super().__init__(pin, pin_factory=pin_factory)
            self.active_high = active_high  # Though less relevant for PWM duty cycle
            self.frequency = frequency
            # initial_value for PWMOutputDevice is duty cycle (0.0 to 1.0)
            self.value = float(initial_value) if initial_value is not None else 0.0
            if hasattr(self, '_mock_pin_obj'):
                self._mock_pin_obj.frequency = frequency

        # 'value' property (0.0-1.0 for duty cycle) is inherited from Device and its setter handles it.
        # 'frequency' property
        @property
        def frequency(self):
            if hasattr(self, '_mock_pin_obj'):
                return self._mock_pin_obj.frequency
            return self._frequency_val

        @frequency.setter
        def frequency(self, freq: int):
            self._frequency_val = freq
            if hasattr(self, '_mock_pin_obj'):
                self._mock_pin_obj.frequency = freq

        def on(self):  # Set to full duty cycle
            self.value = 1.0

        def off(self):  # Set to zero duty cycle
            self.value = 0.0

    class InputDevice(Device):  # type: ignore
        # value property inherited
        def __init__(self, pin=None, pull_up=None, pin_factory=None):  # Added pull_up
            super().__init__(pin, pin_factory=pin_factory)
            self.pull_up = pull_up

    class Button(InputDevice):  # type: ignore
        def __init__(self, pin=None, pull_up=True, pin_factory=None):
            super().__init__(pin, pull_up=pull_up, pin_factory=pin_factory)
            # Add is_pressed for basic simulation consistency
            self.is_pressed = False  # pylint: disable=invalid-name
            self.when_pressed = None
            self.when_released = None
            self.bounce_time: Optional[float] = None  # Add for compatibility
            self.hold_time: Optional[float] = None  # Add for compatibility


# Define constants for pull-up/down to be used by the manager
# gpiozero uses True/False/None for pull_up on Button/InputDevice
PULL_UP = True
PULL_DOWN = False
PULL_NONE = None


class GPIOManager:
    """
    GPIO Manager class using the gpiozero library.

    This class supports hardware GPIO access through gpiozero and provides
    a simulation mode when hardware is not available or explicitly chosen.
    It manages a collection of gpiozero device objects.
    @hardware_interface
    """

    # @gpio_pin_usage {pin_number} (BCM) - {purpose}
    # These will be documented per instance of device creation.
    PIN_CONFIG: Dict[str, int] = {
        "BLADE_ENABLE": 17,    # @gpio_pin_usage 17 (BCM) - Blade PWM Control
        "BLADE_DIRECTION": 27,  # @gpio_pin_usage 27 (BCM) - Blade Direction
        # @gpio_pin_usage 7 (BCM) - Emergency Stop Button
        "EMERGENCY_STOP": 7,
        "MOTOR_LEFT": 22,      # @gpio_pin_usage 22 (BCM) - Left Motor Control (Purpose TBD: Enable or RoboHAT related)
        "MOTOR_RIGHT": 23,     # @gpio_pin_usage 23 (BCM) - Right Motor Control (Purpose TBD: Enable or RoboHAT related)
    }

    def __init__(self, simulate: bool = False):
        """
        Initialize the GPIO manager.

        Args:
            simulate (bool): If True, forces simulation mode
                             even if gpiozero is available.
        """
        self._devices: Dict[int, Union[OutputDevice,
                                       InputDevice, Button, PWMOutputDevice, Device]] = {}
        self._simulation_mode: bool = simulate or not GPIOZERO_AVAILABLE

        # Store the type of our dummy MockFactory for later checks if gpiozero
        # is not available
        self.dummy_MockFactory_type = type(None)
        self.dummy_PWMOutputDevice_type = type(None)  # For dummy PWM device check
        if not GPIOZERO_AVAILABLE:
            self.dummy_MockFactory_type = MockFactory  # Our dummy MockFactory type
            self.dummy_PWMOutputDevice_type = PWMOutputDevice  # Our dummy PWMOutputDevice type

        if self._simulation_mode:
            logging.info("GPIOManager running in simulation mode.")
            if GPIOZERO_AVAILABLE and not simulate:  # gpiozero available but failed init
                logging.warning(
                    "gpiozero seemed available but failed initial factory setup, "
                    "forcing MockFactory for simulation.")
                try:
                    # Ensure it's the real gpiozero Device and MockFactory
                    from gpiozero import Device as GpioZeroDevice_real
                    from gpiozero.pins.mock import MockFactory as GpioZeroMockFactory_real
                    GpioZeroDevice_real.pin_factory = GpioZeroMockFactory_real()
                    logging.info(
                        "Using gpiozero.MockFactory for forced simulation.")
                except Exception as e_mock_force:
                    logging.error(
                        f"Failed to set gpiozero.MockFactory during forced sim: {e_mock_force}")
            elif GPIOZERO_AVAILABLE and simulate:  # User requested simulation with gpiozero
                try:
                    from gpiozero import Device as GpioZeroDevice_real
                    from gpiozero.pins.mock import MockFactory as GpioZeroMockFactory_real
                    GpioZeroDevice_real.pin_factory = GpioZeroMockFactory_real()
                    logging.info(
                        "Using gpiozero.MockFactory for user-requested simulation.")
                except Exception as e_mock_user:
                    logging.error(
                        f"Failed to set gpiozero.MockFactory for user sim: {e_mock_user}")
            else:  # gpiozero not installed, use our dummy classes
                if Device.pin_factory is None:  # Our dummy Device
                    Device.pin_factory = MockFactory()  # Our dummy MockFactory
                logging.info(
                    "Using basic dictionary-based simulation with dummy MockFactory "
                    "as gpiozero is not installed.")
        else:  # Hardware mode with gpiozero
            if GPIOZERO_AVAILABLE:
                from gpiozero import Device as GpioZeroDevice_real  # Real gpiozero Device
                logging.info(
                    f"GPIOManager running with hardware access via gpiozero "
                    f"and pin factory: {GpioZeroDevice_real.pin_factory.__class__.__name__}")
            else:  # Should not happen if logic is correct
                logging.error(
                    "In hardware mode but GPIOZERO_AVAILABLE is False. This is a bug.")

    def _get_pin_obj(
        self, pin: int
    ) -> Optional[Union[OutputDevice, InputDevice, Button, PWMOutputDevice, Device]]:  # Added PWMOutputDevice
        if pin not in self._devices:
            logging.warning(f"Pin {pin} has not been set up.")
            return None
        return self._devices[pin]

    def setup_pin(  # pylint: disable=too-many-arguments
        self,
        pin: int,
        pin_type: str = "out",  # "out", "in", "button", "pwm"
        initial_value: Optional[Union[bool, float]] = None,  # For "out" (bool) or "pwm" (float)
        pull_up: Optional[bool] = None,  # For "in" or "button"
        active_high: Optional[bool] = True,  # For OutputDevice, PWMOutputDevice
        frequency: Optional[int] = None,  # For "pwm"
    ) -> bool:
        """
        Set up a GPIO pin for use using gpiozero.
        @gpio_pin_usage {pin} (BCM) - {pin_type}
        Args:
            pin: The GPIO pin number (BCM mode).
            pin_type: "out", "in", "button", or "pwm".
            initial_value: For "out": Initial state (True for high, False for low).
                             For "pwm": Initial duty cycle (0.0 to 1.0).
            pull_up: For InputDevice/Button: True for pull-up,
                     False for pull-down, None for floating.
            active_high: For OutputDevice/PWMOutputDevice: If True, .on() sets high/full duty.
                         If False, .on() sets low/zero duty. (Less typical for PWM)
            frequency: For "pwm": PWM frequency in Hz.

        Returns:
            bool: True if setup successful, False otherwise.
        """
        if pin in self._devices:
            logging.warning(
                f"Pin {pin} already configured. Cleaning up before re-configuring.")
            self.cleanup_pin(pin)

        try:
            # Determine if using gpiozero's MockFactory or our dummy MockFactory
            is_gpiozero_real_available = GPIOZERO_AVAILABLE

            # Get the correct Device class (real gpiozero or our dummy)
            CurrentDeviceClass = Device
            CurrentOutputDeviceClass = OutputDevice
            CurrentPWMOutputDeviceClass = PWMOutputDevice
            CurrentInputDeviceClass = InputDevice
            CurrentButtonClass = Button

            if is_gpiozero_real_available:
                from gpiozero import (
                    Device as GpioZeroDevice_real,
                    OutputDevice as GpioZeroOutputDevice_real,
                    PWMOutputDevice as GpioZeroPWMOutputDevice_real,
                    InputDevice as GpioZeroInputDevice_real,
                    Button as GpioZeroButton_real,
                )

                CurrentDeviceClass = GpioZeroDevice_real
                CurrentOutputDeviceClass = GpioZeroOutputDevice_real
                CurrentPWMOutputDeviceClass = GpioZeroPWMOutputDevice_real
                CurrentInputDeviceClass = GpioZeroInputDevice_real
                CurrentButtonClass = GpioZeroButton_real
                # If not in simulation mode forced by user, and gpiozero is available,
                # it should use the real pin factory or the one set (e.g. MockFactory if default failed)

            # In simulation mode (either gpiozero's MockFactory or our dummy classes)
            if self._simulation_mode:
                current_pin_factory_instance = CurrentDeviceClass.pin_factory
                # If gpiozero is NOT available, we must use our dummy classes
                if not is_gpiozero_real_available:
                    # Ensure our dummy factory is used for our dummy devices
                    current_pin_factory_instance = Device.pin_factory  # This is our dummy Device.pin_factory
                    if pin_type == "pwm":
                        if frequency is None:
                            logging.error(f"Frequency must be provided for PWM pin {pin}.")
                            return False
                        device = PWMOutputDevice(  # Our dummy PWMOutputDevice
                            pin, initial_value=initial_value if initial_value is not None else 0.0,
                            frequency=frequency, active_high=active_high if active_high is not None else True,
                            pin_factory=current_pin_factory_instance)
                    elif pin_type == "out":
                        device = OutputDevice(  # Our dummy OutputDevice
                            pin, initial_value=bool(initial_value) if initial_value is not None else False,
                            active_high=active_high if active_high is not None else True,
                            pin_factory=current_pin_factory_instance)
                    elif pin_type == "in":
                        device = InputDevice(pin, pull_up=pull_up, pin_factory=current_pin_factory_instance)
                    elif pin_type == "button":
                        device = Button(
                            pin,
                            pull_up=pull_up if pull_up is not None else PULL_UP,
                            pin_factory=current_pin_factory_instance
                            )
                    else:
                        logging.error(f"Invalid pin_type '{pin_type}' for pin {pin}.")
                        return False
                    self._devices[pin] = device
                    logging.debug(f"Simulated (dummy class) setup for pin {pin} as {pin_type}")
                    return True
                # If gpiozero IS available but we are in simulation (e.g. MockFactory is active)
                # Fall through to use Current<Type>Class which will be gpiozero's types with MockFactory

            # Real hardware OR gpiozero with MockFactory
            if pin_type == "pwm":
                if frequency is None:
                    logging.error(f"Frequency must be provided for PWM pin {pin}.")
                    return False
                device = CurrentPWMOutputDeviceClass(
                    pin, initial_value=initial_value if initial_value is not None else 0.0,
                    frequency=frequency, active_high=active_high if active_high is not None else True)
                logging.info(
                    f"Pin {pin} configured as {CurrentPWMOutputDeviceClass.__name__} "
                    f"with freq={device.frequency}, initial_duty_cycle={device.value}")
            elif pin_type == "out":
                device = CurrentOutputDeviceClass(
                    pin, initial_value=bool(initial_value) if initial_value is not None else False,
                    active_high=active_high if active_high is not None else True)
                logging.info(
                    f"Pin {pin} configured as {CurrentOutputDeviceClass.__name__}, "
                    f"initial_value={device.value}, active_high={active_high}")
            elif pin_type == "in":
                device = CurrentInputDeviceClass(pin, pull_up=pull_up)
                logging.info(
                    f"Pin {pin} configured as {CurrentInputDeviceClass.__name__} with pull_up={device.pull_up}")
            elif pin_type == "button":
                device = CurrentButtonClass(
                    pin, pull_up=pull_up if pull_up is not None else PULL_UP)
                logging.info(
                    f"Pin {pin} configured as {CurrentButtonClass.__name__} with pull_up={device.pull_up}")
            else:
                logging.error(f"Invalid pin_type '{pin_type}' for pin {pin}.")
                return False

            self._devices[pin] = device
            return True

        except (
            GPIOZeroError, PinInvalidFunction, PinSetInput, PinFixedPull, ValueError, PinUnsupportedVCN,
        ) as e:
            logging.error(
                f"Error setting up GPIO pin {pin} (type: {pin_type}) with gpiozero: {e}")
            # If setup fails, and we are using gpiozero, it might be because the pin factory is bad
            # Forcing simulation might be an option if this is a persistent issue on some setups
            if GPIOZERO_AVAILABLE and not self._simulation_mode:
                logging.warning("Consider forcing simulation mode if hardware access is problematic.")
            return False
        except Exception as e_setup:  # Catch-all for unexpected issues
            logging.error(
                f"Unexpected error setting up GPIO pin {pin} (type: {pin_type}): {e_setup}")
            return False

    def cleanup_pin(self, pin: int) -> None:
        """
        Clean up a single GPIO pin by closing its gpiozero device.

        Args:
            pin: The GPIO pin number to clean up.
        """
        device = self._devices.pop(pin, None)
        if device:
            try:
                device.close()
                logging.info(f"Closed and cleaned up pin {pin}.")
            except GPIOZeroError as e_gpio_close:  # type: ignore
                logging.error(
                    f"Error closing gpiozero device for pin {pin}: {e_gpio_close}")
            except Exception as e_close:  # Catch-all for unexpected issues
                logging.error(
                    f"Unexpected error cleaning up pin {pin}: {e_close}")
        else:
            logging.debug(
                f"Pin {pin} not found for cleanup or already cleaned.")

    def cleanup_all(self) -> None:
        """Clean up all GPIO pins by closing all managed gpiozero devices."""
        if not self._devices:
            logging.info("No GPIO pins were set up to clean.")
            return
        pins_to_clean = list(self._devices.keys())
        for pin_num in pins_to_clean:
            self.cleanup_pin(pin_num)
        logging.info("All managed GPIO pins have been cleaned up.")

    def set_pin(self, pin: int, value: bool) -> bool:
        """
        Set the value of an OutputDevice pin (digital on/off).
        For PWM pins, use set_pin_duty_cycle.

        Args:
            pin: The GPIO pin number.
            value: The value to set (True for on/high, False for off/low).

        Returns:
            bool: True if successful, False otherwise.
        """
        device = self._get_pin_obj(pin)
        if not device:
            return False

        # Check if it's a PWM device (real or dummy)
        is_pwm_device = False
        if GPIOZERO_AVAILABLE:
            from gpiozero import PWMOutputDevice as RealPWMOutputDevice
            if isinstance(device, RealPWMOutputDevice):
                is_pwm_device = True
        elif not GPIOZERO_AVAILABLE and isinstance(device, self.dummy_PWMOutputDevice_type):
            is_pwm_device = True

        if is_pwm_device:
            logging.warning(f"Pin {pin} is a PWM pin. Use set_pin_duty_cycle() to control its duty cycle. "
                            "Interpreting True as 1.0 and False as 0.0 duty cycle for compatibility.")
            return self.set_pin_duty_cycle(pin, 1.0 if value else 0.0)

        is_dummy_simulation_output = not GPIOZERO_AVAILABLE and isinstance(device, OutputDevice)
        if is_dummy_simulation_output:
            if hasattr(device, "value"):
                if value:
                    device.on()
                else:
                    device.off()
                logging.debug(
                    f"Simulated (dummy OutputDevice) set pin {pin} to {'ON' if value else 'OFF'}")
                return True
            logging.warning(
                f"Simulated (dummy) pin {pin} cannot be set (not dummy OutputDevice or no value attr).")
            return False

        # If GPIOZERO_AVAILABLE (either real OutputDevice or its MockFactory OutputDevice)
        if GPIOZERO_AVAILABLE and isinstance(device, OutputDevice): # gpiozero.OutputDevice
            try:
                if value:
                    device.on()
                else:
                    device.off()
                logging.debug(
                    f"Set pin {pin} to {'ON' if value else 'OFF'} "
                    f"(actual state: {device.value})"
                )
                return True
            except (GPIOZeroError, PinInvalidFunction) as e_gpio_set:
                logging.error(f"Error setting GPIO pin {pin} state: {e_gpio_set}")
                return False
            except Exception as e_set:
                logging.error(f"Unexpected error setting pin {pin}: {e_set}")
                return False

        logging.warning(f"Cannot set pin {pin}: not a recognized OutputDevice or unhandled simulation case.")
        return False

    def set_pin_duty_cycle(self, pin: int, duty_cycle: float) -> bool:
        """
        Set the duty cycle of a PWMOutputDevice pin.

        Args:
            pin: The GPIO pin number.
            duty_cycle: The duty cycle to set (0.0 to 1.0).

        Returns:
            bool: True if successful, False otherwise.
        """
        device = self._get_pin_obj(pin)
        if not device:
            return False

        # Clamp duty_cycle
        duty_cycle = max(0.0, min(1.0, duty_cycle))

        is_dummy_pwm_device = not GPIOZERO_AVAILABLE and isinstance(device, self.dummy_PWMOutputDevice_type)

        if is_dummy_pwm_device:
            device.value = duty_cycle
            logging.debug(f"Simulated (dummy PWM) set pin {pin} duty cycle to {duty_cycle:.2f}")
            return True

        # If GPIOZERO_AVAILABLE (real PWMOutputDevice or its MockFactory PWMOutputDevice)
        if GPIOZERO_AVAILABLE and isinstance(device, PWMOutputDevice):
            try:
                device.value = duty_cycle
                logging.debug(f"Set PWM pin {pin} duty cycle to {duty_cycle:.2f} (actual: {device.value:.2f})")
                return True
            except (GPIOZeroError, PinInvalidFunction) as e_pwm_set:
                logging.error(f"Error setting PWM pin {pin} duty cycle: {e_pwm_set}")
                return False
            except Exception as e_set:
                logging.error(f"Unexpected error setting PWM pin {pin} duty cycle: {e_set}")
                return False

        logging.warning(f"Cannot set duty cycle for pin {pin}: not a recognized PWMOutputDevice.")
        return False


    def get_pin(self, pin: int) -> Optional[Union[bool, float]]:
        """
        Get the value of an InputDevice, Button, OutputDevice, or PWMOutputDevice pin.

        Args:
            pin: The GPIO pin number.

        Returns:
            Optional[Union[bool, float]]: Pin value (True/False for digital, 0.0-1.0 for PWM) or None on error.
        """
        device = self._get_pin_obj(pin)
        if not device:
            return None

        is_dummy_simulation = not GPIOZERO_AVAILABLE

        if is_dummy_simulation:
            if hasattr(device, "value"):
                val = device.value
                logging.debug(f"Simulated (dummy) get pin {pin} value: {val}")
                return val
            logging.warning(
                f"Simulated (dummy) pin {pin} cannot be read (no value attr or unhandled type).")
            return None

        # If GPIOZERO_AVAILABLE (real or its MockFactory)
        if isinstance(device, (InputDevice, OutputDevice, Button, PWMOutputDevice)):  # gpiozero types
            try:
                val = device.value  # gpiozero .value is 0/1 for digital, 0.0-1.0 for PWM
                if isinstance(device, PWMOutputDevice):
                    logging.debug(f"Get PWM pin {pin} duty cycle: {float(val):.2f}")
                    return float(val)
                else:
                    logging.debug(f"Get pin {pin} value: {bool(val)}")
                    return bool(val)
            except (GPIOZeroError, PinInvalidFunction) as e_gpio_get:
                logging.error(f"Error getting GPIO pin {pin} state: {e_gpio_get}")
                return None
            except Exception as e_get:
                logging.error(f"Unexpected error getting pin {pin} state: {e_get}")
                return None

        logging.warning(
            f"Cannot get pin {pin} value: not a recognized gpiozero device type for this method.")
        return None

    def is_pin_active(self, pin: int) -> Optional[bool]:
        """
        Checks if a Button or InputDevice is active (e.g., button pressed).
        For OutputDevice, this is equivalent to get_pin.

        Args:
            pin: The GPIO pin number.

        Returns:
            Optional[bool]: True if active, False if not, None on error.
        """
        device = self._get_pin_obj(pin)
        if not device:
            return None

        is_dummy_simulation = not GPIOZERO_AVAILABLE

        if isinstance(
                device,
                Button):  # Covers both gpiozero.Button and our dummy Button
            try:
                if is_dummy_simulation:  # Our own dummy Button
                    active = device.is_pressed  # Relies on external simulation setting this
                else:  # gpiozero Button (real or Mock)
                    active = device.is_pressed
                logging.debug(
                    f"Button {pin} active (is_pressed): {active}, value: {
                        device.value}")
                return active
            except (GPIOZeroError, PinInvalidFunction) as e_button_active:
                logging.error(
                    f"Error checking Button {pin} active state: {e_button_active}")
                return None
        elif isinstance(device, InputDevice):  # Covers gpiozero.InputDevice and dummy
            try:
                active = bool(device.value)
                logging.debug(f"InputDevice {pin} active (value): {active}")
                return active
            except (GPIOZeroError, PinInvalidFunction) as e_input_active:
                logging.error(
                    f"Error checking InputDevice {pin} active state: {e_input_active}")
                return None
        elif isinstance(device, OutputDevice):  # Covers gpiozero.OutputDevice and dummy
            return self.get_pin(pin)
        # Removed the basic_dict_simulation specific hasattr check here as
        # covered by types
        else:
            logging.warning(
                f"Cannot determine active state for pin {pin}, "
                f"not a recognized input/button type for this method."
            )
            return None

    def add_event_detect(  # pylint: disable=too-many-arguments
        self,
        pin: int,
        callback_function,
        event_type: str = "when_pressed",
        bounce_time: Optional[float] = None,  # In seconds
        hold_time: Optional[float] = None,  # For when_held
    ):
        """
        Adds event detection to a pin.

        Args:
            pin: The GPIO pin number.
            callback_function: The function to call when the event occurs.
            event_type: Event type (e.g., "when_pressed", "when_released",
                        "when_activated", "when_deactivated", "when_held").
            bounce_time: Debounce time in seconds.
            hold_time: For "when_held", duration in seconds button must be held.


        Returns:
            bool: True if event detection was set up, False otherwise.
        """
        device = self._get_pin_obj(pin)
        if not device:
            logging.error(f"Cannot add event detect: Pin {pin} not set up.")
            return False

        is_dummy_simulation = not GPIOZERO_AVAILABLE

        if is_dummy_simulation:
            # For dummy simulation, we can "register" the callback if the attribute exists
            # but actual event triggering needs to be simulated externally.
            if hasattr(device, event_type):
                setattr(device, event_type, callback_function)
                if bounce_time is not None and hasattr(device, "bounce_time"):
                    device.bounce_time = bounce_time
                if event_type == "when_held" and hasattr(device, "hold_time"):
                    if hold_time is not None:
                        device.hold_time = hold_time
                logging.info(
                    f"Event '{event_type}' callback registered for pin {pin} in dummy simulation. "
                    "External trigger needed."
                )
                return True
            logging.warning(
                f"Event detection for pin {pin} (event: {event_type}) "
                f"not supported on dummy device type {type(device).__name__}."
            )
            return False

        # If GPIOZERO_AVAILABLE (real or its MockFactory)
        try:
            if hasattr(device, event_type):
                if bounce_time is not None and hasattr(device, "bounce_time"):
                    device.bounce_time = bounce_time  # type: ignore
                if event_type == "when_held" and hasattr(device, "hold_time"):
                    if hold_time is not None:
                        device.hold_time = hold_time  # type: ignore
                    else:
                        logging.warning(
                            "\'when_held\' used without specifying hold_time, "
                            "using default."
                        )

                setattr(device, event_type, callback_function)

                logging.info(
                    f"Event detection \'{event_type}\' added to pin {pin}.")
                return True
            else:
                logging.error(
                    f"Device for pin {pin} (type: {type(device).__name__}) "
                    f"does not support event \'{event_type}\'."
                )
                return False
        except (GPIOZeroError, AttributeError) as e_gpio_event:  # type: ignore
            logging.error(
                f"Error adding event detection to pin {pin}: {e_gpio_event}")
            return False
        except Exception as e_event:  # Catch-all for unexpected issues
            logging.error(
                f"Unexpected error adding event detection to pin {pin}: {e_event}")
            return False

    def remove_event_detect(self, pin: int, event_type: str):
        """
        Removes event detection from a pin.

        Args:
            pin: The GPIO pin number.
            event_type: The event type to remove (e.g., "when_pressed").
        """
        device = self._get_pin_obj(pin)
        if not device:
            logging.error(f"Cannot remove event detect: Pin {pin} not set up.")
            return

        is_dummy_simulation = not GPIOZERO_AVAILABLE

        if is_dummy_simulation:
            if hasattr(
                    device,
                    event_type) and getattr(
                    device,
                    event_type) is not None:
                setattr(device, event_type, None)
                logging.info(
                    f"Event detection '{event_type}' removed from pin {pin} in dummy simulation.")
            else:
                logging.warning(
                    f"Dummy device for pin {pin} does not have event '{event_type}' "
                    f"to remove or it was not set."
                )
            return

        # If GPIOZERO_AVAILABLE (real or its MockFactory)
        try:
            if hasattr(
                    device,
                    event_type) and getattr(
                    device,
                    event_type) is not None:
                setattr(device, event_type, None)  # Clear the event handler
                logging.info(
                    f"Event detection \'{event_type}\' removed from pin {pin}.")
            else:
                logging.warning(
                    f"Device for pin {pin} does not have event \'{event_type}\' "
                    f"to remove or it was not set."
                )
        except (GPIOZeroError, AttributeError) as e_gpio_remove_event:  # type: ignore
            logging.error(
                f"Error removing event detection from pin {pin}: {e_gpio_remove_event}")
        except Exception as e_remove_event:  # Catch-all for unexpected issues
            logging.error(
                f"Unexpected error removing event detection from pin {pin}: {e_remove_event}")


# Example Usage (Illustrative)
if __name__ == "__main__":
    import time  # For sleep in example

    logging.basicConfig(level=logging.INFO)

    # Determine if we should force simulation for the example
    # Force sim if gpiozero is not available OR if it is available but already using MockFactory
    # (which implies it couldn't load a real factory)

    # Check if gpiozero is available and if its pin_factory is a MockFactory
    gpiozero_is_mocked = False
    if GPIOZERO_AVAILABLE:
        from gpiozero import Device as GpioZeroDevice_real  # Real gpiozero Device
        from gpiozero.pins.mock import MockFactory as GpioZeroMockFactory_real  # Real MockFactory
        if isinstance(GpioZeroDevice_real.pin_factory, GpioZeroMockFactory_real):
            gpiozero_is_mocked = True

    example_force_sim = not GPIOZERO_AVAILABLE or gpiozero_is_mocked

    manager = GPIOManager(simulate=example_force_sim)

    # Example with PWM pin
    pwm_pin_example = GPIOManager.PIN_CONFIG["BLADE_ENABLE"]  # Using pin 17 as PWM
    if manager.setup_pin(pwm_pin_example, pin_type="pwm", frequency=100, initial_value=0.1):
        logging.info(f"PWM pin {pwm_pin_example} setup with 10% duty cycle.")
        time.sleep(0.1)
        manager.set_pin_duty_cycle(pwm_pin_example, 0.5)
        logging.info(f"PWM pin {pwm_pin_example} set to 50% duty cycle. "
                     f"Current value: {manager.get_pin(pwm_pin_example)}")
        time.sleep(0.1)
        manager.set_pin_duty_cycle(pwm_pin_example, 0.0)
        logging.info(f"PWM pin {pwm_pin_example} set to 0% duty cycle. "
                     f"Current value: {manager.get_pin(pwm_pin_example)}")
    else:
        logging.error(f"Failed to set up PWM pin {pwm_pin_example}.")

    led_pin = GPIOManager.PIN_CONFIG.get("MOTOR_LEFT", 22)  # Use a different pin if BLADE_ENABLE is 17
    button_pin = GPIOManager.PIN_CONFIG["EMERGENCY_STOP"]

    if manager.setup_pin(led_pin, pin_type="out", initial_value=False):
        logging.info(f"LED pin {led_pin} setup.")
        manager.set_pin(led_pin, True)
        logging.info(f"LED pin {led_pin} is ON: {manager.get_pin(led_pin)}")
        time.sleep(0.1)
        manager.set_pin(led_pin, False)
        logging.info(f"LED pin {led_pin} is OFF: {manager.get_pin(led_pin)}")
    else:
        logging.error(f"Failed to set up LED pin {led_pin}.")

    def button_pressed_callback_example():
        logging.info(f"Button on pin {button_pin} pressed! (Example)")
        # Example: Toggle PWM pin if it was set up
        if pwm_pin_example in manager._devices:
            current_pwm_val = manager.get_pin(pwm_pin_example)
            if isinstance(current_pwm_val, float):
                manager.set_pin_duty_cycle(pwm_pin_example, 1.0 - current_pwm_val if current_pwm_val > 0 else 0.2)

    def button_released_callback_example():
        logging.info(f"Button on pin {button_pin} released! (Example)")

    if manager.setup_pin(button_pin, pin_type="button", pull_up=PULL_UP):
        logging.info(f"Button pin {button_pin} setup.")
        manager.add_event_detect(
            button_pin,
            button_pressed_callback_example,
            "when_pressed",
            bounce_time=0.05)
        manager.add_event_detect(
            button_pin, button_released_callback_example, "when_released"
        )
        logging.info(
            f"Event detection added for button {button_pin}. Press/release the button.")

        # Simulation handling for example
        is_gpiozero_fully_available_and_mocked = (
            GPIOZERO_AVAILABLE and
            isinstance(getattr(Device if not GPIOZERO_AVAILABLE else GpioZeroDevice_real, 'pin_factory', None),
                       MockFactory if not GPIOZERO_AVAILABLE else GpioZeroMockFactory_real)
        )

        is_dummy_mode_active = manager._simulation_mode and not is_gpiozero_fully_available_and_mocked

        if manager._simulation_mode:
            logging.info("Simulating button press and release for example...")
            if is_gpiozero_fully_available_and_mocked:
                try:
                    from gpiozero import Device as GpioZeroDevice_real_sim
                    from gpiozero.pins.mock import MockPin as GpioZeroMockPin_real_sim
                    if GpioZeroDevice_real_sim.pin_factory is not None:
                        mock_pin_obj = GpioZeroDevice_real_sim.pin_factory.pin(button_pin)
                        if isinstance(mock_pin_obj, GpioZeroMockPin_real_sim):
                            mock_pin_obj.drive_low()
                            time.sleep(0.05)
                            mock_pin_obj.drive_high()
                            time.sleep(0.05)
                        else:
                            logging.warning(f"gpiozero.MockPin object not found for simulation. "
                                            f"Got {type(mock_pin_obj)}")
                    else:
                        logging.warning("gpiozero.Device.pin_factory not available for detailed simulation.")
                except Exception as e_sim_press:
                    logging.error(f"Error during gpiozero.MockPin simulation: {e_sim_press}")

            elif is_dummy_mode_active:  # Using our dummy classes
                logging.info("Basic dummy sim: Manually calling button callbacks for example.")
                button_device_obj = manager._get_pin_obj(button_pin)
                if isinstance(button_device_obj, Button):  # Our dummy Button
                    button_device_obj.is_pressed = True
                button_pressed_callback_example()
                time.sleep(0.05)
                if isinstance(button_device_obj, Button):  # Our dummy Button
                    button_device_obj.is_pressed = False
                button_released_callback_example()
        else:  # Running on hardware
            logging.info("Running with hardware. Waiting 5s for button events...")
            try:
                time.sleep(5)
            except KeyboardInterrupt:
                logging.info("Example interrupted by user.")
    else:
        logging.error(f"Failed to set up button pin {button_pin}.")

    manager.cleanup_all()
    logging.info("GPIO manager example finished and cleaned up.")
