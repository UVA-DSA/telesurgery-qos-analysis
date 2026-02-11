import os
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.legend_handler import HandlerTuple
from matplotlib.lines import Line2D

def plot_the_stacked_bar_chart(data_robot, data_console, transfer_ml_free_robot, transfer_ml_free_console, std_robot, std_console):
    
    net_conditions = ['Normal',
                      'PLM-10',  'PLM-30',  'PLM-50', 
                      'DLM-100', 'DLM-300', 'DLM-500', 
                      'CLM-10',  'CLM-30',  'CLM-50']
    
    plt.figure(figsize=(18, 10), constrained_layout=True)

    colors = ["#A6CEE3", "#1F78B4", "#B2DF8A", "#33A02C", "#FB9A99", "#FDBF6F", "#FF7F00", "#CAB2D6", "#6A3D9A"]

    category_labels = ["Touch(Right_grasper, Peg)",
                       "Grasp(Right_grasper, Peg)", 
                       "Untouch(Right_grasper, Peg, Pole_S)",
                       "Touch(Left_grasper, Peg)",
                       "Grasp(Left_grasper, Peg)",
                       "Release(Right_grasper, Peg)",
                       "Untouch(Right_grasper, Peg)",
                       "Touch(Left_grasper, Peg, Pole_G)",
                       "Release(Left_grasper, Peg)"]

    x = np.arange(len(net_conditions))
    bar_width = 0.3
    x1 = x - bar_width / 2 
    x2 = x + bar_width / 2  
    bottom1 = np.zeros(len(net_conditions))
    bottom2 = np.zeros(len(net_conditions))

    for i in range(data_console.shape[1]):
        # Left bar stack (robot)
        plt.bar(x1, data_robot[:, i], bottom=bottom1, color=colors[i], width=bar_width, alpha=0.5)
        for j in range(len(net_conditions)):
            if data_robot[j, i] > 20:
                plt.text(x1[j], bottom1[j] + data_robot[j, i]/2, f"{data_robot[j, i]:.0f}", ha='center', va='center', fontsize=8)
        bottom1 += data_robot[:, i]

        # Right bar stack (console)
        plt.bar(x2, data_console[:, i], bottom=bottom2, color=colors[i], width=bar_width, edgecolor='black', linewidth=1.2)  # transparent for contrast
        for j in range(len(net_conditions)):
            if data_console[j, i] > 20:
                plt.text(x2[j], bottom2[j] + data_console[j, i]/2, f"{data_console[j, i]:.0f}", ha='center', va='center', fontsize=8)
        bottom2 += data_console[:, i]

    legend_handles = []
    for i in range(len(category_labels)):
        robot_patch = mpatches.Patch(color=colors[i], alpha=0.5)
        console_patch = mpatches.Patch(facecolor=colors[i], edgecolor='black', linewidth=1.2)
        legend_handles.append(((robot_patch, console_patch), category_labels[i]))

    robot_type = mpatches.Patch(facecolor='gray', alpha=0.5)
    console_type = mpatches.Patch(facecolor='gray', edgecolor='black', linewidth=1.2)
    mean_console_line = Line2D([0], [0], color='red', linestyle='--')
    mean_robot_line = Line2D([0], [0], color='orange', linestyle='--')
    

    for idx in [1, 4, 7, 10]:  # positions between groups: after index 2 and index 5
        plt.axvline(x=idx - 0.5, color='gray', linestyle='--', linewidth=1.5, alpha=0.7)

    # Show only upper error bars (positive direction)
    std_dev_container1 = plt.errorbar(x1, bottom1, yerr=[np.zeros_like(std_robot), std_robot], fmt='none', ecolor="#4D4D4D", capsize=6)
    std_dev_container2 = plt.errorbar(x2, bottom2, yerr=[np.zeros_like(std_console), std_console], fmt='none', ecolor="#4D4D4D", capsize=6)
    # group_colors = ["#f9dad1", "#f0e4c0", "#e4d0f0"]  # light shades for clarity
    # group_bounds = [(0.5, 3.5), (3.5, 6.5), (6.5, len(net_conditions) - 0.5)]
    # for (left, right), color in zip(group_bounds, group_colors):
    #     plt.axvspan(left, right, facecolor=color, alpha=0.3)

    plt.axhline(y=np.sum(data_robot[0, :]), color='red', linestyle='--')
    plt.axhline(y=np.sum(data_console[0, :]), color='orange', linestyle='--')
    plt.xticks(x, net_conditions, rotation=45, fontsize=12)
    plt.ylabel('Motion Length (mm)', fontsize=13)
    plt.title('Motion Length Comparison Across Network Conditions', fontsize=14)
    plt.grid(True, axis='y', linestyle='--', alpha=0.5)

    plt.legend(handles=[mean_console_line, mean_robot_line, robot_type, console_type] + [pair[0] for pair in legend_handles] + [std_dev_container1],
    labels=['Console Mean of Normal Condition', 'Robot Mean of Normal Condition', 'Robot Space(Left Bar)', 
            'Console Space(Right Bar)'] + [pair[1] for pair in legend_handles] + ['Std Dev'],
    handler_map={tuple: HandlerTuple(ndivide=None)},
    loc='upper left', framealpha=0.9)   

    plt.tight_layout(pad=2.0)
    plt.show()


def generate_summary_csv(net_conditions, all_means_robot, all_stds_robot, all_means_console, all_stds_console, pvalues_r, pvalues_c):
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
    # Prepare data array (10 net conditions x 10 columns: combined mean±std)
    data = []
    for i in range(len(net_conditions)):
        row = []
        for j in range(10):  # For each motion primitive
            mean_val_robot = round(all_means_robot[j][i], 3)
            std_val_robot = round(all_stds_robot[j][i], 3)
            mean_val_console = round(all_means_console[j][i], 3)
            std_val_console = round(all_stds_console[j][i], 3)
            if pvalues_r[j][i] == 1 and pvalues_c[j][i] == 1:
                combined = f"{mean_val_robot} ± {std_val_robot}* | {mean_val_console} ± {std_val_console}*"
            elif pvalues_r[j][i] == 1:
                combined = f"{mean_val_robot} ± {std_val_robot}* | {mean_val_console} ± {std_val_console}"
            elif pvalues_c[j][i] == 1:
                combined = f"{mean_val_robot} ± {std_val_robot} | {mean_val_console} ± {std_val_console}*"
            else:
                combined = f"{mean_val_robot} ± {std_val_robot} | {mean_val_console} ± {std_val_console}"
            row.append(combined)
        data.append(row)
    
    # Create DataFrame and save to CSV
    df = pd.DataFrame(data, columns=mp_names, index=net_conditions)
    output_file = "metrics_results/summary/mp_motion_length_summary.csv"
    df.to_csv(output_file, index_label='Net Conditions', encoding='utf-8-sig')
    print(f"CSV file '{output_file}' has been generated successfully!")
    print(f"Shape: {df.shape}")

def calculate_p_values(mpr_all, mpc_all):
    normal_r = mpr_all[:, 0]
    normal_c = mpc_all[:, 0]

    plm_c = mpc_all[:, 1:4]
    dlm_c = mpc_all[:, 4:7]
    clm_c = mpc_all[:, 7:10]

    plm_r = mpr_all[:, 1:4]
    dlm_r = mpr_all[:, 4:7]
    clm_r = mpr_all[:, 7:10]
    
    plist_r = np.zeros(10)
    plist_c = np.zeros(10)

    for i in range(3):
        t_stat_r, p_val_r = stats.ttest_rel(normal_r, plm_r[:, i])
        t_stat_c, p_val_c = stats.ttest_rel(normal_c, plm_c[:, i])
        print(f"PLM {i+1} vs Normal Robot: t-statistic = {t_stat_r}, p-value = {p_val_r}")
        print(f"PLM {i+1} vs Normal Console: t-statistic = {t_stat_c}, p-value = {p_val_c}")
        if p_val_r < 0.05:
            plist_r[i+1] = 1
        if p_val_c < 0.05:
            plist_c[i+1] = 1

    for i in range(3):
        t_stat_r, p_val_r = stats.ttest_rel(normal_r, dlm_r[:, i])
        t_stat_c, p_val_c = stats.ttest_rel(normal_c, dlm_c[:, i])
        print(f"DLM {i+1} vs Normal Robot: t-statistic = {t_stat_r}, p-value = {p_val_r}")
        print(f"DLM {i+1} vs Normal Console: t-statistic = {t_stat_c}, p-value = {p_val_c}")
        if p_val_r < 0.05:
            plist_r[i+4] = 1
        if p_val_c < 0.05:
            plist_c[i+4] = 1

    for i in range(3):
        t_stat_r, p_val_r = stats.ttest_rel(normal_r, clm_r[:, i])
        t_stat_c, p_val_c = stats.ttest_rel(normal_c, clm_c[:, i])
        print(f"CLM {i+1} vs Normal Robot: t-statistic = {t_stat_r}, p-value = {p_val_r}")
        print(f"CLM {i+1} vs Normal Console: t-statistic = {t_stat_c}, p-value = {p_val_c}")
        if p_val_r < 0.05:
            plist_r[i+7] = 1
        if p_val_c < 0.05:
            plist_c[i+7] = 1
    print("----------------------------------------------------------------")        

    return plist_r, plist_c

if __name__ == "__main__":
    root_address = "exp_data"
    net_conditions = ['Normal', 'PLM-10',  'PLM-30',  'PLM-50', 
                      'DLM-100', 'DLM-300', 'DLM-500', 
                      'CLM-10',  'CLM-30',  'CLM-50']
    mp_columns = [
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
    
    tr, mpr1, mpr2, mpr3, mpr4, mpr5, mpr6, mpr7, mpr8, mpr9 = [], [], [], [], [], [], [], [], [], []
    tc, mpc1, mpc2, mpc3, mpc4, mpc5, mpc6, mpc7, mpc8, mpc9 = [], [], [], [], [], [], [], [], [], []

    for subject in os.listdir(root_address):
        robot_path = os.path.join(root_address, subject, "statistics", "motion_length_robot_analysis.csv")
        robot_motion= pd.read_csv(robot_path)

        console_path = os.path.join(root_address, subject, "statistics", "motion_length_console_analysis.csv")
        console_motion = pd.read_csv(console_path)

        mps_robot = [robot_motion[[col]].values.flatten() for col in mp_columns]
        mps_console = [console_motion[[col]].values.flatten() for col in mp_columns]

        for i, mp in enumerate(mps_robot):
            mps_robot[i] = np.concatenate([[round(np.mean(mp[:3]), 3)], mp[3:]])
        
        for i, mp in enumerate(mps_console):
            mps_console[i] = np.concatenate([[round(np.mean(mp[:3]), 3)], mp[3:]])

        mps_robot = np.array(mps_robot)
        mps_console = np.array(mps_console)

        tr.append(mps_robot[0, :])
        mpr1.append(mps_robot[1, :])
        mpr2.append(mps_robot[2, :])
        mpr3.append(mps_robot[3, :])
        mpr4.append(mps_robot[4, :])
        mpr5.append(mps_robot[5, :])
        mpr6.append(mps_robot[6, :])
        mpr7.append(mps_robot[7, :])
        mpr8.append(mps_robot[8, :])
        mpr9.append(mps_robot[9, :])

        tc.append(mps_console[0, :])
        mpc1.append(mps_console[1, :])
        mpc2.append(mps_console[2, :])
        mpc3.append(mps_console[3, :])
        mpc4.append(mps_console[4, :])
        mpc5.append(mps_console[5, :])
        mpc6.append(mps_console[6, :])
        mpc7.append(mps_console[7, :])
        mpc8.append(mps_console[8, :])
        mpc9.append(mps_console[9, :])

    tr_all = np.array(tr)
    tc_all = np.array(tc)
    tr_all_mean = np.mean(tr_all, axis=0)
    tc_all_mean = np.mean(tc_all, axis=0)
    tr_all_std = np.std(tr_all, axis=0)
    tc_all_std = np.std(tc_all, axis=0)

    mpr1_all = np.array(mpr1)
    mpc1_all = np.array(mpc1)
    mpr1_all_mean = np.mean(mpr1_all, axis=0)
    mpc1_all_mean = np.mean(mpc1_all, axis=0)
    mpr1_all_std = np.std(mpr1_all, axis=0)
    mpc1_all_std = np.std(mpc1_all, axis=0)

    mpr2_all = np.array(mpr2)
    mpc2_all = np.array(mpc2)
    mpr2_all_mean = np.mean(mpr2_all, axis=0)
    mpc2_all_mean = np.mean(mpc2_all, axis=0)
    mpr2_all_std = np.std(mpr2_all, axis=0)
    mpc2_all_std = np.std(mpc2_all, axis=0)

    mpr3_all = np.array(mpr3)
    mpc3_all = np.array(mpc3)
    mpr3_all_mean = np.mean(mpr3_all, axis=0)
    mpc3_all_mean = np.mean(mpc3_all, axis=0)
    mpr3_all_std = np.std(mpr3_all, axis=0)
    mpc3_all_std = np.std(mpc3_all, axis=0)

    mpr4_all = np.array(mpr4)
    mpc4_all = np.array(mpc4)
    mpr4_all_mean = np.mean(mpr4_all, axis=0)
    mpc4_all_mean = np.mean(mpc4_all, axis=0)
    mpr4_all_std = np.std(mpr4_all, axis=0)
    mpc4_all_std = np.std(mpc4_all, axis=0)

    mpr5_all = np.array(mpr5)
    mpc5_all = np.array(mpc5)
    mpr5_all_mean = np.mean(mpr5_all, axis=0)
    mpc5_all_mean = np.mean(mpc5_all, axis=0)
    mpr5_all_std = np.std(mpr5_all, axis=0)
    mpc5_all_std = np.std(mpc5_all, axis=0)

    mpr6_all = np.array(mpr6)
    mpc6_all = np.array(mpc6)
    mpr6_all_mean = np.mean(mpr6_all, axis=0)
    mpc6_all_mean = np.mean(mpc6_all, axis=0)
    mpr6_all_std = np.std(mpr6_all, axis=0)
    mpc6_all_std = np.std(mpc6_all, axis=0)

    mpr7_all = np.array(mpr7)
    mpc7_all = np.array(mpc7)
    mpr7_all_mean = np.mean(mpr7_all, axis=0)
    mpc7_all_mean = np.mean(mpc7_all, axis=0)
    mpr7_all_std = np.std(mpr7_all, axis=0)
    mpc7_all_std = np.std(mpc7_all, axis=0)

    mpr8_all = np.array(mpr8)
    mpc8_all = np.array(mpc8)
    mpr8_all_mean = np.mean(mpr8_all, axis=0)
    mpc8_all_mean = np.mean(mpc8_all, axis=0)
    mpr8_all_std = np.std(mpr8_all, axis=0)
    mpc8_all_std = np.std(mpc8_all, axis=0)

    mpr9_all = np.array(mpr9)
    mpc9_all = np.array(mpc9)
    mpr9_all_mean = np.mean(mpr9_all, axis=0)
    mpc9_all_mean = np.mean(mpc9_all, axis=0)
    mpr9_all_std = np.std(mpr9_all, axis=0)
    mpc9_all_std = np.std(mpc9_all, axis=0)

    all_means_robot = [tr_all_mean, mpr1_all_mean, mpr2_all_mean, mpr3_all_mean, mpr4_all_mean, mpr5_all_mean,
                       mpr6_all_mean, mpr7_all_mean, mpr8_all_mean, mpr9_all_mean]
    all_stds_robot = [tr_all_std, mpr1_all_std, mpr2_all_std, mpr3_all_std, mpr4_all_std, mpr5_all_std,
                      mpr6_all_std, mpr7_all_std, mpr8_all_std, mpr9_all_std]

    all_means_console = [tc_all_mean, mpc1_all_mean, mpc2_all_mean, mpc3_all_mean, mpc4_all_mean, mpc5_all_mean,
                         mpc6_all_mean, mpc7_all_mean, mpc8_all_mean, mpc9_all_mean]
    all_stds_console = [tc_all_std, mpc1_all_std, mpc2_all_std, mpc3_all_std, mpc4_all_std, mpc5_all_std,
                        mpc6_all_std, mpc7_all_std, mpc8_all_std, mpc9_all_std]

    mpr_all = [tr_all, mpr1_all, mpr2_all, mpr3_all, mpr4_all, mpr5_all, 
              mpr6_all, mpr7_all, mpr8_all, mpr9_all]
    mpc_all = [tc_all, mpc1_all, mpc2_all, mpc3_all, mpc4_all, mpc5_all,
               mpc6_all, mpc7_all, mpc8_all, mpc9_all]
    
    pvalues_r = []
    pvalues_c = []
    for i in range(len(mpr_all)):
        pr, pc = calculate_p_values(mpr_all[i], mpc_all[i])
        pvalues_r.append(pr)
        pvalues_c.append(pc)
    plot_the_stacked_bar_chart(np.array(all_means_robot[1:]).T * 1000, np.array(all_means_console[1:]).T * 1000, tr_all_mean[0]*1000, tc_all_mean[0]*1000, tr_all_std * 1000, tc_all_std * 1000)
    generate_summary_csv(net_conditions, all_means_robot, all_stds_robot, all_means_console, all_stds_console, pvalues_r, pvalues_c)