import redis
from time import sleep
import threading
import smbus
import pcf8574
import board
import busio
import adafruit_mcp4725
import adafruit_tca9548a
import logging
from sys import exit


class LaserlineIO(object):
    def __init__(self):
        # everything passed in between functions goes here
        self.r = redis.Redis(password='laserr3flow', decode_responses=True)
        self.i2c_lock = threading.Lock()
        self.run_toggle = threading.Condition(self.i2c_lock)
        self.run_active = threading.Event()
        self.bus = smbus.SMBus(1)
        self.i2c = busio.I2C(board.SCL, board.SDA)

        # mcp4725 dacs
        self.tca = adafruit_tca9548a.TCA9548A(self.i2c)
        self.power_dac = adafruit_mcp4725.MCP4725(self.tca[0], address=0x60)
        self.x_dac = adafruit_mcp4725.MCP4725(self.tca[1], address=0x60)
        self.y_dac = adafruit_mcp4725.MCP4725(self.tca[2], address=0x60)

        # TODO uncomment this
        try:
            self.power_dac.normalized_value = 0
        except OSError:
            logging.critical(
                'unable to zero power', exc_info=False)
            exit(1)

        # MCP3248 adc is read with SMBus because there's no decent library for it. addresses 0x68 and 0x6e

        # digital i/o
        self.digital_in_1 = pcf8574.PCF8574(1, 0x60)
        self.digital_in_2 = pcf8574.PCF8574(1, 0x61)
        self.digital_out = pcf8574.PCF8574(1, 0x62)

        self.digital_outputs = {
            'threshold_digital': 0,
            'shutter_digital': 0,
            'alignment_laser_digital': 0,
            'reset_error_digital': 0,
        }
        self.analog_outputs = {
            'x_dim_analog': 0.0,
            'y_dim_analog': 0.0,
            'temperature_preset_analog': 0.0,
        }
        self.digital_inputs = {
            'sleep_mode_digital': 0,
            'warning_digital': 0,
            'cable_error_digital': 0,
            'collective_error_digital': 0,
            'safety_circuit_digital': 0,
            'shutter_open_digital': 0,
            'threshold_digital': 0,
            'laser_on_digital': 0,
            'shutter_closed_digital': 0,
        }
        self.analog_inputs = {
            'ldm_temp_analog': 0.0,
            'ldm_current_analog': 0.0,
            'ldm_power_analog': 0.0,
            'optic_housing_temp_analog': 0.0,
            'optic_unit_temp_analog': 0.0,
        }
        pipe = self.r.pipeline()
        pipe.hmset('digital_outputs', self.digital_outputs)
        pipe.hmset('analog_outputs', self.analog_outputs)
        pipe.hmset('digital_inputs', self.digital_inputs)
        pipe.hmset('digital_outputs', self.digital_outputs)
        pipe.set('cancel_run', 0)
        pipe.set('start_run', 0)
        pipe.execute()

    def main(self):
        toggle_happened = False
        run_thread = threading.Thread(target=self.recipe_run)
        run_thread.start()
        while True:
            with self.i2c_lock:
                errorval = self.update_inputs()
                if self.run_active.is_set():
                    if not toggle_happened:  # just timeout happened
                        if int(self.r.get('cancel_run')) or errorval:
                            self.r.set('cancel_run', 0)
                            self.run_toggle.notify()
                else:
                    self.analog_outputs.update(
                        {k: float(v) for k, v in self.r.hgetall('analog_outputs').items()})
                    self.digital_outputs.update(
                        {k: int(v) for k, v in self.r.hgetall('digital_outputs').items()})
                    self.update_outputs()
                    if int(self.r.get('start_run')):
                        self.r.set('start_run', 0)
                        # checks are done in Django before setting start_run
                        self.run_toggle.notify()
                toggle_happened = self.run_toggle.wait(timeout=0.1)

    def recipe_run(self):

        while True:
            with self.i2c_lock:
                if self.run_toggle.wait():  # using "if" as a spurious wakeup defense mechanism
                    self.run_active.set()
                    self.x_dac.normalized_value = float(r.get('x_axis'))
                    self.y_dac.normalized_value = float(r.get('y_axis'))
                    durations = [float(duration)
                                 for duration in self.r.lrange('durations', 0, -1)]
                    levels = [float(duration)
                              for duration in self.r.lrange('levels', 0, -1)]
                    for duration, level in zip(durations, levels):
                        try:
                            self.power_dac.normalized_value = level
                        except OSError:
                            logging.error(
                                'unable to write power level', exc_info=False)
                        if self.run_toggle.wait(timeout=duration):  # cancel
                            break
                    self.power_dac.normalized_value = 0
                    self.run_active.clear()

    def update_inputs(self):
        retval = False
        # return nonzero if any of the error signals are high
        try:
            self.bus.write_byte(0x68, 0x10)
            readback = int.from_bytes(
                bytes(self.bus.read_i2c_block_data(0x68, 0x00, 2)), byteorder='big', signed=True)
        except OSError:
            logging.error('unable to read ldm temperature', exc_info=False)
        self.analog_inputs.update({'ldm_temp_analog': readback})

        try:
            self.bus.write_byte(0x68, 0x30)
            readback = int.from_bytes(
                bytes(self.bus.read_i2c_block_data(0x68, 0x00, 2)), byteorder='big', signed=True)
        except OSError:
            logging.error('unable to read ldm current', exc_info=False)
        self.analog_inputs.update({'ldm_current_analog': readback})

        try:
            self.bus.write_byte(0x68, 0x50)
            readback = int.from_bytes(
                bytes(self.bus.read_i2c_block_data(0x68, 0x00, 2)), byteorder='big', signed=True)
        except OSError:
            logging.error('unable to read ldm power', exc_info=False)
        self.analog_inputs.update({'ldm_power_analog': readback})

        try:
            self.bus.write_byte(0x68, 0x70)
            readback = int.from_bytes(
                bytes(self.bus.read_i2c_block_data(0x68, 0x00, 2)), byteorder='big', signed=True)
        except OSError:
            logging.error(
                'unable to read optic housing temperature', exc_info=False)
        self.analog_inputs.update({'optic_housing_temp_analog': readback})

        try:
            self.bus.write_byte(0x6e, 0x10)
            readback = int.from_bytes(
                bytes(self.bus.read_i2c_block_data(0x68, 0x00, 2)), byteorder='big', signed=True)
        except OSError:
            logging.error(
                'unable to read optic unit temperature', exc_info=False)
        self.analog_inputs.update({'optic_unit_temp_analog': readback})

        self.r.hmset('analog_inputs', self.analog_inputs)

        try:
            input_1 = self.digital_in_1.port
            input_2 = self.digital_in_2.port
            self.digital_inputs.update({
                'sleep_mode_digital': int(input_1[0]),
                'warning_digital': int(input_1[1]),
                'cable_error_digital': int(input_1[2]),
                'collective_error_digital': int(input_1[3]),
                'safety_circuit_digital': int(input_1[4]),
                'shutter_open_digital': int(input_1[5]),
                'threshold_digital': int(input_1[6]),
                'laser_on_digital': int(input_1[7]),
                'shutter_closed_digital': int(input_2[0]),
            })
            self.r.hmset('digital_inputs', self.digital_inputs)
            if input_1[2] or input_1[3]:  # errors
                retval = True
        except OSError:
            logging.error(
                'unable to read digital input', exc_info=False)
            retval = True
        return retval

    def update_outputs(self):
        try:
            self.power_dac.normalized_value = 0
        except OSError:
            logging.critical(
                'unable to zero power', exc_info=False)

        try:
            output_list = [0]  # laser power
            output_list.extend(self.digital_outputs.values())
            output_list.extend([0, 0, 0])
            self.digital_out.port = [bool(i) for i in output_list]
        except OSError:
            logging.error(
                'unable to change digital outputs', exc_info=False)
        try:
            self.x_dac.normalized_value = self.analog_outputs.get(
                'x_dim_analog')
            self.y_dac.normalized_value = self.analog_outputs.get(
                'y_dim_analog')
        except OSError:
            logging.error(
                'unable to change analog outputs', exc_info=False)
        return


if __name__ == "__main__":
    io = LaserlineIO()
    io.main()
