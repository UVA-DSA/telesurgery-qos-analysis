import os
import numpy as np
import pandas as pd
from analyser_mp import AnalyserMP

def get_system_error(peg, error_type):
    index = np.where(error_type == 'System Error')[0]
    peg_list = [peg[i] for i in index]
    return peg_list

def get_failure(peg, failure_type):
    index = np.where(pd.notna(failure_type))[0]
    peg_list = [peg[i] for i in index]
    return peg_list

def calculate_completion_time(start_frame, end_frame, verb, instrument, peg, pole, peg_list):
    Tframe = 1 / 60
    Tmp1, Tmp2, Tmp3, Tmp4, Tmp5, Tmp6, Tmp7, Tmp8, Tmp9 = 0, 0, 0, 0, 0, 0, 0, 0, 0
    l1, l2, l3, l4, l5, l6, l7, l8, l9 = [], [], [], [], [], [], [], [], []
    for i in range(len(verb)):
        time = (end_frame[i] - start_frame[i]) * Tframe
        if verb[i] == 'Touch' and instrument[i] == 'Right_grasper' and peg[i] not in peg_list: 
            Tmp1 += time
            if peg[i] not in l1:
                l1.append(peg[i])
        elif verb[i] == 'Grasp' and instrument[i] == 'Right_grasper' and peg[i] not in peg_list:
            Tmp2 += time
            if peg[i] not in l2:
                l2.append(peg[i])
        elif verb[i] == 'Untouch' and instrument[i] == 'Right_grasper' and isinstance(pole[i], str) and pole[i][-1] == 'S' and peg[i] not in peg_list:
            Tmp3 += time
            if peg[i] not in l3:
                l3.append(peg[i])
        elif verb[i] == 'Touch' and instrument[i] == 'Left_grasper' and not isinstance(pole[i], str) and peg[i] not in peg_list:
            Tmp4 += time
            if peg[i] not in l4:
                l4.append(peg[i])
        elif verb[i] == 'Grasp' and instrument[i] == 'Left_grasper' and peg[i] not in peg_list:
            Tmp5 += time
            if peg[i] not in l5:
                l5.append(peg[i])
        elif verb[i] == 'Release' and instrument[i] == 'Right_grasper' and peg[i] not in peg_list:
            Tmp6 += time
            if peg[i] not in l6:
                l6.append(peg[i])
        elif verb[i] == 'Untouch' and instrument[i] == 'Right_grasper' and peg[i] not in peg_list:
            Tmp7 += time
            if peg[i] not in l7:
                l7.append(peg[i])
        elif verb[i] == 'Touch' and instrument[i] == 'Left_grasper' and isinstance(pole[i], str) and pole[i][-1] == 'G' and peg[i] not in peg_list:
            Tmp8 += time
            if peg[i] not in l8:
                l8.append(peg[i])
        elif verb[i] == 'Release' and instrument[i] == 'Left_grasper' and peg[i] not in peg_list:
            Tmp9 += time
            if peg[i] not in l9:
                l9.append(peg[i])
    n1, n2, n3, n4, n5, n6, n7, n8, n9 = len(l1), len(l2), len(l3), len(l4), len(l5), len(l6), len(l7), len(l8), len(l9)

    return [round(Tmp1/n1, 3), round(Tmp2/n2, 3), round(Tmp3/n3, 3), round(Tmp4/n4, 3), round(Tmp5/n5, 3), 
            round(Tmp6/n6, 3), round(Tmp7/n7, 3), round(Tmp8/n8, 3), round(Tmp9/n9, 3)]

def transfer_completion_time(start_frame, end_frame, peg, peg_list1, peg_list2):
    Tframe = 1 / 60
    peg_list = peg_list1 + peg_list2
    Tred, Tgreen, Tblue, Tcyan, Tyellow, Tmagenta = 0, 0, 0, 0, 0, 0
    n = 6 - len(peg_list)
    for i in range(len(peg)):
        time = (end_frame[i] - start_frame[i]) * Tframe
        if peg[i] == 'Red' and peg[i] not in peg_list:
            Tred += time
        elif peg[i] == 'Green' and peg[i] not in peg_list:
            Tgreen += time
        elif peg[i] == 'Blue' and peg[i] not in peg_list:
            Tblue += time
        elif peg[i] == 'Cyan' and peg[i] not in peg_list:
            Tcyan += time
        elif peg[i] == 'Yellow' and peg[i] not in peg_list:
            Tyellow += time
        elif peg[i] == 'Magenta' and peg[i] not in peg_list:
            Tmagenta += time
    avg_time = round((Tred + Tgreen + Tblue + Tcyan + Tyellow + Tmagenta) / n, 3)
    return avg_time

def generate_completion_time_csv(time_array, all_mps, net_conditions, csv_path):
    df = pd.DataFrame(time_array, columns=all_mps[1:], index=net_conditions)
    output_file = os.path.join(csv_path, "completion_time_analysis.csv")
    df.to_csv(output_file, index_label='Net Conditions')
    print(f"CSV file '{output_file}' has been generated successfully!")
   

if __name__ == "__main__":
    root_address = "exp_data"
    netfolders = ['no_fault', 'packet_loss', 'delay', 'communication_loss']
    all_mps = ['Net Conditions', 'Entire Transfer', 'Touch(Right_grasper, Peg)', 'Grasp(Right_grasper, Peg)', 'Untouch(Right_grasper, Peg, Pole_S)',
               'Touch(Left_grasper, Peg)',  'Grasp(Left_grasper, Peg)',   'Release(Right_grasper, Peg)', 
               'Untouch(Right_grasper, Peg)', 'Touch(Left_grasper, Peg, Pole_G)', 'Release(Left_grasper, Peg)']
    net_conditions = ['Normal-1',  'Normal-2',  'Normal-3',
                      'PLM-10',  'PLM-30',  'PLM-50', 
                      'DLM-100', 'DLM-300', 'DLM-500', 
                      'CLM-10',  'CLM-30',  'CLM-50']
    
    for subject in os.listdir(root_address):
        subject_path = os.path.join(root_address, subject)
        time_list = []
        transfer = []
        for folder in netfolders:
            path = os.path.join(subject_path, folder)
            for sub_folder in os.listdir(path): 
                print(f"Processing folder: {sub_folder}")
                sub_path = os.path.join(path, sub_folder)
                analyser_mp = AnalyserMP(sub_path)
                info_list = analyser_mp.get_MP_info() 
                peg_list1 = get_system_error(info_list[4], info_list[6])
                peg_list2 = get_failure(info_list[4], info_list[7])
                time = calculate_completion_time(info_list[0], info_list[1], info_list[2], info_list[3], info_list[4], info_list[5], peg_list1)
                transfer_time = transfer_completion_time(info_list[0], info_list[1], info_list[4], peg_list1, peg_list2)
                time_list.append(time)
                transfer.append(transfer_time)
        time_array = np.array(time_list)
        transfer_array = np.array(transfer)
        
        time_array = np.column_stack((transfer_array, time_array))

        csv_path = os.path.join(subject_path, "statistics")
        if not os.path.exists(csv_path):
            os.makedirs(csv_path)
        generate_completion_time_csv(time_array, all_mps, net_conditions, csv_path)