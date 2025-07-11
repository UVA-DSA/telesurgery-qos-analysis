import time
import queue
import socket
import struct
import threading
import numpy as np
from collections import namedtuple
from .data_collector import DataLogger
from .random_experiment_new import user_num

class Console:
    def __init__(self, network):
        self.running = True
        self.ip = '127.0.0.1'
        self.port = 5001

        self.udp_queue = queue.Queue()
        self.transform_queue = queue.Queue()
        self.request_event = threading.Event()

        self.delta_pos_0_sum = np.zeros(3)
        self.delta_rot_0_sum = np.zeros(3)
        self.delta_pos_1_sum = np.zeros(3)
        self.delta_rot_1_sum = np.zeros(3)

        self.mapping_ratio = 2 / 2458
        
        self.fields = 'sequence pactyp version delx0 delx1 dely0 dely1 delz0 delz1 Qx0 Qx1 Qy0 Qy1 Qz0 Qz1 Qw0 Qw1 buttonstate0 buttonstate1 grasp0 grasp1 surgeon_mode checksum'.split()
        self.UStruct = namedtuple('UStruct', self.fields)
        self.format_str = '<IIIiiiiiiddddddddiiiiii'

        self.sequence_num = 0 

        p = network.P_enabled
        d = network.D_enabled
        c = network.C_enabled
        m = network.model_str
        n = network.trial_num

        self.logger = DataLogger("console_data_recieved", p, d, c, m, n, str(user_num), buffer_size=200)

    def unpack_data(self, data):
        unpacked_data = struct.unpack(self.format_str, data)
        return self.UStruct(*unpacked_data)

    def init_sock_udp(self):
        # Create a UDP socket and the data struct ----------------------------------------------------
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(2)
        self.sock.bind((self.ip, self.port))
        print(f"Initialized a UDP server on IP: {self.ip} and port: {self.port}")
        print("Listening for incoming data: \n")

    def start_receive_thread(self):
        """Start listening for UDP packets in a separate thread."""
        self.receieve_thread = threading.Thread(target=self.receive_udp_packets, daemon=True)
        self.receieve_thread.start()
        print("Started listening for incoming UDP packets...")   

    def receive_udp_packets(self):
        """Continuously listens for UDP packets and updates the internal state."""
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)  # Buffer size of 1024 bytes
                u_struct = self.unpack_data(data)
                command = u_struct._asdict()
                self.udp_queue.put(command)
                
            except socket.timeout:
                # Timeout reached, continue listening
                continue
            except OSError as e:
                if not self.running:
                    break  # Expected on shutdown
                print(f"Error receiving packet: {e}")
                break
            except Exception as e:
                print(f"Error receiving packet: {e}")
    
    def start_transformation_thread(self):
        """Start listening for UDP packets in a separate thread."""
        self.transformation_thread = threading.Thread(target=self.data_transformation, daemon=True)
        self.transformation_thread.start()
        print("Started listening for incoming UDP packets...") 
    
    def data_transformation(self):
        while self.running:
            command = self.udp_queue.get()
            if command is None:
                break  
            delta_position0, delta_orientation0, delta_grasp0= self.get_psm_vars(command, 0)
            delta_position1, delta_orientation1, delta_grasp1 = self.get_psm_vars(command, 1)
            sequence, pedal = self.get_packet_data(command)
            self.update_delta_variables_dual(sequence, delta_position0, delta_position1, delta_orientation0, delta_orientation1, delta_grasp0, delta_grasp1, pedal)
            
            if self.request_event.is_set():
                #[delta_pos_0, delta_rot_0, delta_pos_1, delta_rot_1, gripper_0, gripper_1]
                self.sequence_num = sequence
                commands =  self.transform_console_data()
                
                self.transform_queue.put(commands)
                
                self.delta_pos_0_sum = np.zeros(3) 
                self.delta_rot_0_sum = np.zeros(3) 
                self.delta_pos_1_sum = np.zeros(3)
                self.delta_rot_1_sum = np.zeros(3)
                self.request_event.clear()

    def get_psm_vars(self, command, index):
        deltaX = command[f'delx{index}']
        deltaY = command[f'dely{index}']
        deltaZ = command[f'delz{index}']

        deltaQx = command[f'Qx{index}']
        deltaQy = command[f'Qy{index}']
        deltaQz = command[f'Qz{index}']

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
        
        self.logger.log_data_recieved(time.time(), sequence, delta_pos_0, delta_rot_0, 
                                      delta_pos_1, delta_rot_1, delta_grasp0, delta_grasp1, surgeon_mode)

        if not np.all(delta_pos_0 == np.zeros(3)):    
            self.delta_pos_0_sum += delta_pos_0

        if not np.all(delta_rot_0 == np.zeros(3)):
            self.delta_rot_0_sum += delta_rot_0

        if not np.all(delta_pos_1 == np.zeros(3)):    
            self.delta_pos_1_sum += delta_pos_1

        if not np.all(delta_rot_1 == np.zeros(3)):
            self.delta_rot_1_sum += delta_rot_1
    
    def transform_console_data(self):
        delta_pos_0 = self.position_transform(self.delta_pos_0_sum)
        delta_pos_1 = self.position_transform(self.delta_pos_1_sum)

        delta_rot_0 = self.orientation_transform(self.delta_rot_0_sum)
        delta_rot_1 = self.orientation_transform(self.delta_rot_1_sum)

        gripper_0 = self.map_grasper(self._left_val)
        gripper_1 = self.map_grasper(self._right_val)

        return [delta_pos_0, delta_rot_0, delta_pos_1, delta_rot_1, gripper_0, gripper_1]

    def position_transform(self, delta_pos):
        P_transform = np.array([[-1,  0,  0],
                                [ 0,  1,  0],
                                [ 0,  0, -1]])
        
        delta_pos = delta_pos * 0.01
        new_delta_pos = P_transform @ delta_pos

        return new_delta_pos
    
    def orientation_transform(self, delta_rot):
        R_transform = np.array([[0, 1, 0],
                                [1, 0, 0],
                                [0, 0, 1]])
        
        delta_rot = delta_rot * 0.2
        new_delta_rot = R_transform @ delta_rot
        
        return new_delta_rot
    
    def map_grasper(self, grasp_i):
        return 1 - (grasp_i * self.mapping_ratio)
    
    def start(self):
        """Start the console to receive and transform data."""
        self.init_sock_udp()
        self.start_receive_thread()
        self.start_transformation_thread()

    def close(self):
        """Close the UDP socket."""
        self.running = False
        self.sock.close()
        self.udp_queue.put(None)
        self.transform_queue.put(None)
        self.receieve_thread.join()
        self.transformation_thread.join()
        
    def set_event(self):
        """Set the event to trigger data transformation."""
        self.request_event.set()

    def get_transformed_data(self):
        """Get the transformed data from the queue."""
        try:
            return self.transform_queue.get(timeout=0)
        except:
            return None