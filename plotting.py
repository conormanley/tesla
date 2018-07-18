#!/usr/bin/env python3

import matplotlib
import matplotlib.pyplot as plt
from .constants import G



def cost_plot(cycle_times_arr, cost_arr, pcs_arr, failures, wip, best, title=None):
	if title != None:
		plt.suptitle(title)
	
	plt.subplot(221)
	plt.plot(cycle_times_arr, cost_arr)
	plt.axvline(x=best, color='r', linestyle='dashed')
	plt.ylabel("Annual Cost")
	plt.xlabel("Cycle Times")
	
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
		time.sleep(5)
		plt.close()