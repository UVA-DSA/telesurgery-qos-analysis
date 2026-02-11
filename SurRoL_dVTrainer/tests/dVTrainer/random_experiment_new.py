import re
import os
import json
import random
import shutil


def update_packet_loss_params(config_path, model, param_array):
    with open(config_path, "r") as file:
        config = json.load(file)
    states = ['Good', 'Bad', 'Intermediate1', 'Intermediate2']
    transitions = [['Good', 'Intermediate1', 'Bad',  'Intermediate2'],
                   ['Bad',  'Intermediate2', 'Good', 'Intermediate1'],
                   ['Intermediate1', 'Bad',  'Good', 'Intermediate2'],
                   ['Intermediate2', 'Good', 'Bad',  'Intermediate1']]
    params = ['alpha', 'lambda']
    for k in range(len(param_array)):
        for i in range(len(transitions)):
            config[model][states[k]]['transitions'][transitions[k][i]] = param_array[k][i]
        for j in range(len(params)):
            config[model][states[k]]['params'][params[j]] = param_array[k][4+j]
    #print(config[model])
    
    with open(config_path, "w") as file:
        json.dump(config, file, indent=2)

def update_delay_params(config_path, model, lower_bound, weights, lambdas):
    with open(config_path, "r") as file:
        config = json.load(file)

    config[model]['lower_bound'] = float(lower_bound)
    config[model]['weights'] = weights
    config[model]['lambdas'] = lambdas
    print(config[model])
    
    with open(config_path, "w") as file:
        json.dump(config, file, indent=2)

def update_communication_loss_params(config_path, loss_prob, min_loss_length, max_loss_length, cooldown_period):
    
    with open(config_path, "r") as file:
        config = json.load(file)
    print(config['Communication_Loss'])
    config['Communication_Loss']['params']['loss_prob']= float(loss_prob)
    config['Communication_Loss']['params']['min_loss_length'] = float(min_loss_length)
    config['Communication_Loss']['params']['max_loss_length'] = float(max_loss_length)
    config['Communication_Loss']['params']['cooldown_period'] = float(cooldown_period)

    print(config['Communication_Loss'])
    with open(config_path, "w") as file:
        json.dump(config, file, indent=2)

def modify_first_line(txt_path, new_num):
    with open(txt_path, "r") as file:
        lines = file.readlines() 
    lines[0] = str(new_num) + lines[0][1:]
    with open(txt_path, "w") as file:
        file.writelines(lines[0:])  

def delete_first_line(txt_path):
    with open(txt_path, "r") as file:
        lines = file.readlines() 
    with open(txt_path, "w") as file:
        file.writelines(lines[1:])  

def shuffle_netfaults(initialize, filename, trial_num, order):
    net_faults = {
        "freefaults":[],

        "GE_Pareto_BLL packetloss1": [[0.95, 0.0, 0.05, 0.0, 4.428, 1.638],   # Good Transitions   ['Good', 'Intermediate1', 'Bad',  'Intermediate2']
                                      [0.90, 0.0, 0.10, 0.0, 4.966, 0.271],   # Bad Transitions    ['Bad',  'Intermediate2', 'Good', 'Intermediate1']
                                      [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],         # Inter1 Transitions ['Intermediate1', 'Bad',  'Good', 'Intermediate2']
                                      [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]],        # Inter2 Transitions ['Intermediate2', 'Good', 'Bad',  'Intermediate1']

        "GE_Pareto_BLL packetloss2": [[0.95, 0.0, 0.05, 0.0, 4.604, 3.552], 
                                      [0.90, 0.0, 0.10, 0.0, 3.901, 1.466],  
                                      [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],  
                                      [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]],

        "GE_Pareto_BLL packetloss3": [[0.95, 0.0, 0.05, 0.0, 3.859, 3.324], 
                                      [0.90, 0.0, 0.10, 0.0, 3.797, 6.049], 
                                      [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],  
                                      [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]],

        "5G delay1" :  [70,                     # Lower Bound
                       [0.72645, 0.27355],      # Weights
                       [0.02711, 0.08529]],     # Lambdas 
        
        "5G delay2" : [210,              
                       [0.89258, 0.10742],      
                       [0.01081, 0.01624]],

        "5G delay3" : [406,              
                      [0.89574, 0.10426],      
                      [0.01025, 0.01551]],


        # [loss_prob, min_loss_length, max_loss_length, cooldown_period]
        "communicationloss1" : [1, 0, 3000, 8500],     # 10%
        
        "communicationloss2" : [1, 0, 1000, 1000],     # 30%
        
        "communicationloss3" : [1, 0, 2000, 1000],     # 50%
    }

    if initialize:
        user_dir = "Data/exp_data_"+ str(user_num) 
        copy_filename = "Data/exp_data_"+ str(user_num) + "/network_conditions_copy.txt"
        os.makedirs(user_dir, exist_ok=True)
        fault_list = list(net_faults.items())
        plm = fault_list[1:4]
        dlm = fault_list[4:7]
        clm = fault_list[7:10]
        random.shuffle(plm)
        random.shuffle(dlm)
        random.shuffle(clm)
        # Combine them back
        orderlist=[]
        for i in order:
            if i == "free":
                orderlist.append([fault_list[0]])
            elif i == "plm":
                orderlist.append(plm)
            elif i == "dlm":    
                orderlist.append(dlm)
            elif i == "clm":
                orderlist.append(clm)
        fault_list = orderlist[0] + orderlist[1] + orderlist[2] + orderlist[3]
        with open(filename, "w") as file:
            for fault in fault_list:
                if fault[0] == "freefaults":
                    file.write(f"{trial_num} freefault1\n{trial_num} freefault2\n{trial_num} freefault3\n")
                else:
                    param_values = " ".join(map(str, fault[1]))
                    file.write(f"{trial_num} {fault[0]} {param_values}\n")
        
        shutil.copy(filename, copy_filename)

def select_netfault(filename, config_path, trial_num):
    f = p = d = c = False
    config_path_p = os.path.join(config_path, "packet_loss_config.json")
    config_path_d = os.path.join(config_path, "delay_config.json")

    with open(filename, "r") as file:
        first_line = file.readline().strip()
    
    arrays = re.findall(r'\[.*?\]', first_line)
    list_str = first_line.split(" ")
    param_array = [list(map(float, arr.strip('[]').split(','))) for arr in arrays]

    net_model_str = ""
    if list_str[1][0] == "f":
        num = int(list_str[0])
        net_model_str = list_str[1]
        f = True
    elif list_str[2][0] == "p":
        num = int(list_str[0])
        model = list_str[1]
        net_model_str = list_str[2]
        p = True
    elif list_str[2][0] == "d":
        num = int(list_str[0])
        model = list_str[1]
        net_model_str = list_str[2]
        lower_bound = float(list_str[3])
        weights = param_array[0]
        lambdas = param_array[1]
        d = True
    else:
        num = int(list_str[0])
        net_model_str = list_str[1]
        loss_prob = list_str[2]
        min_loss_length = list_str[3]
        max_loss_length = list_str[4]
        cooldown_period = list_str[5]
        c = True
    
    #Update Json file
    if p and num == trial_num:
        update_packet_loss_params(config_path_p, model, param_array)
        print("Finish Update Packet Loss Parameters")
    elif d and num == trial_num:
        update_delay_params(config_path_d, model, lower_bound, weights, lambdas)
        print("Finish Update Delay Parameters")
    elif c and num == trial_num:
        update_communication_loss_params(config_path_p, loss_prob, min_loss_length, max_loss_length, cooldown_period)
        print("Finish Update Communication Loss Parameters")
    new_num = num - 1
    
    if new_num == 0:
        delete_first_line(filename)
    else:
        modify_first_line(filename, new_num)
    
    return p, d, c, net_model_str, num 

def load_session_order(filepath, order_number):
    with open(filepath, "r") as file:
        lines = file.readlines()

    # Sanity check
    if order_number < 1 or order_number > len(lines):
        raise ValueError(f"Order number must be between 1 and {len(lines)}")

    # Parse the corresponding line
    line = lines[order_number - 1].strip()
    _, session_str = line.split(": ", 1)
    session_order = session_str.split()
    return session_order

user_num = 15

if __name__ == "__main__":
    filename = "tests/dVTrainer/network_conditions.txt"
    orderfile = "tests/dVTrainer/session_orders.txt"
    trial_num = 1
    order = load_session_order(orderfile, user_num)
    shuffle_netfaults(True, filename, trial_num, order)

    #config_path = "/source/standalone/environments/teleoperation/PyGE/src/pyge/canonical_configs"
    #p, d, c, num = select_netfault(filename, config_path, 5)
