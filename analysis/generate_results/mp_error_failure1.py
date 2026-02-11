import os
import numpy as np
import pandas as pd

def process_error_lists(condition_error):
    ma_count, od_count, cl_count, oov_count, se_count = 0, 0, 0, 0, 0

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
            elif error == 'System Error':
                se_count += 1

    return ma_count, od_count, cl_count, oov_count, se_count

def process_failure_lists(condition_failure):
    dob_count, doo_count, pwp_count = 0, 0, 0

    for failure_string in condition_failure:
        if pd.isna(failure_string) or failure_string == '':
            continue
        
        # Split by both comma and semicolon
        errors = failure_string.replace(';', ',').split(',')
        
        for error in errors:
            error = error.strip()  # Remove whitespace
            if error == 'Dropped_on_board':
                dob_count += 1
            elif error == 'Dropped_OOV':
                doo_count += 1
            elif error == 'Placed_wrong_pole':
                pwp_count += 1

    return dob_count, doo_count, pwp_count

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

    norm1_ma, norm1_od, norm1_cl, norm1_oov, norm1_se = 0, 0, 0, 0, 0
    norm2_ma, norm2_od, norm2_cl, norm2_oov, norm2_se = 0, 0, 0, 0, 0
    norm3_ma, norm3_od, norm3_cl, norm3_oov, norm3_se = 0, 0, 0, 0, 0
    plm1_ma, plm1_od, plm1_cl, plm1_oov, plm1_se = 0, 0, 0, 0, 0
    plm2_ma, plm2_od, plm2_cl, plm2_oov, plm2_se = 0, 0, 0, 0, 0
    plm3_ma, plm3_od, plm3_cl, plm3_oov, plm3_se = 0, 0, 0, 0, 0
    dlm1_ma, dlm1_od, dlm1_cl, dlm1_oov, dlm1_se = 0, 0, 0, 0, 0
    dlm2_ma, dlm2_od, dlm2_cl, dlm2_oov, dlm2_se = 0, 0, 0, 0, 0
    dlm3_ma, dlm3_od, dlm3_cl, dlm3_oov, dlm3_se = 0, 0, 0, 0, 0
    clm1_ma, clm1_od, clm1_cl, clm1_oov, clm1_se = 0, 0, 0, 0, 0
    clm2_ma, clm2_od, clm2_cl, clm2_oov, clm2_se = 0, 0, 0, 0, 0
    clm3_ma, clm3_od, clm3_cl, clm3_oov, clm3_se = 0, 0, 0, 0, 0

    norm1_ob, norm1_ofb, norm1_wc = 0, 0, 0
    norm2_ob, norm2_ofb, norm2_wc = 0, 0, 0
    norm3_ob, norm3_ofb, norm3_wc = 0, 0, 0
    plm1_ob, plm1_ofb, plm1_wc = 0, 0, 0
    plm2_ob, plm2_ofb, plm2_wc = 0, 0, 0
    plm3_ob, plm3_ofb, plm3_wc = 0, 0, 0
    dlm1_ob, dlm1_ofb, dlm1_wc = 0, 0, 0
    dlm2_ob, dlm2_ofb, dlm2_wc = 0, 0, 0
    dlm3_ob, dlm3_ofb, dlm3_wc = 0, 0, 0
    clm1_ob, clm1_ofb, clm1_wc = 0, 0, 0
    clm2_ob, clm2_ofb, clm2_wc = 0, 0, 0
    clm3_ob, clm3_ofb, clm3_wc = 0, 0, 0

    n_subjects = 0
    for subject in os.listdir(root_address):
        n_subjects += 1
        error_path = os.path.join(root_address, subject, "statistics", "error_analysis.csv")
        failure_path = os.path.join(root_address, subject, "statistics", "failure_analysis.csv")

        mp_error= pd.read_csv(error_path)
        mp_failure= pd.read_csv(failure_path)

        mps_error = np.array([mp_error[[col]].values.flatten() for col in mp_columns])
        mps_failure = np.array([mp_failure[[col]].values.flatten() for col in mp_columns])

        for i in range(len(mps_failure[0])):
            condition_failure = mps_failure[:, i]
            ob_count, ofb_count, wc_count = process_failure_lists(condition_failure)
            if wc_count != 0:
                wc_count = wc_count * 2
            
            if i == 0:
                norm1_ob += ob_count
                norm1_ofb += ofb_count
                norm1_wc += wc_count
            if i == 1:
                norm2_ob += ob_count
                norm2_ofb += ofb_count
                norm2_wc += wc_count
            if i == 2:
                norm3_ob += ob_count
                norm3_ofb += ofb_count
                norm3_wc += wc_count
            if i == 3:
                plm1_ob += ob_count
                plm1_ofb += ofb_count
                plm1_wc += wc_count
            if i == 4:
                plm2_ob += ob_count
                plm2_ofb += ofb_count
                plm2_wc += wc_count
            if i == 5:
                plm3_ob += ob_count
                plm3_ofb += ofb_count
                plm3_wc += wc_count
            if i == 6:
                dlm1_ob += ob_count
                dlm1_ofb += ofb_count
                dlm1_wc += wc_count
            if i == 7:
                dlm2_ob += ob_count
                dlm2_ofb += ofb_count
                dlm2_wc += wc_count
            if i == 8:
                dlm3_ob += ob_count
                dlm3_ofb += ofb_count
                dlm3_wc += wc_count
            if i == 9:
                clm1_ob += ob_count
                clm1_ofb += ofb_count
                clm1_wc += wc_count
            if i == 10:
                clm2_ob += ob_count
                clm2_ofb += ofb_count
                clm2_wc += wc_count
            if i == 11:
                clm3_ob += ob_count
                clm3_ofb += ofb_count
                clm3_wc += wc_count

        for i in range(len(mps_error[0])):
            condition_error = mps_error[:, i]
            ma_count, od_count, cl_count, oov_count, se_count = process_error_lists(condition_error)

            if i == 0:
                norm1_ma += ma_count
                norm1_od += od_count
                norm1_cl += cl_count
                norm1_oov += oov_count
                norm1_se += se_count
            elif i == 1:
                norm2_ma += ma_count
                norm2_od += od_count
                norm2_cl += cl_count
                norm2_oov += oov_count
                norm2_se += se_count
            elif i == 2:
                norm3_ma += ma_count
                norm3_od += od_count
                norm3_cl += cl_count
                norm3_oov += oov_count
                norm3_se += se_count
            elif i == 3:
                plm1_ma += ma_count
                plm1_od += od_count
                plm1_cl += cl_count
                plm1_oov += oov_count
                plm1_se += se_count
            elif i == 4:
                plm2_ma += ma_count
                plm2_od += od_count
                plm2_cl += cl_count
                plm2_oov += oov_count
                plm2_se += se_count
            elif i == 5:
                plm3_ma += ma_count
                plm3_od += od_count
                plm3_cl += cl_count
                plm3_oov += oov_count
                plm3_se += se_count
            elif i == 6:
                dlm1_ma += ma_count
                dlm1_od += od_count
                dlm1_cl += cl_count
                dlm1_oov += oov_count
                dlm1_se += se_count
            elif i == 7:
                dlm2_ma += ma_count
                dlm2_od += od_count
                dlm2_cl += cl_count
                dlm2_oov += oov_count
                dlm2_se += se_count
            elif i == 8:
                dlm3_ma += ma_count
                dlm3_od += od_count
                dlm3_cl += cl_count
                dlm3_oov += oov_count
                dlm3_se += se_count
            elif i == 9:
                clm1_ma += ma_count
                clm1_od += od_count
                clm1_cl += cl_count
                clm1_oov += oov_count
                clm1_se += se_count
            elif i == 10:
                clm2_ma += ma_count
                clm2_od += od_count
                clm2_cl += cl_count
                clm2_oov += oov_count
                clm2_se += se_count
            elif i == 11:
                clm3_ma += ma_count
                clm3_od += od_count
                clm3_cl += cl_count
                clm3_oov += oov_count
                clm3_se += se_count

    peg = n_subjects * 6
    peg_normal1 = int(peg - norm1_se)
    peg_normal2 = int(peg - norm2_se)
    peg_normal3 = int(peg - norm3_se)
    peg_plm1 = int(peg - plm1_se)
    peg_plm2 = int(peg - plm2_se)
    peg_plm3 = int(peg - plm3_se)
    peg_dlm1 = int(peg - dlm1_se)
    peg_dlm2 = int(peg - dlm2_se)
    peg_dlm3 = int(peg - dlm3_se)
    peg_clm1 = int(peg - clm1_se)
    peg_clm2 = int(peg - clm2_se)
    peg_clm3 = int(peg - clm3_se)

    peg_normal1_s = int(peg-(norm1_ob+norm1_ofb+norm1_wc+norm1_se))
    peg_normal2_s = int(peg-(norm2_ob+norm2_ofb+norm2_wc+norm2_se))
    peg_normal3_s = int(peg-(norm3_ob+norm3_ofb+norm3_wc+norm3_se))
    peg_plm1_s = int(peg-(plm1_ob+plm1_ofb+plm1_wc+plm1_se))
    peg_plm2_s = int(peg-(plm2_ob+plm2_ofb+plm2_wc+plm2_se))
    peg_plm3_s = int(peg-(plm3_ob+plm3_ofb+plm3_wc+plm3_se))
    peg_dlm1_s = int(peg-(dlm1_ob+dlm1_ofb+dlm1_wc+dlm1_se))
    peg_dlm2_s = int(peg-(dlm2_ob+dlm2_ofb+dlm2_wc+dlm2_se))
    peg_dlm3_s = int(peg-(dlm3_ob+dlm3_ofb+dlm3_wc+dlm3_se))
    peg_clm1_s = int(peg-(clm1_ob+clm1_ofb+clm1_wc+clm1_se))
    peg_clm2_s = int(peg-(clm2_ob+clm2_ofb+clm2_wc+clm2_se))
    peg_clm3_s = int(peg-(clm3_ob+clm3_ofb+clm3_wc+clm3_se))

    # Generate CSV file
    columns = ['Net_Conditions', 'Success_Rate_%', 'Success_Num',  'Multiple_Attempts', 'Object_Drop', 'Collision', 'OOV', 'On_Board', 'Off_Board', 'Wrong_Color']
    
    data = [
        ['Normal-1', round(peg_normal1_s/peg_normal1, 4)*100, str(peg_normal1_s) + "/" + str(peg_normal1),  norm1_ma, norm1_od, norm1_cl, norm1_oov, norm1_ob, norm1_ofb, norm1_wc],
        ['Normal-2', round(peg_normal2_s/peg_normal2, 4)*100, str(peg_normal2_s) + "/" + str(peg_normal2),  norm2_ma, norm2_od, norm2_cl, norm2_oov, norm2_ob, norm2_ofb, norm2_wc],
        ['Normal-3', round(peg_normal3_s/peg_normal3, 4)*100, str(peg_normal3_s) + "/" + str(peg_normal3),  norm3_ma, norm3_od, norm3_cl, norm3_oov, norm3_ob, norm3_ofb, norm3_wc],
        ['PLM-10', round(peg_plm1_s/peg_plm1, 4)*100, str(peg_plm1_s) + "/" + str(peg_plm1),  plm1_ma, plm1_od, plm1_cl, plm1_oov, plm1_ob, plm1_ofb, plm1_wc],
        ['PLM-30', round(peg_plm2_s/peg_plm2, 4)*100, str(peg_plm2_s) + "/" + str(peg_plm2),  plm2_ma, plm2_od, plm2_cl, plm2_oov, plm2_ob, plm2_ofb, plm2_wc],
        ['PLM-50', round(peg_plm3_s/peg_plm3, 4)*100, str(peg_plm3_s) + "/" + str(peg_plm3),  plm3_ma, plm3_od, plm3_cl, plm3_oov, plm3_ob, plm3_ofb, plm3_wc],
        ['DLM-100', round(peg_dlm1_s/peg_dlm1, 4)*100, str(peg_dlm1_s) + "/" + str(peg_dlm1),  dlm1_ma, dlm1_od, dlm1_cl, dlm1_oov, dlm1_ob, dlm1_ofb, dlm1_wc],
        ['DLM-300', round(peg_dlm2_s/peg_dlm2, 4)*100, str(peg_dlm2_s) + "/" + str(peg_dlm2),  dlm2_ma, dlm2_od, dlm2_cl, dlm2_oov, dlm2_ob, dlm2_ofb, dlm2_wc],
        ['DLM-500', round(peg_dlm3_s/peg_dlm3, 4)*100, str(peg_dlm3_s) + "/" + str(peg_dlm3),  dlm3_ma, dlm3_od, dlm3_cl, dlm3_oov, dlm3_ob, dlm3_ofb, dlm3_wc],
        ['CLM-10', round(peg_clm1_s/peg_clm1, 4)*100, str(peg_clm1_s) + "/" + str(peg_clm1),  clm1_ma, clm1_od, clm1_cl, clm1_oov, clm1_ob, clm1_ofb, clm1_wc],
        ['CLM-30', round(peg_clm2_s/peg_clm2, 4)*100, str(peg_clm2_s) + "/" + str(peg_clm2),  clm2_ma, clm2_od, clm2_cl, clm2_oov, clm2_ob, clm2_ofb, clm2_wc],
        ['CLM-50', round(peg_clm3_s/peg_clm3, 4)*100, str(peg_clm3_s) + "/" + str(peg_clm3),  clm3_ma, clm3_od, clm3_cl, clm3_oov, clm3_ob, clm3_ofb, clm3_wc]
    ]
    
    df = pd.DataFrame(data, columns=columns)
    output_file = "metrics_results/summary/error_failure_summary.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\nCSV file '{output_file}' has been generated successfully!")
    print(f"Shape: {df.shape}")
