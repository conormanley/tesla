import simpy
from simpy.events import AnyOf, AllOf, Event
from random import seed, randint
import time



class G:
	move_map = ([["Pos", "100", "110", "120"], 
								["100", 0, 8, 5], 
								["110", 8, 0, 14], 
								["120", 5, 14, 0]])
	
	ROUTER_CAPACITY = 1
	ROUTER_RUNTIME = 90
	ROUTER_LOAD_TIME = 10
	ROUTER_UNLOAD_TIME = 15
	ROUTER_YIELD = 2
	
	SHEETER_RUNTIME = 22
	SHEETER_YIELD = 1
	
	THERMOFORMER_CAPACITY = 10000
	THERMOFORMER_YIELD = 1
	THERMOFORMER_RUNTIME = 131
	
	LOAD_STATION_LOAD_TIME = 15
	LOAD_STATION_UNLOAD_TIME = 7
	LOAD_STATION_CAPACITY = 2
	
	RAW_SHEET_STOCK_SIZE = 1
	FORMED_SHEET_STOCK_SIZE = 2
	ROUTED_PART_STOCK_SIZE = 1000
	
	
	
	


class Operator(simpy.Resource):
	def __init__(self, env):
		super(Operator, self).__init__(env, capacity=1)
		self.env = env

class Thermoformer(object):
	def __init__(self, name, env, load_station):
		self.load_station = load_station
		self.loaded_stock = load_station.finished_stock
		self.oven_stock = simpy.Container(env, 1)
		self.mold_stock = simpy.Container(env, 1)
		self.name = name
		self.env = env
		self.parts = 0
		self.process = env.process(self.run(self.env))
		
	def run(self, env):
		while True:		
			yield env.timeout(G.THERMOFORMER_RUNTIME)
			if self.load_station.process:
				self.load_station.process.interrupt()
			
			print("Ran a cycle at {0}".format(env.now))
			if self.mold_stock.level > 0:
				yield self.mold_stock.get(1)
				self.load_station.status = 'COMPLETE'
				print("{0} created a formed sheet at {1}".format(self.name, env.now))
			else:
				self.load_station.status = 'EMPTY'
			
			if self.oven_stock.level > 0:
				yield self.oven_stock.get(1)
				yield self.mold_stock.put(1)
				print('Sheet has been put in the mold at {0}'.format(env.now))
			
			if self.load_station.capacity.level == G.LOAD_STATION_CAPACITY:
				print('Putting a sheet in the oven at {0}'.format(env.now))
				yield self.oven_stock.put(1)
				print('Sheet has been put in the oven at {0}'.format(env.now))
			else:
				print('FAILED TO LOAD THERMOFORMER IN TIME')
			
			if self.load_station.capacity.level > 0:
				yield self.load_station.capacity.get(self.load_station.capacity.level) #Consume all loaded raw sheet stock
			
			env.process(self.load_station.run(self.load_station.operator, self.env))
			
			

			


class Load_Station(object):
	def __init__(self, name, env, operator, raw_stock, finished_stock):
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
		while True:
			try:
				if self.status == 'EMPTY':
					yield self.raw_stock.get(1)
					load_proc = env.process(self.load_sheet(self.operator, self.env))
					yield load_proc
				
				if self.status == 'COMPLETE':
					yield self.finished_stock.put(G.THERMOFORMER_YIELD)
					unload_proc = env.process(self.unload_sheet(self.operator, self.env))
					yield unload_proc
				
				if self.status == 'READY':
					yield env.timeout(10)
			except simpy.Interrupt:
				try:
					load_proc.interrupt()
				except:
					pass
				try:
					unload_proc.interrupt()
				except:
					pass
	
	def unload_sheet(self, operator, env):
		try:
			with operator.request() as opr:
				yield opr
				yield env.timeout(G.LOAD_STATION_UNLOAD_TIME)
				print("{0} unloaded a formed sheet at {1}".format(self.name, env.now))
				self.status = 'EMPTY'
		except simpy.Interrupt:
			pass
	
	def load_sheet(self, operator, env):
		try:
			with operator.request() as opr:
				yield opr
				yield env.timeout(G.LOAD_STATION_LOAD_TIME)
				yield self.capacity.put(1)
				print("{0} loaded a sheet at {1}".format(self.name, env.now))
				if self.capacity.level == G.LOAD_STATION_CAPACITY:
					self.status = 'READY'
		except simpy.Interrupt:
			pass

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
				with operator.request() as opr:
					yield opr
					yield env.timeout(G.ROUTER_RUNTIME)
					self.parts += G.ROUTER_YIELD
					print("{0} completed a part at {1}".format(self.name, env.now))
					self.status = 'COMPLETE'

	def unload_part(self, operator, env):
		with operator.request() as opr:
			yield opr
			yield env.timeout(G.ROUTER_UNLOAD_TIME)
			print("{0} unloaded a part at {1}".format(self.name, env.now))
			self.status = 'EMPTY'
	
	def load_part(self, operator, env):
		with operator.request() as opr:
			yield opr
			yield env.timeout(G.ROUTER_LOAD_TIME)
			print("{0} loaded a part at {1}".format(self.name, env.now))
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
				yield env.timeout(G.SHEETER_RUNTIME)
				self.sheets += 1
				print("{0} completed a sheet at {1}".format(self.name, env.now))
				self.status = 'COMPLETE'

	def unload_part(self, operator, env):
		print("{0} unloaded a sheet at {1}".format(self.name, env.now))
		self.status = 'READY'



#Environment
env = simpy.Environment()

#Operators
main_op = Operator(env)
sup_op = Operator(env)

#Containers
formed_sheet_stock = simpy.Container(env, G.FORMED_SHEET_STOCK_SIZE, init=0)
routed_part_stock = simpy.Container(env, G.ROUTED_PART_STOCK_SIZE, init=0)
raw_sheet_stock = simpy.Container(env, G.RAW_SHEET_STOCK_SIZE, init=0)

#Thermoformers
load_station_one = Load_Station('Load Station 1', env, main_op, raw_sheet_stock, formed_sheet_stock)
thermoformer_one = Thermoformer('Thermoformer 1', env, load_station_one)
	
#Automatic Sheeters
sheeter_one = Sheeter('Sheeter 1', env, main_op, raw_sheet_stock)

#Robotic Routers
router_one = Router('Router 1', env, main_op, formed_sheet_stock, routed_part_stock)
router_two = Router('Router 2', env, sup_op, formed_sheet_stock, routed_part_stock)

env.run(until=1000)
print('{0} produced {1} parts and {2} produced {3} parts.'.format(router_one.name, router_one. parts, router_two.name, router_two.parts))



