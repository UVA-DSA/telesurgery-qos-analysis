import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture
from sklearn.metrics import adjusted_rand_score

# Suppose you have participant-level medians for 15 people
# Replace with your real numbers (length-15 arrays)
IDs = np.array([1, 2, 3, 4, 6, 
                7, 8, 9, 10, 11, 
                12, 15, 16, 17, 18])

ML = np.array([0.632, 0.488, 0.372, 0.334, 0.439,
               0.542, 0.716, 0.661, 0.52, 0.382,
               0.564, 0.683, 0.605, 0.503, 0.662], dtype=float)  # motion length

CT = np.array([17.757, 22.213, 17.075, 13.619, 23.031, 
               28.399, 25.034, 25.718, 29.952, 15.037,
               17.601, 31.464, 22.138, 15.177, 26.584], dtype=float)  # completion time
PU = np.array([3.667, 7.333, 7.333, 1.667, 4.667,
               11.667, 12.333, 14, 6.667, 2.333,
               6, 16.667, 7.333, 3.667, 12.667], dtype=float)  # pedal usage

def robust_z(x):
    med = np.median(x)
    mad = np.median(np.abs(x - med))
    return (x - med) / (1.4826 * mad if mad > 0 else 1.0)

z_ML, z_CT, z_PU = map(robust_z, (ML, CT, PU))
X = np.vstack([-z_ML, -z_CT, -z_PU]).T  # higher = more proficient

# ---- A) Composite Proficiency Index ----
CPI = X.mean(axis=1)  # equal weights
# tertile cut points:
t1, t2 = np.quantile(CPI, [1/3, 2/3])
labels_cpi = np.where(CPI < t1, "Novice",
               np.where(CPI < t2, "Intermediate", "Expert"))

# Optional: 1D GMM on CPI
gmm1d = GaussianMixture(n_components=3, random_state=0).fit(CPI.reshape(-1,1))
post = gmm1d.predict_proba(CPI.reshape(-1,1))
labels_gmm1d_idx = gmm1d.predict(CPI.reshape(-1,1))
# Order components by mean CPI to map to N/I/E
order = np.argsort(gmm1d.means_.ravel())
map_idx_to_name = {order[0]:"Novice", order[1]:"Intermediate", order[2]:"Expert"}
labels_gmm1d = np.array([map_idx_to_name[i] for i in labels_gmm1d_idx])

# ---- B) Multivariate GMM (K=3) ----
gmm = GaussianMixture(n_components=3, random_state=0).fit(X)
labs = gmm.predict(X)
# order clusters by median CPI for naming
med_cpi_by_cluster = [np.median(CPI[labs==k]) for k in range(3)]
rank = np.argsort(med_cpi_by_cluster)
name_map = {rank[0]:"Novice", rank[1]:"Intermediate", rank[2]:"Expert"}
labels_gmm3 = np.array([name_map[k] for k in labs])

# Agreement metric
ari = adjusted_rand_score(labels_cpi, labels_gmm3)
print("Adjusted Rand Index (CPI tertiles vs 3D GMM):", round(ari, 3))

# Summary table
df = pd.DataFrame({
    "ID": IDs,
    "ML": ML, "CT": CT, "PU": PU,
    "CPI": CPI,
    "CPI_tertile": labels_cpi,
    "GMM3": labels_gmm3,
    "GMM1D_CPI": labels_gmm1d
})

print("=== FINAL GROUPED PARTICIPANT IDs ===")
print("\n1. CPI Tertile Method:")
for group in ["Novice", "Intermediate", "Expert"]:
    ids = df[df["CPI_tertile"] == group]["ID"].values
    print(f"   {group}: {list(ids)}")

print("\n2. Multivariate GMM (3D) Method:")
for group in ["Novice", "Intermediate", "Expert"]:
    ids = df[df["GMM3"] == group]["ID"].values
    print(f"   {group}: {list(ids)}")

print("\n3. 1D GMM on CPI Method:")
for group in ["Novice", "Intermediate", "Expert"]:
    ids = df[df["GMM1D_CPI"] == group]["ID"].values
    print(f"   {group}: {list(ids)}")

print("\n=== SUMMARY STATISTICS ===")
print("\nMedian values by GMM3 groups:")
print(df.groupby("GMM3")[["ML","CT","PU"]].median())

print("\nDetailed participant data:")
print(df[["ID", "CPI_tertile", "GMM3", "GMM1D_CPI"]].sort_values("ID"))
