import os
import numpy as np
import pandas as pd
from analyser_mp import AnalyserMP

pos_scale = 0.00001
Tframe = 1 / 60

def get_system_error(peg, error_type):
    index = np.where(error_type == 'System Error')[0]
    peg_list = [peg[i] for i in index]
    return peg_list

def get_failure(peg, failure_type):
    index = np.where(pd.notna(failure_type))[0]
    peg_list = [peg[i] for i in index]
    return peg_list

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


def calculate_motion_length(Tinitial, completed_data, robot_data, start_frame, end_frame, verb, instrument, peg, pole, peg_list):
    len1_c, len2_c, len3_c, len4_c, len5_c, len6_c, len7_c, len8_c, len9_c = 0, 0, 0, 0, 0, 0, 0, 0, 0
    len1_r, len2_r, len3_r, len4_r, len5_r, len6_r, len7_r, len8_r, len9_r = 0, 0, 0, 0, 0, 0, 0, 0, 0
    l1, l2, l3, l4, l5, l6, l7, l8, l9 = [], [], [], [], [], [], [], [], []
    for i in range(len(verb)):
        start_timestamp = Tinitial + start_frame[i] * Tframe
        end_timestamp = Tinitial + end_frame[i] * Tframe
        completed, robot = get_mp_data(completed_data, robot_data, start_timestamp, end_timestamp)

        motion_length_console_left = get_motion_length_console_left(completed)
        motion_length_console_right = get_motion_length_console_right(completed)
        motion_length_console = motion_length_console_left + motion_length_console_right

        motion_length_robot_left = get_motion_length_robot_left(robot)
        motion_length_robot_right = get_motion_length_robot_right(robot)    
        motion_length_robot = motion_length_robot_left + motion_length_robot_right

        if verb[i] == 'Touch' and instrument[i] == 'Right_grasper' and peg[i] not in peg_list:
            len1_c += motion_length_console
            len1_r += motion_length_robot
            if peg[i] not in l1:
                l1.append(peg[i])
        elif verb[i] == 'Grasp' and instrument[i] == 'Right_grasper' and peg[i] not in peg_list:
            len2_c += motion_length_console
            len2_r += motion_length_robot
            if peg[i] not in l2:
                l2.append(peg[i])
        elif verb[i] == 'Untouch' and instrument[i] == 'Right_grasper' and isinstance(pole[i], str) and pole[i][-1] == 'S' and peg[i] not in peg_list:
            len3_c += motion_length_console
            len3_r += motion_length_robot
            if peg[i] not in l3:
                l3.append(peg[i])
        elif verb[i] == 'Touch' and instrument[i] == 'Left_grasper' and not isinstance(pole[i], str) and peg[i] not in peg_list:
            len4_c += motion_length_console
            len4_r += motion_length_robot
            if peg[i] not in l4:
                l4.append(peg[i])
        elif verb[i] == 'Grasp' and instrument[i] == 'Left_grasper' and peg[i] not in peg_list:
            len5_c += motion_length_console
            len5_r += motion_length_robot
            if peg[i] not in l5:
                l5.append(peg[i])
        elif verb[i] == 'Release' and instrument[i] == 'Right_grasper' and peg[i] not in peg_list:
            len6_c += motion_length_console
            len6_r += motion_length_robot
            if peg[i] not in l6:
                l6.append(peg[i])
        elif verb[i] == 'Untouch' and instrument[i] == 'Right_grasper' and peg[i] not in peg_list:
            len7_c += motion_length_console
            len7_r += motion_length_robot
            if peg[i] not in l7:
                l7.append(peg[i])
        elif verb[i] == 'Touch' and instrument[i] == 'Left_grasper' and isinstance(pole[i], str) and pole[i][-1] == 'G' and peg[i] not in peg_list:
            len8_c += motion_length_console
            len8_r += motion_length_robot
            if peg[i] not in l8:
                l8.append(peg[i])
        elif verb[i] == 'Release' and instrument[i] == 'Left_grasper' and peg[i] not in peg_list:
            len9_c += motion_length_console
            len9_r += motion_length_robot
            if peg[i] not in l9:
                l9.append(peg[i])

    n1, n2, n3, n4, n5, n6, n7, n8, n9 = len(l1), len(l2), len(l3), len(l4), len(l5), len(l6), len(l7), len(l8), len(l9)

    return [round(len1_c/n1, 3), round(len2_c/n2, 3), round(len3_c/n3, 3), round(len4_c/n4, 3), round(len5_c/n5, 3), 
            round(len6_c/n6, 3), round(len7_c/n7, 3), round(len8_c/n8, 3), round(len9_c/n9, 3)], [round(len1_r/n1, 3), round(len2_r/n2, 3), 
            round(len3_r/n3, 3), round(len4_r/n4, 3), round(len5_r/n5, 3), round(len6_r/n6, 3), round(len7_r/n7, 3), round(len8_r/n8, 3), round(len9_r/n9, 3)]

def motion_length_transfer(Tinitial, completed_data, robot_data, start_frame, end_frame, peg, peg_list):
    red_r, green_r, blue_r, cyan_r, yellow_r, magenta_r = 0, 0, 0, 0, 0, 0
    red_c, green_c, blue_c, cyan_c, yellow_c, magenta_c = 0, 0, 0, 0, 0, 0
    n = 6 - len(peg_list)
    for i in range(len(peg)):
        start_timestamp = Tinitial + start_frame[i] * Tframe
        end_timestamp = Tinitial + end_frame[i] * Tframe
        completed, robot = get_mp_data(completed_data, robot_data, start_timestamp, end_timestamp)

        motion_length_console_left = get_motion_length_console_left(completed)
        motion_length_console_right = get_motion_length_console_right(completed)
        motion_length_console = motion_length_console_left + motion_length_console_right

        motion_length_robot_left = get_motion_length_robot_left(robot)
        motion_length_robot_right = get_motion_length_robot_right(robot)    
        motion_length_robot = motion_length_robot_left + motion_length_robot_right

        if peg[i] == 'Red' and peg[i] not in peg_list:
            red_c += motion_length_console
            red_r += motion_length_robot
        elif peg[i] == 'Green' and peg[i] not in peg_list:
            green_c += motion_length_console
            green_r += motion_length_robot
        elif peg[i] == 'Blue' and peg[i] not in peg_list:
            blue_c += motion_length_console
            blue_r += motion_length_robot
        elif peg[i] == 'Cyan' and peg[i] not in peg_list:
            cyan_c += motion_length_console
            cyan_r += motion_length_robot
        elif peg[i] == 'Yellow' and peg[i] not in peg_list:
            yellow_c += motion_length_console
            yellow_r += motion_length_robot
        elif peg[i] == 'Magenta' and peg[i] not in peg_list:
            magenta_c += motion_length_console
            magenta_r += motion_length_robot

    avg_motion_length_console = round((red_c + green_c + blue_c + cyan_c + yellow_c + magenta_c) / n, 3)
    avg_motion_length_robot = round((red_r + green_r + blue_r + cyan_r + yellow_r + magenta_r) / n, 3)
    
    return avg_motion_length_console, avg_motion_length_robot

def generate_motion_length_csv(motion_length_list, all_mps, net_conditions, csv_path):
    console_data = [item[0] for item in motion_length_list]
    robot_data = [item[1] for item in motion_length_list]

    console_array = np.array(console_data)
    robot_array = np.array(robot_data)
    
    column_headers = all_mps[1:]
    
    df_console = pd.DataFrame(console_array, 
                             index=net_conditions, 
                             columns=column_headers)
    
    df_robot = pd.DataFrame(robot_array, 
                           index=net_conditions, 
                           columns=column_headers)

    console_output_file = os.path.join(csv_path, "motion_length_console_analysis.csv")
    robot_output_file = os.path.join(csv_path, "motion_length_robot_analysis.csv")

    df_console.to_csv(console_output_file, index_label='Net Conditions')
    df_robot.to_csv(robot_output_file, index_label='Net Conditions')
    
    print(f"Console CSV file '{console_output_file}' has been generated successfully!")
    print(f"Robot CSV file '{robot_output_file}' has been generated successfully!")

if __name__ == "__main__":
    root_address = "exp_data"
    netfolders = ['no_fault', 'packet_loss', 'delay', 'communication_loss']
    all_mps = ['Net Conditions', 'Transfer', 'Touch(Right_grasper, Peg)', 'Grasp(Right_grasper, Peg)', 'Untouch(Right_grasper, Peg, Pole_S)',
               'Touch(Left_grasper, Peg)',  'Grasp(Left_grasper, Peg)',   'Release(Right_grasper, Peg)', 
               'Untouch(Right_grasper, Peg)', 'Touch(Left_grasper, Peg, Pole_G)', 'Release(Left_grasper, Peg)']
    net_conditions = ['Normal-1',  'Normal-2',  'Normal-3',
                      'PLM-10',  'PLM-30',  'PLM-50', 
                      'DLM-100', 'DLM-300', 'DLM-500', 
                      'CLM-10',  'CLM-30',  'CLM-50']
    
    for subject in os.listdir(root_address):
        subject_path = os.path.join(root_address, subject)
        motion_length_list = []
        transfer_list = []
        for folder in netfolders:
            path = os.path.join(subject_path, folder)
            for sub_folder in os.listdir(path): 
                print(f"Processing folder: {sub_folder}")
                sub_path = os.path.join(path, sub_folder)
                analyser = AnalyserMP(sub_path)
                info_list = analyser.get_MP_info()
                peg_list1 = get_system_error(info_list[4], info_list[6])
                peg_list2 = get_failure(info_list[4], info_list[7])
                peg_list = peg_list1 + peg_list2
                motion_length_console, motion_length_robot = calculate_motion_length(analyser.Tinitial, analyser.completed_data, analyser.robot_data,  
                                                                                     info_list[0], info_list[1], info_list[2], info_list[3], info_list[4], info_list[5], peg_list)
                transfer_console, transfer_robot = motion_length_transfer(analyser.Tinitial, analyser.completed_data, analyser.robot_data,  
                                                                          info_list[0], info_list[1], info_list[4], peg_list)
                motion_length_list.append([motion_length_console, motion_length_robot])
                transfer_list.append([transfer_console, transfer_robot])

        motion_length_array = np.array(motion_length_list)
        transfer_array = np.array(transfer_list)

        transfer_array_expanded = np.expand_dims(transfer_array, axis=2)
        combined_array = np.concatenate([transfer_array_expanded, motion_length_array], axis=2)
        
        csv_path = os.path.join(subject_path, "statistics")
        if not os.path.exists(csv_path):
            os.makedirs(csv_path)
        generate_motion_length_csv(combined_array, all_mps, net_conditions, csv_path)

