from Analyser_mp import *

def calculate_motion_length(completed, interval_min, interval_max, scale, arm):
    motion_len = 0

    for i in range(interval_min, interval_max):
        if arm == 'left':
            motion_len += np.sqrt(completed[i][2]**2 + completed[i][3]**2 + completed[i][4]**2) * 0.000115 * scale
        else:
            motion_len += np.sqrt(completed[i][8]**2 + completed[i][9]**2 + completed[i][10]**2) * 0.000115 * scale
    
    return motion_len

def get_peg_transfer_motion_length(mp_dict, analyser_mp, scale):
    peg_motion_length = []
    left = ['Magenta', 'Yellow', 'Cyan']
    right = ['Red', 'Green', 'Blue']
    for i in mp_dict:
        _, _, completed_delta = analyser_mp.get_one_peg_kinematic_data_new(mp_dict, i)
        mp_intervals_completed = analyser_mp.get_MP_index_interval_completed(mp_dict, completed_delta, i)
        if i in right:
            length = calculate_motion_length(completed_delta, mp_intervals_completed[0][0], mp_intervals_completed[-1][1], scale, 'right')
        elif i in left:
            length = calculate_motion_length(completed_delta, mp_intervals_completed[0][0], mp_intervals_completed[-1][1], scale, 'left')
        peg_motion_length.append(length)

    return peg_motion_length

def get_mp_motion_length(mp_dict, analyser_mp, scale):
    motion_length = []
    left = ['Magenta', 'Yellow', 'Cyan']
    right = ['Red', 'Green', 'Blue']
    
    for i in mp_dict:
        #if len(mp_dict[i]) == 5 and mp_dict[i][0][0] == 'Touch' and mp_dict[i][4][0] == 'Release':
        _, _, completed_delta = analyser_mp.get_one_peg_kinematic_data_new(mp_dict, i)
        mp_intervals_completed = analyser_mp.get_MP_index_interval_completed(mp_dict, completed_delta, i)
        tg, gp, ut, te, rl = 0, 0, 0, 0, 0
        for j in range(len(mp_intervals_completed)):
            if i in right:
                length = calculate_motion_length(completed_delta, mp_intervals_completed[j][0], mp_intervals_completed[j][1], scale, 'right')
            elif i in left:
                length = calculate_motion_length(completed_delta, mp_intervals_completed[j][0], mp_intervals_completed[j][1], scale, 'left')

            if mp_dict[i][j][0] == 'Touch' and type(mp_dict[i][j][1]) != str:
                tg += length
            if mp_dict[i][j][0] == 'Grasp':
                gp += length
            if mp_dict[i][j][0] == 'Untouch':
                ut += length
            if mp_dict[i][j][0] == 'Touch' and type(mp_dict[i][j][1]) == str:
                te += length
            if mp_dict[i][j][0] == 'Release':
                rl += length
    
        motion_length.append([tg, gp, ut, te, rl])
    
    #ml = np.mean([sum(values) for values in motion_length])
    avg_mp_motion_length = [sum(values) / len(motion_length) for values in zip(*motion_length)]
    
    return avg_mp_motion_length

if __name__ == "__main__":
    root_address = "exp_data_new"
    netfolders = ['no_fault', 'packet_loss', 'delay', 'communication_loss']
    pos_scale = 0.15

    net_conditions = ['normal']

    transfer_ml_free = []
    transfer_ml_all = []

    mp_ml_free = []
    mp_ml_all = []

    for folder in netfolders:
        path = os.path.join(root_address, folder)
        for sub_folder in os.listdir(path): 
            sub_path = os.path.join(path, sub_folder)
            analyser_mp = AnalyserMP(sub_path)
            mp_dict = analyser_mp.get_MP_timestamp_error()
            motion_length = get_peg_transfer_motion_length(mp_dict, analyser_mp, pos_scale)
            motion_length_mp = get_mp_motion_length(mp_dict, analyser_mp, pos_scale)
            if sub_folder[0] == 'f':
                transfer_ml_free.append(np.mean(motion_length))
                mp_ml_free.append(motion_length_mp)
            else:
                net_conditions.append(sub_folder)
                transfer_ml_all.append(motion_length)
                mp_ml_all.append(motion_length_mp)
    
    mp_ml_free_mean = [sum(values) / len(mp_ml_free) for values in zip(*mp_ml_free)]
    mp_ml_all.insert(0, mp_ml_free_mean)
    #transfer_ml_free_mean = [sum(values) for values in zip(*transfer_ml_free)]
    
    data = np.array(mp_ml_all)
    std_normal = [np.std(transfer_ml_free), 0, 0, 0, 0, 0, 0, 0, 0, 0]
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

    plt.axhline(y=np.mean(transfer_ml_free), color='red', linestyle='--', label='Mean of Normal Condition')
    #plt.axhline(y=np.min(transfer_ml_free), color='green', linestyle='--', label='Best Mean of Normal Condition')
    plt.xticks(x, net_conditions, rotation=45, fontsize=12)
    plt.ylabel('Motion Length (m)', fontsize=13)
    plt.title('Average Peg Transfer Motion Length Across Network Conditions', fontsize=14)
    plt.grid(True, axis='y', linestyle='--', alpha=0.5)
    plt.legend(title="Baselines and MP Segments", bbox_to_anchor=(1, 1.02), loc='upper left')
    plt.tight_layout(pad=2.0)
    plt.show()


  
            
                
                    
                    