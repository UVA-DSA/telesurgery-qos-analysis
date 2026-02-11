import time
import os
import numpy as np
import pandas as pd

class DataLogger:
    def __init__(self, filename, p, d, c, model, num, user_num, buffer_size=300):
        # Determine directory
        if p:
            subdir = "packet_loss"
        elif d:
            subdir = "delay"
        elif c:
            subdir = "communication_loss"
        else:
            subdir = "no_fault"

        # Construct file path
        self.dir_path = os.path.join(os.path.dirname(__file__),"Data/exp_data_"+ user_num +f"/{subdir}/" + model + "/")
        os.makedirs(self.dir_path, exist_ok=True)  # Ensure directory exists
        self.addr = f"{self.dir_path}{filename}_{num}.csv"

        # Define column names
        if filename == "console_data_recieved":
            self.column_names = ["time_stamp", "sequence_number", 
                                 "pos0_x", "pos0_y", "pos0_z", 
                                 "rot0_x", "rot0_y", "rot0_z", 
                                 "pos1_x", "pos1_y", "pos1_z", 
                                 "rot1_x", "rot1_y", "rot1_z", 
                                 "grasper0", "grasper1", "pedal"]
        elif filename == "robot_command_data":
            self.column_names = ["time_stamp", "sequence_number", 
                                 "pos0_x", "pos0_y", "pos0_z", 
                                 "rot0_x", "rot0_y", "rot0_z", 
                                 "pos1_x", "pos1_y", "pos1_z", 
                                 "rot1_x", "rot1_y", "rot1_z", 
                                 "grasper0", "grasper1"]
        elif filename == "robot_sim_data":
            self.column_names = ["time_stamp", "sequence_number", 
                                 "pos0_x", "pos0_y", "pos0_z", 
                                 "rot0_x", "rot0_y", "rot0_z", 
                                 "pos1_x", "pos1_y", "pos1_z", 
                                 "rot1_x", "rot1_y", "rot1_z"]
            
        # Store data in memory before writing
        self.buffer = []
        self.buffer_size = buffer_size

    def log_data_recieved(self, ts, sequence, delta_pos_0, delta_rot_0, delta_pos_1, delta_rot_1, grasp0, grasp1, surgeon_mode):
        # Convert inputs to lists
        ts = [ts] 
        sequence = [sequence] 
        delta_pos_0 = np.array(delta_pos_0).tolist()
        delta_rot_0 = np.array(delta_rot_0).tolist()
        delta_pos_1 = np.array(delta_pos_1).tolist()
        delta_rot_1 = np.array(delta_rot_1).tolist()
        grasp0 = [grasp0] 
        grasp1 = [grasp1] 
        surgeon_mode = [surgeon_mode] 

        # Combine all values into a single row
        row_data = ts + sequence + delta_pos_0 + delta_rot_0 + delta_pos_1 + delta_rot_1 + grasp0 + grasp1 + surgeon_mode
        self.buffer.append(row_data)

        # Write to file when buffer is full
        if len(self.buffer) >= self.buffer_size:
            self.flush_to_file()

    def log_data_sampled(self, ts, sequence, delta_pos_0, delta_rot_0, delta_pos_1, delta_rot_1, grasp0, grasp1):
        # Convert inputs to lists
        ts = [ts] 
        sequence = [sequence] 
        delta_pos_0 = np.array(delta_pos_0).tolist()
        delta_rot_0 = np.array(delta_rot_0).tolist()
        delta_pos_1 = np.array(delta_pos_1).tolist()
        delta_rot_1 = np.array(delta_rot_1).tolist()
        grasp0 = [grasp0] 
        grasp1 = [grasp1] 
        # Combine all values into a single row
        row_data = ts + sequence + delta_pos_0 + delta_rot_0 + delta_pos_1 + delta_rot_1 + grasp0 + grasp1
        self.buffer.append(row_data)

        # Write to file when buffer is full
        if len(self.buffer) >= self.buffer_size:
            self.flush_to_file()
    
    def log_data_sim(self, ts, sequence, delta_pos_0, delta_rot_0, delta_pos_1, delta_rot_1):
        # Convert inputs to lists
        ts = [ts] 
        sequence = [sequence] 
        delta_pos_0 = np.array(delta_pos_0).tolist()
        delta_rot_0 = np.array(delta_rot_0).tolist()
        delta_pos_1 = np.array(delta_pos_1).tolist()
        delta_rot_1 = np.array(delta_rot_1).tolist()

        # Combine all values into a single row
        row_data = ts + sequence + delta_pos_0 + delta_rot_0 + delta_pos_1 + delta_rot_1
        self.buffer.append(row_data)

        # Write to file when buffer is full
        if len(self.buffer) >= self.buffer_size:
            self.flush_to_file()

    def flush_to_file(self):
        """Writes buffered data to file."""
        if not self.buffer:
            return

        df = pd.DataFrame(self.buffer, columns=self.column_names)
        df.to_csv(self.addr, mode='a', header=not os.path.exists(self.addr), index=False)

        # Clear buffer after writing
        self.buffer = []

    def close(self):
        """Flush remaining data before closing."""
        self.flush_to_file()