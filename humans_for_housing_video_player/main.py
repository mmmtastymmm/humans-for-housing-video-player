import threading
import queue
from datetime import datetime
from typing import Callable, Union
from pynput import keyboard


def create_key_press_handler(
    event_queue: queue.Queue,
) -> Callable[[Union[keyboard.Key, keyboard.KeyCode]], None]:
    """
    Factory function that creates a key press handler with the queue bound via closure.
    """

    def on_key_press(key: Union[keyboard.Key, keyboard.KeyCode]) -> None:
        """
        Callback for keyboard events. Detects space key and enqueues timestamp.
        This is called by pynput's keyboard listener on a separate thread.
        """
        try:
            # Check if the key is the space bar
            if key == keyboard.Key.space:
                timestamp = datetime.now()
                event_queue.put(timestamp)
                print(f"[Input Reader] Space detected at {timestamp}")
        except Exception as e:
            print(f"[Input Reader] Error in key handler: {e}")

    return on_key_press


def input_reader_thread(event_queue: queue.Queue) -> None:
    """
    Thread 1: Uses pynput to capture global keyboard events (works even when VLC has focus).
    Listens for space key presses and enqueues them with timestamps.
    """
    print("[Input Reader] Starting global keyboard listener")

    # Create a keyboard listener that will run until stopped
    on_press_handler = create_key_press_handler(event_queue)
    with keyboard.Listener(on_press=on_press_handler) as listener:
        print("[Input Reader] Keyboard listener active")
        listener.join()


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
