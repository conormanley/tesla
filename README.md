# tesla
Tesla work cell simulation

Consists of the following modules
  constants.py - Contains simulation parameters
  equipment.py - Contains the classes for each machine or operation
  plotting.py  - Contains basic plotting functions for visualization of work cell optimization
  tesla.py     - Contains the two main functions `main()` and `cost_sim()`

Code Example / API Reference
The work cell simulation is already housed within the `main()` function. Set user_input=True for a printout of the simulation. Below is a basic summary of the inputs and outputs from the `main()` function.

  `parts produced`, `number of failed cycles`, `remaining WIP in the cell` = main(user_input=False)

For work cell optimization, used the `cost_sim()` function. This will print out the settings from the best run and also plot the results. Inputs and outputs for this are below.

  `Setting` object for the optimized cell = cost_sim(min_cycle, max_cycle, steps, user_input=False)
  
Motivation
This stems from a continuous improvement effort for our Georgia plant with the focus of optimizing the work cell.

Installation
Clone this repository to your favorite folder.

Tests
A test case is already loaded into the tesla.py module. Run the following command through the command shell in order to fun the cost_sim() function with min_cycle=45, max_cycle=131, steps=100.
  
  python -m tesla.tesla
