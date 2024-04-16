# TikTok Manager

A Python project that manages multiple TikTok accounts automatically. It utilizes YouTube to source content from pre-selected channels for each TikTok account. Each video is processed into short-form content with FFmpeg, and all the clips are scheduled through the TikTok UI using Selenium.

## Getting Started

Before you start using the project, you must create one or more TikTok accounts with email/password. Once done, you will be able to add the account to the project by filling in the form in the console:

```
python main.py -c
```

If you selected the secondary content option (ex: GTA Ramps, Minecraft Parkour, etc...), you will have to find a video from YouTube and add it like the following:

```
python main.py --add_content https://www.youtube.com/watch?v=VS3D8bgYhf4
```

When done adding all your TikTok accounts you can generate and post content for specific accounts like this:

```
python main.py example@example.com another@another.com
```

or all accounts:

```
python main.py -a
```

NOTE: When you start using an account with this program, it will prompt you to enter your password. This password is used temporarily to grab a cookie. Don't worry, the program won't store your password, just the cookies until they expire. Sometimes, after logging in, there might be a CAPTCHA challenge. In such cases, the program will wait until you're fully logged and you press enter in the console before proceeding.

### Prerequisites

You must install [FFmpeg](https://ffmpeg.org/download.html) to be able to process the videos.

### Installing

Install all the packages:

```
pip install -r requirements.txt
```

## Built With

- ![FFmpeg](https://a11ybadges.com/badge?logo=ffmpeg)
- ![Selenium](https://a11ybadges.com/badge?logo=selenium)

## Contributing

1.  Fork it ([https://github.com/yourname/yourproject/fork](https://github.com/yourname/yourproject/fork))
2.  Create your feature branch (`git checkout -b feature/fooBar`)
3.  Commit your changes (`git commit -am 'Add some fooBar'`)
4.  Push to the branch (`git push origin feature/fooBar`)
5.  Create a new Pull Request

## Authors

- **Joel Taylor** - [Portfolio](https://joeltaylor.business)

See also the list of [contributors](https://github.com/PurpleBooth/a-good-readme-template/contributors) who participated in this project.

## License

This project is licensed under the [MIT License](LICENSE.md). See the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments

Special thanks to [yel-hadd](https://github.com/yel-hadd) for the inspiration with the [automatic posting](https://github.com/yel-hadd/tiktok-auto-poster) part of the project. Another thanks to [Баяр Гончикжапов](https://stackoverflow.com/questions/75598230/how-to-draw-text-on-a-rectangle-with-rounded-corners-using-ffmpeg) from Reddit for the FFmpeg "TikTok text" functionality.
