import os
import numpy as np
import pandas as pd

if __name__ == "__main__":
    root_address = "exp_data"
    
    # Initialize lists to collect data from all subjects
    all_subjects = []
    all_time_mean = []
    all_time_std = []
    all_motion_mean = []
    all_motion_std = []
    all_pedal_mean = []
    all_pedal_std = []

    # Get all subject directories and sort them numerically
    subject_dirs = [d for d in os.listdir(root_address) if d.startswith("exp_data_")]
    subject_dirs.sort(key=lambda x: int(x.split("_")[-1]))

    for subject in subject_dirs:
        try:
            subject_n = int(subject.split("_")[-1])

            time_path = os.path.join(root_address, subject, "statistics", "completion_time_analysis.csv")
            motion_path = os.path.join(root_address, subject, "statistics", "motion_length_console_analysis.csv")
            pedal_path = os.path.join(root_address, subject, "statistics", "pedal_usage_analysis.csv")

            # Check if all required files exist
            if not all(os.path.exists(path) for path in [time_path, motion_path, pedal_path]):
                print(f"Warning: Missing files for {subject}, skipping...")
                continue

            time_df = pd.read_csv(time_path)
            motion_df = pd.read_csv(motion_path)
            pedal_df = pd.read_csv(pedal_path)

            # Extract the relevant columns (Normal conditions only - first 3 rows)
            transfer_time = time_df["Entire Transfer"].values[:3]  # Normal-1, Normal-2, Normal-3
            motion_length = motion_df["Transfer"].values[:3]
            pedal_usage = pedal_df["Trial"].values[:3]

            # Calculate mean and std for normal conditions
            normal_time_mean = round(np.mean(transfer_time), 3)
            normal_time_std = round(np.std(transfer_time), 3)

            normal_motion_mean = round(np.mean(motion_length), 3)
            normal_motion_std = round(np.std(motion_length), 3)

            normal_pedal_mean = round(np.mean(pedal_usage), 3)
            normal_pedal_std = round(np.std(pedal_usage), 3)

            # Append to lists
            all_subjects.append(subject_n)
            all_time_mean.append(normal_time_mean)
            all_time_std.append(normal_time_std)
            all_motion_mean.append(normal_motion_mean)
            all_motion_std.append(normal_motion_std)
            all_pedal_mean.append(normal_pedal_mean)
            all_pedal_std.append(normal_pedal_std)

            print(f"Processed subject {subject_n}: Time={normal_time_mean}±{normal_time_std}, Motion={normal_motion_mean}±{normal_motion_std}, Pedal={normal_pedal_mean}±{normal_pedal_std}")

        except Exception as e:
            print(f"Error processing {subject}: {e}")
            continue

    # Create DataFrame with the results
    results_df = pd.DataFrame({
        'Subject': all_subjects,
        'Time_Mean_Std': [f"{mean}±{std}" for mean, std in zip(all_time_mean, all_time_std)],
        'Motion_Mean_Std': [f"{mean}±{std}" for mean, std in zip(all_motion_mean, all_motion_std)],
        'Pedal_Mean_Std': [f"{mean}±{std}" for mean, std in zip(all_pedal_mean, all_pedal_std)]
    })

    # Save to CSV
    output_file = "user_baseline_performance.csv"
    results_df.to_csv(output_file, index=False)
    print(f"\nResults saved to {output_file}")
    print(f"Total subjects processed: {len(all_subjects)}")
    
    # Display summary
    print("\nSummary:")
    print(results_df[['Subject', 'Time_Mean_Std', 'Motion_Mean_Std', 'Pedal_Mean_Std']].to_string(index=False))

        