# Installation Instructions for Raspberry Pi

## Prerequisites

1. Set up a raspberry pi with the default 64bit install found here: https://www.raspberrypi.com/software/
2. Set up the wifi
3. Ensure you can make an ssh connection to the device.

The software can be installed even if not all videos are ready yet.

The easiest way to install is using the automated installation script:

From the raspberry pi via ssh run the following command:

```bash
# Download and run the install script
curl -sSL https://raw.githubusercontent.com/mmmtastymmm/humans-for-housing-video-player/main/install.sh -o /tmp/install.sh && bash /tmp/install.sh
```

Or if you already have the repository:

```bash
chmod +x install.sh
./install.sh
```

The script will install all required software.

---

The above will install the code. Next we need to make sure the videos are in the right spot and correctly named

# Copy the Videos

These instructions will explain how to prepare the videos for playing.

Note: If not all videos are ready you can copy over sample videos to ensure the pi is working correctly.
Then, once the real videos are ready you can delete them and copy over the real videos.

## Prerequisites

1. Ensure you have two videos you want played together.
   1. One video will need to have the word `LOOP` in the filename (eg `humans-for-housing-LOOP.mov`). 
      * This will be the video that is played until someone pushes a button.
   2. The second video will need to have the word `TRIGGER` in the filename (eg `humans-for-housing-TRIGGER.mp4`)
      * This will be the video that plays once someone pushes the button.
2. Make the movies directory in the home directory of the user, which can be down by running the following command:
   ```bash
   ssh <raspberry pi user>@<raspberry pi address> 
   cd ~
   mkdir movies
   exit 
   ```

## Copying the files
Once the files are paired and correctly named, for each file (total of two files) run the following command.

```bash
scp <path to file> <raspberry pi user>@<raspberry pi address>:~/movies/
# The command for a file of Movies/humans-for-housing-LOOP.mov and user of pi for the pi at address 192.168.1.18 would be:
# scp Movies/humans-for-housing-LOOP.mov pi@192.168.1.18:~/movies/
```

Now next time the raspberry pi starts it will play the videos supplied.

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
3. Test running the script manually as your user
4. Ensure evdev has proper permissions (user must be in `input` group)

### Permissions for keyboard input:

The user running the service may need to be in the `input` group:
```bash
sudo usermod -a -G input $USER
```

## Notes

- The service will automatically restart if it crashes (RestartSec=10 seconds)
- Logs are stored in systemd journal, viewable with `journalctl`
- The service starts after the graphical target is available
- VLC will run with the privileges of the user who ran the install script
