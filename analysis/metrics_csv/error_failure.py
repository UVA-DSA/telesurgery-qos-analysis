import os
import numpy as np
import pandas as pd
from analyser_mp import AnalyserMP

def calculate_error_failure(verb, instrument, pole, error, failure):
    e1, e2, e3, e4, e5, e6, e7, e8, e9 = [], [], [], [], [], [], [], [], []
    f1, f2, f3, f4, f5, f6, f7, f8, f9 = [], [], [], [], [], [], [], [], []
    for i in range(len(verb)):
        if verb[i] == 'Touch' and instrument[i] == 'Right_grasper':
            if error[i] != 'NO_ERROR':
                e1.append(error[i])
            if str(failure[i]) != 'nan':
                f1.append(failure[i])
        elif verb[i] == 'Grasp' and instrument[i] == 'Right_grasper':
            if error[i] != 'NO_ERROR':
                e2.append(error[i])
            if str(failure[i]) != 'nan':
                f2.append(failure[i])
        elif verb[i] == 'Untouch' and instrument[i] == 'Right_grasper' and isinstance(pole[i], str) and pole[i][-1] == 'S':
            if error[i] != 'NO_ERROR':
                e3.append(error[i])
            if str(failure[i]) != 'nan':
                f3.append(failure[i])
        elif verb[i] == 'Touch' and instrument[i] == 'Left_grasper' and not isinstance(pole[i], str):
            if error[i] != 'NO_ERROR':
                e4.append(error[i])
            if str(failure[i]) != 'nan':
                f4.append(failure[i])
        elif verb[i] == 'Grasp' and instrument[i] == 'Left_grasper':
            if error[i] != 'NO_ERROR':
                e5.append(error[i])
            if str(failure[i]) != 'nan':
                f5.append(failure[i])
        elif verb[i] == 'Release' and instrument[i] == 'Right_grasper':
            if error[i] != 'NO_ERROR':
                e6.append(error[i])
            if str(failure[i]) != 'nan':
                f6.append(failure[i])
        elif verb[i] == 'Untouch' and instrument[i] == 'Right_grasper':
            if error[i] != 'NO_ERROR':
                e7.append(error[i])
            if str(failure[i]) != 'nan':
                f7.append(failure[i])
        elif verb[i] == 'Touch' and instrument[i] == 'Left_grasper' and isinstance(pole[i], str) and pole[i][-1] == 'G':
            if error[i] != 'NO_ERROR':
                e8.append(error[i])
            if str(failure[i]) != 'nan':
                f8.append(failure[i])
        elif verb[i] == 'Release' and instrument[i] == 'Left_grasper':
            if error[i] != 'NO_ERROR':
                e9.append(error[i])
            if str(failure[i]) != 'nan':
                f9.append(failure[i])
    return [e1, e2, e3, e4, e5, e6, e7, e8, e9], [f1, f2, f3, f4, f5, f6, f7, f8, f9]
# Convert string lists to comma-separated strings for CSV
def format_string_lists(data_list):
    formatted_data = []
    for experiment in data_list:
        experiment_formatted = []
        for mp_strings in experiment:  # mp_strings is a list of strings for one MP
            if len(mp_strings) > 0:
                # Convert all items to strings and filter out NaN values
                string_items = [str(item) for item in mp_strings if str(item) != 'nan']
                if len(string_items) > 0:
                    experiment_formatted.append(','.join(string_items))
                else:
                    experiment_formatted.append('')
            else:
                experiment_formatted.append('')
        formatted_data.append(experiment_formatted)
    return formatted_data

def generate_error_failure_csv(error_data, failure_data, all_mps, net_conditions, csv_path):
    error_formatted = format_string_lists(error_data)
    failure_formatted = format_string_lists(failure_data)
    
    column_headers = all_mps[1:]
    
    df_error = pd.DataFrame(error_formatted, 
                           index=net_conditions, 
                           columns=column_headers)
    
    df_failure = pd.DataFrame(failure_formatted, 
                             index=net_conditions, 
                             columns=column_headers)

    error_output_file = os.path.join(csv_path, "error_analysis.csv")
    failure_output_file = os.path.join(csv_path, "failure_analysis.csv")

    df_error.to_csv(error_output_file, index_label='Net Conditions')
    df_failure.to_csv(failure_output_file, index_label='Net Conditions')
    
    print(f"Error CSV file '{error_output_file}' has been generated successfully!")
    print(f"Failure CSV file '{failure_output_file}' has been generated successfully!")

if __name__ == "__main__":
    root_address = "exp_data"
    netfolders = ['no_fault', 'packet_loss', 'delay', 'communication_loss']
    all_mps = ['Net Conditions', 'Touch(Right_grasper, Peg)', 'Grasp(Right_grasper, Peg)', 'Untouch(Right_grasper, Peg, Pole_S)',
               'Touch(Left_grasper, Peg)',  'Grasp(Left_grasper, Peg)',   'Release(Right_grasper, Peg)', 
               'Untouch(Right_grasper, Peg)', 'Touch(Left_grasper, Peg, Pole_G)', 'Release(Left_grasper, Peg)']
    net_conditions = ['Normal-1',  'Normal-2',  'Normal-3',
                      'PLM-10',  'PLM-30',  'PLM-50', 
                      'DLM-100', 'DLM-300', 'DLM-500', 
                      'CLM-10',  'CLM-30',  'CLM-50']
    
    for subject in os.listdir(root_address):
        subject_path = os.path.join(root_address, subject)
        motion_length_list = []
        for folder in netfolders:
            path = os.path.join(subject_path, folder)
            for sub_folder in os.listdir(path): 
                print(f"Processing folder: {sub_folder}")
                sub_path = os.path.join(path, sub_folder)
                analyser = AnalyserMP(sub_path)
                info_list = analyser.get_MP_info()
                error, failure = calculate_error_failure(info_list[2], info_list[3], info_list[5], info_list[6], info_list[7])
                motion_length_list.append([error, failure])
        
        error_data = [item[0] for item in motion_length_list]
        failure_data = [item[1] for item in motion_length_list]

        csv_path = os.path.join(subject_path, "statistics")
        if not os.path.exists(csv_path):
            os.makedirs(csv_path)
        generate_error_failure_csv(error_data, failure_data, all_mps, net_conditions, csv_path)
