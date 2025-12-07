"""Tests for the main module."""

from humans_for_housing_video_player.main import main


def test_main_runs_without_error(capsys):
    """Test that main function runs without error."""
    main()
    captured = capsys.readouterr()
    assert "Hello from humans-for-housing-video-player!" in captured.out


def test_main_output_format(capsys):
    """Test that main function outputs the expected message."""
    main()
    captured = capsys.readouterr()
    assert captured.out.strip() == "Hello from humans-for-housing-video-player!"
