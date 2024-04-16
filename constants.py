
ACCOUNTS_PATH = "accounts"

# TikTok only allows to schedule videos 10 days in advance
MAX_DAYS = 10

# CLIPPER VARS
CLIP_DURATION = 60
CLIP_RESOLUTION = (1080, 1920)
FONT_FILE = "assets/tiktoksans.ttf"

SECONDARY_CONTENT_PATH = "assets/content"
TEMP_PATH = "temp"
OUTPUT_PATH = "output"

# SCHEDULER VARS
# PATHS
COOKIES_PATH = "cookies"

# URLs
TIKTOK_URL = "https://www.tiktok.com"
TIKTOK_UPLOAD_URL = (
    "https://www.tiktok.com/creator#/upload?scene=creator_center&lang=en"
)
TIKTOK_LOGIN_URL = TIKTOK_URL + "/login/phone-or-email/email/?lang=en"

languages = [
    "af",
    "sq",
    "ar-SA",
    "ar-IQ",
    "ar-EG",
    "ar-LY",
    "ar-DZ",
    "ar-MA",
    "ar-TN",
    "ar-OM",
    "ar-YE",
    "ar-SY",
    "ar-JO",
    "ar-LB",
    "ar-KW",
    "ar-AE",
    "ar-BH",
    "ar-QA",
    "eu",
    "bg",
    "be",
    "ca",
    "zh-TW",
    "zh-CN",
    "zh-HK",
    "zh-SG",
    "hr",
    "cs",
    "da",
    "nl",
    "nl-BE",
    "en",
    "en-US",
    "en-EG",
    "en-AU",
    "en-GB",
    "en-CA",
    "en-NZ",
    "en-IE",
    "en-ZA",
    "en-JM",
    "en-BZ",
    "en-TT",
    "et",
    "fo",
    "fa",
    "fi",
    "fr",
    "fr-BE",
    "fr-CA",
    "fr-CH",
    "fr-LU",
    "gd",
    "gd-IE",
    "de",
    "de-CH",
    "de-AT",
    "de-LU",
    "de-LI",
    "el",
    "he",
    "hi",
    "hu",
    "is",
    "id",
    "it",
    "it-CH",
    "ja",
    "ko",
    "lv",
    "lt",
    "mk",
    "mt",
    "no",
    "pl",
    "pt-BR",
    "pt",
    "rm",
    "ro",
    "ro-MO",
    "ru",
    "ru-MI",
    "sz",
    "sr",
    "sk",
    "sl",
    "sb",
    "es",
    "es-AR",
    "es-GT",
    "es-CR",
    "es-PA",
    "es-DO",
    "es-MX",
    "es-VE",
    "es-CO",
    "es-PE",
    "es-EC",
    "es-CL",
    "es-UY",
    "es-PY",
    "es-BO",
    "es-SV",
    "es-HN",
    "es-NI",
    "es-PR",
    "sx",
    "sv",
    "sv-FI",
    "th",
    "ts",
    "tn",
    "tr",
    "uk",
    "ur",
    "ve",
    "vi",
    "xh",
    "ji",
    "zu",
]
vendors = [
    "Google Inc.",
    "Firefox",
    "Google" "Chrome",
    "Microsoft",
    "Edge",
    "Apple",
    "Safari",
    "Opera",
    "Brave",
    "Vivaldi",
    "DuckDuckGo",
    "Chromium",
    "Epic",
]
platforms = ["ChromeOS", "Windows", "MAC", "Linux"]
webgl = ["WebKit", "Intel Inc.", "AMD"]
renderers = ["M1", "Intel", "Nvidia", "AMD"]
