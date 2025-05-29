from Analyser_mp import *
from collections import Counter

def count_errors_for_each_condition(mp_error_dict):
    drop = 0
    collision = 0
    oov = 0
    multi_attempts = 0

    for color in mp_error_dict:
        for mp in mp_error_dict[color]:
            if mp[2] != 'NO_ERROR':
                errors = mp[2].split(";")
                for error in errors:
                    if error == "Multiple Attempts":
                        multi_attempts += 1
                    elif error == "Object Drop":
                        drop += 1
                    elif error == "Collision":
                        collision += 1
                    elif error == "OOV":
                        oov += 1
    
    return drop, collision, oov, multi_attempts

def mp_errors_for_each_condition1(mp_error_dict):
    touch_peg = []
    grasp = []
    untouch = []
    touch_pole = []
    release = []

    for color in mp_error_dict:
          for mp in mp_error_dict[color]:
            if mp[0] == 'Touch' and type(mp[1]) != str and type(mp[2]) == str:
                touch_peg.append(mp[2])
            elif mp[0] == 'Grasp' and type(mp[2]) == str:
                grasp.append(mp[2])
            elif mp[0] == 'Untouch' and type(mp[2]) == str: 
                untouch.append(mp[2])
            elif mp[0] == 'Touch' and type(mp[1]) == str  and type(mp[2]) == str:
                touch_pole.append(mp[2])
            elif mp[0] == 'Release' and type(mp[2]) == str:
                release.append(mp[2])
    
    return touch_peg, grasp, untouch, touch_pole, release 

def mp_errors_for_each_condition2(mp_error_dict):
    drop = []
    collision = []
    oov = []
    multi_attempts = []

    for color in mp_error_dict:
          for mp in mp_error_dict[color]:
            if mp != 'NO_ERROR':
                errors = mp[2].split(";")
                for error in errors:
                    if error == "Multiple Attempts":
                        if mp[0] == 'Touch' and type(mp[1]) != str:
                            multi_attempts.append("Touch Peg")
                        elif mp[0] == 'Touch' and type(mp[1]) == str:
                            multi_attempts.append("Touch Pole")
                        else:
                            multi_attempts.append(mp[0])
                    elif error == "Object Drop":
                        if mp[0] == 'Touch' and type(mp[1]) != str:
                            drop.append("Touch Peg")
                        elif mp[0] == 'Touch' and type(mp[1]) == str:
                            drop.append("Touch Pole")
                        else:
                            drop.append(mp[0])
                    elif error == "Collision":
                        if mp[0] == 'Touch' and type(mp[1]) != str:
                            collision.append("Touch Peg")
                        elif mp[0] == 'Touch' and type(mp[1]) == str:
                            collision.append("Touch Pole")
                        else:
                            collision.append(mp[0])
                    elif error == "OOV":
                        if mp[0] == 'Touch' and type(mp[1]) != str:
                            oov.append("Touch Peg")
                        elif mp[0] == 'Touch' and type(mp[1]) == str:
                            oov.append("Touch Pole")
                        else:
                            oov.append(mp[0])
    
    return drop, collision, oov, multi_attempts

def plot_pie_chart(mp_error_list, MP):
    counts = Counter(mp_error_list)

    labels = list(counts.keys())
    sizes = list(counts.values())

    label_color_map = {
    'Touch Peg': "#f4c542",    # warm amber/golden yellow
    'Grasp': "#4c72b0",        # muted royal blue
    'Touch Pole': "#55a868",   # soft green-teal
    'Untouch': "#c44e52",      # rich red
    'Release': "#8172b2"       # lavender-purple
    } 

    colors = [label_color_map[label] for label in labels]

    plt.figure(figsize=(6, 6))
    plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140)
    plt.title("Motion Primitives Distribution in Error: " + MP, pad=20)
    plt.axis('equal') 
    plt.show()

if __name__ == "__main__":
    root_address = "exp_data_new"
    netfolders = ['no_fault', 'packet_loss', 'delay', 'communication_loss']

    drop_free = 0
    collision_free = 0
    oov_free = 0
    multi_attempts_free = 0
    
    touch_peg_all = []
    grasp_all = [] 
    untouch_all = [] 
    touch_pole_all = []
    release_all = []

    drop_mp_all = []
    collision_mp_all = [] 
    oov_mp_all = [] 
    multi_attempts_mp_all = []

    for folder in netfolders:
        path = os.path.join(root_address, folder)
        for sub_folder in os.listdir(path): 
            sub_path = os.path.join(path, sub_folder)
            analyser_mp = AnalyserMP(sub_path)
            mp_error_dict = analyser_mp.get_MP_timestamp_error()
            drop, collision, oov, multi_attempts = count_errors_for_each_condition(mp_error_dict)
            touch_peg, grasp, untouch, touch_pole, release = mp_errors_for_each_condition1(mp_error_dict)
            drop_mp, collision_mp, oov_mp, multi_attempts_mp = mp_errors_for_each_condition2(mp_error_dict)
            
            touch_peg_all += touch_peg
            grasp_all += grasp
            untouch_all += untouch
            touch_pole_all += touch_pole
            release_all += release

            drop_mp_all+=drop_mp
            collision_mp_all+=collision_mp
            multi_attempts_mp_all+=multi_attempts_mp

            print("-------------------------------------")
            print("Error counts for " + sub_folder + ":")
            print(f"Object Drop has {drop} times.")
            print(f"Collision has {collision} times.")
            print(f"Multiple attempts has {multi_attempts} times.")
            print(f"Instrument Out of View has {oov} times.")
            if sub_folder[0] == 'f':
                drop_free += drop
                collision_free += collision
                oov_free += oov
                multi_attempts_free += multi_attempts

    plot_pie_chart(drop_mp_all, "Object Dropped")  
    plot_pie_chart(collision_mp_all, "Collision") 
    plot_pie_chart(multi_attempts_mp_all, "Multiple Attempts")    

    print("-------------------------------------")
    print("Total error counts for normal conditions:")
    print(f"Object Drop has {drop_free} times.")
    print(f"Collision has {collision_free} times.")
    print(f"Multiple attempts has {multi_attempts_free} times.")
    print(f"Instrument Out of View has {oov_free} times.")
