from Analyser_mp import *

def calculate_pedal_usage(completed, interval_min, interval_max):
    pedal_data = completed[interval_min:interval_max+1, 16]
    diff = np.diff(pedal_data)
    starts = np.where(diff == -1)[0]

    return len(starts)

def get_pedal_usage(mp_dict):
    pedal_usage = []
    for i in mp_dict:
        tg, gp, ut, te, rl = 0, 0, 0, 0, 0
        _, _, completed = analyser_mp.get_one_peg_kinematic_data_new(mp_dict, i)
        mp_intervals_completed = analyser_mp.get_MP_index_interval_completed(mp_dict, completed, i)
        for j in range(len(mp_intervals_completed)):
            pedal = calculate_pedal_usage(completed, mp_intervals_completed[j][0], mp_intervals_completed[j][1])
            if mp_dict[i][j][0] == 'Touch' and type(mp_dict[i][j][1]) != str:
                tg += pedal
            if mp_dict[i][j][0] == 'Grasp':
                gp += pedal
            if mp_dict[i][j][0] == 'Untouch':
                ut += pedal
            if mp_dict[i][j][0] == 'Touch' and type(mp_dict[i][j][1]) == str:
                te += pedal
            if mp_dict[i][j][0] == 'Release':
                rl += pedal
    
        pedal_usage.append([tg, gp, ut, te, rl])
    
    avg_mp_pedal_usage = [sum(values) for values in zip(*pedal_usage)]
    
    return avg_mp_pedal_usage 

def plot_stacked_barchart(net_conditions, pedal_all, pedal_free):
    data = np.array(pedal_all)
    std_normal = [np.std(pedal_free), 0, 0, 0, 0, 0, 0, 0, 0, 0]
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
                plt.text(x[j], bottom[j] + data[j, i] / 2, f"{data[j, i]}", ha='center', va='center', fontsize=8)
        bottom += data[:, i]

    plt.errorbar(x, bottom, yerr=std_normal, fmt='none',ecolor='gray',capsize=5,label='Std Dev')
    #plt.errorbar(x, bottom, fmt='none',ecolor='gray',capsize=5)  

    plt.axhline(y=np.sum(pedal_all[0]), color='red', linestyle='--', label='Mean of Normal Condition')
    #plt.axhline(y=np.min(transfer_ml_free), color='green', linestyle='--', label='Best Mean of Normal Condition')
    plt.xticks(x, net_conditions, rotation=45, fontsize=12)
    plt.ylabel('Pedal Usage (times)', fontsize=13)
    plt.title('All 6 Peg Transfers Padel Usage Across Network Conditions', fontsize=14)
    plt.grid(True, axis='y', linestyle='--', alpha=0.5)
    plt.legend(title="Baselines and MP Segments", bbox_to_anchor=(1, 1.02), loc='upper left')
    plt.tight_layout(pad=2.0)
    plt.show()

if __name__ == "__main__":
    root_address = "exp_data_new"
    netfolders = ['no_fault', 'packet_loss', 'delay', 'communication_loss']

    net_conditions = ['normal']

    mp_pedal_free = []

    transfer_pedal_free = []
    transfer_pedal_all = []

    for folder in netfolders:
        path = os.path.join(root_address, folder)
        for sub_folder in os.listdir(path): 
            sub_path = os.path.join(path, sub_folder)
            analyser_mp = AnalyserMP(sub_path)
            mp_dict = analyser_mp.get_MP_timestamp_error()
            pedal_transfer = get_pedal_usage(mp_dict)
            if sub_folder[0] == 'f':
                mp_pedal_free.append(pedal_transfer)
                transfer_pedal_free.append(np.sum(pedal_transfer))
            else:
                net_conditions.append(sub_folder)
                transfer_pedal_all.append(pedal_transfer)

    avg_mp_pedal_free = [int(sum(values) / len(mp_pedal_free)) for values in zip(*mp_pedal_free)]
    transfer_pedal_all.insert(0, avg_mp_pedal_free)
    plot_stacked_barchart(net_conditions, transfer_pedal_all, transfer_pedal_free)


    # means = [np.mean(vals) for vals in transfer_pedal_fault]
    # stds = [np.std(vals) for vals in transfer_pedal_fault]

    # colors = ["#3a9ad5", "#3a9ad5", "#3a9ad5", "#DB702E","#DB702E", "#DB702E", "#CA2EDB","#CA2EDB", "#CA2EDB"]
    # bar_width = 0.6
    # # Create bar chart with error bars
    # plt.figure(figsize=(12, 6))
    # plt.bar(net_conditions, means, yerr=stds, capsize=8, alpha=0.9, color=colors, width=bar_width)

    # # Reference lines from normal condition
    # plt.axhline(y=int(np.mean(transfer_pedal_free)), color='red', linestyle='--', label='Mean of Normal Condition')
    # plt.axhline(y=np.min(transfer_pedal_free), color='green', linestyle='--', label='Best Mean of Normal Condition')

    # # Labels and formatting
    # plt.title('Total Numbers of Pedal Usage for Each Peg Transfer Across Network Conditions', fontsize=14)
    # plt.ylabel('Times', fontsize=14)
    # plt.xticks(rotation=45, fontsize=12)
    # plt.yticks(fontsize=12)
    # plt.grid(True, linestyle='--', alpha=0.6)
    # plt.tight_layout()
    # plt.legend()
    # plt.show()