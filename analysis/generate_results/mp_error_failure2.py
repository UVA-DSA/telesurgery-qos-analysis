import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def process_error_lists(condition_error):
    ma_count, od_count, cl_count, oov_count = 0, 0, 0, 0
    
    for error_string in condition_error:
        if pd.isna(error_string) or error_string == '':
            continue
        
        # Split by both comma and semicolon
        errors = error_string.replace(';', ',').split(',')
        
        for error in errors:
            error = error.strip()  # Remove whitespace
            if error == 'Multiple Attempts':
                ma_count += 1
            elif error == 'Object Drop':
                od_count += 1
            elif error == 'Collision':
                cl_count += 1
            elif error == 'OOV':
                oov_count += 1
    
    return ma_count, od_count, cl_count, oov_count

def create_mp_pie_chart(error_all, error_types):
  
    mp_labels = ["MP1","MP2", "MP3","MP4","MP5", "MP6","MP7","MP8","MP9"]
    
    # Filter out MPs with zero attempts to avoid empty slices
    non_zero_data = [(label, count) for label, count in zip(mp_labels, error_all) if count > 0]

    if not non_zero_data:
        print("No multiple attempts found across all motion primitives.")
        return
    
    labels, counts = zip(*non_zero_data)
    total_attempts = sum(counts)
    
    # Calculate percentages
    percentages = [count/total_attempts * 100 for count in counts]
    
    # Create the pie chart
    plt.figure(figsize=(8, 6))
    
    # Define professional, publication-ready colors for each MP
    # Colors are colorblind-friendly and print-friendly
    mp_colors = [
        '#2E86C1',  # Professional Blue - MP1: Touch(Right_grasper, Peg)
        '#28B463',  # Forest Green - MP2: Grasp(Right_grasper, Peg)
        '#E74C3C',  # Crimson Red - MP3: Untouch(Right_grasper, Peg, Pole_S)
        '#F39C12',  # Orange - MP4: Touch(Left_grasper, Peg)
        '#8E44AD',  # Purple - MP5: Grasp(Left_grasper, Peg)
        '#17A2B8',  # Teal - MP6: Release(Right_grasper, Peg)
        '#DC7633',  # Brown Orange - MP7: Untouch(Right_grasper, Peg)
        '#5D6D7E',  # Steel Gray - MP8: Touch(Left_grasper, Peg, Pole_G)
        '#A569BD'   # Light Purple - MP9: Release(Left_grasper, Peg)
    ]
    
    # Get colors for non-zero data based on original MP index
    colors = []
    for label, _ in non_zero_data:
        mp_index = next(i for i, mp_label in enumerate(mp_labels) if mp_label == label)
        colors.append(mp_colors[mp_index])
    
    # Custom autopct function to handle small percentages
    def autopct_func(pct):
        if pct < 2.0:  # Don't show percentage for slices smaller than 2%
            return ''
        return f'{pct:.1f}%'
    
    wedges, texts, autotexts = plt.pie(counts, labels=labels, autopct=autopct_func, 
                                       colors=colors, startangle=90, pctdistance=0.85)
    
    # Customize the appearance
    plt.title('Distribution of ' + error_types + ' Across Motion Primitives', 
              fontsize=16, fontweight='bold', pad=20)
    
    # Rotate labels for better readability
    for text in texts:
        text.set_fontsize(10)
        text.set_fontweight('bold')  # Make MP labels bold
        text.set_rotation(0)
    
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
        autotext.set_fontsize(10)
    
    plt.axis('equal') 
    plt.tight_layout()
    
    # Print summary statistics
    print(f"Total {error_types}: {total_attempts}")
    print("\nBreakdown by Motion Primitive:")
    for label, count, percentage in zip(labels, counts, percentages):
        print(f"{label}: {count} attempts ({percentage:.1f}%)")
    
    plt.show()

if __name__ == "__main__":
    root_address = "exp_data"
    net_conditions = ['Normal', 'PLM-10',  'PLM-30',  'PLM-50', 
                      'DLM-100', 'DLM-300', 'DLM-500', 
                      'CLM-10',  'CLM-30',  'CLM-50']
    mp_columns = [
            "Touch(Right_grasper, Peg)",
            "Grasp(Right_grasper, Peg)", 
            "Untouch(Right_grasper, Peg, Pole_S)",
            "Touch(Left_grasper, Peg)",
            "Grasp(Left_grasper, Peg)",
            "Release(Right_grasper, Peg)",
            "Untouch(Right_grasper, Peg)",
            "Touch(Left_grasper, Peg, Pole_G)",
            "Release(Left_grasper, Peg)"
        ]

    mp1_ma, mp1_od, mp1_cl, mp1_oov = 0, 0, 0, 0
    mp2_ma, mp2_od, mp2_cl, mp2_oov = 0, 0, 0, 0
    mp3_ma, mp3_od, mp3_cl, mp3_oov = 0, 0, 0, 0
    mp4_ma, mp4_od, mp4_cl, mp4_oov = 0, 0, 0, 0
    mp5_ma, mp5_od, mp5_cl, mp5_oov = 0, 0, 0, 0
    mp6_ma, mp6_od, mp6_cl, mp6_oov = 0, 0, 0, 0
    mp7_ma, mp7_od, mp7_cl, mp7_oov = 0, 0, 0, 0
    mp8_ma, mp8_od, mp8_cl, mp8_oov = 0, 0, 0, 0
    mp9_ma, mp9_od, mp9_cl, mp9_oov = 0, 0, 0, 0

    for subject in os.listdir(root_address):
        error_path = os.path.join(root_address, subject, "statistics", "error_analysis.csv")
        failure_path = os.path.join(root_address, subject, "statistics", "failure_analysis.csv")

        mp_error= pd.read_csv(error_path)
        mp_failure= pd.read_csv(failure_path)

        mps_error = np.array([mp_error[[col]].values.flatten() for col in mp_columns])
        mps_failure = np.array([mp_failure[[col]].values.flatten() for col in mp_columns])

        for i in range(len(mps_error)):
            mpe = mps_error[i]
            ma_count, od_count, cl_count, oov_count = process_error_lists(mpe)
            if i == 0:
                mp1_ma += ma_count
                mp1_od += od_count
                mp1_cl += cl_count
                mp1_oov += oov_count
            elif i == 1:
                mp2_ma += ma_count
                mp2_od += od_count
                mp2_cl += cl_count
                mp2_oov += oov_count
            elif i == 2:
                mp3_ma += ma_count
                mp3_od += od_count
                mp3_cl += cl_count
                mp3_oov += oov_count
            elif i == 3:
                mp4_ma += ma_count
                mp4_od += od_count
                mp4_cl += cl_count
                mp4_oov += oov_count
            elif i == 4:
                mp5_ma += ma_count
                mp5_od += od_count
                mp5_cl += cl_count
                mp5_oov += oov_count
            elif i == 5:
                mp6_ma += ma_count
                mp6_od += od_count
                mp6_cl += cl_count
                mp6_oov += oov_count
            elif i == 6:
                mp7_ma += ma_count
                mp7_od += od_count
                mp7_cl += cl_count
                mp7_oov += oov_count
            elif i == 7:
                mp8_ma += ma_count
                mp8_od += od_count
                mp8_cl += cl_count
                mp8_oov += oov_count
            elif i == 8:
                mp9_ma += ma_count
                mp9_od += od_count
                mp9_cl += cl_count
                mp9_oov += oov_count

    ma_all = [mp1_ma, mp2_ma, mp3_ma, mp4_ma, mp5_ma, mp6_ma, mp7_ma, mp8_ma, mp9_ma]
    od_all = [mp1_od, mp2_od, mp3_od, mp4_od, mp5_od, mp6_od, mp7_od, mp8_od, mp9_od]
    cl_all = [mp1_cl, mp2_cl, mp3_cl, mp4_cl, mp5_cl, mp6_cl, mp7_cl, mp8_cl, mp9_cl]
    oov_all = [mp1_oov, mp2_oov, mp3_oov, mp4_oov, mp5_oov, mp6_oov, mp7_oov, mp8_oov, mp9_oov]
    
    # Create pie chart for multiple attempts distribution
    create_mp_pie_chart(ma_all, "Multiple Attempts")
    create_mp_pie_chart(od_all, "Object Drop")
    create_mp_pie_chart(cl_all, "Collision")
    create_mp_pie_chart(oov_all, "Out of View")

