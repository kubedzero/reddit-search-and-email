# PRAW from https://github.com/praw-dev/praw
# https://stackoverflow.com/questions/4770297/convert-utc-datetime-string-to-local-datetime
from datetime import datetime

from os import path

import praw
# https://medium.com/@eleroy/10-things-you-need-to-know-about-date-and-time-in-python-with-datetime-pytz-dateutil-timedelta-309bfbafb3f7
import pytz

# https://docs.python.org/3/library/argparse.html
# https://stackabuse.com/command-line-arguments-in-python/
import argparse
import sys

from util.json_config_parser import JsonConfig
from util.log_setup import get_logger_with_name

# https://stackoverflow.com/questions/1312331/using-a-global-dictionary-with-threads-in-python
# TODO use locks to add search results directly to a global dictionary (but then we lose the result->searchparam relation)

# https://docs.python.org/3/library/logging.html#logging.Formatter
# https://docs.python.org/3/library/time.html#time.strftime

# Chosen from https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
local_timezone = 'UTC'
#'America/Los_Angeles'
to_zone = pytz.timezone(local_timezone)

def dedupe_and_write_search_results(new_search_result_dict, path_to_old_results):
    if (path.exists(path_to_old_results) or path.isfile(path_to_old_results)):
        old_results_set = set()
        new_results_to_write = set()
        with open(path_to_old_results, 'r') as opened_file:
            # TODO test if list wrapper is needed
            for string in list(opened_file):
                old_results_set.add(string.rstrip())
            # https://docs.python.org/3/library/stdtypes.html#dictionary-view-objects
            for dict_entry in list(new_search_result_dict.values()):
                for submission_id in list(dict_entry.keys()):
                    if submission_id in old_results_set:
                        dict_entry.pop(submission_id, None)
                    else:
                        new_results_to_write.add(submission_id + '\n')

        # Open the CSV file (1 column schema [submission_id] without header) in append mode (creating if it didn't exist)
        with open(path_to_old_results, 'a+') as opened_file:
            opened_file.writelines(list(new_results_to_write))

    # TODO add a log message in case this does nothing since no file existed



def main(args):

    # set up the argparse object that defines and handles program input arguments
    parser = argparse.ArgumentParser(description='A program to perform Reddit searches')
    parser.add_argument('--config', '-c', help="Path to a configuration file", type=str)
    # interprets as true if passed in, false otherwise
    parser.add_argument('--skipdedupe', '-s', help="Skip deduping on existing results", action='store_true')
    args = parser.parse_args()

    # TODO test if default config path works if calling run.py from other locations
    config_list = ["./default_base_config.json"]
    # Add the passed-in config path if it is passed in
    if args.config is not None:
        config_list.insert(0,args.config)
    # Initialize the configuration reader using the list of configuration files
    configuration = JsonConfig(config_list)

    file_log_level = configuration.get_config_value("logging.file_log_level")
    console_log_level = configuration.get_config_value("logging.console_log_level")
    file_log_filepath = configuration.get_config_value("logging.file_log_filepath")

    logger_instance = get_logger_with_name("core", console_log_level, file_log_filepath, file_log_level)

    # Start up PRAW
    logger_instance.info('Initializing PRAW instance...')
    reddit = praw.Reddit(client_id=configuration.get_config_value("praw_client_id"),
                         client_secret=configuration.get_config_value("praw_client_secret"),
                         user_agent='reddit-search-and-email')

    # define the results dictionary
    search_result_dict = {}  # could also say = dict()
    # get all the configured searches from the configuration and run them, adding results to the dict
    for search_params in configuration.get_config_value("searches"):
        run_search(logger_instance, reddit, search_result_dict, search_params.get("search_name"),
                   search_params.get("subreddits"), search_params.get("search_params"))

    # Dedupe the search results with the stored previous results if the skip argument is false (not passed in)
    if not args.skipdedupe:
        dedupe_and_write_search_results(search_result_dict,"./old_results.csv")

    # delete any entries in the results dictionary whose submission IDs are listed in the already_returned file
    # TODO make a function diff_with_existing_results(search_result_dict, path_to_existing_CSV_file, update_existing=True) that returns a dict with only new results while adding all new
    # configuration option to choose whether to ignore existing or not
    # configuration option on where to store existing items
    # TODO take the remaining results and format them into an email body
    # TODO configure the email client
    # format the email output
    print(search_result_dict)


def run_search(logger_instance, reddit, search_dict, search_name, subreddits, search_string):
    # Define a temporary multireddit and perform a search as documented on https://praw.readthedocs.io/en/latest/code_overview/reddit/subreddits.html
    searchListingGenerator = reddit.subreddit(subreddits).search(search_string, sort='new', time_filter='week')
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
# Call main(sys.argv[1:]) this file is run. Pass the arg array from element 1 onwards to exclude the program name arg
if __name__ == "__main__": main(sys.argv[1:])

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
