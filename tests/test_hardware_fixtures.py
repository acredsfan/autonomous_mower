"""
Test module for test_hardware_fixtures.py.
"""


from .hardware_fixtures import MockGPIOPin, MockPWM


# Test fixtures
def test_mock_gpio_pin_initialization():
    """Test the MockGPIOPin initialization and value setting."""
    pin = MockGPIOPin()
    assert pin.value == 0

    pin.set_value(1)
    assert pin.value == 1
    assert pin.get_value() == 1

    pin.set_value(0)
    assert pin.value == 0
    assert pin.get_value() == 0


def test_mock_pwm_initialization():
    """Test the MockPWM initialization and starting."""
    pwm = MockPWM(pin=18, frequency=100)
    pwm.start(50)
    assert pwm.duty_cycle == 50
    assert pwm.running


def test_mock_pwm_change_duty_cycle():
    """Test changing the duty cycle of a MockPWM."""
    pwm = MockPWM(pin=19, frequency=100)
    pwm.change_duty_cycle(75)
    assert pwm.duty_cycle == 75


def test_mock_pwm_stop():
    """Test stopping a MockPWM."""
    pwm = MockPWM(pin=20, frequency=100)
    pwm.start(50)
    assert pwm.running
    pwm.stop()
    assert not pwm.running
