import os
import json
import importlib.util
from netfi.emulators.packet_loss_emulator import PacketLossEmulator
from netfi.emulators.delay_emulator import DelayEmulator
from netfi.emulators.packet_logger_emulator import PacketLoggerEmulator
from .random_experiment_new import select_netfault, user_num

class Net:
    def __init__(self):
        self.EMULATOR_PORT = 36000
        self.RECEIVER_PORT = 5001

        self.spec = importlib.util.find_spec("netfi")
        self.config_rootpath = os.path.join(list(self.spec.submodule_search_locations)[0], "canonical_configs")
        self.config_packetloss = os.path.join(self.config_rootpath, "packet_loss_config.json")
        self.config_delay = os.path.join(self.config_rootpath, "delay_config.json")
        
        self.numbers = 1
        network_conditions_file = os.path.join(os.path.dirname(__file__), "network_conditions.txt")
        self.P_enabled, self.D_enabled, self.C_enabled, self.model_str, self.trial_num = select_netfault(network_conditions_file, self.config_rootpath, self.numbers)

        self.filename = "console_data_complete"

    def start(self):

        if self.P_enabled:
            dir_path = os.path.join(os.path.dirname(__file__), f"Data/exp_data_"+ str(user_num) +"/packet_loss/" + self.model_str + "/")
            os.makedirs(dir_path, exist_ok=True)
            self.LOG_FILE = f"{dir_path}{self.filename}_{self.trial_num}.bin"
            with open(self.config_packetloss, 'r') as f:
                params = json.load(f)
            self.packetloss = PacketLossEmulator(input_port=self.EMULATOR_PORT,output_port=self.RECEIVER_PORT, model_name='GE_Pareto_BLL', 
                                                 params=params, protocol='udp', log_packets=True, log_path=self.LOG_FILE)
            self.packetloss.start()
            print("Packet Loss Enabled")

        elif self.D_enabled:
            dir_path = os.path.join(os.path.dirname(__file__), f"Data/exp_data_"+ str(user_num) +"/delay/" + self.model_str + "/")
            os.makedirs(dir_path, exist_ok=True)
            self.LOG_FILE = f"{dir_path}{self.filename}_{self.trial_num}.bin"
            with open(self.config_delay, 'r') as f:
                params = json.load(f)
            self.delay = DelayEmulator(input_port=self.EMULATOR_PORT,output_port=self.RECEIVER_PORT, network_type='5G',
                                       params=params,protocol='udp', log_packets=True, log_path=self.LOG_FILE)
            self.delay.start()
            print("Delay Enabled")

        elif self.C_enabled:
            dir_path = os.path.join(os.path.dirname(__file__), f"Data/exp_data_"+ str(user_num) +"/communication_loss/" + self.model_str + "/")
            os.makedirs(dir_path, exist_ok=True)
            self.LOG_FILE = f"{dir_path}{self.filename}_{self.trial_num}.bin"
            with open(self.config_packetloss, 'r') as f:
                params = json.load(f)
            self.packetloss = PacketLossEmulator(input_port=self.EMULATOR_PORT,output_port=self.RECEIVER_PORT, model_name='Communication_Loss', 
                                                 params=params, protocol='udp', log_packets=True, log_path=self.LOG_FILE)
            self.packetloss.start()
            print("Communication Loss Enabled")

        else:
            dir_path = os.path.join(os.path.dirname(__file__), f"Data/exp_data_"+ str(user_num) +"/no_fault/" + self.model_str + "/")
            os.makedirs(dir_path, exist_ok=True)
            self.LOG_FILE = f"{dir_path}{self.filename}_{self.trial_num}.bin"
            self.nofault = PacketLoggerEmulator(input_port=self.EMULATOR_PORT,output_port=self.RECEIVER_PORT,
                                                protocol='udp', log_path=self.LOG_FILE)
            self.nofault.start()
            print("No Net Fault Enabled")

    def stop(self):
        if self.P_enabled or self.C_enabled:
            self.packetloss.stop()
            print("Packet Loss Emulator Stopped")
        elif self.D_enabled:
            self.delay.stop()
            print("Delay Emulator Stopped")
        else:
            self.nofault.stop()
            print("No Fault Emulator Stopped")