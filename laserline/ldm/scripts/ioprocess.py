#!/usr/bin/env python3
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
from datetime import datetime, timedelta


class LaserlineIO(object):
    def __init__(self):
        logging.basicConfig(filename='ioprocess.log',level=logging.DEBUG)
        # constants
        self.NUM_DIGITAL_INPUTS = 9
        self.NUM_DIGITAL_OUTPUTS = 4
        self.TEMP_ANALOG_IN_PARAMS = (0x68, 0x10)
        self.CURRENT_ANALOG_IN_PARAMS = (0x68, 0x30)
        self.POWER_ANALOG_IN_PARAMS = (0x68, 0x50)
        self.HOUSING_TEMP_ANALOG_IN_PARAMS = (0x68, 0x70)
        self.OPTIC_TEMP_ANALOG_IN_PARAMS = (0x6e, 0x10)
        # TODO paramaterize addresses and error signal indices


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

        try:
            self.power_dac.normalized_value = 0
        except OSError:
            logging.critical(
                'unable to zero power', exc_info=False)
            exit(1)

        # MCP3248 adc is read with SMBus because there's no decent library for it. addresses 0x68 and 0x6e

        self.digital_in_1 = pcf8574.PCF8574(1, 0x60)
        self.digital_in_2 = pcf8574.PCF8574(1, 0x61)
        self.digital_out = pcf8574.PCF8574(1, 0x62)

        self.digital_outputs = []
        '''
        (
            'threshold_digital',
            'shutter_digital',
            'alignment_laser_digital',
            'reset_error_digital',
        )
        '''
        self.analog_outputs = {
            'x_dim_analog': 0.0,
            'y_dim_analog': 0.0,
        }

        self.digital_inputs = []
        '''
        (
            'sleep_mode_digital',
            'warning_digital',
            'cable_error_digital',
            'collective_error_digital',
            'safety_circuit_digital',
            'shutter_open_digital',
            'threshold_digital',
            'laser_on_digital',
            'shutter_closed_digital',
        )
        '''
        self.analog_inputs = {
            'ldm_temp_analog': 0.0,
            'ldm_current_analog': 0.0,
            'ldm_power_analog': 0.0,
            'optic_housing_temp_analog': 0.0,
            'optic_unit_temp_analog': 0.0,
        }
        pipe = self.r.pipeline()
        pipe.hmset('analog_outputs', self.analog_outputs)
        pipe.hmset('analog_inputs', self.analog_inputs)
        for i in range(self.NUM_DIGITAL_INPUTS):
            pipe.setbit('digital_inputs', i, 0)
        for i in range(self.NUM_DIGITAL_OUTPUTS):
            pipe.setbit('digital_outputs', i, 1)
        pipe.delete('cancel_run', 'start_run', 'run_active')
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
                        # delete returns 1 if key existed
                        if self.r.delete('cancel_run') or errorval:
                            self.run_toggle.notify()
                else:
                    self.r.delete('run_active')
                    self.analog_outputs.update(
                        {k: float(v) for k, v in self.r.hgetall('analog_outputs').items()})
                    self.update_outputs()
                    if self.r.delete('start_run'):  # delete returns 1 if key existed
                        # checks are done in Django before setting start_run
                        self.run_toggle.notify()
                toggle_happened = self.run_toggle.wait(timeout=2)

    def recipe_run(self):
        while True:
            with self.i2c_lock:
                if self.run_toggle.wait():  # using "if" as a spurious wakeup defense mechanism
                    self.run_active.set()
                    self.r.set('run_active', '')
                    logging.info('x '+self.r.get('x_axis')+' y '+self.r.get('y_axis'))
                    self.x_dac.normalized_value = float(self.r.get('x_axis'))
                    self.y_dac.normalized_value = float(self.r.get('y_axis'))
                    durations = [float(duration)
                                 for duration in self.r.lrange('durations', 0, -1)]
                    levels = [float(duration)
                              for duration in self.r.lrange('levels', 0, -1)]
                    self.digital_out.set_output(0, False)  # on!
                    logging.info('laser on!')
                    prevtime = datetime.now()
                    for duration, level in zip(durations, levels):
                        try:
                            self.power_dac.normalized_value = level
                            currtime = datetime.now()
                            logging.info('actually waited milliseconds: ' + str((currtime-prevtime)/timedelta(milliseconds=1)))
                            prevtime = currtime
                            logging.info('power set to: '+str(level))
                            logging.info('planning to wait ms:'+str(duration))
                        except OSError:
                            logging.error(
                                'unable to write power level', exc_info=False)
                        if self.run_toggle.wait(timeout=duration/1000):  # cancel
                            break
                    self.power_dac.normalized_value = 0
                    self.digital_out.set_output(0, True)  # off
                    logging.info('laser off!')
                    self.r.delete('run_active')
                    self.run_active.clear()

    def update_inputs(self):
        retval = False
        # return nonzero if any of the error signals are high
        try:
            self.bus.write_byte(*self.TEMP_ANALOG_IN_PARAMS)
            readback = int.from_bytes(
                bytes(self.bus.read_i2c_block_data(self.TEMP_ANALOG_IN_PARAMS[0], 0x00, 2)), byteorder='big', signed=True)
        except OSError:
            logging.error('unable to read ldm temperature', exc_info=False)
        self.analog_inputs.update({'ldm_temp_analog': readback})

        try:
            self.bus.write_byte
            readback = int.from_bytes(*self.CURRENT_ANALOG_IN_PARAMS)
                bytes(self.bus.read_i2c_block_data(self.CURRENT_ANALOG_IN_PARAMS[0], 0x00, 2)), byteorder='big', signed=True)
        except OSError:
            logging.error('unable to read ldm current', exc_info=False)
        self.analog_inputs.update({'ldm_current_analog': readback})

        try:
            self.bus.write_byte(*self.POWER_ANALOG_IN_PARAMS)
            readback = int.from_bytes(
                bytes(self.bus.read_i2c_block_data(self.POWER_ANALOG_IN_PARAMS[0], 0x00, 2)), byteorder='big', signed=True)
        except OSError:
            logging.error('unable to read ldm power', exc_info=False)
        self.analog_inputs.update({'ldm_power_analog': readback})

        try:
            self.bus.write_byte(*self.HOUSING_TEMP_ANALOG_IN_PARAMS)
            readback = int.from_bytes(
                bytes(self.bus.read_i2c_block_data(self.HOUSING_TEMP_ANALOG_IN_PARAMS[0], 0x00, 2)), byteorder='big', signed=True)
        except OSError:
            logging.error(
                'unable to read optic housing temperature', exc_info=False)
        self.analog_inputs.update({'optic_housing_temp_analog': readback})

        try:
            self.bus.write_byte(*self.OPTIC_TEMP_ANALOG_IN_PARAMS)
            readback = int.from_bytes(
                bytes(self.bus.read_i2c_block_data(self.OPTIC_TEMP_ANALOG_IN_PARAMS[0], 0x00, 2)), byteorder='big', signed=True)
        except OSError:
            logging.error(
                'unable to read optic unit temperature', exc_info=False)
        self.analog_inputs.update({'optic_unit_temp_analog': readback})

        self.r.hmset('analog_inputs', self.analog_inputs)

        try:
            self.digital_inputs = self.digital_in_2.port + self.digital_in_1.port
            pipe = self.r.pipeline()
            for i in range(self.NUM_DIGITAL_INPUTS):
                pipe.setbit('digital_inputs', i, self.digital_inputs[i])
            pipe.execute()
            if self.digital_inputs[2] or self.digital_inputs[3]:  # errors
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
            output_list = [True]  # laser power off
            output_list.extend(
                [bool(self.r.getbit('digital_outputs', i)) for i in range(self.NUM_DIGITAL_OUTPUTS)])
            output_list.extend([True]*3)
            logging.info('outputs at '+str(datetime.now())+': ')
            logging.info(str(output_list))
            self.digital_out.port = output_list
        except OSError:
            logging.error(
                'unable to change digital outputs', exc_info=False)
        try:
            self.x_dac.normalized_value = self.analog_outputs.get(
                'x_dim_analog')
            self.y_dac.normalized_value = self.analog_outputs.get(
                'y_dim_analog')
                
            logging.info(str(self.analog_outputs.get(
                'x_dim_analog')))
            logging.info(str(self.analog_outputs.get(
                'y_dim_analog')))
        except OSError:
            logging.error(
                'unable to change analog outputs', exc_info=False)
        return


if __name__ == "__main__":
    io = LaserlineIO()
    io.main()
