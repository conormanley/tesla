#!/usr/bin/env python3

from numpy.random import seed



class G:
	#Class to store constants of which are unique to this simulation
	
	#Environment constants
	SIMULATION_TIME = 50000
	EAU = 120000
	seed(seed=10)
	USER_INPUT = False
	
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
	SHEET_COST = 2.56826 * 2 		#USD/sheet
	BOX_COST = .51675 					#USD/part
	OPERATOR_RATE = 18.00 			#USD/hr
	MACHINE_RATE = 14.78 				#USD/hr
	OVERHEAD_RATE = 19.4964 		#USD/hr