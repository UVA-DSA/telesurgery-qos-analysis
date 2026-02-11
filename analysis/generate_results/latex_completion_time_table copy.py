import pandas as pd

def process_cell(cell: str) -> str:
    """Format cell with standard deviation but no bold formatting."""
    if not isinstance(cell, str):
        return str(cell)
    
    # Check if cell contains ± symbol for standard deviation
    if "±" in cell:
        # Split by ± to get mean and std parts
        parts = cell.split("±")
        if len(parts) == 2:
            mean_part = parts[0].strip()
            std_part = parts[1].strip()
            
            # Remove asterisk if present (no bold formatting)
            if "*" in std_part:
                std_part = std_part.replace("*", "")
            if "*" in mean_part:
                mean_part = mean_part.replace("*", "")
            
            # Format the standard deviation part
            formatted_cell = f"{mean_part}{{\\scriptsize($\\pm${std_part})}}"

            return formatted_cell
    
    # Handle cells with '*' but no ± (just remove asterisk)
    if "*" in cell:
        return cell.replace("*", "")
    
    return cell

def insert_group_midrules(df: pd.DataFrame) -> list:
    """Return rows of LaTeX tabular with \midrule inserted at group boundaries."""
    rows = []
    prev_group = None

    for _, row in df.iterrows():
        condition = row.iloc[0]
        # Detect group from condition name
        if condition == "Normal":
            group = "Normal"
        elif condition.startswith("PLM"):
            group = "PLM"
        elif condition.startswith("DLM"):
            group = "DLM"
        elif condition.startswith("CLM"):
            group = "CLM"
        else:
            group = "Other"

        # Insert \midrule when group changes (except first row)
        if prev_group is not None and group != prev_group:
            rows.append("\\midrule")

        # Format row as LaTeX line
        row_str = " & ".join(str(x) for x in row) + " \\\\"
        rows.append(row_str)

        prev_group = group

    return rows

def csv_to_latex(csv_path: str, caption: str, label: str) -> str:
    # Load CSV
    df = pd.read_csv(csv_path)

    # Copy for LaTeX processing
    df_latex = df.copy()

    # Process cells (bold if contains '*')
    for col in df_latex.columns[1:]:
        df_latex[col] = df_latex[col].apply(process_cell)

    # Rename headers to MP1, MP2, ...
    num_mps = len(df.columns) - 1  # exclude first column
    headers = ["Conditions", "Transfer"]  + [f"MP{i}" for i in range(1, num_mps)]
    # Make headers bold
    headers_bold = ["\\textbf{" + h + "}" for h in headers]

    # Build LaTeX table manually with \midrule placement
    header_line = " & ".join(headers_bold) + " \\\\"
    body_lines = insert_group_midrules(df_latex)

    latex_table = (
        "\\begin{table*}[h]\n"
        "\\centering\n"
        f"\\caption{{{caption}}}\n"
        "\\resizebox{\\textwidth}{!}{%\n"
        "\\begin{tabular}{" + "l" + "c" * (num_mps) + "}\n"
        "\\toprule\n"
        + header_line + "\n"
        "\\midrule\n"
        + "\n".join(body_lines) + "\n"
        "\\bottomrule\n"
        "\\end{tabular}\n"
        "}\n"
        f"\\label{{{label}}}\n"
        "\\end{table*}"
    )

    return latex_table

# Example usage
if __name__ == "__main__":
    csv_file = "metrics_results/summary/mp_completion_time_summary.csv"  
    caption = "Completion Time for Each MP Under Defined Network Conditions"
    label = "tab:CompletionTime"
    latex_code = csv_to_latex(csv_file, caption, label)
    print(latex_code)
