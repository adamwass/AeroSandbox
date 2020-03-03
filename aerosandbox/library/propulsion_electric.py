import numpy as np
import casadi as cas

def motor_electric_performance(
        voltage=None,
        current=None,
        rpm=None,
        torque=None,
        kv=1000,  # rpm/volt
        resistance=0.1,  # ohms
        no_load_current=0.4  # amps
):
    """
    A function for predicting the performance of an electric motor.
    Performance equations based on Mark Drela's First Order Motor Model:
    http://web.mit.edu/drela/Public/web/qprop/motor1_theory.pdf
    Instructions: Input EXACTLY TWO of the following parameters: voltage, current, rpm, torque.
    Exception: You cannot supply the combination of current and torque - this makes for an ill-posed problem.
    The function will output a tuple of all four parameters, plus efficiency: (voltage, current, rpm, torque, efficiency)
    :param voltage: Voltage across motor terminals [Volts]
    :param current: Current through motor [Amps]
    :param rpm: Motor rotation speed [rpm]
    :param torque: Motor torque [N m]
    :param kv: voltage constant, in rpm/volt
    :param resistance: resistance, in ohms
    :param no_load_current: no-load current, in amps
    :return: tuple of all four parameters, plus efficiency: (voltage, current, rpm, torque, efficiency)
    """
    # Validate inputs
    voltage_known = voltage is not None
    current_known = current is not None
    rpm_known = rpm is not None
    torque_known = torque is not None

    assert (
                   voltage_known + current_known + rpm_known + torque_known) == 2, "You must give exactly two input arguments."
    assert not (
            current_known and torque_known), "You cannot supply the combination of current and torque - this makes for an ill-posed problem."

    kv_rads_per_sec_per_volt = kv * np.pi / 30  # rads/sec/volt

    while not (voltage_known and current_known and rpm_known and torque_known):
        if rpm_known:
            if current_known and not voltage_known:
                speed = rpm * np.pi / 30  # rad/sec
                back_EMF_voltage = speed / kv_rads_per_sec_per_volt
                voltage = back_EMF_voltage + current * resistance
                voltage_known = True

        if torque_known:
            if not current_known:
                current = torque * kv_rads_per_sec_per_volt + no_load_current
                current_known = True

        if voltage_known:
            if rpm_known and not current_known:
                speed = rpm * np.pi / 30  # rad/sec
                back_EMF_voltage = speed / kv_rads_per_sec_per_volt
                current = (voltage - back_EMF_voltage) / resistance
                current_known = True
            if not rpm_known and current_known:
                back_EMF_voltage = voltage - (current * resistance)
                speed = back_EMF_voltage * kv_rads_per_sec_per_volt
                rpm = speed * 30 / np.pi
                rpm_known = True

        if current_known:
            if not torque_known:
                torque = (current - no_load_current) / kv_rads_per_sec_per_volt
                torque_known = True

    efficiency = (rpm * np.pi/30) * torque / (voltage * current)

    return voltage, current, rpm, torque, efficiency


def mass_ESC(
        max_power,
):
    """
    Estimates the mass of an ESC.
    Informal correlation to Hobbyking ESCs in the 8s 100A range
    :param max_power: maximum power [W]
    :return: estimated ESC mass [kg]
    """
    return 2.38e-5 * max_power

def mass_battery_pack(
        battery_capacity_Wh,
        battery_cell_specific_energy_Wh_kg = 240,
        battery_pack_cell_fraction = 0.7, # Figure given by Ed Lovelace in a Feb. 2020 presentation for MIT 16.82
):
    """
    Estimates the mass of a lithium-polymer battery.
    :param battery_capacity_Wh: Battery capacity, in Watt-hours [W*h]
    :param battery_cell_specific_energy: Specific energy of the battery at the CELL level [W*h/kg]
    :param battery_pack_cell_fraction: Fraction of the battery pack that is cells, by weight.
    :return: Estimated battery mass [kg]
    """
    return battery_capacity_Wh / battery_cell_specific_energy_Wh_kg / battery_pack_cell_fraction

def mass_motor_electric(
        max_power,
):
    """
    Estimates the mass of a brushless DC electric motor.
    Curve fit to scraped Hobbyking BLDC motor data as of 2/24/2020.
    Estimated range of validity: 50 < max_power < 10000
    :param max_power: maximum power [W]
    :return: estimated motor mass [kg]
    """
    # return max_power / 4128 # Less sophisticated model. 95% CI (3992, 4263), R^2 = 0.866
    return 10 ** (0.8205*cas.log10(max_power)-3.155) # More sophisticated model


if __name__ == '__main__':
    print(motor_electric_performance(
        rpm=100,
        current=3
    ))
    print(motor_electric_performance(
        rpm=4700,
        torque=0.02482817
    ))

    print(
        mass_battery_pack(100)
    )