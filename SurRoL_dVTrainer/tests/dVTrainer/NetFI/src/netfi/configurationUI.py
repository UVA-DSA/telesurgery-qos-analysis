import json
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
from PIL import Image, ImageTk
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

class ConfigEditor:
    def __init__(self):
        self.window = ctk.CTk()
        self.window.title("GE Configuration Editor")
        self.window.geometry("1200x800")
        ctk.set_appearance_mode("dark")
        
        # Store references to prevent garbage collection of callbacks
        self.update_callback = None
        self.dpi_callback = None
        
        # Cancel any pending callbacks when window closes
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Main container
        self.main_container = ctk.CTkFrame(self.window)
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header with buttons
        self.header = ctk.CTkFrame(self.main_container)
        self.header.pack(fill="x", pady=(0, 20))
        
        self.load_btn = ctk.CTkButton(
            self.header, 
            text="Load Configuration", 
            command=self.load_config,
            width=200
        )
        self.load_btn.pack(side="left", padx=10)
        
        self.save_btn = ctk.CTkButton(
            self.header, 
            text="Save Configuration", 
            command=self.save_config,
            width=200
        )
        self.save_btn.pack(side="left", padx=10)
        
        # Content area with two columns
        self.content = ctk.CTkFrame(self.main_container)
        self.content.pack(fill="both", expand=True)
        
        # GE Pareto BLL Section
        self.pareto_frame = ctk.CTkFrame(self.content)
        self.pareto_frame.pack(side="left", fill="both", expand=True, padx=10)
        
        self.pareto_label = ctk.CTkLabel(
            self.pareto_frame, 
            text="GE Pareto BLL Configuration", 
            font=("Helvetica", 20, "bold")
        )
        self.pareto_label.pack(pady=10)
        
        # GE Classic Section
        self.classic_frame = ctk.CTkFrame(self.content)
        self.classic_frame.pack(side="right", fill="both", expand=True, padx=10)
        
        self.classic_label = ctk.CTkLabel(
            self.classic_frame, 
            text="GE Classic Configuration", 
            font=("Helvetica", 20, "bold")
        )
        self.classic_label.pack(pady=10)
        
        self.config_data = {}
        self.pareto_sliders = {}
        self.classic_sliders = {}
        
        # Create frames first
        self.pareto_frame = ctk.CTkFrame(self.content)
        self.pareto_frame.pack(side="left", fill="both", expand=True, padx=10)
        
        self.classic_frame = ctk.CTkFrame(self.content)
        self.classic_frame.pack(side="right", fill="both", expand=True, padx=10)
        
        # Create matplotlib figures with dark style
        plt.style.use('dark_background')
        self.pareto_fig, self.pareto_ax = plt.subplots(figsize=(8, 6), facecolor='#2b2b2b')
        self.classic_fig, self.classic_ax = plt.subplots(figsize=(8, 6), facecolor='#2b2b2b')
        
        # Set figure background color to match dark theme
        self.pareto_fig.patch.set_facecolor('#2b2b2b')
        self.classic_fig.patch.set_facecolor('#2b2b2b')
        
        # Create canvas for graphs
        self.pareto_canvas = FigureCanvasTkAgg(self.pareto_fig, self.pareto_frame)
        self.classic_canvas = FigureCanvasTkAgg(self.classic_fig, self.classic_frame)
        
        # Add update button for graphs
        self.update_graphs_btn = ctk.CTkButton(
            self.header,
            text="Update Graphs",
            command=self.update_transition_graphs,
            width=200
        )
        self.update_graphs_btn.pack(side="left", padx=10)
        
        # Initialize empty UI
        self.create_pareto_controls()
        self.create_classic_controls()
        
        # Initial graph update
        self.update_transition_graphs()
        
        # Initialize DPI check callback
        self.dpi_callback = None
        self.check_dpi_scaling_initial()
        
    def create_pareto_controls(self):
        states = ["Good", "Bad", "Intermediate1", "Intermediate2"]
        
        # Parameters section
        params_frame = ctk.CTkFrame(self.pareto_frame)
        params_frame.pack(fill="x", pady=(0, 10), padx=10)
        
        params_label = ctk.CTkLabel(
            params_frame,
            text="State Parameters",
            font=("Helvetica", 16, "bold")
        )
        params_label.pack(pady=5)
        
        # Create parameter controls in a grid
        for idx, state in enumerate(states):
            state_frame = ctk.CTkFrame(params_frame)
            state_frame.pack(fill="x", pady=2)
            
            ctk.CTkLabel(
                state_frame,
                text=f"{state}:",
                font=("Helvetica", 12),
                width=100
            ).pack(side="left", padx=5)
            
            # Alpha control with value display
            alpha_frame = ctk.CTkFrame(state_frame)
            alpha_frame.pack(side="left", fill="x", expand=True, padx=5)
            
            alpha_label = ctk.CTkLabel(alpha_frame, text="α:", width=20)
            alpha_label.pack(side="left")
            
            self.pareto_sliders[f"{state}_alpha"] = self.create_slider_with_value(
                alpha_frame, 0, 50, 3
            )
            
            # Lambda control with value display
            lambda_frame = ctk.CTkFrame(state_frame)
            lambda_frame.pack(side="left", fill="x", expand=True, padx=5)
            
            lambda_label = ctk.CTkLabel(lambda_frame, text="λ:", width=20)
            lambda_label.pack(side="left")
            
            self.pareto_sliders[f"{state}_lambda"] = self.create_slider_with_value(
                lambda_frame, 0, 50, 6
            )
        
        # Transition Matrix section
        trans_frame = ctk.CTkFrame(self.pareto_frame)
        trans_frame.pack(fill="both", expand=True, pady=10, padx=10)
        
        trans_label = ctk.CTkLabel(
            trans_frame,
            text="Transition Matrix",
            font=("Helvetica", 16, "bold")
        )
        trans_label.pack(pady=5)
        
        matrix_frame = ctk.CTkFrame(trans_frame)
        matrix_frame.pack(pady=10)
        
        # Column headers
        ctk.CTkLabel(matrix_frame, text="To →", width=80).grid(row=0, column=0)
        for j, state in enumerate(states):
            ctk.CTkLabel(matrix_frame, text=state, width=80).grid(row=0, column=j+1)
        
        # Row headers and transition inputs
        for i, from_state in enumerate(states):
            ctk.CTkLabel(matrix_frame, text=from_state).grid(row=i+1, column=0)
            for j, to_state in enumerate(states):
                entry = self.create_transition_entry(matrix_frame, i+1, j+1)
                self.pareto_sliders[f"{from_state}_to_{to_state}"] = entry
                
                # Set default value
                entry.insert(0, "0.25")
        
        # Add separator
        separator = ctk.CTkFrame(self.pareto_frame, height=2)
        separator.pack(fill='x', pady=10, padx=20)
        
        # Add graph title
        graph_label = ctk.CTkLabel(
            self.pareto_frame,
            text="Transition Graph Visualization",
            font=("Helvetica", 14, "bold")
        )
        graph_label.pack(pady=(10, 5))
        
        # Add graph canvas
        self.pareto_canvas.get_tk_widget().pack(pady=10, padx=20, fill="both", expand=True)

    def create_classic_controls(self):
        states = ["Good", "Bad"]
        
        # Parameters section
        params_frame = ctk.CTkFrame(self.classic_frame)
        params_frame.pack(fill="x", pady=(0, 10), padx=10)
        
        params_label = ctk.CTkLabel(
            params_frame,
            text="State Parameters",
            font=("Helvetica", 16, "bold")
        )
        params_label.pack(pady=5)
        
        # Create parameter controls
        for state in states:
            state_frame = ctk.CTkFrame(params_frame)
            state_frame.pack(fill="x", pady=2)
            
            param_name = "k" if state == "Good" else "h"
            ctk.CTkLabel(
                state_frame,
                text=f"{state} ({param_name}):",
                font=("Helvetica", 12),
                width=100
            ).pack(side="left", padx=5)
            
            self.classic_sliders[f"{state}_{param_name}"] = self.create_slider_with_value(
                state_frame, 0, 1, 0.5
            )
        
        # Transition Matrix section
        trans_frame = ctk.CTkFrame(self.classic_frame)
        trans_frame.pack(fill="both", expand=True, pady=10, padx=10)
        
        trans_label = ctk.CTkLabel(
            trans_frame,
            text="Transition Matrix",
            font=("Helvetica", 16, "bold")
        )
        trans_label.pack(pady=5)
        
        matrix_frame = ctk.CTkFrame(trans_frame)
        matrix_frame.pack(pady=10)
        
        # Column headers
        ctk.CTkLabel(matrix_frame, text="To →", width=80).grid(row=0, column=0)
        for j, state in enumerate(states):
            ctk.CTkLabel(matrix_frame, text=state, width=80).grid(row=0, column=j+1)
        
        # Row headers and transition inputs
        for i, from_state in enumerate(states):
            ctk.CTkLabel(matrix_frame, text=from_state).grid(row=i+1, column=0)
            for j, to_state in enumerate(states):
                entry = self.create_transition_entry(matrix_frame, i+1, j+1)
                self.classic_sliders[f"{from_state}_to_{to_state}"] = entry
                
                # Set default value
                entry.insert(0, "0.5")
        
        # Add separator
        separator = ctk.CTkFrame(self.classic_frame, height=2)
        separator.pack(fill='x', pady=10, padx=20)
        
        # Add graph title
        graph_label = ctk.CTkLabel(
            self.classic_frame,
            text="Transition Graph Visualization",
            font=("Helvetica", 14, "bold")
        )
        graph_label.pack(pady=(10, 5))
        
        # Add graph canvas
        self.classic_canvas.get_tk_widget().pack(pady=10, padx=20, fill="both", expand=True)

    def create_slider_with_value(self, parent, min_val, max_val, default):
        frame = ctk.CTkFrame(parent)
        frame.pack(side="left", fill="x", expand=True)
        
        value_label = ctk.CTkLabel(frame, text=f"{default:.2f}", width=50)
        value_label.pack(side="right", padx=5)
        
        slider = ctk.CTkSlider(
            frame,
            from_=min_val,
            to=max_val,
            number_of_steps=100,
            command=lambda val: value_label.configure(text=f"{val:.2f}")
        )
        slider.pack(side="left", fill="x", expand=True, padx=5)
        slider.set(default)
        
        return slider

    def create_transition_entry(self, matrix_frame, row, col):
        entry = ctk.CTkEntry(
            matrix_frame,
            width=60,
            placeholder_text="0.0"
        )
        entry.grid(row=row, column=col, padx=2, pady=2)
        # Bind the entry to update graphs when value changes
        entry.bind('<KeyRelease>', lambda e: self.update_transition_graphs())
        return entry

    def load_config(self):
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")]
        )
        if filename:
            with open(filename, 'r') as f:
                self.config_data = json.load(f)
                self.update_ui_from_config()
    
    def update_ui_from_config(self):
        # Update Pareto BLL values
        for state in ["Good", "Bad", "Intermediate1", "Intermediate2"]:
            state_data = self.config_data["GE_Pareto_BLL"][state]
            
            # Update parameters
            self.pareto_sliders[f"{state}_alpha"].set(
                state_data["params"]["alpha"]
            )
            self.pareto_sliders[f"{state}_lambda"].set(
                state_data["params"]["lambda"]
            )
            
            # Update transitions
            for target, value in state_data["transitions"].items():
                self.pareto_sliders[f"{state}_to_{target}"].delete(0, tk.END)
                self.pareto_sliders[f"{state}_to_{target}"].insert(0, f"{value:.2f}")
        
        # Update Classic values
        for state in ["Good", "Bad"]:
            state_data = self.config_data["GE_Classic"][state]
            
            # Update parameters
            param_name = "k" if state == "Good" else "h"
            self.classic_sliders[f"{state}_{param_name}"].set(
                state_data["params"][param_name]
            )
            
            # Update transitions
            for target, value in state_data["transitions"].items():
                self.classic_sliders[f"{state}_to_{target}"].delete(0, tk.END)
                self.classic_sliders[f"{state}_to_{target}"].insert(0, f"{value:.2f}")

        self.update_transition_graphs()

    def save_config(self):
        config = {
            "GE_Pareto_BLL": {},
            "GE_Classic": {}
        }
        
        # Save Pareto BLL configuration
        for state in ["Good", "Bad", "Intermediate1", "Intermediate2"]:
            config["GE_Pareto_BLL"][state] = {
                "transitions": {},
                "distribution": "pareto",
                "params": {
                    "alpha": self.pareto_sliders[f"{state}_alpha"].get(),
                    "lambda": self.pareto_sliders[f"{state}_lambda"].get()
                }
            }
            
            for target in ["Good", "Bad", "Intermediate1", "Intermediate2"]:
                config["GE_Pareto_BLL"][state]["transitions"][target] = \
                    float(self.pareto_sliders[f"{state}_to_{target}"].get())
        
        # Save Classic configuration
        for state in ["Good", "Bad"]:
            param_name = "k" if state == "Good" else "h"
            config["GE_Classic"][state] = {
                "transitions": {},
                "params": {
                    param_name: self.classic_sliders[f"{state}_{param_name}"].get()
                }
            }
            
            for target in ["Good", "Bad"]:
                config["GE_Classic"][state]["transitions"][target] = \
                    float(self.classic_sliders[f"{state}_to_{target}"].get())
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")]
        )
        if filename:
            with open(filename, 'w') as f:
                json.dump(config, f, indent=4)
    
    def run(self):
        self.window.mainloop()

    def on_closing(self):
        """Clean up all callbacks before closing"""
        # Cancel pending updates
        if self.update_callback:
            self.window.after_cancel(self.update_callback)
        if self.dpi_callback:
            self.window.after_cancel(self.dpi_callback)
            
        # Destroy all widgets and terminate
        self.window.quit()
        self.window.destroy()

    def check_dpi_scaling_initial(self):
        """Initial DPI scaling check with proper callback cleanup"""
        self.check_dpi_scaling()
        self.dpi_callback = self.window.after(1000, self.check_dpi_scaling_initial)

    def check_dpi_scaling(self):
        """DPI scaling check implementation"""
        # Your existing DPI check logic here
        # ... existing code ...

    def update_transition_graphs(self):
        try:
            # Cancel any pending update
            if self.update_callback:
                self.window.after_cancel(self.update_callback)
            
            # Update Pareto BLL graph
            self.update_graph(
                ax=self.pareto_ax,
                states=["Good", "Bad", "Intermediate1", "Intermediate2"],
                sliders=self.pareto_sliders,
                title="Pareto BLL Transitions"
            )
            self.pareto_canvas.draw()
            
            # Update Classic graph
            self.update_graph(
                ax=self.classic_ax,
                states=["Good", "Bad"],
                sliders=self.classic_sliders,
                title="Classic Transitions"
            )
            self.classic_canvas.draw()
        except Exception as e:
            print(f"Error updating graphs: {e}")

    def update_graph(self, ax, states, sliders, title):
        ax.clear()
        G = nx.DiGraph()
        
        # Set background color
        ax.set_facecolor('#2b2b2b')
        
        # Add nodes
        pos = {}
        n = len(states)
        for i, state in enumerate(states):
            angle = 2 * np.pi * i / n
            # Adjust radius to make layout more compact
            radius = 0.8
            pos[state] = (radius * np.cos(angle), radius * np.sin(angle))
            G.add_node(state)
        
        # Add edges with weights
        edge_weights = []
        for from_state in states:
            for to_state in states:
                try:
                    weight = float(sliders[f"{from_state}_to_{to_state}"].get())
                    G.add_edge(from_state, to_state, weight=weight)
                    edge_weights.append(weight)
                except Exception as e:
                    print(f"Error getting weight for {from_state} -> {to_state}: {e}")
                    weight = 0.25  # default weight
                    G.add_edge(from_state, to_state, weight=weight)
                    edge_weights.append(weight)
        
        # Draw nodes with smaller size
        nx.draw_networkx_nodes(
            G, pos,
            node_color='#4a90e2',  # Professional blue
            node_size=1000,  # Reduced size
            ax=ax,
            edgecolors='white',
            linewidths=2
        )
        
        # Draw node labels
        nx.draw_networkx_labels(
            G, pos,
            font_size=10,
            font_weight='bold',
            font_color='white',
            ax=ax
        )
        
        # Draw edges with red to green color scheme
        edges = G.edges()
        weights = [G[u][v]['weight'] for u, v in edges]
        
        # Create red to green colormap
        colors = ['#ff4444', '#ffff44', '#44ff44']  # Red -> Yellow -> Green
        custom_cmap = LinearSegmentedColormap.from_list("custom", colors, N=100)
        
        # Calculate edge styles based on self-loops
        edge_styles = []
        for (u, v) in edges:
            if u == v:  # Self-loop
                edge_styles.append({
                    'connectionstyle': 'arc3,rad=0.5',  # Larger arc for self-loops
                    'arrowsize': 20
                })
            else:
                edge_styles.append({
                    'connectionstyle': 'arc3,rad=0.2',
                    'arrowsize': 20
                })
        
        # Draw edges
        for (u, v), weight, style in zip(edges, weights, edge_styles):
            nx.draw_networkx_edges(
                G, pos,
                edgelist=[(u, v)],
                edge_color=[weight],
                edge_cmap=custom_cmap,
                edge_vmin=0,    # Minimum probability
                edge_vmax=1,    # Maximum probability
                width=3,
                ax=ax,
                **style
            )
        
        # Add colorbar with custom styling
        if hasattr(self, 'colorbar'):
            self.colorbar.remove()
        norm = plt.Normalize(0, 1)
        sm = plt.cm.ScalarMappable(cmap=custom_cmap, norm=norm)
        self.colorbar = plt.colorbar(sm, ax=ax)
        self.colorbar.ax.set_ylabel('Transition Probability', color='white')
        self.colorbar.ax.yaxis.set_tick_params(color='white')
        plt.setp(plt.getp(self.colorbar.ax.axes, 'yticklabels'), color='white')
        
        # Add custom tick labels
        tick_locs = np.array([0, 0.2, 0.4, 0.6, 0.8, 1.0])
        self.colorbar.set_ticks(tick_locs)
        
        # Style the title
        ax.set_title(title, color='white', pad=20, fontsize=14)
        ax.set_axis_off()
        
        # Adjust layout
        plt.tight_layout()
        
        # Ensure the graph fits within the figure
        ax.set_xlim([-1.2, 1.2])
        ax.set_ylim([-1.2, 1.2])

        # Force drawing update
        self.window.update()

if __name__ == "__main__":
    app = ConfigEditor()
    app.run()