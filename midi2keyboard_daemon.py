#!/usr/bin/env python3
"""
MIDI to Keyboard Daemon - Key Combinations
Supports complex key combinations like Ctrl+Z, Shift+Alt+A, etc.

Copyright (c) 2025 Francesco Fantoni (arto_at_arto.site)
MIT License - https://opensource.org/licenses/MIT
"""


import rtmidi
import time
import json
import argparse
import os
import sys
from evdev import UInput, ecodes as e
import math

class WaylandMidiMapper:
    def __init__(self, config_file, port=0):
        self.config_file = config_file
        self.midi_port = port
        self.midi_in = rtmidi.MidiIn()
        self.ui = None
        self.running = False
        self.active_notes = {}
        self.active_cc = {}
        self.key_mappings = {}
        self.cc_mappings = {}
        self.cc_last_values = {}
        self.cc_last_event_time = {}
        
        self.load_config()
        self.setup_uinput()
    
    def load_config(self):
        """Load configuration from file"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                if 'mappings' in config:
                    for midi_id, mapping in config['mappings'].items():
                        try:
                            midi_num = int(midi_id)
                            map_type = mapping.get('type', 'key')
                            
                            if map_type == 'key':
                                # Key mapping
                                key_codes = []
                                for key_name in mapping.get('keys', []):
                                    key_code = self.get_key_code(key_name)
                                    if key_code is not None:
                                        key_codes.append(key_code)
                                    else:
                                        print(f"Warning: Unknown key name '{key_name}' for MIDI {midi_num}")
                                
                                if key_codes:
                                    self.key_mappings[midi_num] = {
                                        'type': 'key',
                                        'key_codes': key_codes,
                                        'desc': mapping.get('desc', '')
                                    }
                                    print(f"Loaded key mapping: MIDI {midi_num} -> {[self.get_key_name(kc) for kc in key_codes]}")
                            
                            else:
                                # CC mapping - store the entire mapping
                                self.cc_mappings[midi_num] = mapping
                                # Make sure keys are converted to key codes if present
                                if 'keys' in mapping:
                                    key_codes = []
                                    for key_name in mapping.get('keys', []):
                                        key_code = self.get_key_code(key_name)
                                        if key_code is not None:
                                            key_codes.append(key_code)
                                    if key_codes:
                                        mapping['key_codes'] = key_codes
                                
                                print(f"Loaded CC mapping: CC {midi_num} -> {map_type} ({mapping.get('desc', '')})")
                        
                        except ValueError:
                            print(f"Warning: Invalid MIDI number '{midi_id}'")
                
                print(f"Configuration loaded from {self.config_file}")
        
        except Exception as ex:
            print(f"Error loading config: {ex}")
            sys.exit(1)
    
    def setup_uinput(self):
        """Setup uinput device with keyboard and mouse capabilities"""
        # Keyboard capabilities
        key_capabilities = list(e.keys.keys())
        
        # Mouse capabilities
        rel_capabilities = [
            e.REL_X, e.REL_Y,           # Mouse movement
            e.REL_WHEEL, e.REL_HWHEEL,  # Mouse wheel
            e.REL_WHEEL_HI_RES, e.REL_HWHEEL_HI_RES  # High-res wheel
        ]
        
        # Button capabilities
        btn_capabilities = [
            e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE,  # Mouse buttons
            e.BTN_SIDE, e.BTN_EXTRA,                # Extra mouse buttons
        ]
        
        capabilities = {
            e.EV_KEY: key_capabilities,
            e.EV_REL: rel_capabilities,
        }
        
        self.ui = UInput(capabilities, name='midi2keyboard-virtual-device')
        print("Virtual input device created with keyboard and mouse capabilities")
    
    def get_key_code(self, key_name):
        """Get the key code from key name"""
        key_aliases = {
            'ctrl': 'leftctrl',
            'control': 'leftctrl',
            'shift': 'leftshift',
            'alt': 'leftalt',
            'super': 'leftmeta',
            'meta': 'leftmeta',
            'windows': 'leftmeta',
            'cmd': 'leftmeta',
        }
        
        normalized_name = key_aliases.get(key_name.lower(), key_name.lower())
        key_attr = f"KEY_{normalized_name.upper()}"
        
        if hasattr(e, key_attr):
            return getattr(e, key_attr)
        
        # Special cases
        special_cases = {
            'leftbrace': e.KEY_LEFTBRACE,
            'rightbrace': e.KEY_RIGHTBRACE,
            'comma': e.KEY_COMMA,
            'period': e.KEY_DOT,
            'slash': e.KEY_SLASH,
            'semicolon': e.KEY_SEMICOLON,
            'apostrophe': e.KEY_APOSTROPHE,
            'backslash': e.KEY_BACKSLASH,
            'equal': e.KEY_EQUAL,
            'minus': e.KEY_MINUS,
            'grave': e.KEY_GRAVE,
        }
        
        return special_cases.get(normalized_name)
    
    def get_key_name(self, key_code):
        """Get the name of a key from its key code"""
        if not hasattr(self, '_key_code_map'):
            self._key_code_map = {}
            for name in dir(e):
                if name.startswith('KEY_'):
                    code = getattr(e, name)
                    self._key_code_map[code] = name[4:].lower()
        
        return self._key_code_map.get(key_code, f"UNKNOWN({key_code})")
    
    def press_key_combination(self, key_codes):
        """Press a combination of keys"""
        for key_code in key_codes:
            self.ui.write(e.EV_KEY, key_code, 1)
        
        self.ui.syn()
        time.sleep(0.05)
        
        for key_code in reversed(key_codes):
            self.ui.write(e.EV_KEY, key_code, 0)
        
        self.ui.syn()
    
    def note_on_handler(self, note, velocity):
        """Handle MIDI note-on events"""
        if note in self.key_mappings:
            mapping = self.key_mappings[note]
            if mapping['type'] == 'key':
                key_codes = mapping['key_codes']
                print(f"Note {note} -> Key combination: {[self.get_key_name(kc) for kc in key_codes]}")
                self.press_key_combination(key_codes)
                self.active_notes[note] = key_codes
        else:
            print(f"Note {note} pressed but no mapping found")
    
    def note_off_handler(self, note):
        """Handle MIDI note-off events"""
        if note in self.active_notes:
            del self.active_notes[note]
    
    def control_change_handler(self, control, value):
        """Handle MIDI control change events with various mapping types"""
        if control in self.cc_mappings:
            mapping = self.cc_mappings[control]
            map_type = mapping.get('type', 'toggle')
            
            if map_type == 'toggle':
                self.handle_cc_toggle(control, value, mapping)
            
            elif map_type == 'key':
                self.handle_cc_key(control, value, mapping)
            
            elif map_type == 'slider':
                self.handle_cc_slider(control, value, mapping)
            
            elif map_type == 'mouse_wheel':
                self.handle_cc_mouse_wheel(control, value, mapping)
        
        else:
            print(f"CC {control} changed to {value} but no mapping found")
    
    def handle_cc_toggle(self, control, value, mapping):
        """Handle CC as toggle (on/off at threshold)"""
        threshold = mapping.get('threshold', 64)
        key_codes = mapping.get('key_codes', [])
        
        if value >= threshold:
            if control not in self.active_cc:
                # Press and hold
                for key_code in key_codes:
                    self.ui.write(e.EV_KEY, key_code, 1)
                self.ui.syn()
                self.active_cc[control] = key_codes
                print(f"CC {control} (value {value}) -> TOGGLE ON")
        else:
            if control in self.active_cc:
                # Release
                for key_code in reversed(self.active_cc[control]):
                    self.ui.write(e.EV_KEY, key_code, 0)
                self.ui.syn()
                del self.active_cc[control]
                print(f"CC {control} (value {value}) -> TOGGLE OFF")
    
    def handle_cc_key(self, control, value, mapping):
        """Handle CC as key press (press on threshold crossing)"""
        threshold = mapping.get('threshold', 64)
        key_codes = mapping.get('key_codes', [])
        
        last_value = self.cc_last_values.get(control, 0)
        
        # Check if we crossed the threshold
        if last_value < threshold <= value:
            print(f"CC {control} crossed threshold up -> Key press")
            self.press_key_combination(key_codes)
        
        elif last_value >= threshold > value:
            print(f"CC {control} crossed threshold down -> Key press")
            self.press_key_combination(key_codes)
        
        self.cc_last_values[control] = value
    
    def handle_cc_slider(self, control, value, mapping):
        """Handle CC as slider (repeated key presses based on value)"""
        threshold = mapping.get('threshold', 64)
        key_codes = mapping.get('key_codes', [])
        repeat_rate = mapping.get('repeat_rate', 0)
        
        last_value = self.cc_last_values.get(control, 64)
        last_time = self.cc_last_event_time.get(control, 0)
        
        # Calculate direction and amount
        if value > last_value:
            direction = "up"
            amount = value - last_value
        elif value < last_value:
            direction = "down"
            amount = last_value - value
        else:
            return  # No change
        
        current_time = time.time()
        
        # Apply repeat rate if specified
        if repeat_rate > 0 and (current_time - last_time) < (1.0 / repeat_rate):
            return  # Too soon for next event
        
        # Press keys based on amount (scaled)
        if amount > 5:  # Significant change
            print(f"CC {control} slider: {direction} (value: {value}, change: {amount})")
            self.press_key_combination(key_codes)
        
        self.cc_last_values[control] = value
        self.cc_last_event_time[control] = current_time
    
    def handle_cc_mouse_wheel(self, control, value, mapping):
        """Handle CC as mouse wheel"""
        last_value = self.cc_last_values.get(control, 64)
        wheel_dir = mapping.get('wheel_dir', 'vertical')
        
        # Calculate wheel movement
        diff = value - last_value
        
        if diff > 0:
            # Wheel up/right
            if wheel_dir == 'vertical':
                self.ui.write(e.EV_REL, e.REL_WHEEL, 1)
                self.ui.write(e.EV_REL, e.REL_WHEEL_HI_RES, 120)
                print(f"CC {control} -> Mouse wheel UP ({diff})")
            else:
                self.ui.write(e.EV_REL, e.REL_HWHEEL, 1)
                self.ui.write(e.EV_REL, e.REL_HWHEEL_HI_RES, 120)
                print(f"CC {control} -> Mouse wheel RIGHT ({diff})")
        
        elif diff < 0:
            # Wheel down/left
            if wheel_dir == 'vertical':
                self.ui.write(e.EV_REL, e.REL_WHEEL, -1)
                self.ui.write(e.EV_REL, e.REL_WHEEL_HI_RES, -120)
                print(f"CC {control} -> Mouse wheel DOWN ({abs(diff)})")
            else:
                self.ui.write(e.EV_REL, e.REL_HWHEEL, -1)
                self.ui.write(e.EV_REL, e.REL_HWHEEL_HI_RES, -120)
                print(f"CC {control} -> Mouse wheel LEFT ({abs(diff)})")
        
        self.ui.syn()
        self.cc_last_values[control] = value
    
    def midi_callback(self, event, data=None):
        """Callback for MIDI input"""
        message, delta_time = event
        message_type = message[0] & 0xF0
        
        if message_type == 0x90:  # Note On
            note, velocity = message[1], message[2]
            if velocity > 0:
                self.note_on_handler(note, velocity)
            else:
                self.note_off_handler(note)
                
        elif message_type == 0x80:  # Note Off
            note = message[1]
            self.note_off_handler(note)
            
        elif message_type == 0xB0:  # Control Change
            control, value = message[1], message[2]
            self.control_change_handler(control, value)
    
    def start(self):
        """Start the MIDI mapper"""
        ports = self.midi_in.get_ports()
        if not ports:
            print("No MIDI input ports found!")
            return False
        
        port_number = self.midi_port
        if port_number >= len(ports):
            print(f"Error: Requested port {port_number} not available. Only {len(ports)} ports found.")
            return False
        
        try:
            print(f"Attempting to connect to MIDI port {port_number}: {ports[port_number]}")
            self.midi_in.open_port(port_number)
            self.midi_in.set_callback(self.midi_callback)
            self.midi_in.ignore_types(sysex=False, timing=False, active_sense=False)
            
            self.running = True
            
            print(f"Successfully connected to MIDI port: {ports[port_number]}")
            print("MIDI to Keyboard/CC mapper started!")
            
            # Display active mappings
            if self.key_mappings:
                print("\nKey mappings:")
                for note, mapping in self.key_mappings.items():
                    if mapping['type'] == 'key':
                        key_names = [self.get_key_name(kc) for kc in mapping['key_codes']]
                        print(f"  MIDI {note} -> {key_names}")
            
            if self.cc_mappings:
                print("\nCC mappings:")
                for cc, mapping in self.cc_mappings.items():
                    print(f"  CC {cc} -> {mapping.get('type', 'unknown')} ({mapping.get('desc', '')})")
            
            print("\nPress Ctrl+C to stop")
            
            # Keep the program running
            while self.running:
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\nStopping...")
        except Exception as ex:
            print(f"Error: {ex}")
        finally:
            self.stop()
        
        return True
    
    def stop(self):
        """Stop the mapper and clean up"""
        self.running = False
        
        # Release all active keys
        for key_codes in self.active_cc.values():
            for key_code in reversed(key_codes):
                self.ui.write(e.EV_KEY, key_code, 0)
        
        self.ui.syn()
        
        if self.midi_in:
            self.midi_in.close_port()
        if self.ui:
            self.ui.close()
        
        print("MIDI mapper stopped.")

def main():
    parser = argparse.ArgumentParser(description='MIDI to Keyboard/CC Mapper')
    parser.add_argument('--config', '-c', required=True, help='Configuration file')
    parser.add_argument('--port', '-p', type=int, default=0, help='MIDI port number')
    
    args = parser.parse_args()
    
    if os.geteuid() != 0:
        print("Error: This daemon requires root privileges to simulate input.")
        print("Please run through the GUI or use: sudo python3 midi2keyboard_daemon.py -c config.json -p PORT")
        sys.exit(1)
    
    if not os.path.exists(args.config):
        print(f"Error: Configuration file not found: {args.config}")
        sys.exit(1)
    
    print(f"Starting MIDI mapper with config: {args.config}, port: {args.port}")
    mapper = WaylandMidiMapper(args.config, args.port)
    mapper.start()

if __name__ == "__main__":
    main()