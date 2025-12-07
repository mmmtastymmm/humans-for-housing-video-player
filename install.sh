#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/mmmtastymmm/humans-for-housing-video-player.git"
INSTALL_DIR="/home/pi/humans-for-housing-video-player"
SERVICE_NAME="humans-for-housing-video-player.service"
USER="pi"

echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}Humans for Housing Video Player Setup${NC}"
echo -e "${GREEN}=====================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Error: Please do not run this script as root${NC}"
    echo "Run as your normal user (it will prompt for sudo when needed)"
    exit 1
fi

# Prompt for repository URL
echo -e "${YELLOW}Enter the Git repository URL:${NC}"
echo -e "(default: $REPO_URL)"
read -r repo_input
if [ -n "$repo_input" ]; then
    REPO_URL="$repo_input"
fi

# Prompt for installation directory
echo -e "${YELLOW}Enter installation directory:${NC}"
echo -e "(default: $INSTALL_DIR)"
read -r dir_input
if [ -n "$dir_input" ]; then
    INSTALL_DIR="$dir_input"
fi

echo ""
echo -e "${GREEN}Step 1: Installing system dependencies...${NC}"
sudo apt-get update
sudo apt-get install -y git vlc python3-venv

echo ""
echo -e "${GREEN}Step 2: Installing uv (Python package manager)...${NC}"
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
else
    echo "uv is already installed"
fi

echo ""
echo -e "${GREEN}Step 3: Cloning repository...${NC}"
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}Directory $INSTALL_DIR already exists.${NC}"
    echo -e "${YELLOW}Do you want to remove it and clone fresh? (y/N)${NC}"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        rm -rf "$INSTALL_DIR"
        git clone "$REPO_URL" "$INSTALL_DIR"
    else
        echo -e "${YELLOW}Updating existing repository...${NC}"
        cd "$INSTALL_DIR"
        git pull
    fi
else
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

echo ""
echo -e "${GREEN}Step 4: Installing Python dependencies with uv...${NC}"
uv sync

echo ""
echo -e "${GREEN}Step 5: Adding user to input group (for keyboard access)...${NC}"
sudo usermod -a -G input "$USER"

echo ""
echo -e "${GREEN}Step 6: Installing systemd service...${NC}"
# Update service file with actual install directory and uv venv python
sed -i "s|WorkingDirectory=.*|WorkingDirectory=$INSTALL_DIR|g" "$SERVICE_NAME"
sed -i "s|ExecStart=.*|ExecStart=$INSTALL_DIR/.venv/bin/python $INSTALL_DIR/humans_for_housing_video_player/main.py|g" "$SERVICE_NAME"

# Copy service file to systemd directory
sudo cp "$SERVICE_NAME" /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable "$SERVICE_NAME"

echo ""
echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}Installation Complete!${NC}"
echo -e "${GREEN}=====================================${NC}"
echo ""
echo "The service has been installed and enabled to start on boot."
echo ""
echo -e "${YELLOW}Important: You need to reboot or re-login for group changes to take effect.${NC}"
echo ""
echo "Available commands:"
echo "  Start service:   sudo systemctl start $SERVICE_NAME"
echo "  Stop service:    sudo systemctl stop $SERVICE_NAME"
echo "  Service status:  sudo systemctl status $SERVICE_NAME"
echo "  View logs:       sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo -e "${YELLOW}Would you like to start the service now? (y/N)${NC}"
read -r start_now
if [[ "$start_now" =~ ^[Yy]$ ]]; then
    sudo systemctl start "$SERVICE_NAME"
    echo ""
    echo -e "${GREEN}Service started!${NC}"
    echo "Check status with: sudo systemctl status $SERVICE_NAME"
else
    echo ""
    echo "Service will start automatically on next boot."
    echo "To start it manually, run: sudo systemctl start $SERVICE_NAME"
fi

echo ""
echo -e "${GREEN}Setup complete!${NC}"
