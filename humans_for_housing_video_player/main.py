import queue
import select
import threading
from datetime import datetime

from evdev import InputDevice, categorize, ecodes, list_devices


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

    while True:
        try:
            # Wait for and consume space events from the queue
            timestamp = event_queue.get(timeout=1)
            print(f"[Video Control] Received space event from {timestamp}", flush=True)

        except queue.Empty:
            # No events in queue, continue waiting
            continue
        except Exception as e:
            print(f"[Video Control] Error: {e}", flush=True)
            break


def main():
    """ """
    print("Hello from humans-for-housing-video-player!", flush=True)

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
