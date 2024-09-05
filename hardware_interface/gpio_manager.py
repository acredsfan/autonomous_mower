
import gpiod
import logging

def init_gpio(shutdown_pins, interrupt_pins):
    chip = gpiod.Chip('gpiochip0')
    shutdown_lines = [chip.get_line(pin) for pin in shutdown_pins]
    interrupt_lines = [chip.get_line(pin) for pin in interrupt_pins]

    for line in shutdown_lines:
        line.request(consumer='shutdown', type=gpiod.LINE_REQ_DIR_OUT)
        line.set_value(1)

    for line in interrupt_lines:
        line.request(consumer='interrupt', type=gpiod.LINE_REQ_EV_FALLING_EDGE)

    return shutdown_lines, interrupt_lines
