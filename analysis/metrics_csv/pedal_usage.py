import os
import numpy as np
import pandas as pd
from analyser_mp import AnalyserMP
from motion_length import get_mp_data

Tframe = 1 / 60

def get_system_error(peg, error_type):
    index = np.where(error_type == 'System Error')[0]
    peg_list = [peg[i] for i in index]
    return peg_list

def get_failure(peg, failure_type):
    index = np.where(pd.notna(failure_type))[0]
    peg_list = [peg[i] for i in index]
    return peg_list

def get_pedal_usage(completed):
    pedal_data = completed[:, 16]
    diff = np.diff(pedal_data)
    starts = np.where(diff == -1)[0]
    return len(starts)

def calculate_pedal_usage(Tinitial, completed_data, robot_data, start_frame, end_frame, verb, instrument, peg, pole, peg_list):
    n1, n2, n3, n4, n5, n6, n7, n8, n9, n10 = 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    for i in range(len(verb)):
        start_timestamp = Tinitial + start_frame[i] * Tframe
        end_timestamp = Tinitial + end_frame[i] * Tframe
        completed, _ = get_mp_data(completed_data, robot_data, start_timestamp, end_timestamp)
        usage = get_pedal_usage(completed)
        if verb[i] == 'Touch' and instrument[i] == 'Right_grasper' and peg[i] not in peg_list:
            n1 += usage
        elif verb[i] == 'Grasp' and instrument[i] == 'Right_grasper' and peg[i] not in peg_list:
            n2 += usage
        elif verb[i] == 'Untouch' and instrument[i] == 'Right_grasper' and isinstance(pole[i], str) and pole[i][-1] == 'S' and peg[i] not in peg_list:
            n3 += usage
        elif verb[i] == 'Touch' and instrument[i] == 'Left_grasper' and not isinstance(pole[i], str) and peg[i] not in peg_list:
            n4 += usage
        elif verb[i] == 'Grasp' and instrument[i] == 'Left_grasper' and peg[i] not in peg_list:
            n5 += usage
        elif verb[i] == 'Release' and instrument[i] == 'Right_grasper' and peg[i] not in peg_list:
            n6 += usage
        elif verb[i] == 'Untouch' and instrument[i] == 'Right_grasper' and peg[i] not in peg_list:
            n7 += usage
        elif verb[i] == 'Touch' and instrument[i] == 'Left_grasper' and isinstance(pole[i], str) and pole[i][-1] == 'G' and peg[i] not in peg_list:
            n8 += usage
        elif verb[i] == 'Release' and instrument[i] == 'Left_grasper' and peg[i] not in peg_list:
            n9 += usage
        else:
            n10 += usage
    
    return [round(n1, 0), round(n2, 0), round(n3, 0), round(n4, 0), round(n5, 0),
            round(n6, 0), round(n7, 0), round(n8, 0), round(n9, 0)]

def transfer_pedal_usage(Tinitial, completed_data, robot_data, start_frame, end_frame, peg, peg_list):
    red, green, blue, cyan, yellow, magenta = 0, 0, 0, 0, 0, 0
    n = 6 - len(peg_list)

    for i in range(len(peg)):
        start_timestamp = Tinitial + start_frame[i] * Tframe
        end_timestamp = Tinitial + end_frame[i] * Tframe
        completed, _ = get_mp_data(completed_data, robot_data, start_timestamp, end_timestamp)
        usage = get_pedal_usage(completed)
        if peg[i] == 'Red' and peg[i] not in peg_list:
            red += usage
        elif peg[i] == 'Green' and peg[i] not in peg_list:
            green += usage
        elif peg[i] == 'Blue' and peg[i] not in peg_list:
            blue += usage
        elif peg[i] == 'Cyan' and peg[i] not in peg_list:
            cyan += usage
        elif peg[i] == 'Yellow' and peg[i] not in peg_list:
            yellow += usage
        elif peg[i] == 'Magenta' and peg[i] not in peg_list:
            magenta += usage

    sum_usage = red + green + blue + cyan + yellow + magenta

    return sum_usage

def generate_pedal_usage_csv(pedal_list, all_mps, net_conditions, csv_path):
    pedal_array = np.array(pedal_list)
    column_headers = all_mps[1:]
    df_pedal = pd.DataFrame(pedal_array, 
                           index=net_conditions, 
                           columns=column_headers)
    pedal_output_file = os.path.join(csv_path, "pedal_usage_analysis.csv")
    df_pedal.to_csv(pedal_output_file, index_label='Net Conditions')
    print(f"Pedal usage CSV file '{pedal_output_file}' has been generated successfully!")
  
if __name__ == "__main__":
    root_address = "exp_data"
    netfolders = ['no_fault', 'packet_loss', 'delay', 'communication_loss']
    all_mps = ['Net Conditions', 'Trial', 'Touch(Right_grasper, Peg)', 'Grasp(Right_grasper, Peg)', 'Untouch(Right_grasper, Peg, Pole_S)',
               'Touch(Left_grasper, Peg)',  'Grasp(Left_grasper, Peg)',   'Release(Right_grasper, Peg)', 
               'Untouch(Right_grasper, Peg)', 'Touch(Left_grasper, Peg, Pole_G)', 'Release(Left_grasper, Peg)']
    net_conditions = ['Normal-1',  'Normal-2',  'Normal-3',
                      'PLM-10',  'PLM-30',  'PLM-50', 
                      'DLM-100', 'DLM-300', 'DLM-500', 
                      'CLM-10',  'CLM-30',  'CLM-50']
    
    for subject in os.listdir(root_address):
        subject_path = os.path.join(root_address, subject)
        pedal_list = []
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
                pedal = calculate_pedal_usage(analyser.Tinitial, analyser.completed_data, analyser.robot_data,  
                                        info_list[0], info_list[1], info_list[2], info_list[3], info_list[4], info_list[5], peg_list)
                transfer = transfer_pedal_usage(analyser.Tinitial, analyser.completed_data, analyser.robot_data, 
                                        info_list[0], info_list[1], info_list[4], peg_list)
                pedal_list.append(pedal)
                transfer_list.append(transfer)

        pedal_array = np.array(pedal_list)
        transfer_array = np.array(transfer_list)
        new_array = np.column_stack((transfer_array, pedal_array))

        csv_path = os.path.join(subject_path, "statistics")
        if not os.path.exists(csv_path):
            os.makedirs(csv_path)
        generate_pedal_usage_csv(new_array, all_mps, net_conditions, csv_path)