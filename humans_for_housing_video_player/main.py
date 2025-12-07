import sys
import time

import vlc


def play_video(video_path: str, loop: bool = False) -> None:
    """
    Play a video file in full screen with no UI.

    Args:
        video_path: Path to the video file to play.
        loop: If True, the video will loop continuously until interrupted.
              If False, the video plays once and then exits.
    """
    # Create VLC instance with options for no UI
    vlc_args = [
        "--fullscreen",
        "--no-video-title-show",  # Don't show title on screen
        "--no-osd",  # No on-screen display
        "--mouse-hide-timeout=0",  # Hide mouse immediately
        "--no-keyboard-events",  # Disable VLC keyboard input handling
        "--no-mouse-events",  # Disable VLC mouse input handling
    ]

    if loop:
        vlc_args.append(
            "--input-repeat=65535"
        )  # Repeat many times (effectively infinite)

    instance = vlc.Instance(vlc_args)
    player = instance.media_player_new()

    media = instance.media_new(video_path)
    player.set_media(media)

    # Set fullscreen
    player.set_fullscreen(True)

    # Start playback
    player.play()

    # Wait a moment for playback to start
    time.sleep(0.5)

    try:
        # Keep running while video is playing
        while True:
            state = player.get_state()

            if state == vlc.State.Ended:
                if loop:
                    # Restart the video
                    player.stop()
                    player.play()
                    time.sleep(0.5)
                else:
                    break
            elif state == vlc.State.Error:
                print(f"Error playing video: {video_path}", file=sys.stderr)
                break

            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        player.stop()
        player.release()


def main():
    print("Hello from humans-for-housing-video-player!")
    play_video("movies/HFHEXHIBIT_VIDEO_01_LOOP.mov")


if __name__ == "__main__":
    main()
