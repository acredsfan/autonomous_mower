import time
import sys
import board

# Import appropriate INA3221 library based on platform
if 'SAMD21' in sys.platform:
    from barbudor_ina3221.lite import INA3221
else:
    from barbudor_ina3221.full import *
    
i2c_bus = board.I2C()
ina3221 = INA3221(i2c_bus)

# Configure INA3221 for better accuracy if using full API
if INA3221.IS_FULL_API:
    print("Full API sample: improve accuracy")
    ina3221.update(
        reg=C_REG_CONFIG,
        mask=C_AVERAGING_MASK | C_VBUS_CONV_TIME_MASK | 
             C_SHUNT_CONV_TIME_MASK | C_MODE_MASK,
        value=C_AVERAGING_128_SAMPLES | 
              C_VBUS_CONV_TIME_8MS | 
              C_SHUNT_CONV_TIME_8MS | 
              C_MODE_SHUNT_AND_BUS_CONTINOUS
    )

# Enable all 3 channels
ina3221.enable_channel(1)
ina3221.enable_channel(2)
ina3221.enable_channel(3)

while True:
    if INA3221.IS_FULL_API:
        while not ina3221.is_ready:
            print(".", end='')
            time.sleep(0.1)
        print("")

    print("------------------------------")
    line_title = "Measurement   "
    line_psu_voltage = "PSU voltage   "
    line_load_voltage = "Load voltage  "
    line_shunt_voltage = "Shunt voltage "
    line_current = "Current       "
    battery_charge = "Battery charge"

    for chan in range(1, 4):
        if ina3221.is_channel_enabled(chan):
            bus_voltage = ina3221.bus_voltage(chan)
            shunt_voltage = ina3221.shunt_voltage(chan)
            current = ina3221.current(chan)
            
            # Calculate battery charge percentage
            # Using 11.2V as 0% and 14.6V as 100%
            battery_charge_percent = round(
                (bus_voltage - 11.2) / (14.6 - 11.2) * 100, 1
            )
            battery_charge_percent = max(0, min(battery_charge_percent, 100))  # Clamp between 0 and 100
            
            # Update display lines
            line_title += f"| Chan#{chan}      "
            line_psu_voltage += f"| {bus_voltage + shunt_voltage:6.3f} V "
            line_load_voltage += f"| {bus_voltage:6.3f} V "
            line_shunt_voltage += f"| {shunt_voltage:9.6f} V "
            line_current += f"| {current:9.6f} A "
            battery_charge += f"| {battery_charge_percent:6.1f}% "

    print(line_title)
    print(line_psu_voltage)
    print(line_load_voltage)
    print(line_shunt_voltage)
    print(line_current)
    print(battery_charge)  # Added to display battery charge percentage

    time.sleep(2.0)
