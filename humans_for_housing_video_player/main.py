import queue
import select
import sys
import threading
import time
from collections.abc import Callable
from datetime import datetime

import vlc
from evdev import InputDevice, categorize, ecodes, list_devices

LOOPING_VIDEO = "movies/HFHEXHIBIT_VIDEO_01_LOOP.mov"
TRIGGER_VIDEO = "movies/HFHEXHIBIT_VIDEO_02_TRIGGER.mp4"


def get_framebuffer_size(fb_path: str = "/dev/fb0") -> tuple[int, int] | None:
    """Get the framebuffer resolution."""
    try:
        import fcntl
        import struct

        FBIOGET_VSCREENINFO = 0x4600
        with open(fb_path, "rb") as fb:
            # Get variable screen info
            vinfo = fcntl.ioctl(fb, FBIOGET_VSCREENINFO, b"\x00" * 160)
            xres, yres = struct.unpack("II", vinfo[:8])
            return (xres, yres)
    except (OSError, IOError):
        return None


def blank_framebuffer(fb_path: str = "/dev/fb0") -> None:
    """Fill the framebuffer with black pixels."""
    try:
        size = get_framebuffer_size(fb_path)
        if size is None:
            return

        xres, yres = size
        # Assuming 32-bit color depth (4 bytes per pixel)
        # Write black (all zeros) to framebuffer
        black_screen = b"\x00" * (xres * yres * 4)

        with open(fb_path, "wb") as fb:
            fb.write(black_screen)
    except (OSError, IOError, PermissionError) as e:
        print(f"Could not blank framebuffer: {e}", file=sys.stderr)


def find_keyboard_devices() -> list[InputDevice]:
    """
    Find all keyboard devices in /dev/input/ that have KEY_SPACE capability.
    Returns a list of InputDevice objects.
    """
    devices = [InputDevice(path) for path in list_devices()]
    keyboards = []

    for device in devices:
        # Check if device has KEY_SPACE capability (indicates it's a keyboard)
        if ecodes.KEY_SPACE in device.capabilities().get(ecodes.EV_KEY, []):
            print(
                f"[Input Reader] Found keyboard: {device.name} at {device.path}",
                flush=True,
            )
            keyboards.append(device)

    return keyboards


def input_reader_thread(event_queue: queue.Queue) -> None:
    """
    Thread 1: Uses evdev to capture keyboard events from /dev/input/.
    Monitors ALL keyboard devices simultaneously using select().
    Listens for space key presses and enqueues them with timestamps.
    """
    print("[Input Reader] Starting keyboard listener", flush=True)

    # Find all keyboard devices
    devices = find_keyboard_devices()
    if not devices:
        print("[Input Reader] ERROR: No keyboard devices found!", flush=True)
        return

    print(
        f"[Input Reader] Listening for space key on {len(devices)} device(s)",
        flush=True,
    )

    # Create a mapping from file descriptor to device for quick lookup
    fd_to_device = {dev.fd: dev for dev in devices}

    try:
        # Grab exclusive access to all devices
        for device in devices:
            try:
                device.grab()
                print(
                    f"[Input Reader] Grabbed exclusive access to {device.name}",
                    flush=True,
                )
            except Exception as e:
                print(
                    f"[Input Reader] Warning: Could not grab {device.name}: {e}",
                    flush=True,
                )

        # Monitor all devices using select
        while True:
            # Wait for any device to have data available
            r, w, x = select.select(devices, [], [])

            for device in r:
                try:
                    for event in device.read():
                        # We only care about key press events
                        if event.type == ecodes.EV_KEY:
                            key_event = categorize(event)
                            # keycode can be a list when multiple keycodes are mapped
                            keycodes = (
                                key_event.keycode
                                if isinstance(key_event.keycode, list)
                                else [key_event.keycode]
                            )
                            # Check if it's a key press (not release) and it's the space key
                            if "KEY_SPACE" in keycodes and key_event.keystate == 1:
                                timestamp = datetime.now()
                                event_queue.put(timestamp)
                                print(
                                    f"[Input Reader] Space detected at {timestamp} from {device.name}",
                                    flush=True,
                                )
                except Exception as e:
                    print(
                        f"[Input Reader] Error reading from {device.name}: {e}",
                        flush=True,
                    )

    except Exception as e:
        print(f"[Input Reader] Error: {e}", flush=True)
    finally:
        # Release all grabbed devices
        for device in devices:
            try:
                device.ungrab()
                device.close()
            except Exception:
                pass


def video_control_thread(event_queue: queue.Queue) -> None:
    """
    Thread 2: Consumes space key events from the queue and prints them.
    TODO: Implement actual video logic with VLC
    """
    print("[Video Control] Thread started", flush=True)
    vlc_args = [
        "--fullscreen",
        "--video-wallpaper",
        "--no-video-title-show",
        "--no-osd",
        "--mouse-hide-timeout=0",
        "--no-keyboard-events",
        "--no-mouse-events",
    ]
    vlc_instance = vlc.Instance(vlc_args)
    vlc_player = vlc_instance.media_player_new()

    # Pre-load both media files
    looping_media = vlc_instance.media_new(LOOPING_VIDEO)
    trigger_media = vlc_instance.media_new(TRIGGER_VIDEO)

    # Set fullscreen
    vlc_player.set_fullscreen(True)

    # Start with the looping video
    vlc_player.set_media(looping_media)
    vlc_player.play()
    time.sleep(0.1)

    playing_trigger = False

    while True:
        try:
            # Wait for and consume space events from the queue
            timestamp = event_queue.get(timeout=1)
            print(f"[Video Control] Received space event from {timestamp}", flush=True)
            vlc_player.set_media(trigger_media)
            vlc_player.play()
            time.sleep(0.1)
            playing_trigger = True

        except queue.Empty:
            # No events in queue, do nothing
            pass
        except Exception as e:
            print(f"[Video Control] Error: {e}", flush=True)
            break

        # Check player state
        state = vlc_player.get_state()

        if state == vlc.State.Ended:
            if playing_trigger:
                # Trigger video finished, go back to looping
                vlc_player.set_media(looping_media)
                vlc_player.play()
                time.sleep(0.1)
                playing_trigger = False
            else:
                # Looping video ended, restart it
                vlc_player.set_media(looping_media)
                vlc_player.play()
                time.sleep(0.1)
        elif state == vlc.State.Error:
            print("Error playing video", file=sys.stderr)
            break

        time.sleep(0.05)

    vlc_player.stop()
    vlc_player.release()


def main():
    print("Hello from humans-for-housing-video-player!", flush=True)
    # Write a blank screen so that screen is blank when switching videos
    blank_framebuffer()

    # Create the queue for space key events
    event_queue = queue.Queue()

    # Create and start all threads, passing the queue to each
    input_thread = threading.Thread(
        target=input_reader_thread, args=(event_queue,), daemon=True
    )
    video_thread = threading.Thread(
        target=video_control_thread, args=(event_queue,), daemon=True
    )

    input_thread.start()
    video_thread.start()

    print(
        "All threads started. Press space to toggle state. Ctrl+C to exit.", flush=True
    )

    try:
        # Keep main thread alive
        input_thread.join()
        video_thread.join()
    except KeyboardInterrupt:
        print("\nShutting down...", flush=True)


if __name__ == "__main__":
    main()
