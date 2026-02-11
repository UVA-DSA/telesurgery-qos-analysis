import os
import numpy as np
import pandas as pd
from scipy import stats

def generate_summary_csv(net_conditions, all_means, all_stds, pvalues, group_name):
    mp_names = [
        group_name+"_Trial"
    ]
    # Prepare data array (10 net conditions x 10 columns: combined mean±std)
    data = []
    for i in range(len(net_conditions)):
        row = []
        for j in range(1):  # For each motion primitive
            mean_val = round(all_means[j][i], 3)
            std_val = round(all_stds[j][i], 2)
            if pvalues[j][i] == 1:
                combined = f"{mean_val} ± {std_val}*"
            else:
                combined = f"{mean_val} ± {std_val}"
            row.append(combined)
        data.append(row)
    
    # Create DataFrame and save to CSV
    df = pd.DataFrame(data, columns=mp_names, index=net_conditions)
    output_file = f"metrics_results/summary/mp_pedal_usage_summary_{group_name}.csv"
    df.to_csv(output_file, index_label='Net Conditions', encoding='utf-8-sig')
    print(f"CSV file '{output_file}' has been generated successfully!")
    print(f"Shape: {df.shape}")

def calculate_p_values(mp_all): 
    normal = mp_all[:, 0]
    plm = mp_all[:, 1:4]
    dlm = mp_all[:, 4:7]
    clm = mp_all[:, 7:10]

    plist = np.zeros(10)

    for i in range(3):
        t_stat, p_val = stats.ttest_rel(normal, plm[:, i])
        print(f"PLM {i+1} vs Normal: t-statistic = {t_stat}, p-value = {p_val}")
        if p_val < 0.05:
            plist[i+1] = 1

    for i in range(3):
        t_stat, p_val = stats.ttest_rel(normal, dlm[:, i])
        print(f"DLM {i+1} vs Normal: t-statistic = {t_stat}, p-value = {p_val}")
        if p_val < 0.05:
            plist[i+4] = 1

    for i in range(3):
        t_stat, p_val = stats.ttest_rel(normal, clm[:, i])
        print(f"CLM {i+1} vs Normal: t-statistic = {t_stat}, p-value = {p_val}")
        if p_val < 0.05:
            plist[i+7] = 1
    print("----------------------------------------------------------------")
    
    return plist

if __name__ == "__main__":
    root_address = "exp_data"
    net_conditions = ['Normal', 'PLM-10',  'PLM-30',  'PLM-50', 
                      'DLM-100', 'DLM-300', 'DLM-500', 
                      'CLM-10',  'CLM-30',  'CLM-50']
    mp_columns = ["Trial"]

    
    # Based on Pedal Usage Study
    Expert = ['exp_data_1', 'exp_data_4', 'exp_data_6', 'exp_data_11', 'exp_data_17']
    Intermediate = ['exp_data_2', 'exp_data_3', 'exp_data_10', 'exp_data_12', 'exp_data_16']
    Novice = ['exp_data_7', 'exp_data_8', 'exp_data_9', 'exp_data_15', 'exp_data_18']

    # Based on Completion Time Study
    # Expert = ['exp_data_3', 'exp_data_4', 'exp_data_11', 'exp_data_12', 'exp_data_17']
    # Intermediate = ['exp_data_1', 'exp_data_2', 'exp_data_6', 'exp_data_8', 'exp_data_16']
    # Novice = ['exp_data_7', 'exp_data_9', 'exp_data_10', 'exp_data_15', 'exp_data_18']

    data_all = [Novice, Intermediate, Expert]
    n = 0
    for group in data_all:
        n += 1
        if n == 1:
            name = "Novice"
        elif n == 2:
            name = "Intermediate"
        elif n == 3:
            name = "Expert"
            
        trial = []
        for subject in group:
            path = os.path.join(root_address, subject, "statistics", "pedal_usage_analysis.csv")
            mp_time= pd.read_csv(path)

            mps = [mp_time[[col]].values.flatten() for col in mp_columns]
            for i, mp in enumerate(mps):
                mps[i] = np.concatenate([[int(np.ceil(np.mean(mp[:3])))], mp[3:]])
        
            mps = np.array(mps)
            trial.append(mps[0, :])
            

        trial_all = np.array(trial)
        trial_all_mean = np.ceil(np.mean(trial_all, axis=0)).astype(int)
        trial_all_std = np.std(trial_all, axis=0)

    
        all_means = [trial_all_mean]
        all_stds = [trial_all_std]
        all_mp = [trial_all]
    
        pvalues = []
        for mp in all_mp:
            mp_plist = calculate_p_values(mp)
            pvalues.append(mp_plist)

        generate_summary_csv(net_conditions, all_means, all_stds, pvalues, name)