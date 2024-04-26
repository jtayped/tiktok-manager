from typing import List
from bs4 import BeautifulSoup
from collections import defaultdict
import argparse
import logging
import os
import requests

from Account import Account
from Scheduler import Scheduler
from clipper import make_clips
from constants import *
from util import create_directory, download_youtube_video

# Configure the logger
logging.basicConfig(
    level=logging.INFO, format="[%(levelname)s][%(asctime)s]: %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Tool for processing YouTube videos.")
    parser.add_argument(
        "emails",
        metavar="emails",
        type=str,
        nargs="*",
        help="List of emails for the accounts to schedule videos for.",
    )
    parser.add_argument(
        "-c", "--create_account", action="store_true", help="Form to add a new account."
    )
    parser.add_argument(
        "-e",
        "--edit_account",
        nargs=1,
        type=str,
        help="Edit a specific account by it's email.",
    )
    parser.add_argument(
        "-a",
        "--all_accounts",
        action="store_true",
        help="Schedules videos for all accounts.",
    )
    parser.add_argument(
        "--add_content",
        nargs="*",
        type=str,
        help="URLs to secondary content on YouTube (ex: GTA Ramps, Minecraft Parkour, etc...)",
    )

    args = parser.parse_args()
    if args.create_account:
        add_account_form()

    elif args.edit_account:
        account = args.edit_account[0]
        edit_account_form(account)

    elif args.add_content:
        for url in args.add_content:
            logger.info(f"Saving {url}...")
            save_secondary_content(url)

    else:
        if args.all_accounts:
            emails = get_all_emails()
        else:
            emails = args.emails

        for email in emails:
            process_account_videos(email)


def save_secondary_content(url: str):
    # Create the secondary content directory
    create_directory(SECONDARY_CONTENT_PATH)

    # Download video
    download_youtube_video(url, SECONDARY_CONTENT_PATH)


def add_account_form() -> Account:
    print(
        "Welcome to TikTok Account Setup.\n"
        "You will not be asked for the password until logging in to TikTok, "
        "after which the cookie will be saved, and you will not be asked for the password until it expires.\n"
    )

    email = input("Enter the email for the account: ")

    channels = get_input_list(
        message="Enter the channels you want to source videos from (type 'done' when finished): ",
        prompt="Channel username: ",
    )

    schedule = get_input_list(
        message="Enter the times you want to post videos (HH:mm) (type 'done' when finished): ",
        prompt="Time of day (HH:mm): ",
    )

    subtitles = get_yes_no_input("Do you want to have subtitles in the videos (y/N)? ")

    secondary_content = get_yes_no_input(
        "Do you want to have secondary content in the videos (ex: GTA Ramps) (y/N)? "
    )

    video_length = int(
        input("What is the max source video duration in seconds (default: 600)? ")
        or "600"
    )

    clip_length = int(
        input("What length do you want your clips to be in seconds (default: 60)? ")
        or "60"
    )

    account = Account.create(
        email,
        channels,
        schedule,
        secondary_content,
        subtitles,
        clip_length,
        video_length,
    )

    return account


def edit_account_form(account_email: str):
    """
    A form for the user to edit an account, it displays previous account values. If the user wants to keep the previous setting the user should just press Enter.
    """
    account = Account(account_email)

    print(
        f"Welcome to the editing form for {account}!",
        "If you want to leave the values the same as before, simply leave the inputs empty.",
        "If you entered something wrong, you will be asked to confirm your changes at the end.",
    )

    schedule = (
        get_input_list(
            message=f"Add your schedule again, type 'done' when finished ({account.schedule}).",
            prompt="Time of day (HH:mm): ",
        )
        or account.schedule
    )
    account.schedule = schedule

    channels = (
        get_input_list(
            message=f"Enter the channels you want to source videos from again. Type 'done' when finished ({account.channels}).",
            prompt="Channel username: ",
        )
        or account.channels
    )
    account.channels = channels

    subtitles = get_yes_no_input("Do you want to have subtitles in the videos (y/N)? ")
    account.subtitles = subtitles

    secondary_content = get_yes_no_input(
        "Do you want to have secondary content in the videos (ex: GTA Ramps) (y/N)? "
    )
    account.secondary_content = secondary_content

    video_length = int(
        input(
            f"What is the max source video duration in seconds ({account.video_length})? "
        )
        or account.video_length
    )
    account.video_length = video_length

    clip_length = int(
        input(
            f"What length do you want your clips to be in seconds ({account.clip_length})? "
        )
        or account.clip_length
    )
    account.clip_length = clip_length

    confirm = get_yes_no_input("Confirm changes (y/N)? ")

    # Save changes
    if confirm:
        account.save()


def get_input_list(message: str, prompt: str) -> List[str]:
    print(message)

    inputs = []
    while True:
        user_input = input(prompt)
        if user_input.lower() == "done":
            break

        # Check if the input has data in it
        if user_input:
            inputs.append(user_input)

    print()  # newline
    return inputs


def get_yes_no_input(message: str) -> bool:
    response = input(message)
    return response.lower() == "y"


def process_account_videos(email: str):
    """
    The main function that handles, making and scheduling videos for an account.

    Args:
        email (str): email of an existing account in the "accounts" folder.
    """
    logger.info(f"Initializing {email}...")
    account = Account(email)

    # Get valid clip dates
    valid_dates = get_valid_dates(account)

    # Check if there are no valid dates
    if not valid_dates:
        logging.info("The schedule is full!")
        return

    logger.info(f"Calculated {len(valid_dates)} dates")

    # Get unused clips
    unused_clips = account.get_processed_videos()

    # Calculate clips data
    clips_data = calculate_clips_data(account, valid_dates, unused_clips)

    # Schedule videos if any
    schedule_videos(account, clips_data)


def get_valid_dates(account: Account) -> List[str]:
    """
    TikTok allows users to schedule videos up to 10 days in advance

    Returns:
        List[str]: list of available dates to post a video
    """
    valid_dates = []
    date = None
    while True:
        date = account.get_next_date(date)
        if date:
            valid_dates.append(date)
        else:
            break
    return valid_dates


def calculate_clips_data(
    account: Account, valid_dates: List[str], unused_clips: List[str]
) -> List[dict]:
    """
    Pairs existing or newly created clips with valid dates.

    Returns:
        List[dict]: [{"path": "path/to/clip.mp4", "date": valid_date}, ...]
    """
    # Initialize the list to store the clip data
    clips_data = []

    # Find last scheduled clip if any
    last_scheduled_clip = account.last_scheduled_video()
    last_scheduled_id = last_scheduled_clip["id"] if last_scheduled_clip else None

    # Group unused clips by their ID
    id_clips_map = defaultdict(list)
    for clip in unused_clips:
        _, _, clip_id = os.path.basename(clip).removesuffix(".mp4").split(",")
        id_clips_map[clip_id].append(clip)

    # Order clips by ID and group IDs
    ordered_clips = []
    if unused_clips:
        ordered_clips.extend(id_clips_map.pop(last_scheduled_id, []))

    for clips in id_clips_map.values():
        ordered_clips.extend(clips)

    # Pair unused clips with dates if available
    for clip in ordered_clips:
        if valid_dates:
            clip_data = {"path": clip, "date": valid_dates.pop(0)}
            clips_data.append(clip_data)
        else:
            break

    # Generate new clips if needed
    while valid_dates:
        # Create clips from a video
        id = account.get_videos(1)[0]
        url = f"https://www.youtube.com/watch?v={id}"

        logger.info(f"Creating clips from {url}...")
        clips = make_clips(
            url,
            account.email,
            account.secondary_content,
            account.subtitles,
        )

        # Pair up clips with as many valid dates left
        for clip in clips:
            if valid_dates:
                clip_data = {"path": clip, "date": valid_dates.pop(0)}
                clips_data.append(clip_data)
            else:
                break

    return clips_data


def schedule_videos(account: Account, clips_data: List[dict]):
    """
    Handles the scheduling of videos, adding captions and saving the data to the account.
    """
    scheduler = Scheduler(account)
    logger.info("Logging in to the TikTok...")
    for clip in clips_data:
        video_path = clip["path"]
        date = clip["date"]

        logger.info(f"Scheduling the video for {date}...")

        # Create the caption for the video
        video_name = os.path.basename(video_path).removesuffix(".mp4")
        id = video_name.split(",")[-1]
        part_number = int(video_name.split(",")[1]) + 1
        caption = generate_caption(id, f"Part {part_number}")

        # Schedule the post and add it to the history
        scheduler.post(video_path, caption, date)
        account.add_video_to_history(id, date)

        # Remove video once posted
        logger.info("Removing the video")
        os.remove(video_path)


def generate_caption(id: str, part_text: str | None) -> str:
    """
    Returns the title of a YouTube video with some hashtags

    Args:
        id (str): ID of the YouTube video
        part_text (str): indicates what part the video is (optional)

    Returns:
        str: the caption
    """
    r = requests.get(f"https://www.youtube.com/watch?v={id}")
    soup = BeautifulSoup(r.text, features="html.parser")

    link = soup.find_all(name="title")[0]
    title = str(link)
    title = title.replace("<title>", "")
    title = title.replace("</title>", "")
    title = title.removesuffix(" - YouTube")

    main_text = title
    if part_text:
        main_text += f" | {part_text}"

    caption = f"{main_text} #reels #viral #tiktok #explore #foryou #explorepage #trending #reelsinstagram #foryoupage #love #fashion #instagram #instagood #music #likeforlikes"
    return caption


def get_all_emails() -> List[str]:
    # Get all files in the accounts path
    account_files = os.listdir(ACCOUNTS_PATH)

    # Remove the extension name to get the email
    emails = [file.removesuffix(".pkl") for file in account_files]

    return emails


if __name__ == "__main__":
    main()
