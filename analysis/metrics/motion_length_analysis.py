from Analyser_mp import *
import matplotlib.patches as mpatches
from matplotlib.legend_handler import HandlerTuple
from matplotlib.lines import Line2D
import matplotlib.lines as mlines
from matplotlib.container import ErrorbarContainer
from matplotlib.legend_handler import HandlerErrorbar

def calculate_motion_length(completed, interval_min, interval_max, scale, arm):
    motion_len = 0

    for i in range(interval_min, interval_max):
        if arm == 'left':
            motion_len += np.sqrt(completed[i][2]**2 + completed[i][3]**2 + completed[i][4]**2) * SIM_POS_SCALE * scale
        else:
            motion_len += np.sqrt(completed[i][8]**2 + completed[i][9]**2 + completed[i][10]**2) * SIM_POS_SCALE * scale
    
    return motion_len

def get_peg_transfer_motion_length_console(mp_dict, analyser_mp, scale):
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

def get_mp_motion_length_console(mp_dict, analyser_mp, scale):
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


def calculate_motion_length_robot(robot, interval_min, interval_max, arm):
    motion_len = 0

    for i in range(interval_min, interval_max):
        if arm == 'left':
            motion_len += np.sqrt(robot[i][0]**2 + robot[i][1]**2 + robot[i][2]**2)
        else:
            motion_len += np.sqrt(robot[i][6]**2 + robot[i][7]**2 + robot[i][8]**2)
    
    return motion_len


def get_peg_transfer_motion_length_robot(mp_dict, analyser_mp):
    peg_motion_length = []
    left = ['Magenta', 'Yellow', 'Cyan']
    right = ['Red', 'Green', 'Blue']
    for i in mp_dict:
        robot, _, _ = analyser_mp.get_one_peg_kinematic_data_new(mp_dict, i)
        mp_intervals_completed = analyser_mp.get_MP_index_interval_robot(mp_dict, robot, i)
        robot_delta = np.diff(robot[:, 2:], axis=0)
        if i in right:
            length = calculate_motion_length_robot(robot_delta, mp_intervals_completed[0][0], mp_intervals_completed[-1][1], 'right')
        elif i in left:
            length = calculate_motion_length_robot(robot_delta, mp_intervals_completed[0][0], mp_intervals_completed[-1][1], 'left')
        peg_motion_length.append(length)

    return peg_motion_length

def get_mp_motion_length_robot(mp_dict, analyser_mp):
    motion_length = []
    left = ['Magenta', 'Yellow', 'Cyan']
    right = ['Red', 'Green', 'Blue']
    
    for i in mp_dict:
        #if len(mp_dict[i]) == 5 and mp_dict[i][0][0] == 'Touch' and mp_dict[i][4][0] == 'Release':
        robot, _, _ = analyser_mp.get_one_peg_kinematic_data_new(mp_dict, i)
        mp_intervals_completed = analyser_mp.get_MP_index_interval_robot(mp_dict, robot, i)
        robot_delta = np.diff(robot[:, 2:], axis=0)
        tg, gp, ut, te, rl = 0, 0, 0, 0, 0
        for j in range(len(mp_intervals_completed)):
            if i in right:
                length = calculate_motion_length_robot(robot_delta, mp_intervals_completed[j][0], mp_intervals_completed[j][1], 'right')
            elif i in left:
                length = calculate_motion_length_robot(robot_delta, mp_intervals_completed[j][0], mp_intervals_completed[j][1], 'left')

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

    net_conditions = ['normal']

    transfer_ml_free_console = []
    transfer_ml_free_robot = []
    transfer_ml_all = []

    mp_ml_free_console = []
    mp_ml_all_console = []

    mp_ml_free_robot = []
    mp_ml_all_robot = []

    for folder in netfolders:
        path = os.path.join(root_address, folder)
        for sub_folder in os.listdir(path): 
            sub_path = os.path.join(path, sub_folder)
            analyser_mp = AnalyserMP(sub_path)
            mp_dict = analyser_mp.get_MP_timestamp_error()
            motion_length_console = get_peg_transfer_motion_length_console(mp_dict, analyser_mp, CONSOLE_SIM_SCALE)
            motion_length_mp_console = get_mp_motion_length_console(mp_dict, analyser_mp, CONSOLE_SIM_SCALE)
            motion_length_robot = get_peg_transfer_motion_length_robot(mp_dict, analyser_mp)
            motion_length_mp_robot = get_mp_motion_length_robot(mp_dict, analyser_mp)
            
            if sub_folder[0] == 'f':
                transfer_ml_free_console.append(np.mean(motion_length_console))
                transfer_ml_free_robot.append(np.mean(motion_length_robot))
                mp_ml_free_console.append(motion_length_mp_console)
                mp_ml_free_robot.append(motion_length_mp_robot)
            else:
                net_conditions.append(sub_folder)
                #transfer_ml_all.append(motion_length_console)
                mp_ml_all_console.append(motion_length_mp_console)
                mp_ml_all_robot.append(motion_length_mp_robot)
    
    mp_ml_free_mean1 = [sum(values) / len(mp_ml_free_console) for values in zip(*mp_ml_free_console)]
    mp_ml_free_mean2 = [sum(values) / len(mp_ml_free_robot) for values in zip(*mp_ml_free_robot)]
    
    mp_ml_all_console.insert(0, mp_ml_free_mean1)
    mp_ml_all_robot.insert(0, mp_ml_free_mean2)
    #transfer_ml_free_mean = [sum(values) for values in zip(*transfer_ml_free)]
    
    data_console = np.array(mp_ml_all_console)
    data_robot = np.array(mp_ml_all_robot)

    std_normal1 = [np.std(transfer_ml_free_robot), 0, 0, 0, 0, 0, 0, 0, 0, 0]
    std_normal2 = [np.std(transfer_ml_free_console), 0, 0, 0, 0, 0, 0, 0, 0, 0]
    #stds = [np.std(vals) for vals in transfer_ml_all]
    plt.figure(figsize=(18, 7), constrained_layout=True)

    colors = ["#A6CEE3", "#1F78B4", "#B2DF8A", "#33A02C", "#FB9A99"]

    category_labels = ['Touch Peg', 'Grasp', 'Untouch Start Pole', 'Touch Goal Pole', 'Release']

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
            if data_robot[j, i] > 0:
                plt.text(x1[j], bottom1[j] + data_robot[j, i]/2, f"{data_robot[j, i]:.2f}", ha='center', va='center', fontsize=8)
        bottom1 += data_robot[:, i]

        # Right bar stack (console)
        plt.bar(x2, data_console[:, i], bottom=bottom2, color=colors[i], width=bar_width, edgecolor='black', linewidth=1.2)  # transparent for contrast
        for j in range(len(net_conditions)):
            if data_console[j, i] > 0:
                plt.text(x2[j], bottom2[j] + data_console[j, i]/2, f"{data_console[j, i]:.2f}", ha='center', va='center', fontsize=8)
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

    std_dev_container1 = plt.errorbar(x1, bottom1, yerr=std_normal1, fmt='none', ecolor="#4D4D4D", capsize=6)
    std_dev_container2 = plt.errorbar(x2, bottom2, yerr=std_normal2, fmt='none', ecolor="#4D4D4D", capsize=6)
    # group_colors = ["#f9dad1", "#f0e4c0", "#e4d0f0"]  # light shades for clarity
    # group_bounds = [(0.5, 3.5), (3.5, 6.5), (6.5, len(net_conditions) - 0.5)]
    # for (left, right), color in zip(group_bounds, group_colors):
    #     plt.axvspan(left, right, facecolor=color, alpha=0.3)

    plt.axhline(y=np.mean(transfer_ml_free_console), color='red', linestyle='--')
    plt.axhline(y=np.mean(transfer_ml_free_robot), color='orange', linestyle='--')
    plt.xticks(x, net_conditions, rotation=45, fontsize=12)
    plt.ylabel('Motion Length (m)', fontsize=13)
    plt.title('Motion Length Comparison Across Network Conditions', fontsize=14)
    plt.grid(True, axis='y', linestyle='--', alpha=0.5)

    plt.legend(title="Motion Primitive Segments", bbox_to_anchor=(1, 1.02), loc='upper left')
    plt.legend(handles=[mean_console_line, mean_robot_line, robot_type, console_type] + [pair[0] for pair in legend_handles] + [std_dev_container1],
    labels=['Console Mean of Normal Condition', 'Robot Mean of Normal Condition', 'Robot Space(Left Bar)', 
            'Console Space(Right Bar)'] + [pair[1] for pair in legend_handles] + ['Std Dev'],
    handler_map={tuple: HandlerTuple(ndivide=None)},
    bbox_to_anchor=(1, 1.02), loc='upper left')   

    plt.tight_layout(pad=2.0)
    plt.show()


    # # Create stacked bars
    # plt.figure(figsize=(18, 7), constrained_layout=True)
    # for i in range(data.shape[1]):
    #     plt.bar(x, data[:, i], bottom=bottom, color=colors[i], width=bar_width, label=category_labels[i])
    #     # Add segment label
    #     for j in range(len(net_conditions)):
    #         if data[j, i] > 0:
    #             plt.text(x[j], bottom[j] + data[j, i] / 2, f"{data[j, i]:.2f}", ha='center', va='center', fontsize=8)
    #     bottom += data[:, i]

    # plt.errorbar(x, bottom, yerr=std_normal, fmt='none',ecolor='gray',capsize=5,label='Std Dev')
    # #plt.errorbar(x, bottom, fmt='none',ecolor='gray',capsize=5)  

    # plt.axhline(y=np.mean(transfer_ml_free), color='red', linestyle='--', label='Mean of Normal Condition')
    # #plt.axhline(y=np.min(transfer_ml_free), color='green', linestyle='--', label='Best Mean of Normal Condition')
    # plt.xticks(x, net_conditions, rotation=45, fontsize=12)
    # plt.ylabel('Motion Length (m)', fontsize=13)
    # plt.title('Average Peg Transfer Motion Length Across Network Conditions', fontsize=14)
    # plt.grid(True, axis='y', linestyle='--', alpha=0.5)
    # plt.legend(title="Baselines and MP Segments", bbox_to_anchor=(1, 1.02), loc='upper left')
    # plt.tight_layout(pad=2.0)
    # plt.show()


  
            
                
                    
                    