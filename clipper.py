from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import SRTFormatter
from typing import List, Tuple
from PIL import Image
import subprocess
import os
import math
import logging
import syllapy
import shutil

from constants import *
from util import *

# Configure the logger
logging.basicConfig(
    level=logging.INFO, format="[%(levelname)s][%(asctime)s]: %(message)s"
)
logger = logging.getLogger(__name__)


def make_videos(
    url: str, file_name: str, secondary_content: bool = True, captions: bool = True
) -> List[str]:
    """
    Process a YouTube video: download, add captions, split into clips, combine with the secondary content.

    Args:
        url (str): URL of the YouTube video.
        file_name (str): start of the filename joined with the ID and part number (ex: username_videoid123_1.mp4).
        secondary_content (bool): if the video contains secondary content below the main video.
        captions (bool): if the video contains captions.

    Returns:
        List[str]: list of absolute file paths for all the clips
    """
    id = get_url_id(url)

    # Create necessary directories
    create_directory(TEMP_PATH)

    # Download video from YouTube
    video_path = download_youtube_video(url, TEMP_PATH)

    if secondary_content:
        # Add secondary content and crop the video
        video_path = add_secondary_content(video_path)
    else:
        # Cropping is handled in the secondary content process for optimization purposes
        # so if there is no secondary content, the clip must be cropped seperatly
        logging.info("Cropping video...")
        video_path = crop(video_path, os.path.join(TEMP_PATH, f"{id}_CROPPED.mp4"))

    if captions:
        # Fetch and process captions
        logger.info(f"Fetching and processing captions!")
        transcript_path = fetch_transcript(id)

        # Check if transcript was found
        if transcript_path:
            # Add subtitles to the combined video
            logging.info("Adding subtitles")
            video_path = add_subtitles(
                video_path, os.path.join(TEMP_PATH, "subtitled.mp4"), transcript_path
            )

    # Create necessary dirs
    CLIPS_PATH = os.path.join(TEMP_PATH, id)

    create_directory(CLIPS_PATH)
    create_directory(OUTPUT_PATH)

    # Divide the clips in to segments
    clips = clip(video_path, CLIPS_PATH, id)

    # Process all clips
    processed_clips = []
    for i, clip_path in enumerate(clips):
        logger.info(f"Adding text to clip {i+1}/{len(clips)}")
        target_path = os.path.join(OUTPUT_PATH, f"{file_name},{i},{id}.mp4")
        clip_path = add_text(clip_path, target_path, f"Part {i+1}")
        processed_clips.append(clip_path)

    # Remove temp folder
    shutil.rmtree(TEMP_PATH)

    return processed_clips


def add_secondary_content(video_path: str) -> str:
    # Process secondary content
    logging.info("Processing secondary content...")
    secondary_video = get_random_file(SECONDARY_CONTENT_PATH)
    secondary_video = extend(
        secondary_video,
        os.path.join(TEMP_PATH, "content.mp4"),
        get_video_duration(video_path),
    )

    # Stack secondary content with primary video
    logging.info("Stacking secondary content...")
    video_path = stack(
        os.path.join(TEMP_PATH, "stacked.mp4"), video_path, secondary_video
    )

    return video_path


def crop(
    file_path: str, output_file: str, crop: Tuple[int, int] = CLIP_RESOLUTION
) -> str:
    """
    Crop a video to a specific resolution,

    Args:
        file_path (str): Path to the video being cropped.
        output_file (str): Path to the output file
        crop (Tuple[int, int]): Target resolution

    Returns:
        str: Path to the cropped video
    """
    # Get input video resolution
    resolution_cmd = f"ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 {file_path}"
    resolution_output = subprocess.check_output(
        resolution_cmd, shell=True, encoding="utf-8"
    )
    width, height = map(int, resolution_output.split("x"))

    # Calculate crop dimensions based on aspect ratio
    input_aspect_ratio = width / height
    target_aspect_ratio = crop[0] / crop[1]
    if input_aspect_ratio > target_aspect_ratio:
        new_width = int(height * target_aspect_ratio)
        crop_filter = f"crop={new_width}:{height}, scale={crop[0]}:{crop[1]}"
    else:
        new_height = int(width / target_aspect_ratio)
        crop_filter = f"crop={width}:{new_height}, scale={crop[0]}:{crop[1]}"

    # Execute ffmpeg command
    cmd = (
        f"ffmpeg -hide_banner -loglevel error -stats -i {file_path} "
        f'-vf "{crop_filter}" {output_file}'
    )
    subprocess.run(cmd, shell=True)

    return output_file


def stack(
    file_path: str, top: str, bottom: str, crop: Tuple[int, int] = CLIP_RESOLUTION
) -> str:
    """
    Combine two videos vertically and save the result to a file.

    Args:
        file_path (str): Path to save the combined video.
        top (str): Path to the top video.
        bottom (str): Path to the bottom video.
        crop (Tuple[int, int]): Cropping dimensions for the combined video.

    Returns:
        str: Path of the combined video.
    """
    # Get resolution to match it to the top one (gives error if not)
    bottom_width, bottom_height = get_video_dimensions(bottom)

    # Stack both videos and adjust resolution if needed
    subprocess.run(
        f'ffmpeg -hide_banner -loglevel error -stats -i {top} -i {bottom} -filter_complex "[0:v]scale={bottom_width}:{bottom_height}[scaled_top];[scaled_top][1:v]vstack,crop={crop[0]}:{crop[1]}:(iw-{crop[0]})/2:0" {file_path}',
        shell=True,
    )
    return file_path


def extend(video_path: str, output_path: str, duration: float) -> str:
    """
    Extend a video to match a specified duration by looping it.

    Args:
        video_path (str): Path to the input video.
        output_path (str): Path to save the extended video.
        duration (float): Desired duration of the extended video.

    Returns:
        str: Path of the extended video.
    """
    # Determine the duration of the input video
    video_duration = get_video_duration(video_path)

    # Calculate the number of loops needed to match the desired duration
    n_loops = math.ceil(duration / video_duration)

    # Construct ffmpeg command to loop the video and cut it to the exact duration
    ffmpeg_command = f"ffmpeg -hide_banner -loglevel error -stats -i {video_path} -vf loop={n_loops}:1 -ss 0 -to {duration} -c:a copy {output_path}"
    subprocess.run(ffmpeg_command, shell=True)

    return output_path


def add_subtitles(video_path: str, output_path: str, transcript_path: str) -> str:
    """
    Add subtitles to a video.

    Args:
        video_path (str): Path to the input video.
        output_path (str): Path to save the video with subtitles.
        transcript_path (str): Path to the transcript file.

    Returns:
        str: Path of the video with added subtitles.
    """
    # Construct ffmpeg command to add subtitles
    cmd = (
        f"ffmpeg -hide_banner -loglevel error -stats -i {video_path} "
        f"-vf subtitles={transcript_path.replace('\\', '/')}:force_style="
        f"'Alignment=10,FontName={FONT_FILE},Fontsize=18,BackColour=H000000,"
        f"BorderStyle=4,Shadow=0'"
        f" {output_path}"
    )
    subprocess.run(cmd, shell=True)

    return output_path


def fetch_transcript(video_id: str) -> str | None:
    """
    Fetch and process the transcript for a YouTube video.

    Args:
        video_id (str): ID of the YouTube video.

    Returns:
        str: Path to the transcript file.
    """
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        transcript = process_transcript(transcript)
        transcript = fix_overlaps(transcript)

        formatter = SRTFormatter()
        srt = formatter.format_transcript(transcript)

        filepath = "transcript.srt"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(srt)
        return filepath
    except:
        return None


def process_transcript(transcript: List[dict]) -> List[dict]:
    """
    Process the transcript to split it into smaller segments and calculate their durations.

    Args:
        transcript (List[dict]): List of transcript segments.

    Returns:
        List[dict]: Processed transcript with smaller segments.
    """
    processed_transcript = []

    for segment in transcript:
        text = segment["text"]

        if text.startswith("["):  # Skip segments that describe sounds
            continue

        words = text.split()
        total_syllables = sum(syllapy.count(word) for word in words)
        syllable_duration = segment["duration"] / total_syllables
        start_time = segment["start"]

        for word in words:
            word_duration = syllapy.count(word) * syllable_duration
            word_segment = {
                "text": word,
                "start": start_time,
                "duration": word_duration,
            }
            processed_transcript.append(word_segment)
            start_time += word_duration

    return processed_transcript


def fix_overlaps(transcript: List[dict]) -> List[dict]:
    """
    Fix overlaps in the transcript segments by adjusting start times.

    Args:
        transcript (List[dict]): List of transcript segments.

    Returns:
        List[dict]: Transcript with adjusted start times to resolve overlaps.
    """
    # Sort the transcript segments by start time
    sorted_transcript = sorted(transcript, key=lambda x: x["start"])

    # Iterate through the sorted transcript to fix overlaps
    for i in range(1, len(sorted_transcript)):
        # Check if there is an overlap with the previous segment
        if (
            sorted_transcript[i]["start"]
            < sorted_transcript[i - 1]["start"] + sorted_transcript[i - 1]["duration"]
        ):
            # If there is an overlap, adjust the start time of the current segment
            sorted_transcript[i]["start"] = (
                sorted_transcript[i - 1]["start"] + sorted_transcript[i - 1]["duration"]
            )

    return sorted_transcript


def save_secondary_content(url: str) -> None:
    """
    Download and save secondary content from a URL.

    Args:
        url (str): URL of the content to download.
    """
    # Create necessary directories
    create_directory(SECONDARY_CONTENT_PATH)

    # Download the content
    download_youtube_video(url, SECONDARY_CONTENT_PATH)


def clip(
    input_video: str, output_path: str, file_name: str, duration: int = CLIP_DURATION
) -> List[str]:
    """
    Split a video into clips of approximately equal duration.

    Args:
        input_video (str): Path to the input video.
        output_path (str): Directory to save the generated clips.
        file_name (str): Base name for the generated clips.
        duration (int): Duration of each clip (in seconds).

    Returns:
        List[str]: List of paths to the generated clips.
    """
    output_template = os.path.join(output_path, f"{file_name}_%03d.mp4")

    # Construct ffmpeg command to split the video into clips
    cmd = f'ffmpeg.exe -hide_banner -loglevel error -stats -i {input_video} -reset_timestamps 1 -sc_threshold 0 -g {duration} -force_key_frames "expr:gte(t, n_forced * {duration})" -segment_time {duration} -f segment {output_template}'
    subprocess.run(cmd)

    # Get paths of the generated clips
    clip_paths = [
        os.path.join(output_path, filename) for filename in os.listdir(output_path)
    ]
    return clip_paths


def add_text(input_video: str, output_video: str, text: str, radius=10):
    """
    Add text overlay to a video with rounded corners.

    Parameters:
        input_video (str): Path to the input video file.
        output_video (str): Path to save the output video file.
        text (str): Text to be overlaid on the video.
        radius (int): Radius of the rounded corners (default is 8).

    Returns:
        None
    """

    # Temporary file paths
    text_image_path = os.path.join(TEMP_PATH, "text.png")

    # Create pic with dynamic text
    text_filter = (
        f"color=black@0:size=700x150,"
        f"drawtext=text='{text}':box=1:boxborderw=30:boxcolor=white:borderw=0:"
        "fontsize=75:fontcolor=black:x=(w-text_w)/2:y=(h-text_h)/2:"
        f"fontfile={FONT_FILE}"
    )

    # Execute ffmpeg command to generate text image
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-stats",
            "-lavfi",
            text_filter,
            "-frames",
            "1",
            "-f",
            "image2",
            "-c:v",
            "png",
            "-pix_fmt",
            "rgb24",
            text_image_path,
        ]
    )

    # Use Pillow to trim the text image
    img = Image.open(text_image_path)
    trimmed_img = img.crop(img.getbbox())
    trimmed_img.save(text_image_path)
    img.close()

    # Rounded corners filtergraph
    rounded_corners_filtergraph = (
        f"[1:v]geq=lum='p(X,Y)':a='if(gt(abs(W/2-X),W/2-{radius})*gt(abs(H/2-Y),H/2-{radius}),"
        f"if(lte(hypot({radius}-(W/2-abs(W/2-X)),{radius}-(H/2-abs(H/2-Y))),{radius}),255,0),255)'[t];"
        "[0][t]overlay=(W-w)/2:(H-h)*2/3"
    )

    # Execute ffmpeg command with rounded corners filter
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-stats",
            "-i",
            input_video,
            "-i",
            text_image_path,
            "-lavfi",
            rounded_corners_filtergraph,
            "-c:v",
            "h264_nvenc",
            "-cq",
            "20",
            "-c:a",
            "copy",
            output_video,
            "-y",
        ]
    )

    # Clean up temporary files
    os.remove(text_image_path)

    return output_video
