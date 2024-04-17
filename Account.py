from datetime import datetime, timedelta
from typing import List
import scrapetube
import os
import pickle
import random

from constants import *
from util import create_directory


class Account:
    def __init__(self, email: str) -> None:
        # Get the path to the account path given the usenrame
        account_path = os.path.join(ACCOUNTS_PATH, email + ".pkl")

        # Get the user data from the file
        self.load_data(account_path)

    def get_next_date(self, start_date: datetime | None = None) -> datetime:
        """
        Returns the next available date to post a video given the account's schedule.

        Args:
            start_date (datetime): it is *optional* to specify a start date to see what dates are available from then on.
        """

        if start_date:
            last_video_date = start_date
        elif len(self.videos) == 0:
            last_video_date = datetime.now()
        else:
            # Get latest video
            last_video_date = max(self.videos, key=lambda x: x["date"])["date"]

        # Extract time part from the schedule
        schedule_times = [
            datetime.strptime(time_str, "%H:%M").time() for time_str in self.schedule
        ]

        # Find the next available date after last_video_date
        next_date = last_video_date.date()

        # Check if the next available date has any available time slot
        while True:
            for time in schedule_times:
                # Combine next_date with each time from the schedule
                next_datetime = datetime.combine(next_date, time)
                # If the next_datetime is after the last_video_date, return it
                if next_datetime > last_video_date:
                    # Check if the date is more than 10 days after today
                    if next_datetime > datetime.now() + timedelta(days=MAX_DAYS):
                        return None
                    else:
                        return next_datetime
            # If no available time slots on the current date, try the next day
            next_date += timedelta(days=1)

    def get_processed_videos(self) -> List[str]:
        """
        Find the videos in the output folder that belong to the account.

        Returns:
            List[str]: list of absolute file paths to video files.
        """
        # Create the output dir if necessary
        create_directory(OUTPUT_PATH)

        # Get videos from the dir
        videos = os.listdir(OUTPUT_PATH)

        account_videos = []
        for video in videos:
            # Check if the file is owned by the user (ex: "email@example.com,videoID,n.mp4") TODO: check this example
            if video.split(",")[0] == self.email:
                full_path = os.path.join(os.getcwd(), OUTPUT_PATH, video)
                account_videos.append(full_path)

        return account_videos

    def get_videos(self, n_videos: int) -> List[dict]:
        """
        Finds YouTube videos that haven't been used before.

        Args:
            n_videos (int): number of videos to return

        Returns:
            List[dict]: list of YouTube videos
        """
        # Get videos from the account channels
        channel_videos = []
        for channel in self.channels:
            videos = self.get_channel_videos(channel)
            channel_videos.extend(videos)

        # Filter out the already processed videos
        used_videos = self.get_used_videos()
        for used_video in used_videos:
            if used_videos in channel_videos:
                channel_videos.remove(used_video)

        return channel_videos[:n_videos]

    def get_used_videos(self) -> List[str]:
        """
        Returns:
            List[str]: list of unique video IDs (unused videos)
        """
        # Find the unique videos in the list of posted videos
        unique_ids = []
        for video in self.videos:
            if video["id"] not in unique_ids:
                unique_ids.append(video["id"])

        # Add used videos to the list
        clips = os.listdir(OUTPUT_PATH)
        for clip in clips:
            id = clip.split(",")[2]
            if id not in unique_ids:
                unique_ids.append(id)

        return unique_ids

    def get_channel_videos(self, channel_username: str) -> List[str]:
        """
        Args:
            channel_username (str): username of a channel (ex: CodeBullet)

        Returns:
            List[str]: list of videos from a channel
        """
        videos = scrapetube.get_channel(channel_username=channel_username, limit=60)

        # Filter out videos that are longer than the video_length specified for the account
        output_videos = []
        for video in videos:
            duration = self.duration_to_seconds(video["lengthText"]["simpleText"])
            if duration <= self.video_length:
                output_videos.append(video["videoId"])

        # Shuffle to not get the very most recent videos
        # TODO: check if this is even useful
        random.shuffle(output_videos)
        return output_videos

    def duration_to_seconds(self, duration: str):
        """
        Transforms a HH:mm:ss or mm:ss to seconds.

        Args:
            duration (str): (example: "28:39", "1:43:32")
        """
        parts = duration.split(":")
        if len(parts) == 3:  # Format is HH:mm:ss
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2])
            total_seconds = hours * 3600 + minutes * 60 + seconds
        elif len(parts) == 2:  # Format is mm:ss
            minutes = int(parts[0])
            seconds = int(parts[1])
            total_seconds = minutes * 60 + seconds
        else:
            raise ValueError("Invalid duration format")

        return total_seconds

    def add_video_to_history(
        self, id: str, date_posted: datetime | None, save: bool = True
    ):
        # If no date is provided the date shall be now
        if not date_posted:
            date_posted = datetime.now()

        # Add the video to the list along with the date it was posted
        self.videos.append({"id": id, "date": date_posted})

        # Save if necessary
        if save:
            self.save()

    def load_data(self, account_path: str):
        """
        Loads and extracts the account data.

        Args:
            path (str): path to the account
        """
        self.account_path = account_path
        with open(account_path, "rb") as file:
            data = pickle.load(file)

        # Account data
        self.email = data["email"]
        self.cookies = data["cookies"]
        self.videos = data["videos"]
        self.channels = data["channels"]
        self.schedule = data["schedule"]

        # Video structure
        self.secondary_content = data["secondary_content"]
        self.subtitles = data["subtitles"]
        self.clip_length = data["clip_length"]
        self.video_length = data["video_length"]

    def save(self):
        """
        Applies any changes to the account file.
        """
        data = {}  # init

        # Account data
        data["email"] = self.email
        data["cookies"] = self.cookies
        data["videos"] = self.videos
        data["channels"] = self.channels
        data["schedule"] = self.schedule

        # Video structure
        data["secondary_content"] = self.secondary_content
        data["subtitles"] = self.subtitles
        data["clip_length"] = self.clip_length
        data["video_length"] = self.video_length

        with open(self.account_path, "wb") as file:
            pickle.dump(data, file)

    @classmethod
    def create(
        cls,
        email: str,
        channels: List[str] = [],
        schedule: List[str] = ["12:00", "16:30"],
        secondary_content: str = True,
        subtitles: str = True,
        clip_length: int = 60,
        video_length: int = 600,
    ):
        # Check if the account already exists
        account_path = os.path.join(ACCOUNTS_PATH, email + ".pkl")
        if os.path.exists(account_path):
            return None

        data = {
            "email": email,
            "channels": channels,
            "schedule": schedule,
            "secondary_content": secondary_content,
            "subtitles": subtitles,
            "clip_length": clip_length,
            "video_length": video_length,
            "videos": [],
            "cookies": None,
        }

        # Create path if necessary
        create_directory(ACCOUNTS_PATH)

        # Write the data to the account file
        account_path = os.path.join(ACCOUNTS_PATH, email + ".pkl")
        with open(account_path, "wb") as file:
            pickle.dump(data, file)

        return cls(email)

    def __str__(self) -> str:
        return self.email
