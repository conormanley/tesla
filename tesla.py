#!/usr/bin/env python3

import simpy
from .equipment import Operator, Sheeter, Thermoformer, Load_Station, Splitter, Router, Hotwire_Trimmer, Driller, Boxer 
from .constants import G
from .plotting import cost_plot



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
	load_station_one = Load_Station('Load Station 1', env, main_ops, station, raw_sheet_stock, formed_sheet_stock, user_input=G.USER_INPUT)
	thermoformer_one = Thermoformer('Thermoformer 1', env, station, load_station_one, user_input=G.USER_INPUT)

	#Formed sheet splitting operation
	splitting_one = Splitter('Splitter 1', env, main_ops, formed_sheet_stock, split_formed_stock, user_input=G.USER_INPUT)
		
	#Automatic Sheeters
	sheeter_one = Sheeter('Sheeter 1', env, main_ops, raw_sheet_stock, user_input=G.USER_INPUT)

	#Robotic Routers
	router_one = Router('Router 1', env, main_ops, split_formed_stock, routed_part_stock, user_input=G.USER_INPUT)
	router_two = Router('Router 2', env, sup_ops, split_formed_stock, routed_part_stock, user_input=G.USER_INPUT)
	router_three = Router('Router 3', env, sup_ops, split_formed_stock, routed_part_stock, user_input=G.USER_INPUT)

	#Hotwire Trimmer
	trimmer_one = Hotwire_Trimmer('Hotwire trimmer 1', env, sup_ops, routed_part_stock, trimmed_part_stock, user_input=G.USER_INPUT)

	#Driller
	driller_one = Driller('Driller 1', env, sup_ops, trimmed_part_stock, finished_part_stock, user_input=G.USER_INPUT)

	#Boxer
	boxer_one = Boxer('Boxer 1', env, sup_ops, finished_part_stock, box, user_input=G.USER_INPUT)

	#Run the simulation environment
	env.run(until=G.SIMULATION_TIME)
	
	wip = formed_sheet_stock.level * 2 + split_formed_stock.level + routed_part_stock.level + trimmed_part_stock.level + finished_part_stock.level
	
	#Generic summary report
	if G.USER_INPUT == True:
		print('\n\nResults:')
		print('{0} produced {1} sheets'.format(sheeter_one.name, sheeter_one.sheets))
		print('{0} produced {1} parts'.format(router_one.name, router_one. parts))
		print('{0} produced {1} parts'.format(router_two.name, router_two. parts))
		print('{0} produced {1} parts'.format(router_three.name, router_three. parts))
		print('{0} produced {1} parts'.format(trimmer_one.name, trimmer_one.parts))
		print('{0} produced {1} parts'.format(driller_one.name, driller_one.parts))
		print('{0} produced {1} boxes'.format(boxer_one.name, boxer_one.boxes))
		print('{0} missed {1} of {2} total cycles'.format(thermoformer_one.name, 
				 thermoformer_one.failures, thermoformer_one.cycles))
		print('{0} parts as WIP still in cell'.format(wip))
		print('Effecitve cycle: {0: .1f}s, Average production rate: {1: .1f} parts/hr'.format(G.SIMULATION_TIME
				  / max(1, (driller_one.parts / 2)), driller_one.parts / (G.SIMULATION_TIME / 3600)))
	
	return driller_one.parts, thermoformer_one.failures, wip


class Setting(object):
	#Used to store run setting and result information from a particular simulation
	def __init__(self, cycle, cost, pcs, wip, failures):
		self.cost = cost
		self.pcs = pcs
		self.wip = wip
		self.failures = failures
		self.cycle = cycle
		self.cost_factor = 0
		self.get_cost_factor()

	def get_cost_factor(self):
		#Weights the results of the simulation into `cost_factor`; higher is better
		if self.cost == 0:
			return
		#Annual revenue is 960,000 and cost is heaviest, followed by number of failures
		self.cost_factor = (960000 / self.cost * 1.5 + 1 / (self.wip + 10) * .01 + 1 / (self.failures + 1) * .02)
	
	def print_out(self):
		print("""Results for a {0}s run:
	Optimized Monark cycle time: {1: .1f}
	Annual cost to run: {2: .0f}
	Pieces produced: {3}
	Cycle failures: {4}
	Remaining WIP in the cell: {5}""".format(G.SIMULATION_TIME, self.cycle, self.cost, self.pcs, self.failures, self.wip))


def cost_sim(min_cycle, max_cycle, steps, user_input=False):
	MIN_CYCLE = min_cycle
	G.THERMOFORMER_RUNTIME = max_cycle
	STEP_COUNT = steps
	STEP_SIZE = (G.THERMOFORMER_RUNTIME - MIN_CYCLE) / 100
	cycle_times_arr = []
	pcs_arr = []
	failures_arr = []
	wip_arr = []
	cost_arr = []
	best_setting = Setting(0, 0, 0, 0, 0)
	labor_cost = G.SIMULATION_TIME / 3600 * (G.MACHINE_RATE + G.OVERHEAD_RATE 
						+ (G.MAIN_OPERATORS + G.SUPPORT_OPERATORS) * G.OPERATOR_RATE)
	
	for i in range(STEP_COUNT):
		pcs, failures, wip = main()
		pcs_arr.append(pcs)
		failures_arr.append(failures)
		wip_arr.append(wip)
		cycle_times_arr.append(G.THERMOFORMER_RUNTIME)
		run_cost = pcs * (G.SHEET_COST + G.BOX_COST) + labor_cost
		annual_cost = G.EAU / max(1, pcs) * run_cost
		cost_arr.append(annual_cost)
		new_setting = Setting(G.THERMOFORMER_RUNTIME, annual_cost, pcs, wip, failures)
		if new_setting.cost_factor > best_setting.cost_factor:
			best_setting = new_setting
		
		print("Run {0} of {1},  run_cost: {2} pcs: {3}".format(i, STEP_COUNT, run_cost, pcs))
		G.THERMOFORMER_RUNTIME -= STEP_SIZE
		
	best_setting.print_out()
	title = "Tesla Monark Simulation Results (3 Oprs, 3 Robots) - Ideal Rate: {0: 0.0f}s, Annual Cost: ${1: 0.0f}".format(best_setting.cycle, best_setting.cost)
	cost_plot(cycle_times_arr, cost_arr, pcs_arr, failures_arr, wip_arr, best_setting.cycle, title=title)
	
	return best_setting
		

if __name__ == '__main__':
	best_setting = cost_sim(45, G.THERMOFORMER_RUNTIME, 100)

	
	
	
	
	
	
	
