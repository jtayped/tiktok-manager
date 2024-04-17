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


def make_clips(
    url: str, file_name: str, secondary_content: bool = True, captions: bool = True
) -> List[str]:
    """
    Process a YouTube video:
    1. Downloads YouTube video
    2. Adds secondary content if specified
        - Loops a video n times and cuts it to the duration of the content
        - Stacks it on the content
    3. Adds captions if specified
        - Grabs the transcript from YouTube
        - Cuts the captions in to one word parts
        - Further processes the transcript
    4. Cuts the video in to clips
    5. Adds text to each clip (Part 1, Part 2, etc...)

    Args:
        url (str): URL of the YouTube video.
        file_name (str): start of the filename joined with the ID and part number (ex: username_videoid123_1.mp4).
        secondary_content (bool): if the video contains secondary content below the main video.
        captions (bool): if the video contains captions.

    Returns:
        List[str]: list file paths to each clip
    """
    id = get_url_id(url)

    # Create a temporary directory to keep the iterations of the video
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

    # Create a folder to dump all the clips
    CLIPS_PATH = os.path.join(TEMP_PATH, id)

    create_directory(CLIPS_PATH)
    create_directory(OUTPUT_PATH)

    # Divide the video in to segments
    clips = clip(video_path, CLIPS_PATH, id)

    # Process all clips
    processed_clips = []
    for i, clip_path in enumerate(clips):
        logger.info(f"Adding text to clip {i+1}/{len(clips)}")

        # Add some text to specify which part the clip is
        target_path = os.path.join(OUTPUT_PATH, f"{file_name},{i},{id}.mp4")
        clip_path = add_text(clip_path, target_path, f"Part {i+1}")

        processed_clips.append(clip_path)

    # Remove all the temporary files
    shutil.rmtree(TEMP_PATH)

    return processed_clips


def add_secondary_content(video_path: str) -> str:
    """
    Adds secondary content (ex: GTA Ramps, Minecraft Parkour, etc...) below the content.
    """
    # Loop a random video from the secondary content library and cut it
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
    video_path: str, output_path: str, crop: Tuple[int, int] = CLIP_RESOLUTION
) -> str:
    """
    Crop a video to a specific resolution.

    Args:
        video_path (str): Path to the video being cropped.
        output_path (str): Path to the output file
        crop (Tuple[int, int]): Target resolution

    Returns:
        str: Path to the cropped video
    """
    # Get input video resolution
    width, height = get_video_dimensions(video_path)

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
        f"ffmpeg -hide_banner -loglevel error -stats -i {video_path} "
        f'-vf "{crop_filter}" {output_path}'
    )
    subprocess.run(cmd, shell=True)

    return output_path


def stack(
    output_path: str,
    top_path: str,
    bottom_path: str,
    crop: Tuple[int, int] = CLIP_RESOLUTION,
) -> str:
    """
    Combine two videos vertically and save the result to a file.

    Args:
        output_path (str): Path to save the combined video.
        top_path (str): Path to the top video.
        bottom_path (str): Path to the bottom video.
        crop (Tuple[int, int]): Cropping dimensions for the combined video.

    Returns:
        str: Path of the combined video.
    """
    # Get resolution to match it to the top one (gives error if not)
    bottom_width, bottom_height = get_video_dimensions(bottom_path)

    # Stack both videos and adjust resolution if needed
    cmd = (
        f"ffmpeg -hide_banner -loglevel error -stats -i {top_path} -i {bottom_path} -filter_complex "
        f'"[0:v]scale={bottom_width}:{bottom_height}[scaled_top];[scaled_top][1:v]vstack,crop={crop[0]}:{crop[1]}:(iw-{crop[0]})/2:0" '
        f"{output_path}"
    )
    subprocess.run(cmd)
    return output_path


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
    cmd = (
        f"ffmpeg -hide_banner -loglevel error -stats -i {video_path}"
        f"-vf loop={n_loops}:1 -ss 0 -to {duration} -c:a copy {output_path}"
    )
    subprocess.run(cmd)

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
    Splits the YouTube transcript in to one word segments and removes overlaps.

    Args:
        video_id (str): ID of the YouTube video.

    Returns:
        str: Path to the SRT transcript file.
    """
    try:
        # Fetches the transcript from YouTube
        transcript = YouTubeTranscriptApi.get_transcript(video_id)

        # When there are two or more people talking FFmpeg stacks the words
        # This looks very weird, so these overlaps shall be fixed
        transcript = fix_overlaps(transcript)

        # Divides the captions in to one word segments
        transcript = process_transcript(transcript)

        # Create an SRT file with the transcript
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
    Process the transcript to split it into smaller one word segments.

    Args:
        transcript (List[dict]): List of transcript segments.

    Returns:
        List[dict]: Processed transcript with smaller segments.
    """
    processed_transcript = []

    for segment in transcript:
        text = segment["text"]

        # Skip segments that describe sounds
        # ex: [Music], [Applause], etc.
        if text.startswith("["):
            continue

        # Calculate how long each syllable in a caption is
        words = text.split()
        total_syllables = sum(syllapy.count(word) for word in words)
        syllable_duration = segment["duration"] / total_syllables

        # Calculate the start time for each word and append it to the new transcript
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


def clip(
    video_path: str, output_path: str, file_name: str, duration: int = CLIP_DURATION
) -> List[str]:
    """
    Split a video into clips of equal duration.

    Args:
        video_path (str): Path to the input video.
        output_path (str): Directory to save the generated clips.
        file_name (str): Base name for the generated clips. A number will be added to the end of each file (ex: filename_2.mp4)
        duration (int): Duration of each clip (in seconds).

    Returns:
        List[str]: List of paths to the generated clips.
    """

    # Add the number of the clip to the end of the file_name the user specified.
    # If there is no file name specified, it shall only name it with the number.
    extension = "%03d.mp4"
    if file_name:
        # ex: "example_2.mp4"
        output_file_name = "_".join([file_name, extension])
    else:
        # ex: "2.mp4"
        output_file_name = extension

    output_template = os.path.join(output_path, output_file_name)

    # There are faster ways of divding videos in to segments of specified duration
    # but they for some reason aren't exact, and vary up to 4 seconds from the set length
    cmd = (
        f"ffmpeg.exe -hide_banner -loglevel error -stats -i {video_path} "
        f"-reset_timestamps 1 -sc_threshold 0 -g {duration} "
        f'-force_key_frames "expr:gte(t, n_forced * {duration})" '
        f"-segment_time {duration} -f segment {output_template}"
    )
    subprocess.run(cmd)

    # Get paths of the generated clips
    clip_paths = [
        os.path.join(output_path, filename) for filename in os.listdir(output_path)
    ]
    return clip_paths


def add_text(video_path: str, output_path: str, text: str, radius=10):
    """
    Add text overlay to a video with rounded corners.

    Parameters:
        video_path (str): Path to the input video file.
        output_path (str): Path to save the output video file.
        text (str): Text to be overlaid on the video.
        radius (int): Radius of the rounded corners.
    """
    text_image_path = os.path.join(TEMP_PATH, "text.png")

    # Create picture with dynamic text
    text_filter = (
        f"color=black@0:size=700x150,"
        f"drawtext=text='{text}':box=1:boxborderw=30:boxcolor=white:borderw=0:"
        "fontsize=75:fontcolor=black:x=(w-text_w)/2:y=(h-text_h)/2:"
        f"fontfile={FONT_FILE}"
    )
    cmd = (
        f"ffmpeg hide_banner loglevel rror -stats -lavfi {text_filter} "
        f"-frames 1 -f image2 -c:v png -pix_fmt rgb24 {text_image_path}"
    )
    subprocess.run(cmd)

    # Trim the transparent outer parts of the text image
    img = Image.open(text_image_path)
    trimmed_img = img.crop(img.getbbox())
    trimmed_img.save(text_image_path)
    img.close()

    # Rounded corners filtergraph
    rounded_corners_filtergraph = (
        f"[1:v]geq=lum='p(X,Y)':a='if(gt(abs(W/2-X),W/2-{radius})*gt(abs(H/2-Y),H/2-{radius}),"
        f"if(lte(hypot({radius}-(W/2-abs(W/2-X)),{radius}-(H/2-abs(H/2-Y))),{radius}),255,0),255)'[t];"
        "[0][t]overlay=(W-w)/2:(H-h)*2/3",
    )
    cmd = (
        f"ffmpeg -hide_banner -loglevel error -stats -i {video_path} -i {text_image_path} "
        f"-lavfi {rounded_corners_filtergraph} -c:v h264_nvenc -cq 20 -c:a copy {output_path} -y"
    )
    subprocess.run(cmd)

    # Clean up temporary files
    os.remove(text_image_path)

    return output_path
