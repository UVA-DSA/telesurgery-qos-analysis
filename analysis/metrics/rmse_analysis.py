from Analyser_mp import *

def plot_trjactory_pos(robot,completed, scale, grasper, arm):
    t = np.linspace(0, int(robot[-1, 0] - robot[0, 0]), len(robot))
    # mp_intervals = mp_intervals - mp_intervals[0][0]
    colors = ['skyblue', 'lightgreen', 'yellow', 'orchid', '#FFD580']

    fig, axs = plt.subplots(5, 1, sharex=True, figsize=(12, 10), gridspec_kw={'height_ratios': [3, 3, 3, 1, 1]})

    if arm == 'left':
        j = 2
    else: 
        j = 8

    for i, pos_label in enumerate(['X', 'Y', 'Z']):
        ri = robot[:, i+j] - robot[0, i+j]
        #ti = transformed[:, i+j] * scale
        ci = completed[:, i+j] * scale
    
        ax = axs[i]
    
        # for j, mp in enumerate(mp_intervals):
        #     if (mp[0] != mp[1]):
        #         ax.axvspan(t[mp[0]], t[mp[1]-1], color=colors[j], alpha=0.3)

        ax.plot(t, ci, label='Complete Console Trajectory ' + pos_label, alpha=0.7, linewidth=2)
        #ax.plot(t, ti, label='Emulated Console Trajectory ' + pos_label, alpha=0.7, linewidth=2)
        ax.plot(t, ri, label='Sim Robot Trajectory ' + pos_label, alpha=0.7, linewidth=2)
        ax.set_ylabel(f'{pos_label} (m)', fontsize=13)
        ax.tick_params(axis='both', labelsize=11)
        if pos_label == 'Z' or pos_label == 'Y':
            ax.legend(loc='upper right', prop={'size': 8})
        else:
            ax.legend(loc='lower right', prop={'size': 8})

    pi = completed[:, 16] * -1 + 1# Pedal signal
    ax_grasper = axs[3]
    ax_pedal = axs[4]
    
    # Pedal signal subplot
    # for j, mp in enumerate(mp_intervals):
    #     if (mp[0] != mp[1]):
    #         ax_pedal.axvspan(t[mp[0]], t[mp[1]-1], color=colors[j % len(colors)], alpha=0.3)

    ax_grasper.plot(t, grasper, label='Grasper Status', color='red', alpha=0.6, linewidth=2)
    ax_grasper.set_xlabel('Time (s)', fontsize=14)
    ax_grasper.set_ylabel('Grasper', fontsize=14)
    ax_grasper.set_yticks([0, 1])
    ax_grasper.set_yticklabels(['Open', 'Close'])
    ax_grasper.tick_params(axis='both', labelsize=12)
    ax_grasper.legend(prop={'size': 8})

    ax_pedal.plot(t, pi, label='Pedal Signal', color='red', alpha=0.6, linewidth=2)
    ax_pedal.set_xlabel('Time (s)', fontsize=14)
    ax_pedal.set_ylabel('Pedal', fontsize=14)
    ax_pedal.set_yticks([0, 1])
    ax_pedal.set_yticklabels(['Up', 'Down'])
    ax_pedal.tick_params(axis='both', labelsize=12)
    ax_pedal.legend(prop={'size': 8})

    #axs[-1].set_xlabel('Time (s)', fontsize=14)
    plt.suptitle(f'Position Trajectories with Pedal Signal')
    plt.tight_layout()
    plt.show()

def get_RMSE_robot_console(mp_dict, analyser_mp, scale):
    right = ['Red', 'Green', 'Blue']
    left = ['Magenta', 'Yellow', 'Cyan']

    for i in mp_dict:
        if len(mp_dict[i]) == 5 and mp_dict[i][0][0] == 'Touch' and mp_dict[i][4][0] == 'Release':
            print(i)
            robot, transformed_delta, completed_delta = analyser_mp.get_one_peg_kinematic_data_new(mp_dict, i)
            robot, transformed, completed = analyser_mp.align_console_kinematic_data_new(robot, transformed_delta, completed_delta)
            Lgrasper, Rgrasper = analyser_mp.get_robot_grasper_commands(transformed)
            if i in right and len(robot) == len(completed):
                plot_trjactory_pos(robot, completed, scale, Rgrasper, 'right')
            if i in left and len(robot) == len(completed):
                plot_trjactory_pos(robot, completed, scale, Lgrasper, 'left')

if __name__ == "__main__":
    root_address = "exp_data_new"
    netfolders = ['no_fault', 'packet_loss', 'delay', 'communication_loss']
    scale = 0.15
    for folder in netfolders:
        path = os.path.join(root_address, folder)
        for sub_folder in os.listdir(path): 
            print(sub_folder)
            sub_path = os.path.join(path, sub_folder)
            analyser_mp = AnalyserMP(sub_path)
            mp_dict = analyser_mp.get_MP_timestamp_error()
            get_RMSE_robot_console(mp_dict, analyser_mp, scale)