import os
import re
import numpy as np
from scipy.optimize import minimize

def rmse_with_scaling_and_offset(params, robot_position, console_position):
        scale = params[0]
        offset = params[1:4]
    
        scaled_console_position = console_position * scale + offset
    
        robot_position_origin = robot_position - robot_position[0]
    
        differences = np.linalg.norm(robot_position_origin - scaled_console_position, axis=1)
    
        rmse = np.sqrt(np.mean(differences**2))

        return rmse
    
def wrap_angle_radians(angle):
    return (angle + np.pi) % (2 * np.pi) - np.pi
    
def euler_rmse_with_scaling_and_offset_radians(params, desired_euler, actual_euler):
    
    scale = params[0]
    offset = params[1:4]

    adjusted_actual = scale * actual_euler + offset

    differences = wrap_angle_radians(adjusted_actual - desired_euler)

    rmse = np.sqrt(np.mean(differences**2))
    return rmse

def get_offset_and_coefficient_pos(robot, console):
    initial_guess = [0.1, 0, 0, 0]

    bounds = [(0.01, 2), 
                (-10, 10), 
                (-10, 10), 
                (-10, 10)]  

    result = minimize(rmse_with_scaling_and_offset, x0=initial_guess, args=(robot, console), bounds=bounds, method='L-BFGS-B')

    return result.x[0], result.x[1:4], result.fun

def get_offset_and_coefficient_rot(robot, console):
    initial_guess = [1.0, 0, 0, 0]  

    bounds = [
        (0.1, 2),  
        (-np.pi, np.pi),  
        (-np.pi, np.pi),  
        (-np.pi, np.pi) 
    ]

    result = minimize(euler_rmse_with_scaling_and_offset_radians, x0=initial_guess, args=(robot - robot[0], console),
                        bounds=bounds, method='L-BFGS-B')

    return result.x[0], result.x[1:4], result.fun