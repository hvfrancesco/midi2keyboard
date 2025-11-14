# MIDI to Keyboard Mapper

A powerful Linux application that maps MIDI controller inputs to keyboard shortcuts and key combinations. Perfect for controlling creative applications like Krita, Inkscape, and Blender with a MIDI controller.

![Platform](https://img.shields.io/badge/Platform-Linux-blue.svg)
![Python](https://img.shields.io/badge/Python-3.6+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## Features

- 🎹 **MIDI Controller Support** - Works with any MIDI controller or keyboard
- ⌨️ **Key Combinations** - Map to complex shortcuts like Ctrl+Z, Shift+Alt+A, etc.
- 🎨 **Application Presets** - Pre-configured mappings for Krita, Inkscape, and Blender
- 🖥️ **Graphical Interface** - Easy-to-use GUI for mapping configuration
- 🐧 **Wayland Compatible** - Works on both X11 and Wayland displays
- 🔧 **Real-time Configuration** - Change mappings without restarting
- 💾 **Profile Management** - Save and load different mapping configurations

## Use Cases

- **Digital Art** - Use MIDI pads for brush shortcuts in Krita
- **Vector Graphics** - Map tools and actions in Inkscape
- **3D Modeling** - Control viewport and tools in Blender
- **Video Editing** - Create custom shortcuts for DaVinci Resolve, Kdenlive
- **Music Production** - Additional controller support for DAWs
- **Any Application** - Custom mappings for your workflow

## Installation

### Prerequisites

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3-pip python3-tk libasound2-dev

# Fedora
sudo dnf install python3-pip python3-tkinter alsa-lib-devel

# Arch Linux
sudo pacman -S python-pip tk alsa-lib
```

### Install dependencies
```bash
pip3 install python-rtmidi evdev
```

## Download and run
```bash
# Clone or download the project files
git clone <repository-url>
cd midi2keyboard

# Make scripts executable
chmod +x midi2keyboard.py
chmod +x midi2keyboard_daemon.py

# Run the application
python3 midi2keyboard.py
```

## Usage

### Basic Setup

1. **Connect your MIDI controller** to your computer
2. **Run the application**: `python3 midi2keyboard.py`
3. **Select your MIDI port** from the dropdown menu
4. **Create mappings** using the key combination builder
5. **Click "Start Mapping"** to begin (will prompt for admin password)

### Creating Mappings

1. **Check modifier keys** (Ctrl, Shift, Alt, Super) as needed
2. **Select a main key** from the dropdown
3. **Enter MIDI note/CC number** (0-127)
4. **Add description** (optional)
5. **Click "Add Mapping"**

### Example Mappings

| MIDI Note | Key Combination | Description |
|-----------|-----------------|-------------|
| 36 | `B` | Brush tool |
| 37 | `E` | Eraser tool |
| 40 | `Ctrl+Z` | Undo |
| 41 | `Ctrl+Shift+Z` | Redo |
| 42 | `Ctrl+S` | Save |
| 43 | `[` | Decrease brush size |
| 44 | `]` | Increase brush size |

### Application Presets

The application includes ready-to-use presets for popular creative software:

- **Krita Preset** - Digital painting shortcuts
- **Inkscape Preset** - Vector graphics tools
- **Blender Preset** - 3D modeling commands

Click the preset buttons to load these configurations instantly.

## Configuration Files
### User Configuration
~/.config/midi2keyboard/mappings.json

```json
{
  "mappings": {
    "36": {"keys": ["b"], "desc": "Brush Tool"},
    "40": {"keys": ["leftctrl", "z"], "desc": "Undo"}
  },
  "midi_port": 0
}
```

## Troubleshooting

### Common Issues

**"No MIDI ports found"**
- Ensure your MIDI controller is connected and powered on
- Check if it appears in `arecord -l` output
- Try different USB ports

**"Permission denied" when starting mapping**
- The daemon requires root privileges for uinput access
- The GUI uses `pkexec` to request privileges automatically

**Key combinations not working**
- Ensure the target application has focus
- Try simpler combinations first
- Check if the application uses different shortcut modifiers

**"Operation not permitted" when stopping**
- Use the built-in stop button in the GUI
- If needed, manually stop with: `sudo pkill -f midi2keyboard_daemon.py`

## Manual Daemon Control

```bash
# Start daemon manually
sudo python3 midi2keyboard_daemon.py -c config.json -p 0

# Stop daemon manually
sudo pkill -f midi2keyboard_daemon.py

# Emergency stop
sudo killall python3
```

## Supported Keys

The application supports all standard keyboard keys including:

- **Letters**: A-Z
- **Numbers**: 0-9
- **Function keys**: F1-F12
- **Modifiers**: Ctrl, Shift, Alt, Super (Windows/Command)
- **Navigation**: Arrow keys, Home, End, Page Up/Down
- **Special**: Space, Enter, Tab, Escape, Backspace
- **Symbols**: [, ], {, }, ,, ., /, ;, ', \, =, -, `

## Technical Details

- **MIDI Handling**: Uses `python-rtmidi` for robust MIDI input
- **Keyboard Simulation**: Uses `evdev` for Wayland-compatible input injection
- **GUI**: Built with Tkinter for cross-distribution compatibility
- **Privilege Separation**: GUI runs as user, daemon runs with elevated privileges

## Security Notes

- The daemon requires root privileges to simulate keyboard input
- No data is sent over the network
- Configuration files are stored locally
- The application only reads MIDI input and writes keyboard events

## Contributing

Contributions are welcome! Please feel free to submit pull requests for:

- New application presets
- Bug fixes
- Feature enhancements
- Documentation improvements

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Copyright (c) 2025 Francesco Fantoni

## Acknowledgments

- Built with [python-rtmidi](https://github.com/SpotlightKid/python-rtmidi) for MIDI support
- Uses [python-evdev](https://github.com/gvalkov/python-evdev) for input simulation
- Inspired by the need for better controller support in creative applications

## Support

If you encounter issues or have questions:

1. Check the troubleshooting section above
2. Ensure your system meets the prerequisites
3. Verify your MIDI controller is properly detected
4. Create an issue on the project repository with details about your setup