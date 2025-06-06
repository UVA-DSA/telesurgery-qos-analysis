import os
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict
import matplotlib.patches as mpatches
from utilities import *

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
        self.transformed_data   = np.loadtxt(os.path.join(data_path, "console_data_sampled_1.csv"), delimiter=",", skiprows=1)
        self.robot_data     = np.loadtxt(os.path.join(data_path, "robot_sim_data_1.csv"), delimiter=",", skiprows=1)
        self.annotation     = pd.read_csv(os.path.join(annotation_folder, name + "_annotation_processed.csv"))  
        self.completed_data[:, 0] *= 10**-9  # Change the timestamp unit 
        self.Tframe = 1 / 60   # Frame rate 60 Hz
        self.Tinitial = self.robot_data[0][0] # Initial frame timestamp
        self.sf_pos = 0.000115      # System scale factor of postion
        self.sf_rot = 0.12 * 0.3    # System scale factor of rotation
        self.Tpos = np.array([[0, -1,  0],
                              [-1, 0,  0],
                              [0,  0, -1]])  # Position transformation matrix
        self.Trot = np.array([[0, 1, 0],
                              [1, 0, 0],
                              [0, 0, 1]])   # Orientation transformation matrix
    
    def get_MP_timestamp_intervals(self):
        verbs  = self.annotation[["verb"]].values.flatten()
        colors = self.annotation[["peg"]].values.flatten()

        segments = []
        start_idx = 0
        for i in range(1, len(verbs)):
            if verbs[i] != verbs[i - 1]:
                segments.append((colors[start_idx], verbs[start_idx], start_idx, i - 1))
                start_idx = i
        segments.append((colors[start_idx], verbs[start_idx], start_idx, len(verbs) - 1))

        peg_mp_dict = defaultdict(list)
        for color, verb, start, end in segments:
            if verb != "Idle":
                Ts = self.Tinitial + start*self.Tframe
                Te = self.Tinitial + end*self.Tframe
                peg_mp_dict[color] += [(verb, Ts, Te)]
        
        return peg_mp_dict

    def get_MP_timestamp_error(self):
        verbs  = self.annotation[["verb"]].values.flatten()
        colors = self.annotation[["peg"]].values.flatten()
        poles = self.annotation[["pole"]].values.flatten()
        errors = self.annotation[["error_type"]].values.flatten()

        segments = []
        start_idx = 0
        for i in range(1, len(verbs)):
            if verbs[i] != verbs[i - 1]:
                segments.append((colors[start_idx+1], verbs[start_idx+1], poles[start_idx+1], errors[start_idx+1], start_idx, i-1))
                start_idx = i-1
        segments.append((colors[start_idx+1], verbs[start_idx+1], poles[start_idx+1], errors[start_idx+1], start_idx, len(verbs)))
        
        peg_mp_dict = defaultdict(list)
        for color, verb, pole, error, start, end in segments:
            if verb != "Idle":
                Ts = self.Tinitial + start*self.Tframe
                Te = self.Tinitial + end*self.Tframe
                peg_mp_dict[color] += [(verb, pole, error, Ts, Te)]
        
        return peg_mp_dict

    def get_MP_completion_time(self, peg_mp_dict, color):
        ctime = []
        for i in range(len(peg_mp_dict[color])):
            Ts = peg_mp_dict[color][i][1]
            Te = peg_mp_dict[color][i][2]
            t = Te - Ts
            ctime.append(t)
    
        return ctime

    def get_MP_index_interval_completed(self, peg_mp_dict, completed, color):
        interval = []

        for i in range(len(peg_mp_dict[color])):
            if i == 0:
                idx_Ts_completed = np.argmin(np.abs(completed[:, 0] - peg_mp_dict[color][i][-2]))
                idx_Te_completed = np.argmin(np.abs(completed[:, 0] - peg_mp_dict[color][i][-1]))
            else:
                idx_Ts_completed = idx_Te_completed
                idx_Te_completed = np.argmin(np.abs(completed[:, 0] - peg_mp_dict[color][i][-1]))
            
            interval.append([idx_Ts_completed, idx_Te_completed])
    
        return interval

    def get_MP_index_interval_robot(self, peg_mp_dict, robot, color):
        interval = []
        
        for i in range(len(peg_mp_dict[color])):
            if i == 0:
                idx_Ts_robot = np.argmin(np.abs(robot[:, 0] - peg_mp_dict[color][i][-2]))
                idx_Te_robot = np.argmin(np.abs(robot[:, 0] - peg_mp_dict[color][i][-1]))
            else:
                idx_Ts_robot = idx_Te_robot
                idx_Te_robot = np.argmin(np.abs(robot[:, 0] - peg_mp_dict[color][i][-1]))
            interval.append([idx_Ts_robot, idx_Te_robot])
    
        return interval

    def get_robot_grasper_commands(self, command_data):
        Left_Commands = command_data[:, -2]
        Right_Commands = command_data[:, -1]
        Left = np.zeros(len(Left_Commands))
        Right = np.zeros(len(Right_Commands))

        for i in range(len(Left_Commands)):
            if Left_Commands[i] < -0.7:
                Left[i] = 1
            if Right_Commands[i] < -0.7:
                Right[i] = 1

        return Left, Right

    def remove_repeated_robot_data(self):
        robot_column = self.robot_data[:, 1]
        unique_values, counts= np.unique(robot_column, return_counts=True)
        repeated_values = unique_values[counts > 1]
        if len(repeated_values) != 0:
            mask = np.ones(len(robot_column), dtype=bool)
            for value in repeated_values:
                indices = np.where(robot_column == value)[0]
                mask[indices[:-1]] = False
            
            self.robot_data = self.robot_data[mask]

    def get_one_peg_kinematic_data_new(self, peg_mp_dict, color):
        Ts = peg_mp_dict[color][0][3]
        Te = peg_mp_dict[color][-1][-1]
        #print(f"Time start: {Ts}, Time end: {Te}.")

        idx_Ts_robot = np.argmin(np.abs(self.robot_data[:, 0] - Ts))
        idx_Te_robot = np.argmin(np.abs(self.robot_data[:, 0] - Te))
        robot = self.robot_data[idx_Ts_robot:idx_Te_robot+1, :]

        # idx_Ts_transformed = np.argmin(np.abs(self.transformed_data[:, 0] - Ts))
        # idx_Te_transformed = np.argmin(np.abs(self.transformed_data[:, 0] - Te))
        transformed = self.transformed_data[idx_Ts_robot:idx_Te_robot+1, :]

        idx_Ts_completed = np.argmin(np.abs(self.completed_data[:, 0] - Ts))
        idx_Te_completed = np.argmin(np.abs(self.completed_data[:, 0] - Te))
        completed = self.completed_data[idx_Ts_completed:idx_Te_completed+1, :]

        # print(f"robot length {len(robot)}: start {idx_Ts_robot}, end {idx_Te_robot}")
        # print(f"transformed length {len(transformed)}: start {idx_Ts_robot}, end {idx_Te_robot}")
        # print(len(completed))
        
        return robot, transformed, completed

    def align_console_kinematic_data_new(self, robot, transformed, completed):
        new_completed = np.zeros((len(robot), completed.shape[1]))
        r, c = new_completed.shape
        for i in range(r):
            e = np.argmin(np.abs(completed[:, 0] - robot[i, 0]))
            #e = np.where(completed[:, 1] == robot[i, 1])[0][0]
            new_completed[i, :] = completed[e, :] 
            pos0 = self.Tpos @ np.sum(completed[0:e+1, 2:5], axis=0) * self.sf_pos
            rot0 = self.Trot @ np.sum(completed[0:e+1, 5:8], axis=0) * self.sf_rot 
            pos1 = self.Tpos @ np.sum(completed[0:e+1, 8:11], axis=0) * self.sf_pos
            rot1 = self.Trot @ np.sum(completed[0:e+1, 11:14], axis=0) * self.sf_rot
            Ti = np.concatenate([pos0, rot0, pos1, rot1])
            new_completed[i, 2:14] = Ti
        #transformed[:, 2:14] = np.cumsum(transformed[:, 2:14], axis=0)
        #robot[:, 2:14] = robot[:, 2:14]
        
        # if len(robot) == len(transformed) == len(new_completed):
        #     print("robot, transformed, new_completed data has same length!")

        return robot, transformed, new_completed

    def get_loss_intervals(self, drop_list):
        intervals = []
        start = None
        for i, val in enumerate(drop_list):
            if val == 1 and start is None:
                start = i
            elif val == 0 and start is not None:
                intervals.append((start, i))
                start = None
        
        if start is not None:
            intervals.append((start, len(drop_list)))
        
        return intervals
        
    def get_one_peg_kinematic_data(self, peg_mp_dict, color):
        Ts = peg_mp_dict[color][0][1]
        Te = peg_mp_dict[color][-1][2]

        self.remove_repeated_robot_data()
        idx_Ts_robot = np.argmin(np.abs(self.robot_data[:, 0] - Ts))
        idx_Te_robot = np.argmin(np.abs(self.robot_data[:, 0] - Te))
        robot = self.robot_data[idx_Ts_robot:idx_Te_robot, :]

        unique_values, counts = np.unique(self.robot_data[:, 1], return_counts=True)
        repeated_values = unique_values[counts > 1]
        print("Repeated values Robot:", repeated_values)

        idx_Ts_transformed = np.where(self.transformed_data[:, 1] == robot[0, 1])[0][0]
        idx_Te_transformed = np.where(self.transformed_data[:, 1] == robot[-1, 1])[0][0]
        transformed = self.transformed_data[idx_Ts_transformed:idx_Te_transformed+1, :]

        unique_values, counts = np.unique(self.transformed_data[:, 1], return_counts=True)
        repeated_values = unique_values[counts > 1]
        print("Repeated values Transformed:", repeated_values)

        idx_Ts_completed = np.where(self.completed_data[:, 1] == robot[0, 1])[0][0]
        idx_Te_completed = np.where(self.completed_data[:, 1] == robot[-1, 1])[0][0]
        completed = self.completed_data[idx_Ts_completed:idx_Te_completed+1, :]

        if len(robot) == len(transformed):
            print("robot and transformed data has same length!")
        else:
            print("robot and transformed data doesn't have same length!")
            
            for i in range (len(robot[:, 1])):
                if robot[:, 1][i] != transformed[:, 1][i]:
                    print(robot[:, 1][i]) 
                    print(transformed[:, 1][i])
        return robot, transformed, completed
    
    def align_console_kinematic_data(self, robot, transformed, completed):
        new_completed = np.zeros((len(transformed), completed.shape[1]))
        r, c = new_completed.shape
        for i in range(r):
            e = np.where(completed[:, 1] == transformed[i, 1])[0][0]
            new_completed[i, :] = completed[e, :] 
            pos0 = self.Tpos @ np.sum(completed[0:e+1, 2:5], axis=0) * self.sf_pos
            rot0 = self.Trot @ np.sum(completed[0:e+1, 5:8], axis=0) * self.sf_rot 
            pos1 = self.Tpos @ np.sum(completed[0:e+1, 8:11], axis=0) * self.sf_pos
            rot1 = self.Trot @ np.sum(completed[0:e+1, 11:14], axis=0) * self.sf_rot
            Ti = np.concatenate([pos0, rot0, pos1, rot1])
            new_completed[i, 2:14] = Ti
        transformed[:, 2:14] = np.cumsum(transformed[:, 2:14], axis=0)
        robot[:, 2:14] = robot[:, 2:14] - robot[0, 2:14]
        
        if len(robot) == len(transformed) == len(new_completed):
            print("robot, transformed, new_completed data has same length!")

        return robot, transformed, new_completed
    
    def get_offset_coefficients(self, robot, transformed, arm):
        if arm == "left":
            scale_pos, offset_pos, RMSE_pos = get_offset_and_coefficient_pos(robot[:, 2:5], transformed[:, 2:5])
            scale_rot, offset_rot, RMSE_rot = get_offset_and_coefficient_rot(robot[:, 5:8], transformed[:, 5:8])
        else:
            scale_pos, offset_pos, RMSE_pos = get_offset_and_coefficient_pos(robot[:, 8:11],  transformed[:, 8:11])
            scale_rot, offset_rot, RMSE_rot = get_offset_and_coefficient_rot(robot[:, 11:14], transformed[:, 11:14])
        
        return [scale_pos, scale_rot], [offset_pos, offset_rot], [RMSE_pos, RMSE_rot]

    def plot_trjactory_pos(self, mp_intervals, robot, transformed, completed, scale, offset, arm):
        t = np.linspace(0, int(robot[-1, 0] - robot[0, 0]), len(robot))
        mp_intervals = mp_intervals - mp_intervals[0][0]
        colors = ['skyblue', 'lightgreen', 'yellow', 'orchid', '#FFD580']

        fig, axs = plt.subplots(4, 1, sharex=True, figsize=(12, 10), gridspec_kw={'height_ratios': [3, 3, 3, 1]})

        if arm == 'left':
            j = 2
        else: 
            j = 8

        for i, pos_label in enumerate(['X', 'Y', 'Z']):
            ri = robot[:, i+j]
            ti = transformed[:, i+j] * scale[0] + offset[0][i]
            ci = completed[:, i+j] * scale[0] + offset[0][i]
        
            ax = axs[i]
     
            for j, mp in enumerate(mp_intervals):
                if (mp[0] != mp[1]):
                    ax.axvspan(t[mp[0]], t[mp[1]-1], color=colors[j], alpha=0.3)

            ax.plot(t, ci, label='Complete Console Trajectory ' + pos_label, alpha=0.7, linewidth=2)
            ax.plot(t, ti, label='Emulated Console Trajectory ' + pos_label, alpha=0.7, linewidth=2)
            ax.plot(t, ri, label='Sim Robot Trajectory ' + pos_label, alpha=0.7, linewidth=2)
            ax.set_ylabel(f'{pos_label} (m)', fontsize=13)
            ax.tick_params(axis='both', labelsize=11)
            if pos_label == 'Z' or pos_label == 'Y':
                ax.legend(loc='upper right', prop={'size': 8})
            else:
                ax.legend(loc='lower right', prop={'size': 8})

        pi = completed[:, 16] * -1 + 1# Pedal signal
        ax_pedal = axs[3]
        # Pedal signal subplot
        for j, mp in enumerate(mp_intervals):
            if (mp[0] != mp[1]):
                ax_pedal.axvspan(t[mp[0]], t[mp[1]-1], color=colors[j % len(colors)], alpha=0.3)

        ax_pedal.plot(t, pi, label='Pedal Signal', color='red', alpha=0.6, linewidth=2)
        ax_pedal.set_xlabel('Time (s)', fontsize=14)
        ax_pedal.set_ylabel('Pedal', fontsize=14)
        ax_pedal.set_yticks([0, 1])
        ax_pedal.set_yticklabels(['Up', 'Down'])
        ax_pedal.tick_params(axis='both', labelsize=12)
        ax_pedal.legend(prop={'size': 8})

        #axs[-1].set_xlabel('Time (s)', fontsize=14)
        plt.suptitle(f'Position Trajectories with Pedal Signal')
        plt.tight_layout()
        plt.show()
    
    def plot_trjactory_rot(self, mp_intervals, robot, transformed, completed, scale, offset, arm):
        t = np.linspace(0, int(robot[-1, 0] - robot[0, 0]), len(robot))
        mp_intervals = mp_intervals - mp_intervals[0][0]
        colors = ['skyblue', 'lightgreen', 'yellow', 'orchid', '#FFD580']

        fig, axs = plt.subplots(4, 1, sharex=True, figsize=(12, 10), gridspec_kw={'height_ratios': [3, 3, 3, 1]})

        if arm == 'left':
            j = 5
        else: 
            j = 11


        for i, rot_label in enumerate(['X', 'Y', 'Z']):
            ri = robot[:, i+j]
            ti = transformed[:, i+j] * scale[1] + offset[1][i]
            ci = completed[:, i+j] * scale[1] + offset[1][i]
            
            ax = axs[i]

            for j, mp in enumerate(mp_intervals):
                if (mp[0] != mp[1]):
                    ax.axvspan(t[mp[0]], t[mp[1]-1], color=colors[j], alpha=0.3)
                
            ax.plot(t, ci, label='Complete Console Rotation ' + rot_label, alpha=0.7, linewidth=2)
            ax.plot(t, ti, label='Emulated Console Rotation ' + rot_label, alpha=0.7, linewidth=2)
            ax.plot(t, ri, label='Sim Robot Rotation ' + rot_label, alpha=0.7, linewidth=2)
            ax.set_ylabel(f'Rotation {rot_label} (rad)', fontsize=14)
            ax.tick_params(axis='both', labelsize=12)
            ax.legend(loc='lower right', prop={'size': 8})

        pi = completed[:, 16] * -1 + 1
        ax_pedal = axs[3]
        for j, mp in enumerate(mp_intervals):
            if (mp[0] != mp[1]):
                ax_pedal.axvspan(t[mp[0]], t[mp[1]-1], color=colors[j], alpha=0.3)

        ax_pedal.plot(t, pi, label='Pedal Signal', color='red', alpha=0.6, linewidth=2)
        ax_pedal.set_xlabel('Time (s)',fontsize=14)
        ax_pedal.set_ylabel('Pedal', fontsize=14)
        ax_pedal.set_yticks([0, 1])
        ax_pedal.set_yticklabels(['Up', 'Down'])
        ax_pedal.tick_params(axis='both', labelsize=12)
        ax_pedal.legend(loc='lower right', prop={'size': 8})

        plt.suptitle(f'Rotation Trajectories with Pedal Signal')
        plt.tight_layout()
        plt.show()



# if __name__ == "__main__":
#     path = "exp_data_new/no_fault/freefault1"
#     color = ['Red', 'Green', 'Blue', 'Magenta', 'Yellow', 'Cyan']
#     analyser_mp = AnalyserMP(path)
#     mp_dict = analyser_mp.get_MP_timestamp_error()
#     print("done")
#     for i in range(len(mp_dict)):
#         robot, transformed_delta, completed_delta = analyser_mp.get_one_peg_kinematic_data_new(mp_dict, color[i])
#         mp_intervals_robot = analyser_mp.get_MP_index_interval_robot(mp_dict, color[i])
#         robot, transformed, completed = analyser_mp.align_console_kinematic_data_new(robot, transformed_delta, completed_delta)
#         mp_intervals_completed = analyser_mp.get_MP_index_interval_completed(mp_dict, completed_delta, color[i])
#         if i < 3:
#             scale, offset, rmse = analyser_mp.get_offset_coefficients(robot, transformed, 'right')
#             print(scale)
#             analyser_mp.plot_trjactory_pos(mp_intervals_robot, robot, transformed, completed, scale, offset, 'right')
#             #analyser_mp.plot_trjactory_rot(mp_intervals_robot, robot, transformed, completed, scale, offset, 'right')
#         else:
#             scale, offset, rmse = analyser_mp.get_offset_coefficients(robot, transformed, 'left')
#             print(scale)
#             analyser_mp.plot_trjactory_pos(mp_intervals_robot, robot, transformed, completed, scale, offset, 'left')
#             #analyser_mp.plot_trjactory_rot(mp_intervals_robot, robot, transformed, completed, scale, offset, 'left')
