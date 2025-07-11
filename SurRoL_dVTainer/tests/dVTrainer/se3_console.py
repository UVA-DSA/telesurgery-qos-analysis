# Copyright (c) 2024, The Isaac Lab Project Developer: Zhaomeng Zhang.
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Raven II Console controller for SE(3) control."""
import socket
import struct
import threading
import numpy as np
from collections import namedtuple
from collections.abc import Callable
from scipy.spatial.transform import Rotation as R
from omni.isaac.core.prims import RigidPrimView
from omni.isaac.core.utils.rotations import quat_to_euler_angles
import time
import json
import os
import queue
#from interception import Interception
from pyge.emulators.packet_loss_emulator import PacketLossEmulator
from pyge.emulators.delay_emulator import DelayEmulator
from pyge.emulators.packet_logger_emulator import PacketLoggerEmulator
from obs_controller import OBSController
from random_experiment_new import select_netfault
from random_experiment_new import user_num
from data_collector import DataLogger

class Se3Console:
    
    """
    The command comprises of two parts:

    * delta pose: a 6D vector of (x, y, z, roll, pitch, y
￼
    """
    fields = 'sequence pactyp version delx0 delx1 dely0 dely1 delz0 delz1 Qx0 Qx1 Qy0 Qy1 Qz0 Qz1 Qw0 Qw1 buttonstate0 buttonstate1 grasp0 grasp1 surgeon_mode checksum'.split()
    UStruct = namedtuple('UStruct', fields)
    format_str = '<IIIiiiiiiddddddddiiiiii'
    MAX_GRASP_ITP = 75
    #mapping_ratio = 0.025
    mapping_ratio = 2 / 2458
    position_scaler = 1000
    

    def __init__(self, pos_sensitivity: float = 0.4, rot_sensitivity: float = 0.8):
        """
        Args:
            pos_sensitivity: Magnitude of input position command scaling. Defaults to 0.05.
            rot_sensitivity: Magnitude of scale input rotation commands scaling. Defaults to 0.5.
        """
        # udp connection with console
        self._init_sock_udp()
        # store inputs
        self.pos_sensitivity = pos_sensitivity
        self.rot_sensitivity = rot_sensitivity

        self.udp_queue = queue.Queue()
        self.transform_queue = queue.Queue()
        self.request_event = threading.Event()

        # Initial action bool
        self.action_complete = False
        self.EMULATOR_PORT = 36000
        self.RECEIVER_PORT = 5001
        config_path = "source/standalone/environments/teleoperation/PyGE/src/pyge/canonical_configs"
        config_path_packetloss = config_path + "/packet_loss_config.json"
        config_path_delay = config_path + "/delay_config.json"
        numbers = 1
        self.packet_loss_enabled, self.delay_enabled, self.communication_loss_enabled, self.model_str, self.trial_num = select_netfault("network_conditions.txt", config_path, numbers)
        filename = "console_data_complete"

        if self.packet_loss_enabled:
            self.dir_path = f"Data/exp_data_"+ str(user_num) +"/packet_loss/" + self.model_str + "/"
            os.makedirs(self.dir_path, exist_ok=True)
            self.LOG_FILE = f"{self.dir_path}{filename}_{self.trial_num}.bin"
            with open(config_path_packetloss, 'r') as f:
                params = json.load(f)
            self.packetloss = PacketLossEmulator(input_port=self.EMULATOR_PORT,output_port=self.RECEIVER_PORT, model_name='GE_Pareto_BLL', 
                                                 params=params, protocol='udp', log_packets=True, log_path=self.LOG_FILE)
            self.packetloss.start()
            print("Packet Loss Enabled")
        elif self.delay_enabled:
            self.dir_path = f"Data/exp_data_"+ str(user_num) +"/delay/" + self.model_str + "/"
            os.makedirs(self.dir_path, exist_ok=True)
            self.LOG_FILE = f"{self.dir_path}{filename}_{self.trial_num}.bin"
            with open(config_path_delay, 'r') as f:
                params = json.load(f)
            self.delay = DelayEmulator(input_port=self.EMULATOR_PORT,output_port=self.RECEIVER_PORT, network_type='5G',
                                       params=params,protocol='udp', log_packets=True, log_path=self.LOG_FILE)
            self.delay.start()
            print("Delay Enabled")
        elif self.communication_loss_enabled:
            self.dir_path = f"Data/exp_data_"+ str(user_num) +"/communication_loss/" + self.model_str + "/"
            os.makedirs(self.dir_path, exist_ok=True)
            self.LOG_FILE = f"{self.dir_path}{filename}_{self.trial_num}.bin"
            with open(config_path_packetloss, 'r') as f:
                params = json.load(f)
            self.packetloss = PacketLossEmulator(input_port=self.EMULATOR_PORT,output_port=self.RECEIVER_PORT, model_name='Communication_Loss', 
                                                 params=params, protocol='udp', log_packets=True, log_path=self.LOG_FILE)
            self.packetloss.start()
            print("Communication Loss Enabled")
        else:
            self.dir_path = f"Data/exp_data_"+ str(user_num) +"/no_fault/" + self.model_str + "/"
            os.makedirs(self.dir_path, exist_ok=True)
            self.LOG_FILE = f"{self.dir_path}{filename}_{self.trial_num}.bin"
            self.nofault = PacketLoggerEmulator(input_port=self.EMULATOR_PORT,output_port=self.RECEIVER_PORT,
                                                protocol='udp', log_path=self.LOG_FILE)
            self.nofault.start()
            print("No Net Fault Enabled")
        
        self.logger1 = DataLogger("console_data_recieved", self.packet_loss_enabled, self.delay_enabled, self.communication_loss_enabled, self.model_str, self.trial_num, str(user_num), buffer_size=200)
        self.logger2 = DataLogger("console_data_sampled", self.packet_loss_enabled, self.delay_enabled, self.communication_loss_enabled, self.model_str, self.trial_num, str(user_num), buffer_size=200)
        
        # command buffers
        self.sequence_num = 0
        self._left_val = 0
        self._right_val = 0
        self._gripper_0 = 0
        self._delta_pos_0 = np.zeros(3)  # (x, y, z)
        self._delta_rot_0 = np.zeros(3)  # (roll, pitch, yaw)
        self._gripper_1 = 0
        self._delta_pos_1 = np.zeros(3)  # (x, y, z)
        self._delta_rot_1 = np.zeros(3)  # (roll, pitch, yaw)
        
        self._delta_pos_0_sum = np.zeros(3)
        self._delta_rot_0_sum = np.zeros(3)
        self._delta_pos_1_sum = np.zeros(3)
        self._delta_rot_1_sum = np.zeros(3)

        self.prim_ee_1 = RigidPrimView("/World/envs/env_0/Robot_1/psm_tool_tip_link")
        self.prim_ee_2 = RigidPrimView("/World/envs/env_0/Robot_2/psm_tool_tip_link")
    
        self.R_ce = np.array([[0, 1, 0],
                              [1, 0, 0],
                              [0, 0, 1]])
        
        # dictionary for additional callbacks
        self._additional_callbacks = dict()
        self.obs = OBSController("localhost", 4455, "rYIh2EvZGlDxDV0L")
        self.obs.connect()
        
        self.recording = False

        # Start listening for UDP packets
        self.start_listening()
        self.transform_listening()

    def _init_sock_udp(self):
        # Create a UDP socket and the data struct ----------------------------------------------------
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(2)
        #ip, port = ('0.0.0.0', 5001)
        ip, port = ('127.0.0.1', 5001)
        self.sock.bind((ip, port))
        print(f"Initialized a UDP server on IP: {ip} and port: {port}")
        print("Listening for incoming data: \n")

    def get_sequence_num(self):
        return self.sequence_num

    def reset(self):
        # default flags
        self._gripper_0 = 0
        self._delta_pos_0 = np.zeros(3)  # (x, y, z)
        self._delta_rot_0 = np.zeros(3)  # (roll, pitch, yaw)
        self._gripper_1 = 0
        self._delta_pos_1 = np.zeros(3)  # (x, y, z)
        self._delta_rot_1 = np.zeros(3)  # (roll, pitch, yaw)

    def add_callback(self, key: str, func: Callable):
        """
        Args:
            key: The keyboard button to check against.
            func: The function to call when key is pressed. The callback function should not
                take any arguments.
        """
        self._additional_callbacks[key] = func

    def advance(self) -> tuple[np.ndarray, float, np.ndarray, float]:
        """Provides the result from keyboard event state.

        Returns:
            A tuple containing the delta pose command and gripper commands.
        """
         
        self.request_event.set()
        if not self.transform_queue.empty():
            commands = self.transform_queue.get()
        else:
            commands = (np.zeros(6), self._gripper_0,
                        np.zeros(6), self._gripper_1)
            self.logger2.log_data_sampled(time.time(), self.sequence_num, np.zeros(3), np.zeros(3), 
                                          np.zeros(3), np.zeros(3), self._gripper_0, self._gripper_1)
        
        # return the command and gripper state
        return commands

    """
    Internal helpers.
    """
    def transform_console_data(self):
        self._delta_pos_0 = self._position_transform(self._delta_pos_0_sum)
        self._delta_pos_1 = self._position_transform(self._delta_pos_1_sum)
        self._delta_rot_0, ee_euler0 = self._orientation_transform(self._delta_rot_0_sum, self.prim_ee_1)
        self._delta_rot_1, ee_euler1 = self._orientation_transform(self._delta_rot_1_sum, self.prim_ee_2)

        # convert to rotation vector
        rot_vec_0 = R.from_euler("XYZ", self._delta_rot_0).as_rotvec()
        rot_vec_1 = R.from_euler("XYZ", self._delta_rot_1).as_rotvec()

        self._gripper_0 = self._map_grasper(self._left_val)
        self._gripper_1 = self._map_grasper(self._right_val)

        return [self._delta_pos_0, self._delta_rot_0, self._delta_pos_1, self._delta_rot_1, 
                ee_euler0, ee_euler1, rot_vec_0, rot_vec_1, self._gripper_0, self._gripper_1]

    def _map_grasper(self, grasp_i):
        return 1 - (grasp_i * self.mapping_ratio)

    def quaternion_to_rotation_matrix(self, quaternion):
    
        w, x, y, z = quaternion

        # Calculate the elements of the rotation matrix
        R = np.array([[1 - 2*y**2 - 2*z**2, 2*x*y - 2*w*z,     2*x*z + 2*w*y],
                      [2*x*y + 2*w*z,     1 - 2*x**2 - 2*z**2, 2*y*z - 2*w*x],
                      [2*x*z - 2*w*y,     2*y*z + 2*w*x,     1 - 2*x**2 - 2*y**2]])

        return R

    def _orientation_transform(self, delta_rot, prim_ee):

        _, orientation = prim_ee.get_local_poses()
        rot = orientation.squeeze(0).cpu().numpy()
        R_re_euler = quat_to_euler_angles(rot, degrees=False)
        R_re_mat = R.from_euler('xyz', R_re_euler).as_matrix()

        R_ee_euler = self.R_ce @ delta_rot
        R_ee_mat = R.from_euler('xyz', R_ee_euler).as_matrix()
            
        R_rr = R_re_mat @ R_ee_mat @ R_re_mat.T

        new_delta_rot = R.from_matrix(R_rr).as_euler('xyz', False)

        #self.R_rc = self.R_rc @ R.from_euler('xyz', -delta_rot).as_matrix()
        return new_delta_rot, R_ee_euler

    def _position_transform(self, delta_pos):
        R_transform = np.array([[0, -1,  0],
                                [-1, 0,  0],
                                [0,  0, -1]])

        delta_pos = delta_pos * self.pos_sensitivity
        new_delta_pos = R_transform @ delta_pos

        return new_delta_pos


    def _unpack_data(self, data):
        unpacked_data = struct.unpack(self.format_str, data)
        return self.UStruct(*unpacked_data)

    def _get_psm_vars(self, command, index):
        deltaX = command[f'delx{index}']
        deltaY = command[f'dely{index}']
        deltaZ = command[f'delz{index}']

        deltaQx = command[f'Qx{index}']
        deltaQy = command[f'Qy{index}']
        deltaQz = command[f'Qz{index}']
        #deltaQw = command[f'Qw{index}']

        delta_grasp = command[f'grasp{index}']

        return ((deltaX, deltaY, deltaZ), (deltaQx, deltaQy, deltaQz), delta_grasp)
    
    def get_packet_data(self, command):
        sequence = command[f'sequence']
        surgeon_mode = command[f'surgeon_mode'] 

        return sequence, surgeon_mode

    def update_delta_variables_dual(self, sequence, delta_position0, delta_position1, delta_orientation0, delta_orientation1, delta_grasp0, delta_grasp1, surgeon_mode):
        self._left_val = delta_grasp0
        self._right_val = delta_grasp1
        

        delta_pos_0 = np.array(delta_position0)
        delta_rot_0 = np.array(delta_orientation0)
        delta_pos_1 = np.array(delta_position1) 
        delta_rot_1 = np.array(delta_orientation1)
        
        if self.action_complete:
            current_time = time.time()
            self.logger1.log_data_recieved(current_time, sequence, delta_pos_0, delta_rot_0, 
                                           delta_pos_1, delta_rot_1, delta_grasp0, delta_grasp1, surgeon_mode)
            
            if not np.all(delta_pos_0 == np.zeros(3)):    
                self._delta_pos_0_sum += delta_pos_0 * 0.02

            if not np.all(delta_rot_0 == np.zeros(3)):
                self._delta_rot_0_sum += delta_rot_0 * 0.04

            if not np.all(delta_pos_1 == np.zeros(3)):    
                self._delta_pos_1_sum += delta_pos_1 * 0.02

            if not np.all(delta_rot_1 == np.zeros(3)):
                self._delta_rot_1_sum += delta_rot_1 * 0.04
        
    def update_delta_variables_right(self, delta_position, delta_orientation, delta_grasp):
        if (delta_grasp > 0):
            self._right_val += 1 
            self._right_val = max(min(self.MAX_GRASP_ITP, self._right_val),0)
        elif (delta_grasp < 0):
            self._right_val -= 1 
            self._right_val = max(min(self.MAX_GRASP_ITP, self._right_val),0)

        delta_pos_1 = np.array(delta_position) 
        delta_rot_1 = np.array(delta_orientation) 

        if self.action_complete:
            if not np.all(delta_pos_1 == np.zeros(3)):    
                self._delta_pos_1_sum += delta_pos_1 * 0.03

            if not np.all(delta_rot_1 == np.zeros(3)):
                self._delta_rot_1_sum += delta_rot_1 * 0.03

    # Frequency: 653HZ
    def receive_udp_packets(self):
        """Continuously listens for UDP packets and updates the internal state."""
        while True:
            try:
                data, addr = self.sock.recvfrom(1024)  # Buffer size of 1024 bytes
                u_struct = self._unpack_data(data)
                command = u_struct._asdict()
                self.udp_queue.put(command)
                
            except socket.timeout:
                # Timeout reached, continue listening
                pass
            except Exception as e:
                print(f"Error receiving packet: {e}")

    def data_transformation(self):
        while True:
            command = self.udp_queue.get()
            delta_position0, delta_orientation0, delta_grasp0= self._get_psm_vars(command, 0)
            delta_position1, delta_orientation1, delta_grasp1 = self._get_psm_vars(command, 1)
            sequence, pedal = self.get_packet_data(command)
            self.sequence_num = sequence
            self.update_delta_variables_dual(sequence, delta_position0, delta_position1, delta_orientation0, delta_orientation1, delta_grasp0, delta_grasp1, pedal)
            
            if self.request_event.is_set():
                # [self._delta_pos_0, self._delta_rot_0, self._delta_pos_1, self._delta_rot_1, 
                #  ee_euler0, ee_euler1, rot_vec_0, rot_vec_1, self._gripper_0, self._gripper_1]
                variable_list =  self.transform_console_data()
                self.logger2.log_data_sampled(time.time(), self.sequence_num, variable_list[0], variable_list[4], 
                                              variable_list[2], variable_list[5], variable_list[8], variable_list[9])
                
                commands = (np.concatenate([variable_list[0], variable_list[6]]), variable_list[8],
                            np.concatenate([variable_list[2], variable_list[7]]), variable_list[9])
                self.transform_queue.put(commands)
                
                self._delta_pos_0_sum = np.zeros(3) 
                self._delta_rot_0_sum = np.zeros(3) 
                self._delta_pos_1_sum = np.zeros(3)
                self._delta_rot_1_sum = np.zeros(3)
                self.request_event.clear()


    def start_listening(self):
        """Start listening for UDP packets in a separate thread."""
        listen_thread = threading.Thread(target=self.receive_udp_packets, daemon=True)
        listen_thread.start()
        print("Started listening for incoming UDP packets...")   

    def transform_listening(self):
        """Start listening for UDP packets in a separate thread."""
        listen_thread = threading.Thread(target=self.data_transformation, daemon=True)
        listen_thread.start()
        print("Started listening for incoming UDP packets...")

   