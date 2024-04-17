from typing import Tuple
import subprocess
import yt_dlp
import os
import re
import random


def create_directory(directory):
    """
    Create a directory if it doesn't exist.

    Args:
        directory (str): Path to the directory to be created.
    """
    if not os.path.exists(directory):
        os.makedirs(directory)


def get_random_file(path: str) -> str:
    """
    Get a random file from a directory.
    """
    files = os.listdir(path)
    file = random.choice(files)
    return os.path.join(path, file)


def get_url_id(url: str) -> str:
    """
    Extract the video ID from a YouTube URL.
    """
    match = re.search(r"(?:youtube\.com/(?:[-\w]+\?v=|embed/|v/)?)([-\w]+)", url)
    if match:
        return match.group(1)
    else:
        return ""


def download_youtube_video(
    url: str,
    path: str = "",
    filename: str = None,
    output_format: str = "mp4",
    max_resolution: int = None,
    include_audio: bool = True,
) -> str:
    """
    Downloads a video from a given a URL.

    Args:
        url (str): The URL of the video to be downloaded.
        path (str): Path to the file. This will be joined to the filename
        filename (str): The name of the file, the url ID by default.
        output_format (str, optional): The file extension of the video.
        max_resolution (int, optional): The maximum resolution of the video. Videos with a resolution equal to or lower than this will be preferred. If set to None, the best available quality will be downloaded. Default is None.
        include_audio (bool, optional): Boolean flag indicating whether to include audio in the downloaded video. Default is True.

    Returns:
        file_path (str): Output video path
    """
    # Determine the filename if not provided
    if not filename:
        filename = get_url_id(url)

    # Construct the file path
    file_path = os.path.join(path, f"{filename}.{output_format}")

    # Configure yt-dlp options
    ydl_opts = {
        "format": (
            "bestvideo[height<={}]".format(max_resolution) if max_resolution else "best"
        ),
        "merge_output_format": output_format,
        "postprocessors": [],
        "outtmpl": file_path,
        "quiet": True,
    }

    # Add postprocessors to exclude audio if required
    if not include_audio:
        ydl_opts["postprocessors"].append(
            {
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4",
                "parameters": ["-vn"],
            }
        )

    # Download the video using yt-dlp
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return file_path


def get_video_duration(video_path: str) -> float:
    """
    Get the duration of a video file.

    Returns:
        float: Duration of the video in seconds.
    """
    cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {video_path}"
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )

    # Convert duration to float
    return float(result.stdout)


def get_video_dimensions(video_path: str) -> Tuple[int, int]:
    """
    Get the width and height of a video file.

    Args:
        video_path (str): Path to the video file.

    Returns:
        Tuple[int, int]: Width and height of the video.
    """
    cmd = f"ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 {video_path}"
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Parse dimensions from the result
    dimensions = result.stdout.strip().split("x")
    width, height = int(dimensions[0]), int(dimensions[1])

    return width, height
