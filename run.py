# PRAW from https://github.com/praw-dev/praw
import praw
# https://stackoverflow.com/questions/4770297/convert-utc-datetime-string-to-local-datetime
from datetime import datetime
# https://medium.com/@eleroy/10-things-you-need-to-know-about-date-and-time-in-python-with-datetime-pytz-dateutil-timedelta-309bfbafb3f7
import pytz

from util.log_setup import get_logger_with_name
from util.json_config_parser import JsonConfig

# https://stackoverflow.com/questions/1312331/using-a-global-dictionary-with-threads-in-python
# TODO use locks to add search results directly to a global dictionary (but then we lose the result->searchparam relation)
from threading import RLock

# https://docs.python.org/3/library/logging.html#logging.Formatter
# https://docs.python.org/3/library/time.html#time.strftime

LOG_FILE = "reddit-search-and-email.log"
LOG_LEVEL_FILE = "INFO"
LOG_LEVEL_CONSOLE = "DEBUG"

logger_instance = get_logger_with_name("core", LOG_LEVEL_CONSOLE, LOG_FILE, LOG_LEVEL_FILE)
# Chosen from https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
local_timezone = 'America/Los_Angeles'
logger_instance.debug('Setting local timezone to ' + local_timezone)
to_zone = pytz.timezone(local_timezone)

def main():
    logger_instance.warning('Starting up... File log level set to [%s] and Console to [%s]',
                            LOG_LEVEL_FILE, LOG_LEVEL_CONSOLE)

    logger_instance.info('Initializing PRAW instance')
    # `client_id` and `client_secret` are retrieved from the praw.ini file#
    # TODO move this to a config
    reddit = praw.Reddit(user_agent='reddit-search-and-email')

    # define the results dictionary
    search_dict = {}  # could also say = dict()
    # TODO change searches to happen in a loop (maybe store output dicts, maybe not?
    # TODO move search params to config
    run_search(reddit, search_dict, 'Search 1', 'redditdev+learnpython',
        'title:"PRAW')
    run_search(reddit, search_dict, 'Search 2', 'redditdev',
        'title:Python')
    # delete any entries in the results dictionary whose submission IDs are listed in the already_returned file
    # format the email output



def run_search(reddit, search_dict, search_name, subreddits, search_string):
    # Define a temporary multireddit and perform a search as documented on https://praw.readthedocs.io/en/latest/code_overview/reddit/subreddits.html
    searchListingGenerator = reddit.subreddit(subreddits).search(search_string,sort='new',time_filter='week')
    # make sure a nested submission dict exists in the value of the search dict https://www.programiz.com/python-programming/nested-dictionary
    if not (search_name in search_dict):
        search_dict[search_name] = {}
    # https: // www.w3schools.com / python / python_dictionaries.asp
    for submission in searchListingGenerator:
        search_dict[search_name][submission.id] = submission
        # TODO remove date formatting from here and just leave debug logs as link and/or title so we don't drag around the pytz
        logger_instance.debug('%s %s https://reddit.com%s',
                              to_zone.localize(datetime.fromtimestamp(submission.created_utc)).isoformat('T')
                              , submission.title, submission.permalink)
        # useful submission fields: title, created_utc, permalink, url (linked url or permalink) found on https://praw.readthedocs.io/en/latest/code_overview/models/submission.html

    logger_instance.info('Result count is %d in subreddit [%s] using search [%s]', len(search_dict[search_name]),
                         subreddits, search_string)


# https://stackoverflow.com/questions/419163/what-does-if-name-main-do 
# Call main() when Python runs this file directly
if __name__ == "__main__": main()

# TODO add scheduling system
# Set last email sent to value from cfg file
# get list of submission titles and dates fitting the search critera
# Iterate through and check dates against last email sent var
# if submission is newer, add its URL to the list of URLS
# Send email containing the list of URLs formatted as their titles

# https://stackoverflow.com/questions/419163/what-does-if-name-main-do explains indentation and how to enter into and run a file
# Objectives:
# Get rid of praw.ini and use just one config file
# Have a default configuration file with sample values that gets auto-read
# https://stackoverflow.com/questions/19078170/python-how-would-you-save-a-simple-settings-config-file
# https://martin-thoma.com/configuration-files-in-python/
# Have a custom config file passed in as an argument that overwrites present values over the sample file
# Oauth login for Gmail 
# https://developers.google.com/gmail/api/quickstart/python
# https://github.com/kootenpv/yagmail#oauth2
# https://yagmail.readthedocs.io/en/latest/api.html#authentication
# https://realpython.com/python-send-email/
# https://stackoverflow.com/questions/10147455/how-to-send-an-email-with-gmail-as-provider-using-python
# https://www.geeksforgeeks.org/send-mail-gmail-account-using-python/
# https://stackabuse.com/how-to-send-emails-with-gmail-using-python/
# Multithreaded parallel searches
# History file that stores the permalinks or IDs of previous search results as a sort of dedupe. Could read in the file as a hash set at program start and then every interval add new results to the output list while also writing to the history file and adding to the hash set
# HTML formatting in the email, maybe from markdown? 
# Logging mechanism to track dates, times, different log levels
# Scheduling mechnaism so I don't have to rely on a cron job and can disable/enable at will
# Config file, maybe JSON or XML or CSV that will store settings like Oauth, searches, timezone, interval, etc