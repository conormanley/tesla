#!/usr/bin/env python3

import simpy
from simpy.events import AnyOf, AllOf, Event
import time
import matplotlib
import matplotlib.pyplot as plt
from numpy.random import normal, seed


class G:
	#Environment constants
	SIMULATION_TIME = 50000
	EAU = 120000
	seed(seed=10)
	
	#Operator constants
	MAIN_OPERATORS = 1
	SUPPORT_OPERATORS = 2
	
	#Equipment constants
	SHEETER_RUNTIME = 22.61
	SHEETER_RUNTIME_STDEV = 0.67
	SHEETER_YIELD = 1
	
	ROUTER_CAPACITY = 1
	ROUTER_RUNTIME = 91.29
	ROUTER_RUNTIME_STDEV = 0.37
	ROUTER_LOAD_TIME = 10.97
	ROUTER_LOAD_TIME_STDEV = 1.19
	ROUTER_UNLOAD_TIME = 17.43
	ROUTER_UNLOAD_TIME_STDEV = 5.46
	ROUTER_YIELD = 1
	
	LOAD_STATION_LOAD_TIME = 15
	LOAD_STATION_LOAD_TIME_STDEV = 1.02
	LOAD_STATION_UNLOAD_TIME = 7.96
	LOAD_STATION_UNLOAD_TIME_STDEV = 1.02
	LOAD_STATION_CAPACITY = 2
	
	THERMOFORMER_YIELD = 1
	THERMOFORMER_RUNTIME = 131
	THERMOFORMER_RUNTIME_STDEV = 0.50
	
	SPLITTER_CAPACITY = 1
	SPLITTER_RUNTIME = 8.58
	SPLITTER_RUNTIME_STDEV = 0.75
	SPLITTER_YIELD = 2
	
	TRIMMER_CAPACITY = 1
	TRIMMER_RUNTIME = 24.29
	TRIMMER_RUNTIME_STDEV = 4.30
	TRIMMER_YIELD = 1
	
	DRILLER_CAPACITY = 1
	DRILLER_RUNTIME = 11.97
	DRILLER_RUNTIME_STDEV = 2.58
	DRILLER_YIELD = 1
	
	BOX_BUILDTIME = 15
	BOX_BUILDTIME_STDEV = 2
	BOX_PACKTIME = 12.06
	BOX_PACKTIME_STDEV = 2.55
	BOX_CLOSETIME = 33
	BOX_CLOSETIME_STDEV = 2
	
	#Container constants
	SPLIT_FORMED_STOCK_SIZE = 4
	RAW_SHEET_STOCK_SIZE = 4
	FORMED_SHEET_STOCK_SIZE = 10000
	ROUTED_PART_STOCK_SIZE = 12
	TRIMMED_PART_STOCK_SIZE = 2
	FINISHED_PART_STOCK_SIZE = 1
	BOX_SIZE = 20
	
	#Costs
	SHEET_COST = 2.56826 * 2 #USD/sheet
	BOX_COST = .51675 #USD/part
	OPERATOR_RATE = 18.00 #USD/hr
	MACHINE_RATE = 14.78 #USD/hr
	OVERHEAD_RATE = 19.4964 # USD/hr
	

class Operator(simpy.Resource):
	def __init__(self, env, capacity):
		super(Operator, self).__init__(env, capacity=capacity)
		self.env = env


class Thermoformer(object):
	def __init__(self, name, env, station, load_station):
		self.station = station
		self.load_station = load_station
		self.loaded_stock = load_station.finished_stock
		self.oven_stock = simpy.Container(env, 1)
		self.mold_stock = simpy.Container(env, 1)
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
				#print("Ran a cycle at {0}".format(env.now))
				if self.mold_stock.level > 0:
					yield self.mold_stock.get(1)
					self.load_station.status = 'COMPLETE'
					#print("{0} created a formed sheet at {1}".format(self.name, env.now))
					yield self.load_station.finished_stock.put(G.THERMOFORMER_YIELD)
				else:
					self.load_station.status = 'EMPTY'
				
				if self.oven_stock.level > 0:
					yield self.oven_stock.get(1)
					yield self.mold_stock.put(1)
					#print('Sheet has been put in the mold at {0}'.format(env.now))
				
				if self.load_station.capacity.level == G.LOAD_STATION_CAPACITY:
					#print('Putting a sheet in the oven at {0}'.format(env.now))
					yield self.oven_stock.put(1)
					#print('Sheet has been put in the oven at {0}'.format(env.now))
				else:
					#print('FAILED TO LOAD THERMOFORMER IN TIME')
					self.failures += 1
				
				if self.load_station.capacity.level > 0:
					yield self.load_station.capacity.get(self.load_station.capacity.level) #Consume all loaded raw sheet stock
				
				env.process(self.load_station.run(self.load_station.operator, self.env))


class Load_Station(object):
	def __init__(self, name, env, operator, station, raw_stock, finished_stock):
		self.station = station
		self.raw_stock = raw_stock
		self.finished_stock = finished_stock
		self.name = name
		self.capacity = simpy.Container(env, G.LOAD_STATION_CAPACITY)
		self.env = env
		self.operator = operator
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
					#print("{0} unloaded a formed sheet at {1}".format(self.name, env.now))
					self.status = 'EMPTY'
			except simpy.Interrupt as interrupt:
				by = interrupt.cause.by
				usage = env.now - interrupt.cause.usage_since
				#print('unload_sheet on {0} got preempted by {1} after {2}'.format(self.name, by, usage))

	def load_sheet(self, operator, env):
		with self.station.request(priority=100) as st:
			yield st
			try:
				with operator.request() as opr:
					yield opr
					yield env.timeout(max(7.5, normal(loc=G.LOAD_STATION_LOAD_TIME, scale=G.LOAD_STATION_LOAD_TIME_STDEV)))
					yield self.capacity.put(1)
					#print("{0} loaded a sheet at {1}".format(self.name, env.now))
					if self.capacity.level == G.LOAD_STATION_CAPACITY:
						self.status = 'READY'
			except simpy.Interrupt as interrupt:
				by = interrupt.cause.by
				usage = env.now - interrupt.cause.usage_since
				#print('load_sheet on {0} got preempted by {1} after {2}'.format(self.name, by, usage))


class Splitter(object):
	def __init__(self, name, env, operator, raw_stock, finished_stock):
		self.raw_stock = raw_stock
		self.finished_stock = finished_stock
		self.name = name
		self.env = env
		self.operator = operator
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
			#print("{0} split a sheet at {1}".format(self.name, env.now))


class Hotwire_Trimmer(object):
	def __init__(self, name, env, operator, raw_stock, finished_stock):
		self.raw_stock = raw_stock
		self.finished_stock = finished_stock
		self.name = name
		self.env = env
		self.operator = operator
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
			#print("{0} trimmed a part at {1}".format(self.name, env.now))


class Driller(object):
	def __init__(self, name, env, operator, raw_stock, finished_stock):
		self.raw_stock = raw_stock
		self.finished_stock = finished_stock
		self.name = name
		self.env = env
		self.operator = operator
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
			#print("{0} drilled a part at {1}".format(self.name, env.now))

class Router(object):
	def __init__(self, name, env, operator, raw_stock, finished_stock):
		self.raw_stock = raw_stock
		self.finished_stock = finished_stock
		self.name = name
		self.env = env
		self.operator = operator
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
				#print("{0} completed a part at {1}".format(self.name, env.now))
				self.status = 'COMPLETE'

	def unload_part(self, operator, env):
		with operator.request() as opr:
			yield opr
			yield env.timeout(max(10, normal(loc=G.ROUTER_UNLOAD_TIME, scale=G.ROUTER_UNLOAD_TIME_STDEV)))
			#print("{0} unloaded a part at {1}".format(self.name, env.now))
			self.status = 'EMPTY'
	
	def load_part(self, operator, env):
		with operator.request() as opr:
			yield opr
			yield env.timeout(max(7, normal(loc=G.ROUTER_LOAD_TIME, scale=G.ROUTER_LOAD_TIME_STDEV)))
			#print("{0} loaded a part at {1}".format(self.name, env.now))
			self.status = 'READY'


class Sheeter(object):
	def __init__(self, name, env, operator, finished_stock):
		self.finished_stock = finished_stock
		self.name = name
		self.env = env
		self.operator = operator
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
				#print("{0} completed a sheet at {1}".format(self.name, env.now))
				self.status = 'COMPLETE'

	def unload_part(self, operator, env):
		#print("{0} unloaded a sheet at {1}".format(self.name, env.now))
		self.status = 'READY'
		

class Boxer(object):
	def __init__(self, name, env, operator, raw_stock, finished_stock):
		self.raw_stock = raw_stock
		self.finished_stock = finished_stock
		self.name = name
		self.env = env
		self.operator = operator
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
		#print('Finished box number {0}'.format(self.boxes))
		self.finished_stock.get(self.finished_stock.level)


def main(user_input=False):
	#Environment
	env = simpy.Environment()

	#Operators
	main_ops = Operator(env, G.MAIN_OPERATORS)
	sup_ops = Operator(env, G.SUPPORT_OPERATORS)

	#Containers
	formed_sheet_stock = simpy.Container(env, G.FORMED_SHEET_STOCK_SIZE, init=0)
	split_formed_stock = simpy.Container(env, G.SPLIT_FORMED_STOCK_SIZE, init=0)
	routed_part_stock = simpy.Container(env, G.ROUTED_PART_STOCK_SIZE, init=0)
	trimmed_part_stock = simpy.Container(env, G.TRIMMED_PART_STOCK_SIZE, init=0)
	raw_sheet_stock = simpy.Container(env, G.RAW_SHEET_STOCK_SIZE, init=0)
	finished_part_stock = simpy.Container(env, G.FINISHED_PART_STOCK_SIZE, init=0)
	box = simpy.Container(env, G.BOX_SIZE, init=0)

	#Thermoformers
	station = simpy.PreemptiveResource(env, capacity=1)
	load_station_one = Load_Station('Load Station 1', env, main_ops, station, raw_sheet_stock, formed_sheet_stock)
	thermoformer_one = Thermoformer('Thermoformer 1', env, station, load_station_one)

	#Formed sheet splitting operation
	splitting_one = Splitter('Splitter 1', env, main_ops, formed_sheet_stock, split_formed_stock)
		
	#Automatic Sheeters
	sheeter_one = Sheeter('Sheeter 1', env, main_ops, raw_sheet_stock)

	#Robotic Routers
	router_one = Router('Router 1', env, main_ops, split_formed_stock, routed_part_stock)
	router_two = Router('Router 2', env, sup_ops, split_formed_stock, routed_part_stock)
	router_three = Router('Router 3', env, sup_ops, split_formed_stock, routed_part_stock)

	#Hotwire Trimmer
	trimmer_one = Hotwire_Trimmer('Hotwire trimmer 1', env, sup_ops, routed_part_stock, trimmed_part_stock)

	#Driller
	driller_one = Driller('Driller 1', env, sup_ops, trimmed_part_stock, finished_part_stock)

	#Boxer
	boxer_one = Boxer('Boxer 1', env, sup_ops, finished_part_stock, box)

	env.run(until=G.SIMULATION_TIME)
	if user_input == True:
		print('\n\nResults:')
		print('{0} produced {1} sheets'.format(sheeter_one.name, sheeter_one.sheets))
		print('{0} produced {1} parts'.format(router_one.name, router_one. parts))
		print('{0} produced {1} parts'.format(router_two.name, router_two. parts))
		print('{0} produced {1} parts'.format(router_three.name, router_three. parts))
		print('{0} produced {1} parts'.format(trimmer_one.name, trimmer_one.parts))
		print('{0} produced {1} parts'.format(driller_one.name, driller_one.parts))
		print('{0} produced {1} boxes'.format(boxer_one.name, boxer_one.boxes))
		print('{0} missed {1} of {2} total cycles'.format(thermoformer_one.name, thermoformer_one.failures, thermoformer_one.cycles))
		print('Effecitve cycle: {0: .1f}s, Average production rate: {1: .1f} parts/hr'.format(G.SIMULATION_TIME / (driller_one.parts / 2), driller_one.parts / (G.SIMULATION_TIME / 3600)))
	
	wip = formed_sheet_stock.level * 2 + split_formed_stock.level + routed_part_stock.level + trimmed_part_stock.level + finished_part_stock.level
	
	return driller_one.parts, thermoformer_one.failures, wip


def cost_plot(cycle_times_arr, cost_arr, pcs_arr, failures, wip, best, title=None):
	plt.subplot(221)
	plt.plot(cycle_times_arr, cost_arr)
	plt.axvline(x=best, color='r', linestyle='dashed')
	plt.ylabel("Annual Cost")
	plt.xlabel("Cycle Times")
	
	if title != None:
		plt.suptitle(title)
	
	plt.subplot(222)
	plt.plot(cycle_times_arr, pcs_arr)
	plt.axvline(x=best, color='r', linestyle='dashed')
	plt.ylabel("Pieces Produced per {0}s".format(G.SIMULATION_TIME))
	plt.xlabel("Cycle Times")


	plt.subplot(223)
	plt.plot(cycle_times_arr, failures)
	plt.axvline(x=best, color='r', linestyle='dashed')
	plt.ylabel("Number of failed cycles")
	plt.xlabel("Cycle Times")
	

	plt.subplot(224)
	plt.plot(cycle_times_arr, wip)
	plt.axvline(x=best, color='r', linestyle='dashed')
	plt.ylabel("WIP in cell (pcs)")
	plt.xlabel("Cycle Times")
	
	plt.subplots_adjust(left=0.2, wspace=0.8, top=0.8)
	
	keep_open=True
	plt.show(block=keep_open)	#block=False to exit out of plots
	if keep_open==False:
		time.sleep(1)
		plt.close()

def best_function(pcs, wip, cost, failures):
	#Weights the results of the simulation, higher is better
	return 960000 / cost * 1.5 + pcs / 600 * .01 + 1 / (wip + 1) * .01 + 1 / (failures + 1) * .01

def cost_sim():
	MIN_CYCLE = 45
	STEP_COUNT = 100
	STEP_SIZE = (G.THERMOFORMER_RUNTIME - MIN_CYCLE) / 100
	cycle_times_arr = []
	pcs_arr = []
	failures_arr = []
	wip_arr = []
	cost_arr = []
	best_cost = 0
	best_cost_factor = 0
	labor_cost = G.SIMULATION_TIME / 3600 * (G.MACHINE_RATE + G.OVERHEAD_RATE 
						+ (G.MAIN_OPERATORS + G.SUPPORT_OPERATORS) * G.OPERATOR_RATE)
	
	for i in range(STEP_COUNT):
		pcs, failures, wip = main()
		pcs_arr.append(pcs)
		failures_arr.append(failures)
		wip_arr.append(wip)
		cycle_times_arr.append(G.THERMOFORMER_RUNTIME)
		G.THERMOFORMER_RUNTIME -= STEP_SIZE
		run_cost = pcs * (G.SHEET_COST + G.BOX_COST) + labor_cost
		print("run_cost: {0} pcs: {1}".format(run_cost, pcs))
		annual_cost = G.EAU / max(1, pcs) * run_cost
		cost_factor = best_function(pcs, wip, annual_cost, failures)
		if cost_factor > best_cost_factor or best_cost == 0:
			best = G.THERMOFORMER_RUNTIME
			best_cost = annual_cost
			best_cost_factor = cost_factor
		
		cost_arr.append(annual_cost)		
	#print("Cycles:\n{0}".format(cycle_times_arr))
	#print("PCS:\n{0}".format(pcs_arr))
	#print("Costs:\n{0}".format(cost_arr))
	cost_plot(cycle_times_arr, cost_arr, pcs_arr, failures_arr, wip_arr, best, title="Tesla Monark Simulation Results (3 Oprs, 3 Robots) - Ideal Rate: {0: 0.0f}s, Annual Cost: ${1: 0.0f}".format(best, best_cost))
		
		

if __name__ == '__main__':
	cost_sim()

	
	
	
	
	
	
	
	
