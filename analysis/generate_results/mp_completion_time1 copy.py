import os
import numpy as np
import pandas as pd
from scipy import stats

def generate_summary_csv(net_conditions, all_means, all_stds, pvalues):
    mp_names = [
        "Transfer",
        "Touch(Right_grasper, Peg)",
        "Grasp(Right_grasper, Peg)", 
        "Untouch(Right_grasper, Peg, Pole_S)",
        "Touch(Left_grasper, Peg)",
        "Grasp(Left_grasper, Peg)",
        "Release(Right_grasper, Peg)",
        "Untouch(Right_grasper, Peg)",
        "Touch(Left_grasper, Peg, Pole_G)",
        "Release(Left_grasper, Peg)"
    ]
    
    # Create column names with mean, std, and percentage change columns
    column_names = []
    for mp_name in mp_names:
        column_names.append(f"{mp_name}_mean")
        column_names.append(f"{mp_name}_std")
        column_names.append(f"{mp_name}_change")
    
    # Calculate baseline values (first condition - Normal) for percentage change
    baseline_means = [all_means[j][0] for j in range(10)]
    
    # Prepare data array (10 net conditions x 30 columns: mean, std, and percentage change)
    data = []
    for i in range(len(net_conditions)):
        row = []
        for j in range(10):  # For each motion primitive
            mean_val = round(all_means[j][i], 1)
            std_val = round(all_stds[j][i], 1)
            print(f"Mean: {baseline_means[j]}")
            # Calculate percentage change relative to baseline (first condition)
            if baseline_means[j] != 0:
                pct_change = round(mean_val - baseline_means[j], 1)
            else:
                pct_change = 0.0
            
            row.append(mean_val)     # Add mean value
            row.append(std_val)      # Add std value
            row.append(pct_change)   # Add percentage change
        data.append(row)
    
    # Create DataFrame and save to CSV
    df = pd.DataFrame(data, columns=column_names, index=net_conditions)
    output_file = "metrics_results/summary/mp_completion_time_summary_v3.csv"
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
    transfer, mp1, mp2, mp3, mp4, mp5, mp6, mp7, mp8, mp9 = [], [], [], [], [], [], [], [], [], []
    mp_columns = [
            "Entire Transfer",
            "Touch(Right_grasper, Peg)",
            "Grasp(Right_grasper, Peg)", 
            "Untouch(Right_grasper, Peg, Pole_S)",
            "Touch(Left_grasper, Peg)",
            "Grasp(Left_grasper, Peg)",
            "Release(Right_grasper, Peg)",
            "Untouch(Right_grasper, Peg)",
            "Touch(Left_grasper, Peg, Pole_G)",
            "Release(Left_grasper, Peg)"
        ]
    
    for subject in os.listdir(root_address):
        path = os.path.join(root_address, subject, "statistics", "completion_time_analysis.csv")
        mp_time= pd.read_csv(path)
        
        mps = [mp_time[[col]].values.flatten() for col in mp_columns]
        for i, mp in enumerate(mps):
            mps[i] = np.concatenate([[round(np.mean(mp[:3]), 3)], mp[3:]])
        mps = np.array(mps)
        transfer.append(mps[0, :])
        mp1.append(mps[1, :])
        mp2.append(mps[2, :])
        mp3.append(mps[3, :])
        mp4.append(mps[4, :])
        mp5.append(mps[5, :])
        mp6.append(mps[6, :])
        mp7.append(mps[7, :])
        mp8.append(mps[8, :])
        mp9.append(mps[9, :])

    transfer_all = np.array(transfer)
    transfer_all_mean = np.mean(transfer_all, axis=0)
    transfer_all_std = np.std(transfer_all, axis=0)

    mp1_all = np.array(mp1)
    mp1_all_mean = np.mean(mp1_all, axis=0)
    mp1_all_std = np.std(mp1_all, axis=0)
    
    mp2_all = np.array(mp2)
    mp2_all_mean = np.mean(mp2_all, axis=0)
    mp2_all_std = np.std(mp2_all, axis=0)

    mp3_all = np.array(mp3)
    mp3_all_mean = np.mean(mp3_all, axis=0)
    mp3_all_std = np.std(mp3_all, axis=0)

    mp4_all = np.array(mp4)
    mp4_all_mean = np.mean(mp4_all, axis=0)
    mp4_all_std = np.std(mp4_all, axis=0)

    mp5_all = np.array(mp5)
    mp5_all_mean = np.mean(mp5_all, axis=0)
    mp5_all_std = np.std(mp5_all, axis=0)

    mp6_all = np.array(mp6)
    mp6_all_mean = np.mean(mp6_all, axis=0)
    mp6_all_std = np.std(mp6_all, axis=0)

    mp7_all = np.array(mp7)
    mp7_all_mean = np.mean(mp7_all, axis=0)
    mp7_all_std = np.std(mp7_all, axis=0)

    mp8_all = np.array(mp8)
    mp8_all_mean = np.mean(mp8_all, axis=0)
    mp8_all_std = np.std(mp8_all, axis=0)

    mp9_all = np.array(mp9)
    mp9_all_mean = np.mean(mp9_all, axis=0)
    mp9_all_std = np.std(mp9_all, axis=0)

    all_means = [transfer_all_mean, mp1_all_mean, mp2_all_mean, mp3_all_mean, mp4_all_mean, mp5_all_mean, 
                 mp6_all_mean, mp7_all_mean, mp8_all_mean, mp9_all_mean]
    all_stds = [transfer_all_std, mp1_all_std, mp2_all_std, mp3_all_std, mp4_all_std, mp5_all_std,
                mp6_all_std, mp7_all_std, mp8_all_std, mp9_all_std]
    all_mp = [transfer_all, mp1_all, mp2_all, mp3_all, mp4_all, 
              mp5_all, mp6_all, mp7_all, mp8_all, mp9_all]

    pvalues = []
    for mp in all_mp:
        mp_plist = calculate_p_values(mp)
        pvalues.append(mp_plist)

    generate_summary_csv(net_conditions, all_means, all_stds, pvalues)
