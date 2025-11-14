#!/usr/bin/env python3
"""
MIDI to Keyboard Mapper with Key Combinations
Supports complex key combinations like Ctrl+Z, Shift+Alt+A, etc.

Copyright (c) 2025 Francesco Fantoni (arto_at_arto.site)
MIT License - https://opensource.org/licenses/MIT
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import rtmidi
import json
import os
import subprocess
import sys
import threading
import time
import signal
from pathlib import Path

class MidiMapperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("MIDI to Keyboard Mapper - Key Combinations")
        self.root.geometry("1000x800")
        
        # Configuration
        self.config_file = Path.home() / '.config' / 'midi2keyboard' / 'mappings.json'
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.midi_ports = []
        self.current_mappings = {}
        self.midi_in = None
        self.mapping_process = None
        self.daemon_pid_file = Path.home() / '.config' / 'midi2keyboard' / 'daemon.pid'
        
        # Load existing configuration
        self.load_config()
        
        self.setup_gui()
        self.refresh_midi_ports()
        
        # Bind close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Check if daemon is already running
        self.check_daemon_status()
    
    def check_daemon_status(self):
        """Check if daemon is already running and update UI accordingly"""
        if self.is_daemon_running():
            self.status_var.set("Mapping active (daemon running)")
            self.start_btn.config(state='disabled')
            self.stop_btn.config(state='normal')
    
    def is_daemon_running(self):
        """Check if daemon process is running"""
        if self.daemon_pid_file.exists():
            try:
                with open(self.daemon_pid_file, 'r') as f:
                    pid = int(f.read().strip())
                # Check if process exists
                os.kill(pid, 0)
                return True
            except (OSError, ValueError):
                # PID file exists but process is dead
                self.cleanup_pid_file()
        return False
    
    def cleanup_pid_file(self):
        """Remove stale PID file"""
        try:
            if self.daemon_pid_file.exists():
                self.daemon_pid_file.unlink()
        except:
            pass
    
    def setup_gui(self):
        """Setup the main GUI"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # MIDI Port Selection
        ttk.Label(main_frame, text="MIDI Port:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(main_frame, textvariable=self.port_var, state="readonly")
        self.port_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        
        refresh_btn = ttk.Button(main_frame, text="Refresh Ports", command=self.refresh_midi_ports)
        refresh_btn.grid(row=0, column=2, padx=5, pady=5)
        
        # Status
        self.status_var = tk.StringVar(value="Not running")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, foreground="red")
        status_label.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        self.start_btn = ttk.Button(button_frame, text="Start Mapping", command=self.start_mapping)
        self.start_btn.grid(row=0, column=0, padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="Stop Mapping", command=self.stop_mapping, state="disabled")
        self.stop_btn.grid(row=0, column=1, padx=5)
        
        test_btn = ttk.Button(button_frame, text="Test MIDI Input", command=self.test_midi_input)
        test_btn.grid(row=0, column=2, padx=5)
        
        # Mappings frame
        mappings_frame = ttk.LabelFrame(main_frame, text="MIDI to Keyboard Mappings (Supports Key Combinations)", padding="10")
        mappings_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        mappings_frame.columnconfigure(1, weight=1)
        
        # Treeview for mappings
        columns = ('midi_note', 'key_combination', 'description')
        self.mappings_tree = ttk.Treeview(mappings_frame, columns=columns, show='headings', height=12)
        
        # Define headings
        self.mappings_tree.heading('midi_note', text='MIDI Note/CC')
        self.mappings_tree.heading('key_combination', text='Key Combination')
        self.mappings_tree.heading('description', text='Description')
        
        # Define columns
        self.mappings_tree.column('midi_note', width=120)
        self.mappings_tree.column('key_combination', width=200)
        self.mappings_tree.column('description', width=400)
        
        self.mappings_tree.grid(row=0, column=0, columnspan=4, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar for treeview
        scrollbar = ttk.Scrollbar(mappings_frame, orient=tk.VERTICAL, command=self.mappings_tree.yview)
        self.mappings_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=4, sticky=(tk.N, tk.S))
        
        # Key combination builder
        combo_frame = ttk.LabelFrame(mappings_frame, text="Key Combination Builder", padding="10")
        combo_frame.grid(row=1, column=0, columnspan=5, sticky=(tk.W, tk.E), pady=10)
        
        # Modifier keys
        mod_frame = ttk.Frame(combo_frame)
        mod_frame.grid(row=0, column=0, columnspan=6, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(mod_frame, text="Modifiers:").grid(row=0, column=0, sticky=tk.W, padx=5)
        
        self.ctrl_var = tk.BooleanVar()
        ctrl_cb = ttk.Checkbutton(mod_frame, text="Ctrl", variable=self.ctrl_var)
        ctrl_cb.grid(row=0, column=1, padx=5)
        
        self.shift_var = tk.BooleanVar()
        shift_cb = ttk.Checkbutton(mod_frame, text="Shift", variable=self.shift_var)
        shift_cb.grid(row=0, column=2, padx=5)
        
        self.alt_var = tk.BooleanVar()
        alt_cb = ttk.Checkbutton(mod_frame, text="Alt", variable=self.alt_var)
        alt_cb.grid(row=0, column=3, padx=5)
        
        self.super_var = tk.BooleanVar()
        super_cb = ttk.Checkbutton(mod_frame, text="Super", variable=self.super_var)
        super_cb.grid(row=0, column=4, padx=5)
        
        # Main key selection
        key_frame = ttk.Frame(combo_frame)
        key_frame.grid(row=1, column=0, columnspan=6, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(key_frame, text="Main Key:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.main_key_var = tk.StringVar()
        self.main_key_combo = ttk.Combobox(key_frame, textvariable=self.main_key_var, width=20)
        self.main_key_combo['values'] = self.get_available_keys()
        self.main_key_combo.grid(row=0, column=1, padx=5)
        
        # Preview
        ttk.Label(key_frame, text="Preview:").grid(row=0, column=2, padx=5)
        self.preview_var = tk.StringVar(value="No keys selected")
        preview_label = ttk.Label(key_frame, textvariable=self.preview_var, foreground="blue")
        preview_label.grid(row=0, column=3, padx=5)
        
        # Update preview when anything changes
        self.ctrl_var.trace('w', self.update_preview)
        self.shift_var.trace('w', self.update_preview)
        self.alt_var.trace('w', self.update_preview)
        self.super_var.trace('w', self.update_preview)
        self.main_key_var.trace('w', self.update_preview)
        
        # MIDI input and description
        input_frame = ttk.Frame(combo_frame)
        input_frame.grid(row=2, column=0, columnspan=6, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(input_frame, text="MIDI Note/CC:").grid(row=0, column=0, padx=5)
        self.new_note_var = tk.StringVar()
        note_entry = ttk.Entry(input_frame, textvariable=self.new_note_var, width=10)
        note_entry.grid(row=0, column=1, padx=5)
        
        ttk.Label(input_frame, text="Description:").grid(row=0, column=2, padx=5)
        self.new_desc_var = tk.StringVar()
        desc_entry = ttk.Entry(input_frame, textvariable=self.new_desc_var, width=30)
        desc_entry.grid(row=0, column=3, padx=5)
        
        add_btn = ttk.Button(input_frame, text="Add Mapping", command=self.add_mapping)
        add_btn.grid(row=0, column=4, padx=5)
        
        remove_btn = ttk.Button(input_frame, text="Remove Selected", command=self.remove_mapping)
        remove_btn.grid(row=0, column=5, padx=5)
        
        # Quick presets for common applications
        presets_frame = ttk.LabelFrame(mappings_frame, text="Quick Presets", padding="10")
        presets_frame.grid(row=2, column=0, columnspan=5, sticky=(tk.W, tk.E), pady=10)
        
        # Krita presets
        ttk.Button(presets_frame, text="Load Krita Presets", 
                  command=self.load_krita_presets).grid(row=0, column=0, padx=5, pady=2)
        ttk.Button(presets_frame, text="Load Inkscape Presets", 
                  command=self.load_inkscape_presets).grid(row=0, column=1, padx=5, pady=2)
        ttk.Button(presets_frame, text="Load Blender Presets", 
                  command=self.load_blender_presets).grid(row=0, column=2, padx=5, pady=2)
        
        # File operations
        file_frame = ttk.Frame(main_frame)
        file_frame.grid(row=4, column=0, columnspan=3, pady=10)
        
        ttk.Button(file_frame, text="Load Configuration", command=self.load_config_dialog).grid(row=0, column=0, padx=5)
        ttk.Button(file_frame, text="Save Configuration", command=self.save_config_dialog).grid(row=0, column=1, padx=5)
        ttk.Button(file_frame, text="Reset to Defaults", command=self.reset_to_defaults).grid(row=0, column=2, padx=5)
        
        # Configure main frame row weights
        main_frame.rowconfigure(3, weight=1)
        mappings_frame.rowconfigure(0, weight=1)
        mappings_frame.columnconfigure(0, weight=1)
        
        # Bind double-click to edit
        self.mappings_tree.bind('<Double-1>', self.on_mapping_double_click)
        
        # Populate mappings tree
        self.refresh_mappings_tree()
    
    def get_available_keys(self):
        """Return list of available key names"""
        common_keys = [
            'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
            'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
            '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
            'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12',
            'space', 'tab', 'enter', 'backspace', 'escape',
            'left', 'right', 'up', 'down',
            'comma', 'period', 'slash', 'semicolon', 'apostrophe', 'backslash',
            'leftbrace', 'rightbrace', 'equal', 'minus', 'grave',
            'pageup', 'pagedown', 'home', 'end', 'insert', 'delete'
        ]
        return common_keys
    
    def update_preview(self, *args):
        """Update the key combination preview"""
        modifiers = []
        if self.ctrl_var.get():
            modifiers.append("Ctrl")
        if self.shift_var.get():
            modifiers.append("Shift")
        if self.alt_var.get():
            modifiers.append("Alt")
        if self.super_var.get():
            modifiers.append("Super")
        
        main_key = self.main_key_var.get()
        
        if modifiers and main_key:
            preview = "+".join(modifiers) + "+" + main_key.upper()
        elif main_key:
            preview = main_key.upper()
        else:
            preview = "No keys selected"
        
        self.preview_var.set(preview)
    
    def get_current_combination(self):
        """Get the current key combination as a list"""
        combination = []
        if self.ctrl_var.get():
            combination.append('leftctrl')
        if self.shift_var.get():
            combination.append('leftshift')
        if self.alt_var.get():
            combination.append('leftalt')
        if self.super_var.get():
            combination.append('leftmeta')
        
        main_key = self.main_key_var.get()
        if main_key:
            combination.append(main_key)
        
        return combination
    
    def set_combination_from_list(self, key_list):
        """Set the UI from a key combination list"""
        # Reset all modifiers
        self.ctrl_var.set(False)
        self.shift_var.set(False)
        self.alt_var.set(False)
        self.super_var.set(False)
        self.main_key_var.set('')
        
        for key in key_list:
            if key in ['leftctrl', 'ctrl']:
                self.ctrl_var.set(True)
            elif key in ['leftshift', 'shift']:
                self.shift_var.set(True)
            elif key in ['leftalt', 'alt']:
                self.alt_var.set(True)
            elif key in ['leftmeta', 'super', 'meta']:
                self.super_var.set(True)
            else:
                self.main_key_var.set(key)
        
        self.update_preview()
    
    def refresh_midi_ports(self):
        """Refresh list of available MIDI ports"""
        if self.midi_in is None:
            self.midi_in = rtmidi.MidiIn()
        
        self.midi_ports = self.midi_in.get_ports()
        port_values = []
        for i, port in enumerate(self.midi_ports):
            port_values.append(f"{i}: {port}")
        
        self.port_combo['values'] = port_values
        
        if self.midi_ports:
            self.port_combo.set(port_values[0])
        else:
            self.port_combo.set('')
            messagebox.showwarning("No MIDI Ports", "No MIDI input ports found. Please connect your MIDI controller.")
    
    def load_config(self, filename=None):
        """Load configuration from file"""
        if filename is None:
            filename = self.config_file
        
        if not os.path.exists(filename):
            # Create default configuration with combinations
            self.current_mappings = {
                'mappings': {
                    '48': {'keys': ['b'], 'desc': 'Brush tool'},
                    '50': {'keys': ['e'], 'desc': 'Eraser'},
                    '52': {'keys': ['v'], 'desc': 'Select tool'},
                    '53': {'keys': ['m'], 'desc': 'Move tool'},
                    '55': {'keys': ['leftctrl', 'z'], 'desc': 'Undo'},
                    '60': {'keys': ['leftctrl', 'shift', 'z'], 'desc': 'Redo'},
                    '62': {'keys': ['leftctrl', 's'], 'desc': 'Save'},
                    '64': {'keys': ['leftctrl', 'a'], 'desc': 'Select All'},
                    '65': {'keys': ['leftctrl', 'c'], 'desc': 'Copy'},
                    '67': {'keys': ['leftctrl', 'v'], 'desc': 'Paste'},
                    '72': {'keys': ['leftbrace'], 'desc': 'Decrease brush size'},
                    '74': {'keys': ['rightbrace'], 'desc': 'Increase brush size'},
                },
                'midi_port': 0
            }
            self.save_config()
        else:
            try:
                with open(filename, 'r') as f:
                    self.current_mappings = json.load(f)
                print(f"Configuration loaded from {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load configuration: {e}")
    
    def save_config(self, filename=None):
        """Save configuration to file"""
        if filename is None:
            filename = self.config_file
        
        try:
            with open(filename, 'w') as f:
                json.dump(self.current_mappings, f, indent=2)
            print(f"Configuration saved to {filename}")
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {e}")
            return False
    
    def refresh_mappings_tree(self):
        """Refresh the mappings treeview"""
        for item in self.mappings_tree.get_children():
            self.mappings_tree.delete(item)
        
        if 'mappings' in self.current_mappings:
            for note, mapping in self.current_mappings['mappings'].items():
                # Format key combination for display
                keys = mapping['keys']
                display_keys = "+".join(k.upper() if len(k) > 1 else k for k in keys)
                
                self.mappings_tree.insert('', tk.END, values=(
                    note, display_keys, mapping['desc']
                ))
    
    def add_mapping(self):
        """Add a new mapping"""
        note = self.new_note_var.get().strip()
        key_combination = self.get_current_combination()
        desc = self.new_desc_var.get().strip()
        
        if not note:
            messagebox.showwarning("Input Error", "Please enter a MIDI note/CC number")
            return
        
        if not key_combination:
            messagebox.showwarning("Input Error", "Please select at least one key")
            return
        
        # Validate MIDI note is a number
        try:
            note_int = int(note)
            if note_int < 0 or note_int > 127:
                messagebox.showwarning("Input Error", "MIDI note/CC must be between 0 and 127")
                return
        except ValueError:
            messagebox.showwarning("Input Error", "MIDI note/CC must be a number")
            return
        
        if 'mappings' not in self.current_mappings:
            self.current_mappings['mappings'] = {}
        
        self.current_mappings['mappings'][note] = {
            'keys': key_combination,
            'desc': desc or f"MIDI {note} to {'+'.join(key_combination)}"
        }
        
        self.refresh_mappings_tree()
        self.new_note_var.set('')
        self.new_desc_var.set('')
        # Don't clear the key combination - user might want to add another mapping with same combo
        
        # Auto-save configuration
        self.save_config()
        
        print(f"Added mapping: MIDI {note} -> {key_combination} ({desc})")
    
    def remove_mapping(self):
        """Remove selected mapping"""
        selected = self.mappings_tree.selection()
        if not selected:
            messagebox.showwarning("Selection Error", "Please select one or more mappings to remove")
            return
        
        # Confirm deletion
        if not messagebox.askyesno("Confirm Delete", 
                                f"Are you sure you want to remove {len(selected)} mapping(s)?"):
            return
        
        # Get all selected items and their MIDI note values
        notes_to_remove = []
        for item in selected:
            values = self.mappings_tree.item(item)['values']
            if values and len(values) > 0:
                note = str(values[0])  # Convert to string to match JSON keys
                notes_to_remove.append(note)
        
        # Remove from current_mappings
        removed_count = 0
        if 'mappings' in self.current_mappings:
            for note in notes_to_remove:
                if note in self.current_mappings['mappings']:
                    del self.current_mappings['mappings'][note]
                    removed_count += 1
                    print(f"Removed mapping for MIDI note {note}")
        
        # Update the UI and save
        if removed_count > 0:
            self.refresh_mappings_tree()
            self.save_config()
            messagebox.showinfo("Success", f"Removed {removed_count} mapping(s)")
        else:
            messagebox.showwarning("Remove Error", "No mappings were found to remove")
    
    def on_mapping_double_click(self, event):
        """Edit mapping on double click"""
        item = self.mappings_tree.selection()
        if item:
            item = item[0]
            values = self.mappings_tree.item(item)['values']
            if values:
                self.new_note_var.set(values[0])
                self.new_desc_var.set(values[2])
                
                # Parse the key combination back into the UI
                note = values[0]
                if note in self.current_mappings['mappings']:
                    key_list = self.current_mappings['mappings'][note]['keys']
                    self.set_combination_from_list(key_list)
    
    def load_krita_presets(self):
        """Load Krita-specific presets"""
        krita_presets = {
            '36': {'keys': ['b'], 'desc': 'Brush Tool'},
            '37': {'keys': ['e'], 'desc': 'Eraser Tool'},
            '38': {'keys': ['m'], 'desc': 'Mirror View'},
            '39': {'keys': ['r'], 'desc': 'Rotate Canvas'},
            '40': {'keys': ['leftctrl', 'z'], 'desc': 'Undo'},
            '41': {'keys': ['leftctrl', 'shift', 'z'], 'desc': 'Redo'},
            '42': {'keys': ['leftctrl', 's'], 'desc': 'Save'},
            '43': {'keys': ['leftbrace'], 'desc': 'Decrease Brush Size'},
            '44': {'keys': ['rightbrace'], 'desc': 'Increase Brush Size'},
            '45': {'keys': ['leftshift'], 'desc': 'Color Pick (Hold)'},
            '46': {'keys': ['x'], 'desc': 'Swap Foreground/Background'},
            '47': {'keys': ['d'], 'desc': 'Reset Colors'},
            '48': {'keys': ['leftctrl', 'a'], 'desc': 'Select All'},
            '49': {'keys': ['leftctrl', 'd'], 'desc': 'Deselect'},
        }
        
        if messagebox.askyesno("Load Presets", "Load Krita presets? This will replace your current mappings."):
            self.current_mappings['mappings'] = krita_presets
            self.refresh_mappings_tree()
            self.save_config()
            messagebox.showinfo("Success", "Krita presets loaded!")
    
    def load_inkscape_presets(self):
        """Load Inkscape-specific presets"""
        inkscape_presets = {
            '36': {'keys': ['f1'], 'desc': 'Selector Tool'},
            '37': {'keys': ['f2'], 'desc': 'Edit Paths Tool'},
            '38': {'keys': ['f5'], 'desc': 'Zoom Tool'},
            '39': {'keys': ['f6'], 'desc': 'Rectangle Tool'},
            '40': {'keys': ['leftctrl', 'z'], 'desc': 'Undo'},
            '41': {'keys': ['leftctrl', 'shift', 'z'], 'desc': 'Redo'},
            '42': {'keys': ['leftctrl', 's'], 'desc': 'Save'},
            '43': {'keys': ['leftctrl', 'a'], 'desc': 'Select All'},
            '44': {'keys': ['leftctrl', 'd'], 'desc': 'Duplicate'},
            '45': {'keys': ['leftctrl', 'g'], 'desc': 'Group'},
            '46': {'keys': ['leftctrl', 'shift', 'g'], 'desc': 'Ungroup'},
            '47': {'keys': ['leftctrl', 'shift', 'c'], 'desc': 'Combine Paths'},
            '48': {'keys': ['leftctrl', 'shift', 'b'], 'desc': 'Break Apart'},
        }
        
        if messagebox.askyesno("Load Presets", "Load Inkscape presets? This will replace your current mappings."):
            self.current_mappings['mappings'] = inkscape_presets
            self.refresh_mappings_tree()
            self.save_config()
            messagebox.showinfo("Success", "Inkscape presets loaded!")
    
    def load_blender_presets(self):
        """Load Blender-specific presets"""
        blender_presets = {
            '36': {'keys': ['tab'], 'desc': 'Toggle Edit Mode'},
            '37': {'keys': ['g'], 'desc': 'Grab/Move'},
            '38': {'keys': ['r'], 'desc': 'Rotate'},
            '39': {'keys': ['s'], 'desc': 'Scale'},
            '40': {'keys': ['leftctrl', 'z'], 'desc': 'Undo'},
            '41': {'keys': ['leftctrl', 'shift', 'z'], 'desc': 'Redo'},
            '42': {'keys': ['a'], 'desc': 'Select All'},
            '43': {'keys': ['b'], 'desc': 'Box Select'},
            '44': {'keys': ['c'], 'desc': 'Circle Select'},
            '45': {'keys': ['x'], 'desc': 'Delete'},
            '46': {'keys': ['leftshift', 'a'], 'desc': 'Add Menu'},
            '47': {'keys': ['z'], 'desc': 'Toggle Wireframe'},
        }
        
        if messagebox.askyesno("Load Presets", "Load Blender presets? This will replace your current mappings."):
            self.current_mappings['mappings'] = blender_presets
            self.refresh_mappings_tree()
            self.save_config()
            messagebox.showinfo("Success", "Blender presets loaded!")
    
    def get_selected_port_index(self):
        """Get the selected MIDI port index"""
        selected = self.port_combo.get()
        if selected and ':' in selected:
            return int(selected.split(':')[0])
        return 0
    
    def start_mapping(self):
        """Start the MIDI to keyboard mapping"""
        if not self.midi_ports:
            messagebox.showerror("Error", "No MIDI ports available")
            return
        
        selected_port = self.get_selected_port_index()
        print(f"Starting mapping on port {selected_port}: {self.midi_ports[selected_port]}")
        
        # Save current configuration with selected port
        self.current_mappings['midi_port'] = selected_port
        self.save_config()
        
        # Export configuration for daemon
        daemon_config = self.export_config_for_daemon()
        
        # Start the daemon process
        try:
            # Get the path to the daemon script
            daemon_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'midi2keyboard_daemon.py')
            
            # Start the daemon with the selected port
            self.mapping_process = subprocess.Popen([
                'pkexec', 'python3', daemon_script,
                '--config', daemon_config,
                '--port', str(selected_port)
            ])
            
            self.status_var.set(f"Mapping active - port {selected_port}")
            self.start_btn.config(state='disabled')
            self.stop_btn.config(state='normal')
            
            print(f"Daemon started with config: {daemon_config}, port: {selected_port}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start mapping daemon: {e}")
            print(f"Error starting daemon: {e}")
    
    def stop_mapping(self):
        """Stop the MIDI to keyboard mapping"""
        # Use sudo to kill the daemon process
        try:
            # Method 1: Try to find and kill the daemon process
            kill_cmd = ['pkexec', 'pkill', '-f', 'midi2keyboard_daemon.py']
            subprocess.run(kill_cmd, timeout=10)
            
            # Method 2: If pkill doesn't work, try with sudo killall
            time.sleep(1)
            if self.is_daemon_running():
                kill_cmd = ['pkexec', 'killall', '-9', 'python3']
                subprocess.run(kill_cmd, timeout=5)
            
            # Clean up PID file
            self.cleanup_pid_file()
            
            self.status_var.set("Not running")
            self.start_btn.config(state='normal')
            self.stop_btn.config(state='disabled')
            print("Mapping stopped")
            
        except subprocess.TimeoutExpired:
            messagebox.showerror("Error", "Timeout trying to stop daemon")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop mapping: {e}")
            print(f"Error stopping daemon: {e}")
    
    def test_midi_input(self):
        """Test MIDI input from selected port"""
        selected_port = self.get_selected_port_index()
        if selected_port >= len(self.midi_ports):
            messagebox.showerror("Error", "Invalid MIDI port selected")
            return
        
        def test_thread():
            midi_in = rtmidi.MidiIn()
            try:
                midi_in.open_port(selected_port)
                midi_in.ignore_types(sysex=False, timing=False, active_sense=False)
                
                self.root.after(0, lambda: messagebox.showinfo("MIDI Test", 
                    "MIDI test started. Press keys on your MIDI controller. Check terminal for output."))
                
                print(f"MIDI Test Mode - Port {selected_port}: {self.midi_ports[selected_port]}")
                print("Press keys on your MIDI controller. Press Ctrl+C in terminal to stop test.")
                
                try:
                    timer = time.time()
                    while time.time() - timer < 30:  # 30 second timeout
                        msg = midi_in.get_message()
                        if msg:
                            message, delta_time = msg
                            print(f"MIDI message: {message}")
                        time.sleep(0.01)
                except KeyboardInterrupt:
                    pass
                finally:
                    midi_in.close_port()
                    print("MIDI test ended")
                    
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"MIDI test failed: {e}"))
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def load_config_dialog(self):
        """Load configuration from file dialog"""
        filename = filedialog.askopenfilename(
            title="Load Configuration",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            self.load_config(filename)
            self.refresh_mappings_tree()
            messagebox.showinfo("Success", f"Configuration loaded from {filename}")
    
    def save_config_dialog(self):
        """Save configuration to file dialog"""
        filename = filedialog.asksaveasfilename(
            title="Save Configuration",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            if self.save_config(filename):
                messagebox.showinfo("Success", f"Configuration saved to {filename}")
    
    def reset_to_defaults(self):
        """Reset to default mappings"""
        if messagebox.askyesno("Confirm Reset", "Reset all mappings to defaults?"):
            self.load_config()  # This will reload defaults
            self.refresh_mappings_tree()
            messagebox.showinfo("Success", "Reset to default mappings")
    
    def export_config_for_daemon(self):
        """Export configuration in daemon format"""
        daemon_config = {
            'mappings': {}
        }
        
        if 'mappings' in self.current_mappings:
            for note, mapping in self.current_mappings['mappings'].items():
                daemon_config['mappings'][note] = mapping['keys']
        
        export_path = self.config_file.parent / 'daemon_mappings.json'
        with open(export_path, 'w') as f:
            json.dump(daemon_config, f, indent=2)
        
        print(f"Exported daemon config to {export_path}")
        return str(export_path)
    
    def on_closing(self):
        """Handle application closing"""
        # Only try to stop mapping if it's actually running
        if self.is_daemon_running():
            self.stop_mapping()
        self.root.destroy()

def main():
    # Check if running as root
    if os.geteuid() == 0:
        messagebox.showwarning("Root Warning", 
                             "Running the GUI as root is not recommended.\n"
                             "Please run as regular user and use sudo only for the daemon.")
        return
    
    root = tk.Tk()
    app = MidiMapperGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()