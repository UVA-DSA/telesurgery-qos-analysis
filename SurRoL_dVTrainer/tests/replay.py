# take a path to a binary file, reads packets, sends to 5001 port

import os
import struct
import lz4.frame
import socket
import time
from collections import namedtuple
from netfi.emulators.packet_logger_emulator import PacketLoggerEmulator

class replayoverport:
    def __init__(self, filepath):
        self.EMULATOR_PORT = 36001
        self.RECEIVER_PORT = 5001
        self.filepath = filepath
        # self.emulator = PacketLoggerEmulator(
        #     input_port=self.EMULATOR_PORT,
        #     output_port=self.RECEIVER_PORT,
        #     output_ip='127.0.0.1',
        #     log_path="/dev/null"  # This prevents creating a new log file
        # )
    
    def start(self):
        self.emulator.start()
    
    def stop(self):
        self.emulator.stop()

    def replay_log(self, dest_ip):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        packet_count = 0
        
        # Frequency tracking variables
        start_time = time.time()
        last_freq_print = start_time
        freq_print_interval = 1.0  # Print frequency every 1 second
        
        with lz4.frame.open(self.filepath, 'rb') as f:
            previous_time = 0  # Initialize to 0 for first packet
            system_time = time.time()
            while True:
                header = f.read(11)
                if not header or len(header) < 11:
                    break
                timestamp, length, dropped = struct.unpack('!QH?', header)
                #print(f"Packet {packet_count}: length={length}")
                if length == 0:
                    break
                packed_data = f.read(struct.calcsize(f"!{length}s"))
                if not packed_data:
                    break
                data = struct.unpack(f"!{length}s", packed_data)[0]

                # Proper timestamp-based sleeping for real-time replay
                current_packet_time = timestamp / 1e9  # Convert nanoseconds to seconds
                
                if packet_count > 0:  # Skip sleep for first packet
                    # Calculate time difference between current and previous packet
                    time_delta = current_packet_time - previous_time
                    
                    # Sleep for the remaining time to match original timing
                    sleep_time = max(0, time_delta - (time.time() - system_time))
                    #print(f"Sleeping for {sleep_time:.6f} seconds")
                    if sleep_time > 0:
                        time.sleep(sleep_time + sleep_time * 0.0049)

                system_time = time.time()
                sock.sendto(data, (dest_ip, self.RECEIVER_PORT))
                packet_count += 1
                previous_time = current_packet_time

                # fields = 'sequence pactyp version delx0 delx1 dely0 dely1 delz0 delz1 Qx0 Qx1 Qy0 Qy1 Qz0 Qz1 Qw0 Qw1 buttonstate0 buttonstate1 grasp0 grasp1 surgeon_mode checksum'.split()
                # UStruct = namedtuple('UStruct', fields)
                # format_str = '<IIIiiiiiiddddddddiiiiii'
                # unpacked_data = struct.unpack(format_str, data)
                # data = UStruct(*unpacked_data)
                # packet = data._asdict()
                #print(packet['sequence'])
                
                # Print loop frequency periodically
                # current_time = time.time()
                # if current_time - last_freq_print >= freq_print_interval:
                #     elapsed_time = current_time - start_time
                #     if elapsed_time > 0:
                #         frequency = packet_count / elapsed_time
                #         print(f"Loop frequency: {frequency:.2f} Hz ({packet_count} packets in {elapsed_time:.2f}s)")
                #     last_freq_print = current_time


        sock.close()
        print(f"Replay finished. Sent {packet_count} packets.")
        
        # Print final frequency statistics
        total_time = time.time() - start_time
        if total_time > 0:
            final_frequency = packet_count / total_time
            print(f"Average frequency: {final_frequency:.2f} Hz")

scene = replayoverport(filepath=f"dVTrainer/Data/replay_data/console_data_complete_7.bin")
#scene.start()
scene.replay_log(dest_ip='127.0.0.1')
#scene.stop()