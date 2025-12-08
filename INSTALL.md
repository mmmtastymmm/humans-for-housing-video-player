# Installation Instructions for Raspberry Pi

## Quick Automated Installation

The easiest way to install is using the automated installation script:

```bash
# Download and run the install script
curl -sSL https://raw.githubusercontent.com/mmmtastymmm/humans-for-housing-video-player/main/install.sh | bash
```

Or if you already have the repository:

```bash
chmod +x install.sh
./install.sh
```

The script will:
- Install system dependencies (git, VLC, python3-pip)
- Clone the repository to `/home/pi/humans-for-housing-video-player`
- Install Python dependencies (pynput)
- Set up the systemd service
- Add user to input group for keyboard access
- Enable auto-start on boot

---

## Manual Installation

If you prefer to install manually:

### Prerequisites

1. Install pynput:
```bash
pip3 install pynput
```

2. Ensure VLC is installed:
```bash
sudo apt-get update
sudo apt-get install vlc
```

### Systemd Service Installation

### 1. Update the service file paths

Edit `humans-for-housing-video-player.service` and update these paths if needed:
- `WorkingDirectory` - Path to your project directory
- `ExecStart` - Path to your main.py file
- `User` and `Group` - Your username (default is `pi`)

### 2. Copy the service file to systemd

```bash
sudo cp humans-for-housing-video-player.service /etc/systemd/system/
```

### 3. Reload systemd to recognize the new service

```bash
sudo systemctl daemon-reload
```

### 4. Enable the service to start on boot

```bash
sudo systemctl enable humans-for-housing-video-player.service
```

### 5. Start the service now (optional - to test)

```bash
sudo systemctl start humans-for-housing-video-player.service
```

## Managing the Service

### Check status
```bash
sudo systemctl status humans-for-housing-video-player.service
```

### View logs
```bash
sudo journalctl -u humans-for-housing-video-player.service -f
```

### Stop the service
```bash
sudo systemctl stop humans-for-housing-video-player.service
```

### Restart the service
```bash
sudo systemctl restart humans-for-housing-video-player.service
```

### Disable auto-start on boot
```bash
sudo systemctl disable humans-for-housing-video-player.service
```

## Troubleshooting

### If VLC doesn't display video:

1. Make sure you're running a graphical session (not headless)
2. Check the DISPLAY variable is correct (usually `:0`)
3. Check X authority file location: `ls -la ~/.Xauthority`
4. You may need to run: `xhost +local:` to allow local connections

### If the service fails to start:

1. Check the logs: `sudo journalctl -u humans-for-housing-video-player.service -n 50`
2. Verify all paths in the service file are correct
3. Test running the script manually as the pi user
4. Ensure pynput has proper permissions (may need to be in `input` group)

### Permissions for keyboard input:

The user running the service may need to be in the `input` group:
```bash
sudo usermod -a -G input pi
```

## Notes

- The service will automatically restart if it crashes (RestartSec=10 seconds)
- Logs are stored in systemd journal, viewable with `journalctl`
- The service starts after the graphical target is available
- VLC will run with the privileges of the specified user (default: pi)
