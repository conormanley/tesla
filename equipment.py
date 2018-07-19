#!/usr/bin/env python3

import simpy
from numpy.random import normal, seed
from .constants import G



class Operator(simpy.Resource):
	#Operators are treated as a basic Resource that may be separated by tasks
	
	def __init__(self, env, capacity):
		super(Operator, self).__init__(env, capacity=capacity)
		self.env = env


class Sheeter(object):
	#Automated sheeting operation to convert roll stock into sheets to be inserted into the `Load_Station`
	
	def __init__(self, name, env, operator, finished_stock, user_input=False):
		self.finished_stock = finished_stock
		self.name = name
		self.env = env
		self.operator = operator
		self.user_input = user_input
		self.sheets = 0
		self.status = 'READY'
		self.process = env.process(self.run(self.operator, self.env))
		
	def run(self, operator, env):
		while True:		
			if self.status == 'COMPLETE':
				yield self.finished_stock.put(G.SHEETER_YIELD)
				self.unload_part(self.operator, self.env)
			
			if self.status == 'READY':
				yield env.timeout(max(0, normal(loc=G.SHEETER_RUNTIME, scale=G.SHEETER_RUNTIME_STDEV)))
				self.sheets += 1
				if self.user_input == True:
					print("{0} completed a sheet at {1}".format(self.name, env.now))
				self.status = 'COMPLETE'

	def unload_part(self, operator, env):
		if self.user_input == True:
			print("{0} unloaded a sheet at {1}".format(self.name, env.now))
		self.status = 'READY'


class Thermoformer(object):
	#3-Station thermoformer
	#NOTE: delayed unloading of formed sheets won't stop the thermoformer
	#		any excess sheets will be treated as 'offline' WIP to be processed
	#		outside of the cell at a later time.
	
	def __init__(self, name, env, station, load_station, user_input=False):
		self.station = station
		self.load_station = load_station
		self.loaded_stock = load_station.finished_stock
		self.oven_stock = simpy.Container(env, 1)
		self.mold_stock = simpy.Container(env, 1)
		self.user_input = user_input
		self.name = name
		self.env = env
		self.cycles = 0
		self.failures = 0
		self.process = env.process(self.run(self.env))
		
	def run(self, env):
		while True:		
			yield env.timeout(max(0, normal(loc=G.THERMOFORMER_RUNTIME, scale=G.THERMOFORMER_RUNTIME_STDEV)))
			with self.station.request(priority=0) as st:
				yield st
				self.cycles += 1
				if self.user_input == True:
					print("Ran a cycle at {0}".format(env.now))
				if self.mold_stock.level > 0:
					yield self.mold_stock.get(1)
					self.load_station.status = 'COMPLETE'
					if self.user_input == True:
						print("{0} created a formed sheet at {1}".format(self.name, env.now))
					yield self.load_station.finished_stock.put(G.THERMOFORMER_YIELD)
				else:
					self.load_station.status = 'EMPTY'
				
				if self.oven_stock.level > 0:
					yield self.oven_stock.get(1)
					yield self.mold_stock.put(1)
					if self.user_input == True:
						print('Sheet has been put in the mold at {0}'.format(env.now))
				
				if self.load_station.capacity.level == G.LOAD_STATION_CAPACITY:
					if self.user_input == True:
						print('Putting a sheet in the oven at {0}'.format(env.now))
					yield self.oven_stock.put(1)
					if self.user_input == True:
						print('Sheet has been put in the oven at {0}'.format(env.now))
				else:
					if self.user_input == True:
						print('FAILED TO LOAD THERMOFORMER IN TIME')
					self.failures += 1
				
				#Consume all loaded raw sheet stock (scrapped)
				if self.load_station.capacity.level > 0:
					yield self.load_station.capacity.get(self.load_station.capacity.level) 
				
				env.process(self.load_station.run(self.load_station.operator, self.env))


class Load_Station(object):
	#Interactive station used to load and unload sheets from the `Thermoformer`
	
	def __init__(self, name, env, operator, station, raw_stock, finished_stock, user_input=False):
		self.station = station
		self.raw_stock = raw_stock
		self.finished_stock = finished_stock
		self.name = name
		self.capacity = simpy.Container(env, G.LOAD_STATION_CAPACITY)
		self.env = env
		self.operator = operator
		self.user_input = user_input
		self.parts = 0
		self.status = 'EMPTY'
		self.process = env.process(self.run(self.operator, self.env))
		
	def run(self, operator, env):
		while self.status != 'READY':
			if self.status == 'EMPTY':
				yield self.raw_stock.get(1)
				load_proc = env.process(self.load_sheet(self.operator, self.env))
				yield load_proc
			
			if self.status == 'COMPLETE':
				unload_proc = env.process(self.unload_sheet(self.operator, self.env))
				yield unload_proc
			
	def unload_sheet(self, operator, env):
		with self.station.request(priority=100) as st:
			yield st
			try:
				with operator.request() as opr:
					yield opr
					yield env.timeout(max(5, normal(loc=G.LOAD_STATION_UNLOAD_TIME, scale=G.LOAD_STATION_UNLOAD_TIME_STDEV)))
					if self.user_input == True:
						print("{0} unloaded a formed sheet at {1}".format(self.name, env.now))
					self.status = 'EMPTY'
			except simpy.Interrupt as interrupt:
				by = interrupt.cause.by
				usage = env.now - interrupt.cause.usage_since
				if self.user_input == True:
					print('unload_sheet on {0} got preempted by {1} after {2}'.format(self.name, by, usage))

	def load_sheet(self, operator, env):
		with self.station.request(priority=100) as st:
			yield st
			try:
				with operator.request() as opr:
					yield opr
					yield env.timeout(max(7.5, normal(loc=G.LOAD_STATION_LOAD_TIME, scale=G.LOAD_STATION_LOAD_TIME_STDEV)))
					yield self.capacity.put(1)
					if self.user_input == True:
						print("{0} loaded a sheet at {1}".format(self.name, env.now))
					if self.capacity.level == G.LOAD_STATION_CAPACITY:
						self.status = 'READY'
			except simpy.Interrupt as interrupt:
				by = interrupt.cause.by
				usage = env.now - interrupt.cause.usage_since
				if self.user_input == True:
					print('load_sheet on {0} got preempted by {1} after {2}'.format(self.name, by, usage))


class Splitter(object):
	#Manual hand cutting operation used to split a formed sheet into two parts for downstream trimming
	
	def __init__(self, name, env, operator, raw_stock, finished_stock, user_input=False):
		self.raw_stock = raw_stock
		self.finished_stock = finished_stock
		self.name = name
		self.env = env
		self.operator = operator
		self.user_input = user_input
		self.parts = 0
		self.process = env.process(self.run(self.operator, self.env))
		
	def run(self, operator, env):
		while True:
			yield self.raw_stock.get(G.SPLITTER_CAPACITY)
			with operator.request() as opr:
				yield opr
				yield env.timeout(max(5, normal(loc=G.SPLITTER_RUNTIME, scale=G.SPLITTER_RUNTIME_STDEV)))
				self.parts += G.SPLITTER_YIELD
			yield self.finished_stock.put(G.SPLITTER_YIELD)
			if self.user_input == True:
				print("{0} split a sheet at {1}".format(self.name, env.now))
				

class Router(object):
	#Robotic trim operation used to cut the majority of the offal from the `Thermoformer`
	
	def __init__(self, name, env, operator, raw_stock, finished_stock, user_input=False):
		self.raw_stock = raw_stock
		self.finished_stock = finished_stock
		self.name = name
		self.env = env
		self.operator = operator
		self.user_input = user_input
		self.parts = 0
		self.status = 'EMPTY'
		self.process = env.process(self.run(self.operator, self.env))
		
	def run(self, operator, env):
		while True:
			if self.status == 'EMPTY':
				yield self.raw_stock.get(G.ROUTER_CAPACITY)
				yield env.process(self.load_part(self.operator, self.env))
			
			if self.status == 'COMPLETE':
				yield self.finished_stock.put(G.ROUTER_YIELD)
				yield env.process(self.unload_part(self.operator, self.env))
			
			if self.status == 'READY':
				yield env.timeout(max(0, normal(loc=G.ROUTER_RUNTIME, scale=G.ROUTER_RUNTIME_STDEV)))
				self.parts += G.ROUTER_YIELD
				if self.user_input == True:
					print("{0} completed a part at {1}".format(self.name, env.now))
				self.status = 'COMPLETE'

	def unload_part(self, operator, env):
		with operator.request() as opr:
			yield opr
			yield env.timeout(max(10, normal(loc=G.ROUTER_UNLOAD_TIME, scale=G.ROUTER_UNLOAD_TIME_STDEV)))
			if self.user_input == True:
				print("{0} unloaded a part at {1}".format(self.name, env.now))
			self.status = 'EMPTY'
	
	def load_part(self, operator, env):
		with operator.request() as opr:
			yield opr
			yield env.timeout(max(7, normal(loc=G.ROUTER_LOAD_TIME, scale=G.ROUTER_LOAD_TIME_STDEV)))
			if self.user_input == True:
				print("{0} loaded a part at {1}".format(self.name, env.now))
			self.status = 'READY'


class Hotwire_Trimmer(object):
	#Trimming operation that uses hotwires on pistons to trim the ends after the `Router`
	
	def __init__(self, name, env, operator, raw_stock, finished_stock, user_input=False):
		self.raw_stock = raw_stock
		self.finished_stock = finished_stock
		self.name = name
		self.env = env
		self.operator = operator
		self.user_input = user_input
		self.parts = 0
		self.process = env.process(self.run(self.operator, self.env))
		
	def run(self, operator, env):
		while True:
			yield self.raw_stock.get(G.TRIMMER_CAPACITY)
			with operator.request() as opr:
				yield opr
				yield env.timeout(max(10, normal(loc=G.TRIMMER_RUNTIME, scale=G.TRIMMER_RUNTIME_STDEV)))
				self.parts += G.TRIMMER_YIELD
			yield self.finished_stock.put(G.TRIMMER_YIELD)
			if self.user_input == True:
				print("{0} trimmed a part at {1}".format(self.name, env.now))


class Driller(object):
	#Drilling fixture used to create seven small openings in the part after the `Hotwire_Trimmer`
	
	def __init__(self, name, env, operator, raw_stock, finished_stock, user_input=False):
		self.raw_stock = raw_stock
		self.finished_stock = finished_stock
		self.name = name
		self.env = env
		self.operator = operator
		self.user_input = user_input
		self.parts = 0
		self.process = env.process(self.run(self.operator, self.env))
		
	def run(self, operator, env):
		while True:
			yield self.raw_stock.get(G.DRILLER_CAPACITY)
			with operator.request() as opr:
				yield opr
				yield env.timeout(max(5, normal(loc=G.DRILLER_RUNTIME, scale=G.DRILLER_RUNTIME_STDEV)))
				self.parts += G.DRILLER_YIELD
			yield self.finished_stock.put(G.DRILLER_YIELD)
			if self.user_input == True:
				print("{0} drilled a part at {1}".format(self.name, env.now))


class Boxer(object):
	#Operation for packing the finished parts 
	
	def __init__(self, name, env, operator, raw_stock, finished_stock, user_input=False):
		self.raw_stock = raw_stock
		self.finished_stock = finished_stock
		self.name = name
		self.env = env
		self.operator = operator
		self.user_input = user_input
		self.boxes = 0
		self.status = 'NO BOX'
		self.process = env.process(self.run())
	
	def run(self):
		while True:
			if self.status == 'NO BOX':
				yield self.env.process(self.build_box())
			
			if self.status == 'READY':
				yield self.raw_stock.get(1)
				with self.operator.request() as opr:
					yield self.env.timeout(max(4, normal(loc=G.BOX_PACKTIME, scale=G.BOX_PACKTIME_STDEV)))
				yield self.finished_stock.put(1)
			
			if self.finished_stock.level == self.finished_stock.capacity:
				yield self.env.process(self.close_box())
			
	def build_box(self):
		with self.operator.request() as opr:
			yield opr
			yield self.env.timeout(max(10, normal(loc=G.BOX_BUILDTIME, scale=G.BOX_BUILDTIME_STDEV)))
			self.status = 'READY'
	
	def close_box(self):
		with self.operator.request() as opr:
			yield opr
			yield self.env.timeout(max(20, normal(loc=G.BOX_CLOSETIME, scale=G.BOX_CLOSETIME_STDEV)))
			self.status = 'NO BOX'
		self.boxes += 1
		if self.user_input == True:
			print('Finished box number {0}'.format(self.boxes))
		self.finished_stock.get(self.finished_stock.level)