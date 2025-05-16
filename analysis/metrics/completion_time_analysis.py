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

def get_transfer_completion_time_each_condition(mp_dict):
    peg_transfer_time = []
    for i in mp_dict:
        if len(mp_dict[i]) == 5 and mp_dict[i][0][0] == 'Touch' and mp_dict[i][4][0] == 'Release':
            peg_transfer_time.append(mp_dict[i][4][2]-mp_dict[i][0][1])
    
    return peg_transfer_time

if __name__ == "__main__":
    root_address = "exp_data_1"
    touch_peg_mean = []
    grasp_mean = []
    untouch_mean = []
    touch_pole_mean = []
    release_mean = []

    touch_peg_mean_free = []
    grasp_mean_free = []
    untouch_mean_free = []
    touch_pole_mean_free = []
    release_mean_free = []

    transfer_time_free = []
    transfer_time_fault = []

    net_conditions = []
    free_conditions = []

    for folder in os.listdir(root_address):
        path = os.path.join(root_address, folder)
        if not os.path.isdir(path):
            continue
        for sub_folder in os.listdir(path): 
            sub_path = os.path.join(path, sub_folder)
            analyser_mp = AnalyserMP(sub_path)
            mp_dict = analyser_mp.get_MP_timestamp_intervals()
            touch_peg, grasp, untouch, touch_pole, release = get_mp_completion_time_each_condition(mp_dict)
            transfer_time = get_transfer_completion_time_each_condition(mp_dict)
            if sub_folder[0] == 'f':
                free_conditions.append(sub_folder)
                touch_peg_mean_free.append(np.mean(touch_peg))
                grasp_mean_free.append(np.mean(grasp))
                untouch_mean_free.append(np.mean(untouch))
                touch_pole_mean_free.append(np.mean(touch_pole))
                release_mean_free.append(np.mean(release))
                transfer_time_free.append(np.mean(transfer_time))
            else:
                net_conditions.append(sub_folder)
                touch_peg_mean.append(touch_peg)
                grasp_mean.append(grasp)
                untouch_mean.append(untouch)
                touch_pole_mean.append(touch_pole)
                release_mean.append(release)
                transfer_time_fault.append(np.mean(transfer_time)) 

    for i in range(len(net_conditions)):
        print(f"The average completion time for each peg transfer in {net_conditions[i]} is {transfer_time_fault[i]} seconds.")
    
    for i in range(len(free_conditions)):
        print(f"The average completion time for each peg transfer in {free_conditions[i]} is {transfer_time_free[i]} seconds.")
    
    print(f"The average completion time for each peg transfer in all normal condition is {np.mean(transfer_time_free)}")
    print(f"The lowest average completion time for each peg transfer in all normal condition is {np.min(transfer_time_free)}")
    
    plt.figure(figsize=(12, 6))
    plt.plot(net_conditions,  transfer_time_fault, marker='o', label='Each Peg Transfer Mean')
    plt.axhline(y=np.mean(transfer_time_free), color='red', linestyle='--', label='mean of normal condition')
    plt.axhline(y=np.min(transfer_time_free), color='green', linestyle='--', label='best mean of normal condition')
    plt.title('Each Peg Transfer Completion Time Mean Across Network Conditions', fontsize=14)
    plt.xlabel('Network Conditions', fontsize=14)
    plt.ylabel('Completion Time (s)', fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.xticks(rotation=45, fontsize=12)
    plt.tight_layout()
    plt.legend()
    plt.show()


    plt.figure(figsize=(12, 6))
    plt.boxplot(touch_peg_mean, labels=net_conditions)
    plt.axhline(y=np.mean(touch_peg_mean_free), color='red', linestyle='--', label='mean of normal condition')
    plt.axhline(y=np.min(touch_peg_mean_free), color='green', linestyle='--', label='best mean of normal condition')
    plt.title('Touch Peg Completion Time Box Plots Across Network Conditions', fontsize=14)
    plt.xlabel('Network Conditions', fontsize=14)
    plt.ylabel('Completion Time (s)', fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.xticks(rotation=45, fontsize=12)
    plt.tight_layout()
    plt.legend()
    plt.show()
    
  
    plt.figure(figsize=(12, 6))
    plt.plot(net_conditions,  [np.mean(sublist) for sublist in touch_peg_mean], marker='o', label='Touch Peg Mean')
    plt.axhline(y=np.mean(touch_peg_mean_free), color='red', linestyle='--', label='mean of normal condition')
    plt.axhline(y=np.min(touch_peg_mean_free), color='green', linestyle='--', label='best mean of normal condition')
    plt.title('Touch Peg Completion Time Mean Across Network Conditions', fontsize=14)
    plt.xlabel('Network Conditions', fontsize=14)
    plt.ylabel('Completion Time (s)', fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.xticks(rotation=45, fontsize=12)
    plt.tight_layout()
    plt.legend()
    plt.show()

    plt.figure(figsize=(12, 6))
    plt.boxplot(grasp_mean, labels=net_conditions)
    plt.axhline(y=np.mean(grasp_mean_free), color='red', linestyle='--', label='mean of normal condition')
    plt.axhline(y=np.min(grasp_mean_free), color='green', linestyle='--', label='best mean of normal condition')
    plt.title('Grasp Completion Time Box Plots Across Network Conditions', fontsize=14)
    plt.xlabel('Network Conditions', fontsize=14)
    plt.ylabel('Completion Time (s)', fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.xticks(rotation=45, fontsize=12)
    plt.tight_layout()
    plt.legend()
    plt.show()

    plt.figure(figsize=(12, 6))
    plt.plot(net_conditions, [np.mean(sublist) for sublist in grasp_mean], marker='o', linestyle='-', label='Grasp Mean')
    plt.axhline(y=np.mean(grasp_mean_free), color='red', linestyle='--', label='mean of normal condition')
    plt.axhline(y=np.min(grasp_mean_free), color='green', linestyle='--', label='best mean of normal condition')
    plt.title('Grasp Completion Time Mean Across Network Conditions', fontsize=14)
    plt.xlabel('Network Conditions', fontsize=14)
    plt.ylabel('Completion Time (s)', fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.xticks(rotation=45, fontsize=12)
    plt.tight_layout()
    plt.legend()
    plt.show()

    plt.figure(figsize=(12, 6))
    plt.boxplot(untouch_mean, labels=net_conditions)
    plt.axhline(y=np.mean(untouch_mean_free), color='red', linestyle='--', label='mean of normal condition')
    plt.axhline(y=np.min(untouch_mean_free), color='green', linestyle='--', label='best mean of normal condition')
    plt.title('Untouch Pole Completion Time Box Plots Across Network Conditions', fontsize=14)
    plt.xlabel('Network Conditions', fontsize=14)
    plt.ylabel('Completion Time (s)', fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.xticks(rotation=45, fontsize=12)
    plt.tight_layout()
    plt.legend()
    plt.show()

    plt.figure(figsize=(12, 6))
    plt.plot(net_conditions, [np.mean(sublist) for sublist in untouch_mean], marker='o', linestyle='-', label='Untouch Pole Mean')
    plt.axhline(y=np.mean(untouch_mean_free), color='red', linestyle='--', label='mean of normal condition')
    plt.axhline(y=np.min(untouch_mean_free), color='green', linestyle='--', label='best mean of normal condition')
    plt.title('Untouch Pole Completion Time Mean Across Network Conditions', fontsize=14)
    plt.xlabel('Network Conditions', fontsize=14)
    plt.ylabel('Completion Time (s)', fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.xticks(rotation=45, fontsize=12)
    plt.tight_layout()
    plt.legend()
    plt.show()

    plt.figure(figsize=(12, 6))
    plt.boxplot(touch_pole_mean, labels=net_conditions)
    plt.axhline(y=np.mean(touch_pole_mean_free), color='red', linestyle='--', label='mean of normal condition')
    plt.axhline(y=np.min(touch_pole_mean_free), color='green', linestyle='--', label='best mean of normal condition')
    plt.title('Touch Pole Completion Time Box Plots Across Network Conditions', fontsize=14)
    plt.xlabel('Network Conditions', fontsize=14)
    plt.ylabel('Completion Time (s)', fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.xticks(rotation=45, fontsize=12)
    plt.tight_layout()
    plt.legend()
    plt.show()

    plt.figure(figsize=(12, 6))
    plt.plot(net_conditions, [np.mean(sublist) for sublist in touch_pole_mean], marker='o', linestyle='-', label='Touch Pole Mean')
    plt.axhline(y=np.mean(touch_pole_mean_free), color='red', linestyle='--', label='mean of normal condition')
    plt.axhline(y=np.min(touch_pole_mean_free), color='green', linestyle='--', label='best mean of normal condition')
    plt.title('Touch Pole Completion Time Mean Across Network Conditions', fontsize=14)
    plt.xlabel('Network Conditions', fontsize=14)
    plt.ylabel('Completion Time (s)', fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.xticks(rotation=45, fontsize=12)
    plt.tight_layout()
    plt.legend()
    plt.show()

    plt.figure(figsize=(12, 6))
    plt.boxplot(release_mean, labels=net_conditions)
    plt.axhline(y=np.mean(release_mean_free), color='red', linestyle='--', label='mean of normal condition')
    plt.axhline(y=np.min(release_mean_free), color='green', linestyle='--', label='best mean of normal condition')
    plt.title('Release Completion Time Box Plots Across Network Conditions', fontsize=14)
    plt.xlabel('Network Conditions', fontsize=14)
    plt.ylabel('Completion Time (s)', fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.xticks(rotation=45, fontsize=12)
    plt.tight_layout()
    plt.legend()
    plt.show()

    plt.figure(figsize=(12, 6))
    plt.plot(net_conditions, [np.mean(sublist) for sublist in release_mean], marker='o', linestyle='-', label='Release Mean')
    plt.axhline(y=np.mean(release_mean_free), color='red', linestyle='--', label='mean of normal condition')
    plt.axhline(y=np.min(release_mean_free), color='green', linestyle='--', label='best mean of normal condition')
    plt.title('Release Completion Time Mean Across Network Conditions', fontsize=14)
    plt.xlabel('Network Conditions', fontsize=14)
    plt.ylabel('Completion Time (s)', fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.xticks(rotation=45, fontsize=12)
    plt.tight_layout()
    plt.legend()
    plt.show()