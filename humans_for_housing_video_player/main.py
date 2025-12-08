import queue
import select
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path

import vlc
from evdev import InputDevice, categorize, ecodes, list_devices


def find_video_files() -> tuple[Path | None, Path | None]:
    """
    Search for LOOP and TRIGGER video files in ~/movies.

    Returns a tuple of (looping_video_path, trigger_video_path).
    Either may be None if not found.
    """
    looping_video = None
    trigger_video = None

    MOVIES_DIR = Path.home() / "movies"

    if not MOVIES_DIR.exists():
        print(f"[Video] Warning: Movies directory not found: {MOVIES_DIR}", flush=True)
        return None, None

    for file in MOVIES_DIR.iterdir():
        if not file.is_file():
            continue

        name_upper = file.name.upper()
        if "LOOP" in name_upper:
            looping_video = file
            print(f"[Video] Found looping video: {file}", flush=True)
        elif "TRIGGER" in name_upper:
            trigger_video = file
            print(f"[Video] Found trigger video: {file}", flush=True)

    return looping_video, trigger_video


def process_device_events(device: InputDevice, event_queue: queue.Queue) -> None:
    """Process keyboard events from a single device."""
    for event in device.read():
        if event.type != ecodes.EV_KEY:
            continue

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
            r, _, _ = select.select(devices, [], [])

            for device in r:
                try:
                    process_device_events(device, event_queue)
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


def video_control_thread(
    event_queue: queue.Queue,
    vlc_player: vlc.MediaPlayer,
    vlc_instance: vlc.Instance,
    looping_video: Path,
    trigger_video: Path,
) -> None:
    """
    Thread 2: Consumes space key events from the queue and controls video playback.
    """
    print("[Video Control] Thread started", flush=True)

    # Pre-load both media files
    looping_media = vlc_instance.media_new(str(looping_video))
    trigger_media = vlc_instance.media_new(str(trigger_video))

    # Start with the looping video
    vlc_player.set_media(looping_media)
    vlc_player.play()
    time.sleep(0.1)

    playing_trigger = False

    while True:
        try:
            # Wait for and consume space events from the queue
            timestamp = event_queue.get(timeout=0.1)
            print(f"[Video Control] Received space event from {timestamp}", flush=True)
            if not playing_trigger:
                vlc_player.stop()
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


def main():
    print("Hello from humans-for-housing-video-player!", flush=True)
    # Find video files in ~/movies
    looping_video, trigger_video = find_video_files()

    if looping_video is None:
        print("ERROR: No LOOP video found in ~/movies", flush=True)
        sys.exit(1)
    if trigger_video is None:
        print("ERROR: No TRIGGER video found in ~/movies", flush=True)
        sys.exit(1)

    # Create fullscreen black tkinter window
    root = tk.Tk()
    root.title("Video Player")
    root.configure(background="black")
    root.config(cursor="none")

    # Get screen dimensions and set fullscreen
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    root.geometry(f"{screen_width}x{screen_height}+0+0")
    root.overrideredirect(True)
    root.attributes("-fullscreen", True)

    # Create a frame to hold the video
    video_frame = tk.Frame(root, bg="black")
    video_frame.pack(fill=tk.BOTH, expand=True)

    # Update to get the window ID
    root.update()

    # Create VLC instance and player
    vlc_args = [
        "--no-video-title-show",
        "--no-osd",
        "--mouse-hide-timeout=0",
        "--no-keyboard-events",
        "--no-mouse-events",
        "--avcodec-hw=none",
    ]
    vlc_instance = vlc.Instance(vlc_args)
    vlc_player = vlc_instance.media_player_new()

    # Embed VLC into the tkinter frame
    video_frame.update()
    window_id = video_frame.winfo_id()
    vlc_player.set_xwindow(window_id)

    print(f"[Main] Embedded VLC into window ID: {window_id}", flush=True)

    # Create the queue for space key events
    event_queue = queue.Queue()

    # Create and start threads
    input_thread = threading.Thread(
        target=input_reader_thread, args=(event_queue,), daemon=True
    )
    video_thread = threading.Thread(
        target=video_control_thread,
        args=(event_queue, vlc_player, vlc_instance, looping_video, trigger_video),
        daemon=True,
    )

    input_thread.start()
    video_thread.start()

    print(
        "All threads started. Press space to toggle state. Ctrl+C to exit.", flush=True
    )

    try:
        # Run tkinter main loop
        root.mainloop()
    except KeyboardInterrupt:
        print("\nShutting down...", flush=True)
    finally:
        vlc_player.stop()
        vlc_player.release()
        root.destroy()


if __name__ == "__main__":
    main()
