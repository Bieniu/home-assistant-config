"""
Update Z-Wave thermostats (e.g. Danfoss 014G0013) state and current temperature from sensor.
Arguments:
 - thermostats			- list of thermostats entities (required)
 - sensors				- list of sensors entities (required)
 - heat_state			- name of heating state, default 'heat' (optional)
 - idle_state			- name of idle state, default 'idle' (optional)
 - idle_heat_temp		- temperature value between 'idle' and 'heat' states, default 8 (optional)
 - wait_for_zwave		- defines whether the script has to wait for the initialization of the Z-wave component, default False (optional)
						  With wait_for_zwave = True script waits for zwave.network_ready event to start. You have to restart Home Assistant to generate this event.
The order of thermostats and sensors is important. The first thermostat takes data from the first sensor, the second thermostat from the second sensor, etc.

Configuration example:

update_thermostats:
  module: update_thermostats
  class: UpdateThermostats
  thermostats:
    - climate.thermostat_kitchen
    - climate.thermostat_room
    - climate.thermostat_bathroom
  sensors:
    - sensor.temperature_kitchen
    - sensor.temperature_room
    - sensor.temperature_bathroom
  heat_state: auto
  idle_state: off
  idle_heat_temp: 10
  wait_for_zwave: true

"""

import appdaemon.appapi as appapi

class UpdateThermostats(appapi.AppDaemon):

	def initialize(self):
		try:
			if len(self.args['thermostats']) != len(self.args['sensors']):
				self.error('Wrong arguments! The arguments sensors and thermostats must contain the same number of elements.')
				return
		except KeyError:
			self.error('Wrong arguments! You must supply a valid sensors and thermostats entities.')
			return

		self.zwave_ready_handle = None

		if 'wait_for_zwave' in self.args:
			wait_for_zwave = self.args['wait_for_zwave']
		else:
			wait_for_zwave = False
		if 'heat_state' in self.args:
			self.heat_state = self.args['heat_state']
		else:
			self.heat_state = 'heat'
		if 'idle_state' in self.args:
			self.idle_state = self.args['idle_state']
		else:
			self.idle_state = 'idle'
		if 'idle_heat_temp' in self.args:
			self.idle_heat_temp = self.args['idle_heat_temp']
		else:
			self.idle_heat_temp = 8

		if wait_for_zwave:
			self.zwave_ready_handle = self.listen_event(self.start_listen_states(), event = 'zwave.network_ready')
		else:
			self.start_listen_states()

	def start_listen_states(self):
		if self.zwave_ready_handle is not None:
			self.cancel_listen_event(self.zwave_ready_handle)
		for i in range(len(self.args['thermostats'])):
			if self.entity_exists(self.args['thermostats'][i]) == False:
				raise Exception('Wrong arguments! At least one of the entities does not exist.')
			if self.entity_exists(self.args['sensors'][i]) == False:
				raise Exception('Wrong arguments! At least one of the entities does not exist.')
			self.listen_state(self.thermostat_state_changed, self.args['thermostats'][i], attribute = 'current_temperature', new = None)
			self.listen_state(self.sensor_state_changed, self.args['sensors'][i])
			if self.get_state(self.args['thermostats'][i], attribute="current_temperature") == None:
				self.thermostat_state_changed(self.args['thermostats'][i], attribute = "current_temperature", old = None, new = None, kwargs = None)

	def thermostat_state_changed(self, entity, attribute, old, new, kwargs):
		for i in range(len(self.args['thermostats'])):
			if entity == self.args['thermostats'][i]:
				sensor_id = self.args['sensors'][i]

		sensor_temp = self.get_state(sensor_id)
		target_temp = self.get_state(entity, attribute="temperature")

		if new == None or float(new) != float(sensor_temp):
			if sensor_temp is not None and sensor_temp != 'Unknown':
				self.find_thermostat_state(float(target_temp))
				self.set_state(entity, state=self.state, attributes = {"current_temperature": sensor_temp})
			else:
				self.log('No temperature data on the sensor {}.'.format(sensor_id))

	def sensor_state_changed(self, entity, attribute, old, new, kwargs):
		for i in range(len(self.args['sensors'])):
			if entity == self.args['sensors'][i]:
				thermostat_id = self.args['thermostats'][i]

				current_temp = self.get_state(thermostat_id, attribute="current_temperature")
		target_temp = self.get_state(thermostat_id, attribute="temperature")

		if current_temp == None or float(current_temp) != float(new):
			if new is not None and new != 'Unknown':
				self.find_thermostat_state(float(target_temp))
				self.set_state(thermostat_id, state=self.state, attributes = {"current_temperature": new})
			else:
				self.log('No temperature data on the sensor {}.'.format(self.entity))

	def find_thermostat_state(self, target_temp):
		if target_temp > self.idle_heat_temp:
			self.state = self.heat_state
		else:
			self.state = self.idle_state
