#
# TASKS CONFIGURATION FILE
# 

# Data folder
# If git backup is enabled, this file should be the top-level directory of a
# git repository with a configured remote
FILE_PATH="data"

# File to store todos {file: <file_name>, profile_name: <name>}
# note: the file is relative to the FILE_PATH const
PROFILES=[
    {"file": "todo.txt", "profile_name": "Normal"}
]
assert len(PROFILES) > 0

# You can define a custom rule for the default
# profile, for example, based of time of day
def DEFAULT_PROFILE_RULE(profile:list[dict[str,str]]) -> str:
    return profile[0]['profile_name']

# Enable git backups
ENABLE_GIT=True

# Auth token to be sent to the endpoint to trigger daily cleanup
# Cleanup is triggered with a GET request sent to the /cleanup endpoint
# It should be triggered daily.
#
# Example using crontab:
#   58 23 * * * curl http://localhost:5000/cleanup?code=<CODE>
DAILY_CLEANUP_TRIGGER_CODE=""

# Max number of lines the file can have
FILE_MAX_LINES=1500

# Currently all accounts lead to the same tasks page
# Example credentials.json file
# [
#    {"user": "user1", "password": " ... "},
# ]
CREDENTIALS_FILE="credentials.json"

# Select display language. This is used for the scheduling of events
# `@segunda` -> `@monday`
PORTUGUESE_LANG=False

# Prevent <script> tags from being embedded in the file and executed.
# Script execution can happen if the task is shown on the overview panel as it
# gets rendered as HTML. Sanitizer will prevent it.
SANITIZE_JS=True

# CSS may allow for script execution or fetching of remote resources. To prevent
# this, <style> tags are sanitized and can only have the elements defined below.
SANITIZE_CSS=True

CSS_ALLOWED_FUNCTIONS = (
    "rgb",
    "linear-gradient"
    # allowing url() functions may be problematic and allows for JS execution! 
    # It does however allow to embed images in tags.
)

CSS_ALLOWED_AT_RULE = (
    "keyframes",
    # allowing @import rules may be problematic
)

CSS_ALLOWED_IDENT = (
    #  add more to this list
    "font-family","font-size","font-weight",
    "color",
    "background-color","background-size","background","background-clip",
    "-webkit-background-clip","-webkit-text-fill-color",
    "padding", "padding-top", "padding-left", "padding-right", "padding-bottom",
    "animation",
    "border", "border-radius","border-color",
    "animation",
    "box-shadow",
    "margin", "margin-top", "margin-left", "margin-right", "margin-bottom",
    "display",
    "max-width","max-height","height","width",
    "text-decoration",
    "position","top","left","bottom","right",
    "text-decoration",
    "content",
    "line-height"
)

# Caldav integration
ENABLE_CALDAV=True
CALDAV_SERVER_URL=""
CALDAV_SERVER_USERNAME=""
CALDAV_SERVER_PASSWORD=""
CALDAV_CALENDAR_NAME=""
CALDAV_DEFAULT_EVENT_DURATION_MIN=30
CALDAV_ENABLE_VALARM=False
CALDAV_NOTIFY_TIME="2M"