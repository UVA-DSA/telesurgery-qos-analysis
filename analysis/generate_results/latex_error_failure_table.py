import pandas as pd

# Load CSV file
csv_file ="metrics_results/summary/error_failure_summary.csv"
df = pd.read_csv(csv_file)

# Build LaTeX table
def df_to_latex_table(df, caption="Error and Failure", label="tab:ErrorFailure"):
    # Begin table
    latex = []
    latex.append("\\begin{table}[h]")
    latex.append("    \\centering")
    latex.append(f"    \\caption{{{caption}}}")
    latex.append(f"    \\label{{{label}}}")
    latex.append("    \\resizebox{\\columnwidth}{!}{")
    
    # Column specification
    col_format = "l" + "c" * (len(df.columns) - 1)
    latex.append(f"    \\begin{{tabular}}{{{col_format}}}")
    latex.append("        \\toprule")
    
    # First header row (multi-column groups)
    latex.append("        Network Conditions & Success Rate & \\multicolumn{4}{c}{Error Counts} & \\multicolumn{3}{c}{Failure Counts} \\\\")
    latex.append("        & (\\%) & (1) & (2) & (3) & (4) & (1) & (2) & (3) \\\\")
    latex.append("        \\midrule")
    
    # Add table rows
    for _, row in df.iterrows():
        row_str = ""
        for i in range(len(row)):
            if i == 0:
                row_str += str(row[i])
            elif i == 2:
                row_str += "("+ str(row[i]) + ")"
            else:
                row_str += " & " + str(row[i])
        latex.append(f"        {row_str} \\\\")
    
    latex.append("        \\bottomrule")
    latex.append("    \\end{tabular}")
    latex.append("    }")
    latex.append("\\end{table}")
    
    return "\n".join(latex)


# Convert and save LaTeX table
latex_table = df_to_latex_table(df)
with open("error_failure_table.tex", "w") as f:
    f.write(latex_table)

print(latex_table)
