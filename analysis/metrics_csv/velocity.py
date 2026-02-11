import os
import numpy as np
import pandas as pd
from analyser_mp import AnalyserMP

pos_scale = 0.00001

def get_motion_length_console_left(completed):
    motion_len = 0
    for i in range(len(completed)):
        motion_len += np.sqrt(completed[i][2]**2 + completed[i][3]**2 + completed[i][4]**2) * pos_scale
    return motion_len

def get_motion_length_console_right(completed):
    motion_len = 0
    for i in range(len(completed)):
        motion_len += np.sqrt(completed[i][8]**2 + completed[i][9]**2 + completed[i][10]**2) * pos_scale
    return motion_len

def get_motion_length_robot_left(robot):
    motion_len = 0
    for i in range(len(robot)):
        motion_len += np.sqrt(robot[i][0]**2 + robot[i][1]**2 + robot[i][2]**2)
    return motion_len

def get_motion_length_robot_right(robot):
    motion_len = 0
    for i in range(len(robot)):
        motion_len += np.sqrt(robot[i][6]**2 + robot[i][7]**2 + robot[i][8]**2)
    return motion_len

def get_mp_data(completed_data, robot_data, start_timestamp, end_timestamp):
    idx_Ts_robot = np.argmin(np.abs(robot_data[:, 0] - start_timestamp))
    idx_Te_robot = np.argmin(np.abs(robot_data[:, 0] - end_timestamp))
    robot = robot_data[idx_Ts_robot:idx_Te_robot+1, :]

    idx_Ts_completed = np.argmin(np.abs(completed_data[:, 0] - start_timestamp))
    idx_Te_completed = np.argmin(np.abs(completed_data[:, 0] - end_timestamp))
    completed = completed_data[idx_Ts_completed:idx_Te_completed+1, :]

    return completed,  np.diff(robot[:, 2:], axis=0)


def calculate_velocity(Tinitial, completed_data, robot_data, start_frame, end_frame, verb, instrument, pole):
    Tframe = 1 / 60
    vel1_c, vel2_c, vel3_c, vel4_c, vel5_c, vel6_c, vel7_c, vel8_c, vel9_c = 0, 0, 0, 0, 0, 0, 0, 0, 0
    vel1_r, vel2_r, vel3_r, vel4_r, vel5_r, vel6_r, vel7_r, vel8_r, vel9_r = 0, 0, 0, 0, 0, 0, 0, 0, 0
    n1, n2, n3, n4, n5, n6, n7, n8, n9 = 0, 0, 0, 0, 0, 0, 0, 0, 0
    for i in range(len(verb)):
        start_timestamp = Tinitial + start_frame[i] * Tframe
        end_timestamp = Tinitial + end_frame[i] * Tframe
        time_interval = end_timestamp - start_timestamp 
        completed, robot = get_mp_data(completed_data, robot_data, start_timestamp, end_timestamp)

        motion_length_console_left = get_motion_length_console_left(completed)
        motion_length_console_right = get_motion_length_console_right(completed)
        velocity_console = (motion_length_console_left + motion_length_console_right) / time_interval

        motion_length_robot_left = get_motion_length_robot_left(robot)
        motion_length_robot_right = get_motion_length_robot_right(robot)    
        velocity_robot = (motion_length_robot_left + motion_length_robot_right) / time_interval

        if verb[i] == 'Touch' and instrument[i] == 'Right_grasper': 
            vel1_c += velocity_console
            vel1_r += velocity_robot
            n1 += 1
        elif verb[i] == 'Grasp' and instrument[i] == 'Right_grasper':
            vel2_c += velocity_console
            vel2_r += velocity_robot
            n2 += 1
        elif verb[i] == 'Untouch' and instrument[i] == 'Right_grasper' and isinstance(pole[i], str) and pole[i][-1] == 'S':
            vel3_c += velocity_console
            vel3_r += velocity_robot
            n3 += 1
        elif verb[i] == 'Touch' and instrument[i] == 'Left_grasper' and not isinstance(pole[i], str):
            vel4_c += velocity_console
            vel4_r += velocity_robot
            n4 += 1
        elif verb[i] == 'Grasp' and instrument[i] == 'Left_grasper':
            vel5_c += velocity_console
            vel5_r += velocity_robot
            n5 += 1
        elif verb[i] == 'Release' and instrument[i] == 'Right_grasper':
            vel6_c += velocity_console
            vel6_r += velocity_robot
            n6 += 1
        elif verb[i] == 'Untouch' and instrument[i] == 'Right_grasper':
            vel7_c += velocity_console
            vel7_r += velocity_robot
            n7 += 1
        elif verb[i] == 'Touch' and instrument[i] == 'Left_grasper' and isinstance(pole[i], str) and pole[i][-1] == 'G':
            vel8_c += velocity_console
            vel8_r += velocity_robot
            n8 += 1
        elif verb[i] == 'Release' and instrument[i] == 'Left_grasper':
            vel9_c += velocity_console
            vel9_r += velocity_robot
            n9 += 1

    return [round(vel1_c/n1, 3), round(vel2_c/n2, 3), round(vel3_c/n3, 3), 
            round(vel4_c/n4, 3), round(vel5_c/n5, 3), round(vel6_c/n6, 3), 
            round(vel7_c/n7, 3), round(vel8_c/n8, 3), round(vel9_c/n9, 3)], [round(vel1_r/n1, 3), 
            round(vel2_r/n2, 3), round(vel3_r/n3, 3), round(vel4_r/n4, 3), round(vel5_r/n5, 3), 
            round(vel6_r/n6, 3), round(vel7_r/n7, 3), round(vel8_r/n8, 3), round(vel9_r/n9, 3)]

def generate_velocity_csv(velocity_list, all_mps, net_conditions, csv_path):
    console_data = [item[0] for item in velocity_list]
    robot_data = [item[1] for item in velocity_list]

    console_array = np.array(console_data)
    robot_array = np.array(robot_data)
    
    column_headers = all_mps[1:]
    
    df_console = pd.DataFrame(console_array, 
                             index=net_conditions, 
                             columns=column_headers)
    
    df_robot = pd.DataFrame(robot_array, 
                           index=net_conditions, 
                           columns=column_headers)

    console_output_file = os.path.join(csv_path, "velocity_console_analysis.csv")
    robot_output_file = os.path.join(csv_path, "velocity_robot_analysis.csv")

    df_console.to_csv(console_output_file, index_label='Net Conditions')
    df_robot.to_csv(robot_output_file, index_label='Net Conditions')
    
    print(f"Console CSV file '{console_output_file}' has been generated successfully!")
    print(f"Robot CSV file '{robot_output_file}' has been generated successfully!")

if __name__ == "__main__":
    root_address = "exp_data/exp_data_2"
    netfolders = ['no_fault', 'packet_loss', 'delay', 'communication_loss']
    all_mps = ['Net Conditions', 'Touch(Right_grasper, Peg)', 'Grasp(Right_grasper, Peg)', 'Untouch(Right_grasper, Peg, Pole_S)',
               'Touch(Left_grasper, Peg)',  'Grasp(Left_grasper, Peg)',   'Release(Right_grasper, Peg)', 
               'Untouch(Right_grasper, Peg)', 'Touch(Left_grasper, Peg, Pole_G)', 'Release(Left_grasper, Peg)']
    net_conditions = ['Normal-1',  'Normal-2',  'Normal-3',
                      'PLM-10',  'PLM-30',  'PLM-50', 
                      'DLM-100', 'DLM-300', 'DLM-500', 
                      'CLM-10',  'CLM-30',  'CLM-50']
    velocity_list = []
    for folder in netfolders:
        path = os.path.join(root_address, folder)
        for sub_folder in os.listdir(path): 
            print(f"Processing folder: {sub_folder}")
            sub_path = os.path.join(path, sub_folder)
            analyser = AnalyserMP(sub_path)
            info_list = analyser.get_MP_info()
            velocity_console, velocity_robot = calculate_velocity(analyser.Tinitial, analyser.completed_data, analyser.robot_data,  
                                                                                info_list[0], info_list[1], info_list[2], info_list[3], info_list[5])
            velocity_list.append([velocity_console, velocity_robot])

    csv_path = os.path.join(root_address, "statistics")
    if not os.path.exists(csv_path):
        os.makedirs(csv_path)
    generate_velocity_csv(velocity_list, all_mps, net_conditions, csv_path)