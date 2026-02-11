import numpy as np
import matplotlib.pyplot as plt
import struct
import lz4.frame
from scipy.stats import gaussian_kde
from scipy import stats as scipy_stats

def analyze_logs(log_files):
    """Analyze multiple log files and return combined statistics"""
    combined_stats = {}
    
    for log_file in log_files:
        print(f"[Analyzer] Processing {log_file}...")
        stats = {
            'total_packets': 0,
            'lost_packets': [],
            'burst_lengths': [],
            'model_type': log_file['model_type']
        }
        
        with lz4.frame.open(log_file['path'], 'rb') as f:
            while True:
                header = f.read(11)
                if not header:
                    break
                ts, length, dropped = struct.unpack("!QH?", header)
                data = struct.unpack(f"!{length}s", f.read(length))[0]
                seq = struct.unpack('!I', data[:4])[0]
                
                stats['total_packets'] = max(stats['total_packets'], seq + 1)
                if dropped:
                    stats['lost_packets'].append(seq)
        
        # Calculate burst lengths
        current_burst = 0
        lost_set = set(stats['lost_packets'])
        for seq in range(stats['total_packets']):
            if seq in lost_set:
                current_burst += 1
            elif current_burst > 0:
                stats['burst_lengths'].append(current_burst)
                current_burst = 0
        if current_burst > 0:
            stats['burst_lengths'].append(current_burst)
            
        # Calculate derived metrics
        stats['loss_rate'] = len(stats['lost_packets']) / stats['total_packets']
        stats['mean_bll'] = np.mean(stats['burst_lengths']) if stats['burst_lengths'] else 0
        stats['std_bll'] = np.std(stats['burst_lengths']) if stats['burst_lengths'] else 0
        
        combined_stats[log_file['model_type']] = stats
    
    return combined_stats

def visualize_comparison(combined_stats, figsize=(15, 12)):
    """Create comparative visualization of two packet loss models"""
    plt.style.use('ggplot')
    fig = plt.figure(figsize=figsize)
    gs = fig.add_gridspec(2, 3, hspace=0.15, wspace=0.15)  # Changed to 2x3 grid
    
    # Color scheme
    hist_colors = {
        'Random': '#e74c3c',  # Reddish
        'GE_Pareto_Loss': '#3498db'       # Bluish
    }
    lost_packet_color = '#e74c3c'  # Consistent reddish color for lost packets
    
    # Burst Length Histograms - Position (0,0)
    max_burst = max(
        max(stats['burst_lengths'], default=0) 
        for stats in combined_stats.values()
    )
    bins = np.arange(1, max_burst + 2) - 0.5
    
    # Histograms subplot
    ax1 = fig.add_subplot(gs[0, 0])
    for i, (model_type, stats) in enumerate(combined_stats.items()):
        alpha = 1.0 if i == 0 else 0.6  # First histogram opaque, second transparent
        ax1.hist(
            stats['burst_lengths'], bins=bins, 
            alpha=alpha, label=f"{model_type}",
            color=hist_colors[model_type],
            edgecolor='black', linewidth=0.5,
            density=True  # Normalize to create probability density
        )
    
    ax1.set_title('Burst Length Distribution (Histogram)', fontsize=13, pad=10)
    ax1.set_xlabel('Burst Length (packets)')
    ax1.set_ylabel('Density')
    ax1.legend()
    
    # Statistics Panel - Position (0,1)
    ax2 = fig.add_subplot(gs[0, 1:])  # Span two columns
    ax2.axis('off')

    # Perform Mann-Whitney U test on burst length distributions
    model_names = list(combined_stats.keys())
    statistic, pvalue = scipy_stats.mannwhitneyu(
        combined_stats[model_names[0]]['burst_lengths'],
        combined_stats[model_names[1]]['burst_lengths'],
        alternative='two-sided'
    )
    
    stats_text = ["Comparative Statistics\n"]
    for model_type, stats in combined_stats.items():
        stats_text += [
            f"{model_type}:",
            f"  Loss Rate: {stats['loss_rate']:.2%}",
            f"  Mean BLL: {stats['mean_bll']:.2f} ± {stats['std_bll']:.2f}",
            f"  Max BLL: {max(stats['burst_lengths'], default=0)}",
            f"  Total Bursts: {len(stats['burst_lengths'])}\n"
        ]
    
    # Add Mann-Whitney U test results
    stats_text += [
        "\nMann-Whitney U Test (BLL):",
        f"  Statistic: {statistic:.2f}",
        f"  p-value: {pvalue:.2e}",
        f"  Significant: {'Yes' if pvalue < 0.05 else 'No'} (α=0.05)"
    ]

    ax2.text(0.05, 0.5, "\n".join(stats_text), 
            fontsize=11, linespacing=1.4,
            bbox=dict(facecolor='#f8f9fa', edgecolor='#ddd', boxstyle='round,pad=1'),
            fontfamily='monospace',
            verticalalignment='center')
    
    # Density plots in separate subplot
    ax_density = fig.add_subplot(gs[1, 0]) 
    for model_type, stats in combined_stats.items():
        if len(stats['burst_lengths']) > 0:
            kde = gaussian_kde(stats['burst_lengths'])
            x_range = np.linspace(1, max_burst, 200)
            pdf = kde(x_range)
            ax_density.plot(x_range, pdf, '-', 
                        color=hist_colors[model_type], 
                        linewidth=2, 
                        label=f"{model_type}")
    
    ax_density.set_title('Burst Length Distribution (PDF)', fontsize=13, pad=10)
    ax_density.set_xlabel('Burst Length (packets)')
    ax_density.set_ylabel('Density')
    ax_density.set_ylim(0, 1)  # Set y-axis limit to 1
    ax_density.legend()
    
    # Packet Loss Patterns - Last two positions of second row
    grid_size = 100
    for idx, (model_type, stats) in enumerate(combined_stats.items()):
        ax = fig.add_subplot(gs[1, idx+1])  # Position shifted by 1
        packet_grid = np.zeros((grid_size, grid_size))
        lost_set = set(stats['lost_packets'])
        
        for seq in range(stats['total_packets']):
            i, j = divmod(seq, grid_size)
            if i >= grid_size:  # Ensure we don't exceed grid bounds
                break
            if seq in lost_set:
                packet_grid[i][j] = 1
                
        cmap = plt.cm.colors.ListedColormap(['#2ecc71', lost_packet_color])  # Same red color for both
        ax.imshow(packet_grid, cmap=cmap, interpolation='none', aspect='equal')
        ax.set_title(f'{model_type}', fontsize=13, pad=10)
        ax.axis('off')
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    # Example usage
    log_files = [
        {'path': 'random_loss_log.bin', 'model_type': 'Random'},
        {'path': 'ge_loss_log.bin', 'model_type': 'GE_Pareto_Loss'}
    ]
    
    combined_stats = analyze_logs(log_files)
    visualize_comparison(combined_stats)
