from __future__ import division
import pandas as pd
import numpy as np
import math
import matplotlib as mpl
mpl.use('MacOSX')
import matplotlib.pyplot as plt
# --> Custom Imports Above

from environment import Agent, Environment
from planner import RoutePlanner
from simulator import Simulator

class LearningAgent(Agent):
    """An agent that learns to drive in the smartcab world."""

    def __init__(self, env):
        super(LearningAgent, self).__init__(env)  # sets self.env = env, state = None, next_waypoint = None, and a default color
        self.color = 'red'  # override color
        self.planner = RoutePlanner(self.env, self)  # simple route planner to get next_waypoint

        # NOTE: Custom variables below that are persistent for the entire duration of the simulation
        self.available_actions = ['stay', 'forward', 'left', 'right'] # I chose stay instead of None, because it resolved troubles I had with indexing

        self.alpha = 0.9
        self.gamma = 0
        self.epsilon = 0.4

        self.q_values = dict()

        #TODO: Revise Metrics
        self.metrics = pd.DataFrame(columns=['Success', 'CumSuccess', 'Total Reward', 'CumTotal Reward', 'Planner not Observed', 'Invalid Moves', 'Trip Duration'])
        self.metrics.index.name = 'trial'

        self.trial = 0

    def reset(self, destination=None):
        self.planner.route_to(destination)

        # NOTE: Resetting custom variables
        self.route_duration = None

        # NOTE: Preparing variables for new trial
        self.trial += 1
        self.metrics.loc[self.trial] = [0, 0, 0, 0, 0, 0, 0]

        # NOTE: Decreasing paramters
        self.alpha -= self.alpha * 0.05
        self.epsilon -= self.epsilon * 0.6

    def update(self, t):
        # NOTE: Getting Inputs
        self.next_waypoint = self.planner.next_waypoint()  # from route planner, also displayed by simulator
        inputs = self.env.sense(self)
        deadline = self.env.get_deadline(self)

        # NOTE: Saving the route duration for calculations and analysis
        if self.route_duration == None:
            self.route_duration = deadline

        # NOTE: Setting the current state
        self.state = self.assemble_state(self.next_waypoint, inputs)

        # NOTE: Selecting the appropriate action based on the policy
        action = self.policy(self.state)

        # NOTE: Execute action and get reward
        if action == 'stay':
            reward = self.env.act(self, None)
        else:
            reward = self.env.act(self, action)

        # NOTE: Tracking relevant agent metrics
        if self.env.agent_states[self]["location"] == self.env.agent_states[self]["destination"]:
            self.metrics.loc[self.trial, 'Success'] = 1

        # TODO: Adjust to fit reward structure
        if reward == -0.5:
            self.metrics.loc[self.trial, 'Planner not Observed'] += 1

        if reward == -1:
            self.metrics.loc[self.trial, 'Invalid Moves'] += 1

        self.metrics.loc[self.trial, 'Trip Duration'] = (self.route_duration - deadline)/self.route_duration
        self.metrics.loc[self.trial, 'Total Reward'] += reward

        # NOTE: Getting the new state of smart cab and recording the learned Q value
        new_state = self.assemble_state(self.planner.next_waypoint(), self.env.sense(self))

        self.q_values[(self.state, action)] = (1 - self.alpha) * self.get_qvalue(self.state, action) + self.alpha * (reward + self.gamma * self.max_q(new_state))

        print "LearningAgent.update(): waypoint={}, deadline = {}, inputs = {}, state = {}, action = {}, reward = {}".format(self.next_waypoint, deadline, inputs, self.state, action, reward)  # [debug]

        # NOTE: Saving q matrix and metrics to csv - this has to be optimized
        self.metrics['CumSuccess'] = self.metrics['Success'].cumsum()
        self.metrics['CumTotal Reward'] = self.metrics['Total Reward'].cumsum()

        # self.metrics.to_csv('metrics_agent.csv')

        print "Score: {}".format(0.4 * self.metrics['Success'].mean() + 0.4 * self.metrics['Invalid Moves'].mean() + 0.2 * self.metrics['Trip Duration'].mean())

    def assemble_state(self, next_waypoint, inputs):

        return (next_waypoint, inputs['light'], inputs['left'], inputs['oncoming'], inputs['right'])

    def get_qvalue(self, state, action): # Function to get Q-Values safely

        if (state, action) in self.q_values:
            return self.q_values[(state, action)]
        else:
            # NOTE: I optimized intialization of the Q Matrix to improve results
            if state[0] == action and state[1] != "red":
                return 2
            else:
                return -0.5

    def max_q(self, state, return_action=False): # Function to get the maximum q value safely

        max_q = 0
        max_action = None

        for action in self.available_actions:
            q = self.get_qvalue(state, action)
            if q > max_q:
                max_q = q
                max_action = action

        if return_action:
            return max_action
        else:
            return max_q

    def policy(self, state):

        # NOTE: Based on epsilon choosing either random or policy based actions
        action_category = np.random.choice([0, 1], p=[self.epsilon, 1 - self.epsilon])

        # NOTE: Choosing the action based on the learned policy, if enough data is available
        if action_category and self.max_q(state) > 0:
            action = self.max_q(state, True)
        else:
            action = np.random.choice(self.available_actions)

        return action


def run():
    """Run the agent for a finite number of trials."""

    # Set up environment and agent
    e = Environment()  # create environment (also adds some dummy traffic)
    a = e.create_agent(LearningAgent)  # create agent
    e.set_primary_agent(a, enforce_deadline=True)  # specify agent to track
    # NOTE: You can set enforce_deadline=False while debugging to allow longer trials

    # Now simulate it
    sim = Simulator(e, update_delay=0, display=True)  # create simulator (uses pygame when display=True, if available)
    # NOTE: To speed up simulation, reduce update_delay and/or set display=False

    sim.run(n_trials=100)  # run for a specified number of trials
    # NOTE: To quit midway, press Esc or close pygame window, or hit Ctrl+C on the command-line


if __name__ == '__main__':
    run()
