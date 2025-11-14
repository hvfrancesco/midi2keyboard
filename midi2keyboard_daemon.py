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

class WaylandMidiMapper:
    def __init__(self, config_file, port=0):
        self.config_file = config_file
        self.midi_port = port
        self.midi_in = rtmidi.MidiIn()
        self.ui = None
        self.running = False
        self.active_notes = {}  # note -> list of key_codes that are currently pressed
        self.key_mappings = {}  # note -> list of key_codes to press
        
        self.load_config()
        self.setup_uinput()
    
    def load_config(self):
        """Load configuration from file"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                if 'mappings' in config:
                    # Convert string key names to evdev key codes
                    for midi_note, key_list in config['mappings'].items():
                        key_codes = []
                        key_names = []
                        for key_name in key_list:
                            key_code = self.get_key_code(key_name)
                            if key_code is not None:
                                key_codes.append(key_code)
                                key_names.append(key_name)
                            else:
                                print(f"Warning: Unknown key name '{key_name}' for MIDI note {midi_note}")
                        
                        if key_codes:
                            self.key_mappings[int(midi_note)] = key_codes
                            print(f"Loaded mapping: MIDI {midi_note} -> {key_names}")
                print(f"Configuration loaded from {self.config_file}")
        except Exception as ex:
            print(f"Error loading config: {ex}")
            sys.exit(1)
    
    def get_key_code(self, key_name):
        """Get the key code from key name"""
        # Handle modifier keys with common aliases
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
        
        # Normalize key name
        normalized_name = key_aliases.get(key_name.lower(), key_name.lower())
        
        # Try to find the key code
        key_attr = f"KEY_{normalized_name.upper()}"
        if hasattr(e, key_attr):
            return getattr(e, key_attr)
        
        # If not found, try some common variations
        if normalized_name in ['leftbrace', '[']:
            return e.KEY_LEFTBRACE
        elif normalized_name in ['rightbrace', ']']:
            return e.KEY_RIGHTBRACE
        elif normalized_name in ['comma', ',']:
            return e.KEY_COMMA
        elif normalized_name in ['period', '.']:
            return e.KEY_DOT
        elif normalized_name in ['slash', '/']:
            return e.KEY_SLASH
        elif normalized_name in ['semicolon', ';']:
            return e.KEY_SEMICOLON
        elif normalized_name in ['apostrophe', "'"]:
            return e.KEY_APOSTROPHE
        elif normalized_name in ['backslash', '\\']:
            return e.KEY_BACKSLASH
        elif normalized_name in ['equal', '=']:
            return e.KEY_EQUAL
        elif normalized_name in ['minus', '-']:
            return e.KEY_MINUS
        elif normalized_name in ['grave', '`']:
            return e.KEY_GRAVE
        
        return None
    
    def get_key_name(self, key_code):
        """Get the name of a key from its key code"""
        # Create a reverse mapping of key codes to names
        if not hasattr(self, '_key_code_map'):
            self._key_code_map = {}
            for name in dir(e):
                if name.startswith('KEY_'):
                    code = getattr(e, name)
                    self._key_code_map[code] = name[4:].lower()  # Remove 'KEY_' prefix
        
        return self._key_code_map.get(key_code, f"UNKNOWN({key_code})")
    
    def setup_uinput(self):
        """Setup uinput device for Wayland compatibility"""
        # Include all possible key types to ensure compatibility
        capabilities = {
            e.EV_KEY: list(e.keys.keys())
        }
        self.ui = UInput(capabilities, name='midi2keyboard-virtual-device')
        print("Virtual input device created")
    
    def press_key_combination(self, key_codes):
        """Press a combination of keys"""
        # Press all keys in the combination
        for key_code in key_codes:
            self.ui.write(e.EV_KEY, key_code, 1)
            print(f"  Key PRESSED: {self.get_key_name(key_code)}")
        
        self.ui.syn()
        
        # Small delay to ensure the combination is registered
        time.sleep(0.05)
        
        # Release all keys in reverse order (common practice)
        for key_code in reversed(key_codes):
            self.ui.write(e.EV_KEY, key_code, 0)
            print(f"  Key RELEASED: {self.get_key_name(key_code)}")
        
        self.ui.syn()
    
    def note_on_handler(self, note, velocity):
        """Handle MIDI note-on events"""
        if note in self.key_mappings:
            key_codes = self.key_mappings[note]
            
            print(f"Note {note} (velocity {velocity}) -> Key combination: {[self.get_key_name(kc) for kc in key_codes]}")
            
            # Press and release the key combination
            self.press_key_combination(key_codes)
            
            self.active_notes[note] = key_codes
        else:
            print(f"Note {note} pressed but no mapping found")
    
    def note_off_handler(self, note):
        """Handle MIDI note-off events"""
        if note in self.active_notes:
            # For key combinations, we've already released the keys in press_key_combination
            # But we still track the note as active until note_off
            del self.active_notes[note]
            print(f"Note {note} -> Key combination released")
    
    def control_change_handler(self, control, value):
        """Handle MIDI control change events"""
        if control in self.key_mappings:
            key_codes = self.key_mappings[control]
            # For CC, we can make it toggle or hold based on value
            if value >= 64:  # On threshold
                if control not in self.active_notes:
                    # Press and hold the combination
                    for key_code in key_codes:
                        self.ui.write(e.EV_KEY, key_code, 1)
                    self.ui.syn()
                    self.active_notes[control] = key_codes
                    key_names = [self.get_key_name(kc) for kc in key_codes]
                    print(f"CC {control} (value {value}) -> Key combination PRESSED: {key_names}")
            else:  # Off threshold
                if control in self.active_notes:
                    # Release the combination
                    key_codes = self.active_notes[control]
                    for key_code in reversed(key_codes):
                        self.ui.write(e.EV_KEY, key_code, 0)
                    self.ui.syn()
                    del self.active_notes[control]
                    key_names = [self.get_key_name(kc) for kc in key_codes]
                    print(f"CC {control} (value {value}) -> Key combination RELEASED: {key_names}")
        else:
            print(f"CC {control} changed to {value} but no mapping found")
    
    def midi_callback(self, event, data=None):
        """Callback for MIDI input"""
        message, delta_time = event
        message_type = message[0] & 0xF0
        
        if message_type == 0x90:  # Note On
            note, velocity = message[1], message[2]
            if velocity > 0:
                self.note_on_handler(note, velocity)
            else:  # Note On with velocity 0 treated as Note Off
                self.note_off_handler(note)
                
        elif message_type == 0x80:  # Note Off
            note = message[1]
            self.note_off_handler(note)
            
        elif message_type == 0xB0:  # Control Change
            control, value = message[1], message[2]
            self.control_change_handler(control, value)
        
        elif message_type == 0xA0:  # Aftertouch
            note, value = message[1], message[2]
            print(f"Aftertouch: note {note}, value {value}")
        
        elif message_type == 0xD0:  # Channel Pressure
            value = message[1]
            print(f"Channel Pressure: value {value}")
        
        elif message_type == 0xE0:  # Pitch Bend
            lsb, msb = message[1], message[2]
            value = (msb << 7) | lsb
            print(f"Pitch Bend: value {value}")
    
    def list_ports(self):
        """List available MIDI ports"""
        ports = self.midi_in.get_ports()
        if not ports:
            print("No MIDI input ports found!")
            return []
        
        print("Available MIDI ports:")
        for i, port in enumerate(ports):
            print(f"  {i}: {port}")
        return ports
    
    def start(self):
        """Start the MIDI mapper"""
        ports = self.list_ports()
        if not ports:
            return False
        
        # Use the specified port
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
            print("MIDI to Keyboard mapper with key combinations started!")
            print("Active mappings:")
            for note, key_codes in self.key_mappings.items():
                key_names = [self.get_key_name(kc) for kc in key_codes]
                print(f"  MIDI {note} -> {key_names}")
            print("Press Ctrl+C to stop")
            
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
        # Release all active keys (for CC that are held)
        for key_codes in self.active_notes.values():
            for key_code in reversed(key_codes):
                self.ui.write(e.EV_KEY, key_code, 0)
        self.ui.syn()
        
        if self.midi_in:
            self.midi_in.close_port()
        if self.ui:
            self.ui.close()
        print("MIDI to Keyboard mapper stopped.")

def main():
    parser = argparse.ArgumentParser(description='MIDI to Keyboard Daemon - Key Combinations')
    parser.add_argument('--config', '-c', required=True, help='Configuration file')
    parser.add_argument('--port', '-p', type=int, default=0, help='MIDI port number')
    
    args = parser.parse_args()
    
    # Check if running as root
    if os.geteuid() != 0:
        print("Error: This daemon requires root privileges to simulate keyboard input.")
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