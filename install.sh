#!/bin/bash
echo "Installing MIDI to Keyboard Mapper with Key Combinations..."

# Create virtual environment
python3 -m venv ~/.midi2keyboard
source ~/.midi2keyboard/bin/activate

# Install dependencies
pip install python-rtmidi evdev

# Make scripts executable
chmod +x midi2keyboard.py
chmod +x midi2keyboard_daemon.py

# Create desktop entry
mkdir -p ~/.local/share/applications
cat > ~/.local/share/applications/midi2keyboard.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=MIDI to Keyboard Mapper (Combos)
Comment=Map MIDI controller to keyboard inputs with key combinations
Exec=python3 $(pwd)/midi2keyboard.py
Icon=audio-card
Categories=AudioVideo;Audio;
Terminal=false
StartupWMClass=midi2keyboard
EOF

echo "Installation complete!"
echo "You can now run the application from your application menu"
echo "or by executing: python3 midi2keyboard_combos.py"
echo ""
echo "New features:"
echo "  - Key combinations (Ctrl+Z, Shift+A, etc.)"
echo "  - Application presets (Krita, Inkscape, Blender)"
echo "  - Visual key combination builder"
echo "  - Better key combination display"