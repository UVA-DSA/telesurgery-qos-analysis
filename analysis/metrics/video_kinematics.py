import cv2
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

def align_console_kinematic_data_new(robot, completed):
        Tpos = np.array([[0, -1,  0],
                         [-1, 0,  0],
                         [0,  0, -1]])
        Trot = np.array([[0, 1, 0],
                         [1, 0, 0],
                         [0, 0, 1]]) 
        sf_pos = 0.000115 * 0.13     
        sf_rot = 0.12 * 0.3

        new_completed = np.zeros((len(robot), completed.shape[1]))
        r, c = new_completed.shape
          
        for i in range(r):
            e = np.argmin(np.abs(completed[:, 0] - robot[i, 0]))
            #e = np.where(completed[:, 1] == robot[i, 1])[0][0]
            new_completed[i, :] = completed[e, :] 
            pos0 = Tpos @ np.sum(completed[0:e+1, 2:5], axis=0) * sf_pos
            rot0 = Trot @ np.sum(completed[0:e+1, 5:8], axis=0) * sf_rot 
            pos1 = Tpos @ np.sum(completed[0:e+1, 8:11], axis=0) * sf_pos
            rot1 = Trot @ np.sum(completed[0:e+1, 11:14], axis=0) * sf_rot
            Ti = np.concatenate([pos0, rot0, pos1, rot1])
            new_completed[i, 2:14] = Ti
        
        return new_completed

def get_robot_grasper_commands(command_data):
        Left_Commands = command_data[:, -2]
        Right_Commands = command_data[:, -1]
        Left = np.zeros(len(Left_Commands))
        Right = np.zeros(len(Right_Commands))

        for i in range(len(Left_Commands)):
            if Left_Commands[i] < -0.7:
                Left[i] = 1
            if Right_Commands[i] < -0.7:
                Right[i] = 1

        return Left, Right

# Load trajectory data
# robot_data = pd.read_csv("exp_data_new/no_fault/freefault1/robot_sim_data_1.csv")
robot_data = np.loadtxt("exp_data_new/no_fault/freefault1/robot_sim_data_1.csv", delimiter=",", skiprows=1)
completed_data = np.loadtxt("exp_data_new/no_fault/freefault1/console_data_completed_1.csv", delimiter=",", skiprows=1)
command_data   = np.loadtxt("exp_data_new/no_fault/freefault1/console_data_sampled_1.csv", delimiter=",", skiprows=1)

completed_data[:, 0] *= 10**-9 
console_data = align_console_kinematic_data_new(robot_data, completed_data)
pedal_data = console_data[:, 16] * -1 + 1
left_grasper, right_grasper = get_robot_grasper_commands(command_data)

print(right_grasper.shape)

# Open video
cap = cv2.VideoCapture("exp_data_new/no_fault/freefault1/out_annotation_csv/free1_annotated.mp4")
fps = cap.get(cv2.CAP_PROP_FPS)

# Set up matplotlib for X, Y, Z vs time and pedal in separate subplots
plt.ion()
fig, axs = plt.subplots(5, 1, figsize=(10, 12), sharex=True)

traj_x, = axs[0].plot([], [], 'b-', label='Robot X')
traj_y, = axs[1].plot([], [], 'g-', label='Robot Y')
traj_z, = axs[2].plot([], [], 'r-', label='Robot Z')

# Add console data lines
console_traj_x, = axs[0].plot([], [], 'b--', label='Console X')
console_traj_y, = axs[1].plot([], [], 'g--', label='Console Y')
console_traj_z, = axs[2].plot([], [], 'r--', label='Console Z')

# Grasper plot for left grasper (axs[3] in first figure)
grasper_line, = axs[3].plot([], [], 'c-', label='Left Grasper')
axs[3].set_ylabel('Grasper')
axs[3].set_ylim(-0.1, 1.1)
axs[3].set_yticks([0, 1])
axs[3].set_yticklabels(['Open', 'Close'])
axs[3].legend()

# Pedal plot
pedal_line, = axs[4].plot([], [], 'm-', label='Pedal')
axs[4].set_ylabel('Pedal')
axs[4].set_ylim(-0.1, 1.1)
axs[4].set_yticks([0, 1])
axs[4].set_yticklabels(['Up', 'Down'])
axs[4].set_xlabel('Time (s)')
axs[4].legend()

print(console_data[0, 0])
min_time = min(robot_data[0, 0], console_data[0, 0])
max_time = max(robot_data[-1, 0] - robot_data[0, 0], console_data[-1, 0] - console_data[0, 0])
# Setup for left arm (columns 2, 3, 4)
for i, (ax, idx, label) in enumerate(zip(axs[:3], [2, 3, 4], ['X', 'Y', 'Z'])):
    ax.set_xlim(0, max_time)
    y_vals = np.concatenate([
        robot_data[:, idx] - robot_data[0, idx],
        console_data[:, idx] - console_data[0, idx]
    ])
    ax.set_ylim(y_vals.min(), y_vals.max())
    ax.set_ylabel(f'{label} Position')
    ax.legend()
axs[4].set_xlabel('Time (s)')
fig.suptitle('Left Robotic Arm Trajectory (X, Y, Z), Grasper, and Pedal vs Time')

# Second figure for X, Y, Z, Grasper, and Pedal
fig2, axs2 = plt.subplots(5, 1, figsize=(10, 12), sharex=True)

# Robot data lines
traj2_x, = axs2[0].plot([], [], 'b-', label='Robot X')
traj2_y, = axs2[1].plot([], [], 'g-', label='Robot Y')
traj2_z, = axs2[2].plot([], [], 'r-', label='Robot Z')

# Console data lines
console2_traj_x, = axs2[0].plot([], [], 'b--', label='Console X')
console2_traj_y, = axs2[1].plot([], [], 'g--', label='Console Y')
console2_traj_z, = axs2[2].plot([], [], 'r--', label='Console Z')

# Grasper plot for right grasper (axs2[3] in second figure)
grasper2_line, = axs2[3].plot([], [], 'c-', label='Right Grasper')
axs2[3].set_ylabel('Grasper')
axs2[3].set_ylim(-0.1, 1.1)
axs2[3].set_yticks([0, 1])
axs2[3].set_yticklabels(['Open', 'Close'])
axs2[3].legend()

# Pedal
pedal2_line, = axs2[4].plot([], [], 'm-', label='Pedal')
axs2[4].set_ylabel('Pedal')
axs2[4].set_ylim(-0.1, 1.1)
axs2[4].set_yticks([0, 1])
axs2[4].set_yticklabels(['Up', 'Down'])
axs2[4].set_xlabel('Time (s)')
axs2[4].legend()

# Setup for right arm (columns 8, 9, 10)
for i, (ax, idx, label) in enumerate(zip(axs2[:3], [8, 9, 10], ['X', 'Y', 'Z'])):
    ax.set_xlim(0, max_time)
    y_vals = np.concatenate([
        robot_data[:, idx] - robot_data[0, idx],
        console_data[:, idx] - console_data[0, idx]
    ])
    ax.set_ylim(y_vals.min(), y_vals.max())
    ax.set_ylabel(f'{label} Position')
    ax.legend()
fig2.suptitle('Right Robotic Arm Trajectory (X, Y, Z), Grasper, and Pedal vs Time')

frame_idx = 0
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Resize the frame to half its original size (adjust as needed)
    frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
    time = frame_idx / fps
    timestamp = robot_data[0, 0] + time

    # Robot data
    mask = robot_data[:, 0] <= timestamp
    t_vals = robot_data[mask, 0] - robot_data[0, 0]
    # Robot data for left arm
    x_vals = robot_data[mask, 2] - robot_data[0, 2]
    y_vals = robot_data[mask, 3] - robot_data[0, 3]
    z_vals = robot_data[mask, 4] - robot_data[0, 4]
    traj_x.set_data(t_vals, x_vals)
    traj_y.set_data(t_vals, y_vals)
    traj_z.set_data(t_vals, z_vals)

    # Console data for left arm
    mask_c = console_data[:, 0] <= timestamp
    t_vals_c = console_data[mask_c, 0] - console_data[0, 0]
    x_vals_c = console_data[mask_c, 2] - console_data[0, 2]
    y_vals_c = console_data[mask_c, 3] - console_data[0, 3]
    z_vals_c = console_data[mask_c, 4] - console_data[0, 4]
    console_traj_x.set_data(t_vals_c, x_vals_c)
    console_traj_y.set_data(t_vals_c, y_vals_c)
    console_traj_z.set_data(t_vals_c, z_vals_c)

    # Pedal data (plot up to current time)
    pedal_t = t_vals_c  # Use console time for pedal
    pedal_y = pedal_data[mask_c]
    pedal_line.set_data(pedal_t, pedal_y)

    # Grasper data (plot up to current time) for left grasper
    grasper_t = t_vals_c  # Use console time for grasper
    grasper_y = left_grasper[mask_c]
    grasper_line.set_data(grasper_t, grasper_y)

    axs[0].set_title(f"Current Time: {time:.2f}s")
    for ax in axs:
        ax.legend()
    plt.draw()

    # Update second figure (right arm)
    x2_vals = robot_data[mask, 8] - robot_data[0, 8]
    y2_vals = robot_data[mask, 9] - robot_data[0, 9]
    z2_vals = robot_data[mask, 10] - robot_data[0, 10]
    traj2_x.set_data(t_vals, x2_vals)
    traj2_y.set_data(t_vals, y2_vals)
    traj2_z.set_data(t_vals, z2_vals)

    x2_vals_c = console_data[mask_c, 8] - console_data[0, 8]
    y2_vals_c = console_data[mask_c, 9] - console_data[0, 9]
    z2_vals_c = console_data[mask_c, 10] - console_data[0, 10]
    console2_traj_x.set_data(t_vals_c, x2_vals_c)
    console2_traj_y.set_data(t_vals_c, y2_vals_c)
    console2_traj_z.set_data(t_vals_c, z2_vals_c)

    pedal2_line.set_data(pedal_t, pedal_y)
    grasper2_line.set_data(grasper_t, right_grasper[mask_c])
    for ax in axs2:
        ax.legend()
    axs2[0].set_title(f"Current Time: {time:.2f}s")
    fig2.canvas.draw_idle()

    cv2.imshow('Video Playback', frame)
    if cv2.waitKey(int(1000 / fps)) & 0xFF == ord('q'):
        break

    frame_idx += 1

cap.release()
cv2.destroyAllWindows()
plt.ioff()
plt.show()
