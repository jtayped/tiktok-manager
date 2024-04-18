import subprocess

# Assuming FONT_FILE and text_image_path are defined elsewhere in your code
FONT_FILE = "assets/tiktoksans.ttf"
text_image_path = "output.png"
text = "Your dynamic text here"

# Create picture with dynamic text
text_filter = (
    f"color=black@0:size=700x150,"
    f"drawtext=text='{text}':box=1:boxborderw=30:boxcolor=white:borderw=0:"
    "fontsize=75:fontcolor=black:x=(w-text_w)/2:y=(h-text_h)/2:"
    f"fontfile='{FONT_FILE}'"
)
cmd = (
    f"ffmpeg -hide_banner -loglevel error -stats -lavfi \"{text_filter}\" "
    f"-frames 1 -f image2 -c:v png -pix_fmt rgb24 \"{text_image_path}\""
)
subprocess.run(cmd)
