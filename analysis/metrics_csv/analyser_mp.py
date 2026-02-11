import os
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict
#import matplotlib.patches as mpatches
#from utilities import *

class AnalyserMP:
    def __init__(self, data_path):
        last_dir = os.path.basename(data_path)
        annotation_folder = os.path.join(data_path, "out_annotation_csv")
        if last_dir[0] == 'c': 
            name = "clm"+str(last_dir[-1])
        elif last_dir[0] == 'p':
            name = "plm"+str(last_dir[-1])
        elif last_dir[0] == 'd':
            name = "dlm"+str(last_dir[-1])
        else:
            name = "free"+str(last_dir[-1]) 

        self.completed_data = np.loadtxt(os.path.join(data_path, "console_data_completed_1.csv"), delimiter=",", skiprows=1)
        self.recieved_data  = np.loadtxt(os.path.join(data_path, "console_data_recieved_1.csv"), delimiter=",", skiprows=1)
        self.transformed_data   = np.loadtxt(os.path.join(data_path, "robot_command_data_1.csv"), delimiter=",", skiprows=1)
        self.robot_data     = np.loadtxt(os.path.join(data_path, "robot_sim_data_1.csv"), delimiter=",", skiprows=1)
        self.annotation     = pd.read_csv(os.path.join(annotation_folder, name + "_annotation_segment.csv"))  
        self.completed_data[:, 0] *= 10**-9  # Change the timestamp unit 
        self.Tinitial = self.robot_data[0][0] # Initial frame timestamp
        self.sf_rot = 0.12 * 0.3    # System scale factor of rotation
        self.Tpos = np.array([[0, -1,  0],
                              [-1, 0,  0],
                              [0,  0, -1]])  # Position transformation matrix
        self.Trot = np.array([[0, 1, 0],
                              [1, 0, 0],
                              [0, 0, 1]])   # Orientation transformation matrix

    def get_MP_info(self):
        frame_start = self.annotation[["start_frame"]].values.flatten()
        frame_end = self.annotation[["end_frame"]].values.flatten()
        verb = self.annotation[["verb"]].values.flatten()
        instrument = self.annotation[["instrument"]].values.flatten()
        peg = self.annotation[["peg"]].values.flatten()
        pole = self.annotation[["pole"]].values.flatten()
        error = self.annotation[["error_type"]].values.flatten()
        failure = self.annotation[["failure"]].values.flatten()
        mp = self.annotation[["mp"]].values.flatten()
        
        return [frame_start, frame_end, verb, instrument, peg, pole, error, failure, mp]

  