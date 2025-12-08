import queue
import threading
from datetime import datetime

from evdev import InputDevice, categorize, ecodes, list_devices


def find_keyboard_device() -> InputDevice | None:
    """
    Find the first keyboard device in /dev/input/.
    Returns None if no keyboard is found.
    """
    devices = [InputDevice(path) for path in list_devices()]
    for device in devices:
        # Check if device has KEY_SPACE capability (indicates it's a keyboard)
        if ecodes.KEY_SPACE in device.capabilities().get(ecodes.EV_KEY, []):
            print(f"[Input Reader] Found keyboard: {device.name} at {device.path}")
            return device
    return None


def input_reader_thread(event_queue: queue.Queue) -> None:
    """
    Thread 1: Uses evdev to capture keyboard events from /dev/input/.
    Listens for space key presses and enqueues them with timestamps.
    """
    print("[Input Reader] Starting keyboard listener")

    # Find a keyboard device
    device = find_keyboard_device()
    if device is None:
        print("[Input Reader] ERROR: No keyboard device found!")
        return

    print(f"[Input Reader] Listening for space key on {device.name}")

    try:
        # Grab exclusive access to prevent events from reaching other handlers
        # Comment this out if you want other apps to also receive the events
        device.grab()

        # Read events from the device
        for event in device.read_loop():
            # We only care about key press events (not release)
            if event.type == ecodes.EV_KEY:
                key_event = categorize(event)
                # Check if it's a key press (not release) and it's the space key
                if key_event.keycode == "KEY_SPACE" and key_event.keystate == 1:
                    timestamp = datetime.now()
                    event_queue.put(timestamp)
                    print(f"[Input Reader] Space detected at {timestamp}")
    except Exception as e:
        print(f"[Input Reader] Error: {e}")
    finally:
        device.ungrab()
        device.close()


def video_control_thread(event_queue: queue.Queue) -> None:
    """
    Thread 2: Consumes space key events from the queue and prints them.
    TODO: Implement actual video logic with VLC
    """
    print("[Video Control] Thread started")

    while True:
        try:
            # Wait for and consume space events from the queue
            timestamp = event_queue.get(timeout=1)
            print(f"[Video Control] Received space event from {timestamp}")

        except queue.Empty:
            # No events in queue, continue waiting
            continue
        except Exception as e:
            print(f"[Video Control] Error: {e}")
            break


def main():
    """ """
    print("Hello from humans-for-housing-video-player!")

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

    print("All threads started. Press space to toggle state. Ctrl+C to exit.")

    try:
        # Keep main thread alive
        input_thread.join()
        video_thread.join()
    except KeyboardInterrupt:
        print("\nShutting down...")


if __name__ == "__main__":
    main()
