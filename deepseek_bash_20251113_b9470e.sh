#!/bin/bash
echo "Installing Fixed MIDI to Keyboard Mapper..."

# Create virtual environment
python3 -m venv ~/.midi2keyboard_fixed
source ~/.midi2keyboard_fixed/bin/activate

# Install dependencies
pip install python-rtmidi evdev

# Make scripts executable
chmod +x midi2keyboard_gui_fixed.py
chmod +x midi2keyboard_daemon_fixed.py

# Create desktop entry
mkdir -p ~/.local/share/applications
cat > ~/.local/share/applications/midi2keyboard-fixed.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=MIDI to Keyboard Mapper (Fixed)
Comment=Map MIDI controller to keyboard inputs - Fixed version
Exec=python3 $(pwd)/midi2keyboard_gui_fixed.py
Icon=audio-card
Categories=AudioVideo;Audio;
Terminal=false
StartupWMClass=midi2keyboard-fixed
EOF

echo "Installation complete!"
echo "You can now run the application from your application menu"
echo "or by executing: python3 midi2keyboard_gui_fixed.py"
echo ""
echo "Fixed issues:"
echo "  - Working mapping addition/removal in GUI"
echo "  - Proper port selection for daemon"
echo "  - Better error handling and logging"