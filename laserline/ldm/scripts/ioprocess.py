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


class LaserlineIO(object):
	def __init__(self):
		# everything passed in between functions goes here
		 r = redis.Redis(password='laserr3flow')
		i2c_lock = threading.Lock()
		run_toggle = threading.Condition(i2c_lock)
		run_active = threading.Event()
		bus = smbus.SMBus(1)
		i2c = busio.I2C(board.SCL, board.SDA)

		# mcp4725 dacs
		tca = adafruit_tca9548a.TCA9548A(i2c)
		power_dac = adafruit_mcp4725.MCP4725(tca[0], address=0x60)
		x_dac = adafruit_mcp4725.MCP4725(tca[1], address=0x60)
		y_dac = adafruit_mcp4725.MCP4725(tca[2], address=0x60)
		dacs = {
			'power_dac': power_dac,
			'x_dac': x_dac,
			'y_dac': y_dac
		}
		power_dac.normalized_value = 0
		# MCP3248 adc is read with SMBus because there's no decent library for it. addresses 0x68 and 0x6e

		# digital i/o
		digital_in_1 = pcf8574.PCF8574(1,0x60)
		digital_in_2 = pcf8574.PCF8574(1,0x61)
		digital_out = pcf8574.PCF8574(1,0x62)

		digital_outputs = {
			'threshold_digital': False,
			'shutter_digital': False,
			'alignment_laser_digital': False,
			'reset_error_digital': False,
		}
		analog_outputs = {
			'x_dim_analog': 0.0,
			'y_dim_analog': 0.0,
			'temperature_preset_analog': 0.0,
		}
		digital_inputs = {
			'sleep_mode_digital': False,
            'warning_digital': False,
            'cable_error_digital': False,
            'collective_error_digital': False,
            'safety_circuit_digital': False,
            'shutter_open_digital': False,
            'threshold_digital': False,
            'laser_on_digital': False,
            'shutter_closed_digital': False,
		}
		analog_inputs = {
			'ldm_temp_analog': 0.0,
            'ldm_current_analog': 0.0,
            'ldm_power_analog': 0.0,
            'optic_housing_temp_analog' 0.0,
            'optic_unit_temp_analog' 0.0,
		}
		r.hmset('digital_outputs', digital_outputs)
		r.hmset('analog_outputs', analog_outputs)
		r.hmset('digital_inputs', digital_inputs)
		r.hmset('digital_outputs', digital_outputs)

		

	def main(self):
		toggle_happened = False
		run_thread = threading.Thread(target=self.recipe_run)
		run_thread.start()
		while True:
			with self.i2c_lock:
				errorval = self.update_inputs()
				if self.run_active.is_set():
					if not toggle_happened: # just timeout happened
						if self.r.get('cancel_run') or errorval:
							self.r.set('cancel_run', 0)
							self.run_toggle.notify()
				else:
					self.outputs.update(r.hmget('laserline_outputs'))
					self.update_outputs()
					if self.r.get('start_run'):
						self.r.set('start_run', 0)
						# checks are done in Django before setting start_run
						self.run_toggle.notify()

				toggle_happened = self.run_toggle.wait(timeout=0.1)

	def recipe_run(self):
		while True:
			if self.run_toggle.wait():  # using "if" as a spurious wakeup defense mechanism
				self.run_active.set()
				self.x_dac.normalized_value = r.get('x_axis')
				self.y_dac.normalized_value = r.get('y_axis')
				durations = self.r.lrange('durations', 0, -1)
				levels = self.r.lrange('levels', 0, -1)
				for duration, level in zip(durations, levels):
					with self.i2c_lock:
						try:
							self.power_dac.normalized_value = level
						except OSError:
							logging.error(
								'unable to write power level', exc_info=True)
						if self.run_toggle.wait(timeout=duration):  # cancel
							break
				with self.i2c_lock:
					self.power_dac.normalized_value=0
					# TODO shut off laser power
				self.run_active.clear()

def update_inputs(self):
    # return nonzero if any of the error signals are high


    return False


def update_outputs(self):
    # update outputs dicts, then explicitly disable laser and put power preset to zero
	
    return


if __name__ == "__main__":
    io = LaserlineIO()
	io.main()