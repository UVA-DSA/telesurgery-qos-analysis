from Analyser_mp import *

def get_mp_completion_time_each_condition(mp_dict):
    touch_peg = []
    grasp = []
    untouch = []
    touch_pole = []
    release = []
    for i in mp_dict:
        for j in range(len(mp_dict[i])):
            if j == 0 and mp_dict[i][j][0] == 'Touch':
                touch_peg.append(mp_dict[i][j][2] - mp_dict[i][j][1])
            if j == 1 and mp_dict[i][j][0] == 'Grasp':
                grasp.append(mp_dict[i][j][2] - mp_dict[i][j][1])
            if j == 2 and mp_dict[i][j][0] == 'Untouch':
                untouch.append(mp_dict[i][j][2] - mp_dict[i][j][1])
            if j == 3 and mp_dict[i][j][0] == 'Touch':
                touch_pole.append(mp_dict[i][j][2] - mp_dict[i][j][1])
            if j == 4 and mp_dict[i][4][0] == 'Release':
                release.append(mp_dict[i][j][2] - mp_dict[i][j][1])
    
    return touch_peg, grasp, untouch, touch_pole, release

def get_mp_completion_time_mean(mp_dict):
    touch_peg, grasp, untouch, touch_pole, release = [], [], [], [], []
    for i in mp_dict:
        tg, gp, ut, te, rl = 0, 0, 0, 0, 0
        for j in range(len(mp_dict[i])):
            time = mp_dict[i][j][-1] - mp_dict[i][j][3]
            if mp_dict[i][j][0] == 'Touch' and type(mp_dict[i][j][1]) != str:
                tg += time
            if mp_dict[i][j][0] == 'Grasp':
                gp += time 
            if mp_dict[i][j][0] == 'Untouch':
                ut += time
            if mp_dict[i][j][0] == 'Touch' and type(mp_dict[i][j][1]) == str:
                te += time
            if mp_dict[i][j][0] == 'Release':
                rl += time
        touch_peg.append(tg)
        grasp.append(gp)
        untouch.append(ut)
        touch_pole.append(te)
        release.append(rl)

    mp_time_mean = [np.mean(touch_peg), np.mean(grasp), np.mean(untouch), np.mean(touch_pole), np.mean(release)]
    
    return mp_time_mean

def get_transfer_completion_time_each_condition(mp_dict):
    peg_transfer_time = []
    for i in mp_dict:
        peg_transfer_time.append(mp_dict[i][-1][-1]-mp_dict[i][0][3])
    
    return peg_transfer_time

def plot_stacked_barchart(net_conditions, mp_time_all, transfer_time_free):
    data = np.array(mp_time_all)
    std_normal = [np.std(transfer_time_free), 0, 0, 0, 0, 0, 0, 0, 0, 0]
    #stds = [np.std(vals) for vals in transfer_ml_all]
    
    colors = ["#A6CEE3", "#1F78B4", "#B2DF8A", "#33A02C", "#FB9A99"]

    category_labels = ['Touch Peg', 'Grasp', 'Untouch Source Pole', 'Touch Target Pole', 'Release']

    x = np.arange(len(net_conditions))
    bar_width = 0.6
    bottom = np.zeros(len(net_conditions))

    # Create stacked bars
    plt.figure(figsize=(18, 7), constrained_layout=True)
    for i in range(data.shape[1]):
        plt.bar(x, data[:, i], bottom=bottom, color=colors[i], width=bar_width, label=category_labels[i])
        # Add segment label
        for j in range(len(net_conditions)):
            if data[j, i] > 0:
                plt.text(x[j], bottom[j] + data[j, i] / 2, f"{data[j, i]:.2f}", ha='center', va='center', fontsize=8)
        bottom += data[:, i]

    plt.errorbar(x, bottom, yerr=std_normal, fmt='none',ecolor='gray',capsize=5,label='Std Dev')
    #plt.errorbar(x, bottom, fmt='none',ecolor='gray',capsize=5)  

    plt.axhline(y=np.mean(transfer_time_free), color='red', linestyle='--', label='Mean of Normal Condition')
    #plt.axhline(y=np.min(transfer_ml_free), color='green', linestyle='--', label='Best Mean of Normal Condition')
    plt.xticks(x, net_conditions, rotation=45, fontsize=12)
    plt.ylabel('Completion Time (s)', fontsize=13)
    plt.title('Average Peg Transfer Completion Time Across Network Conditions', fontsize=14)
    plt.grid(True, axis='y', linestyle='--', alpha=0.5)
    plt.legend(title="Baselines and MP Segments", bbox_to_anchor=(1, 1.02), loc='upper left')
    plt.tight_layout(pad=2.0)
    plt.show()

if __name__ == "__main__":
    root_address = "exp_data_new"
    netfolders = ['no_fault', 'packet_loss', 'delay', 'communication_loss']

    transfer_time_free = []
    transfer_time_fault = []

    mp_time_free = []
    mp_time_all = []

    net_conditions = ['normal']

    for folder in netfolders:
        path = os.path.join(root_address, folder)
        for sub_folder in os.listdir(path): 
            sub_path = os.path.join(path, sub_folder)
            analyser_mp = AnalyserMP(sub_path)
            mp_dict = analyser_mp.get_MP_timestamp_error()
            #touch_peg, grasp, untouch, touch_pole, release = get_mp_completion_time_each_condition(mp_dict)
            transfer_time = get_transfer_completion_time_each_condition(mp_dict)
            mp_time_mean = get_mp_completion_time_mean(mp_dict)
            if sub_folder[0] == 'f':
                #print(np.sum(mp_time_mean))
                #print(np.sum(transfer_time))
                mp_time_free.append(mp_time_mean)
                transfer_time_free.append(np.mean(transfer_time))
            else:
                net_conditions.append(sub_folder)
                mp_time_all.append(mp_time_mean)

    mp_time_free_mean = [sum(values) / len(mp_time_free) for values in zip(*mp_time_free)]
    mp_time_all.insert(0, mp_time_free_mean)
    plot_stacked_barchart(net_conditions, mp_time_all, transfer_time_free)

    # for i in range(len(net_conditions)):
    #     print(f"The average completion time for each peg transfer in {net_conditions[i]} is {transfer_time_fault[i]} seconds.")
    
    # for i in range(len(free_conditions)):
    #     print(f"The average completion time for each peg transfer in {free_conditions[i]} is {transfer_time_free[i]} seconds.")
    
    # print(f"The average completion time for each peg transfer in all normal condition is {np.mean(transfer_time_free)}")
    # print(f"The lowest average completion time for each peg transfer in all normal condition is {np.min(transfer_time_free)}")
    
    # plt.figure(figsize=(12, 6))
    # plt.plot(net_conditions,  transfer_time_fault, marker='o', label='Each Peg Transfer Mean')
    # plt.axhline(y=np.mean(transfer_time_free), color='red', linestyle='--', label='mean of normal condition')
    # plt.axhline(y=np.min(transfer_time_free), color='green', linestyle='--', label='best mean of normal condition')
    # plt.title('Each Peg Transfer Completion Time Mean Across Network Conditions', fontsize=14)
    # plt.xlabel('Network Conditions', fontsize=14)
    # plt.ylabel('Completion Time (s)', fontsize=14)
    # plt.grid(True, linestyle='--', alpha=0.6)
    # plt.xticks(rotation=45, fontsize=12)
    # plt.tight_layout()
    # plt.legend()
    # plt.show()


    # plt.figure(figsize=(12, 6))
    # plt.boxplot(touch_peg_mean, labels=net_conditions)
    # plt.axhline(y=np.mean(touch_peg_mean_free), color='red', linestyle='--', label='mean of normal condition')
    # plt.axhline(y=np.min(touch_peg_mean_free), color='green', linestyle='--', label='best mean of normal condition')
    # plt.title('Touch Peg Completion Time Box Plots Across Network Conditions', fontsize=14)
    # plt.xlabel('Network Conditions', fontsize=14)
    # plt.ylabel('Completion Time (s)', fontsize=14)
    # plt.grid(True, linestyle='--', alpha=0.6)
    # plt.xticks(rotation=45, fontsize=12)
    # plt.tight_layout()
    # plt.legend()
    # plt.show()
    
  
    # plt.figure(figsize=(12, 6))
    # plt.plot(net_conditions,  [np.mean(sublist) for sublist in touch_peg_mean], marker='o', label='Touch Peg Mean')
    # plt.axhline(y=np.mean(touch_peg_mean_free), color='red', linestyle='--', label='mean of normal condition')
    # plt.axhline(y=np.min(touch_peg_mean_free), color='green', linestyle='--', label='best mean of normal condition')
    # plt.title('Touch Peg Completion Time Mean Across Network Conditions', fontsize=14)
    # plt.xlabel('Network Conditions', fontsize=14)
    # plt.ylabel('Completion Time (s)', fontsize=14)
    # plt.grid(True, linestyle='--', alpha=0.6)
    # plt.xticks(rotation=45, fontsize=12)
    # plt.tight_layout()
    # plt.legend()
    # plt.show()

    # plt.figure(figsize=(12, 6))
    # plt.boxplot(grasp_mean, labels=net_conditions)
    # plt.axhline(y=np.mean(grasp_mean_free), color='red', linestyle='--', label='mean of normal condition')
    # plt.axhline(y=np.min(grasp_mean_free), color='green', linestyle='--', label='best mean of normal condition')
    # plt.title('Grasp Completion Time Box Plots Across Network Conditions', fontsize=14)
    # plt.xlabel('Network Conditions', fontsize=14)
    # plt.ylabel('Completion Time (s)', fontsize=14)
    # plt.grid(True, linestyle='--', alpha=0.6)
    # plt.xticks(rotation=45, fontsize=12)
    # plt.tight_layout()
    # plt.legend()
    # plt.show()

    # plt.figure(figsize=(12, 6))
    # plt.plot(net_conditions, [np.mean(sublist) for sublist in grasp_mean], marker='o', linestyle='-', label='Grasp Mean')
    # plt.axhline(y=np.mean(grasp_mean_free), color='red', linestyle='--', label='mean of normal condition')
    # plt.axhline(y=np.min(grasp_mean_free), color='green', linestyle='--', label='best mean of normal condition')
    # plt.title('Grasp Completion Time Mean Across Network Conditions', fontsize=14)
    # plt.xlabel('Network Conditions', fontsize=14)
    # plt.ylabel('Completion Time (s)', fontsize=14)
    # plt.grid(True, linestyle='--', alpha=0.6)
    # plt.xticks(rotation=45, fontsize=12)
    # plt.tight_layout()
    # plt.legend()
    # plt.show()

    # plt.figure(figsize=(12, 6))
    # plt.boxplot(untouch_mean, labels=net_conditions)
    # plt.axhline(y=np.mean(untouch_mean_free), color='red', linestyle='--', label='mean of normal condition')
    # plt.axhline(y=np.min(untouch_mean_free), color='green', linestyle='--', label='best mean of normal condition')
    # plt.title('Untouch Pole Completion Time Box Plots Across Network Conditions', fontsize=14)
    # plt.xlabel('Network Conditions', fontsize=14)
    # plt.ylabel('Completion Time (s)', fontsize=14)
    # plt.grid(True, linestyle='--', alpha=0.6)
    # plt.xticks(rotation=45, fontsize=12)
    # plt.tight_layout()
    # plt.legend()
    # plt.show()

    # plt.figure(figsize=(12, 6))
    # plt.plot(net_conditions, [np.mean(sublist) for sublist in untouch_mean], marker='o', linestyle='-', label='Untouch Pole Mean')
    # plt.axhline(y=np.mean(untouch_mean_free), color='red', linestyle='--', label='mean of normal condition')
    # plt.axhline(y=np.min(untouch_mean_free), color='green', linestyle='--', label='best mean of normal condition')
    # plt.title('Untouch Pole Completion Time Mean Across Network Conditions', fontsize=14)
    # plt.xlabel('Network Conditions', fontsize=14)
    # plt.ylabel('Completion Time (s)', fontsize=14)
    # plt.grid(True, linestyle='--', alpha=0.6)
    # plt.xticks(rotation=45, fontsize=12)
    # plt.tight_layout()
    # plt.legend()
    # plt.show()

    # plt.figure(figsize=(12, 6))
    # plt.boxplot(touch_pole_mean, labels=net_conditions)
    # plt.axhline(y=np.mean(touch_pole_mean_free), color='red', linestyle='--', label='mean of normal condition')
    # plt.axhline(y=np.min(touch_pole_mean_free), color='green', linestyle='--', label='best mean of normal condition')
    # plt.title('Touch Pole Completion Time Box Plots Across Network Conditions', fontsize=14)
    # plt.xlabel('Network Conditions', fontsize=14)
    # plt.ylabel('Completion Time (s)', fontsize=14)
    # plt.grid(True, linestyle='--', alpha=0.6)
    # plt.xticks(rotation=45, fontsize=12)
    # plt.tight_layout()
    # plt.legend()
    # plt.show()

    # plt.figure(figsize=(12, 6))
    # plt.plot(net_conditions, [np.mean(sublist) for sublist in touch_pole_mean], marker='o', linestyle='-', label='Touch Pole Mean')
    # plt.axhline(y=np.mean(touch_pole_mean_free), color='red', linestyle='--', label='mean of normal condition')
    # plt.axhline(y=np.min(touch_pole_mean_free), color='green', linestyle='--', label='best mean of normal condition')
    # plt.title('Touch Pole Completion Time Mean Across Network Conditions', fontsize=14)
    # plt.xlabel('Network Conditions', fontsize=14)
    # plt.ylabel('Completion Time (s)', fontsize=14)
    # plt.grid(True, linestyle='--', alpha=0.6)
    # plt.xticks(rotation=45, fontsize=12)
    # plt.tight_layout()
    # plt.legend()
    # plt.show()

    # plt.figure(figsize=(12, 6))
    # plt.boxplot(release_mean, labels=net_conditions)
    # plt.axhline(y=np.mean(release_mean_free), color='red', linestyle='--', label='mean of normal condition')
    # plt.axhline(y=np.min(release_mean_free), color='green', linestyle='--', label='best mean of normal condition')
    # plt.title('Release Completion Time Box Plots Across Network Conditions', fontsize=14)
    # plt.xlabel('Network Conditions', fontsize=14)
    # plt.ylabel('Completion Time (s)', fontsize=14)
    # plt.grid(True, linestyle='--', alpha=0.6)
    # plt.xticks(rotation=45, fontsize=12)
    # plt.tight_layout()
    # plt.legend()
    # plt.show()

    # plt.figure(figsize=(12, 6))
    # plt.plot(net_conditions, [np.mean(sublist) for sublist in release_mean], marker='o', linestyle='-', label='Release Mean')
    # plt.axhline(y=np.mean(release_mean_free), color='red', linestyle='--', label='mean of normal condition')
    # plt.axhline(y=np.min(release_mean_free), color='green', linestyle='--', label='best mean of normal condition')
    # plt.title('Release Completion Time Mean Across Network Conditions', fontsize=14)
    # plt.xlabel('Network Conditions', fontsize=14)
    # plt.ylabel('Completion Time (s)', fontsize=14)
    # plt.grid(True, linestyle='--', alpha=0.6)
    # plt.xticks(rotation=45, fontsize=12)
    # plt.tight_layout()
    # plt.legend()
    # plt.show()