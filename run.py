# PRAW from https://github.com/praw-dev/praw
# https://stackoverflow.com/questions/4770297/convert-utc-datetime-string-to-local-datetime
from datetime import datetime

from os import path

from util.email_tools import EmailTools, create_mime_email

import praw
# https://medium.com/@eleroy/10-things-you-need-to-know-about-date-and-time-in-python-with-datetime-pytz-dateutil-timedelta-309bfbafb3f7
import pytz

import markdown

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
            # check each email address in the search dict
            for email_dict_tuple in new_search_result_dict.items():
                # check each search_name under each email
                for search_name_tuple in email_dict_tuple[1].items():
                    # Check each submission under each search name
                    for submission_id in search_name_tuple[1].keys():
                        if submission_id in old_results_set:
                            # if the submission was previously sent, remove it from the dict.
                            # TODO track the number of items removed
                            # TODO be more verbose
                            search_name_tuple[1].pop(submission_id)
                        else:
                            # Otherwise leave the dict untouched AND add it to the list of items to write
                            new_results_to_write.add(submission_id + '\n')
                    if len(search_name_tuple[1]) == 0:
                        email_dict_tuple[1].pop(search_name_tuple[0])
                if len(email_dict_tuple[1]) == 0:
                    new_search_result_dict.pop(email_dict_tuple[0])


        # Open the CSV file (1 column schema [submission_id] without header) in append mode (creating if it didn't exist)
        with open(path_to_old_results, 'a+') as opened_file:
            opened_file.writelines(list(new_results_to_write))

    # TODO add a log message in case this does nothing since no file existed

# Returns a string of markdown formatted text
def construct_email_markdown(search_result_dict):
    email_body_lines = []
    email_body_lines.append("## New Search Results Found!")
    for dict_entry_tuple in search_result_dict.items():
        email_body_lines.append('### {}'.format(dict_entry_tuple[0]))
        for submission in dict_entry_tuple[1].values():
            email_body_lines.append('* [{}](https://reddit.com{})'.format(submission.title, submission.permalink))
    # Aggregate the lines of markdown into a single string
    return "\n".join(email_body_lines)


# TODO refactor logging and make this a class, then main can just call the class
# TODO reread the configs every interval, in case there are updates to the search params (maybe as a flag)
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

    console_log_level = configuration.get_config_value("logging.console_log_level")
    file_log_filepath = configuration.get_config_value("logging.file_log_filepath")
    file_log_level = configuration.get_config_value("logging.file_log_level")

    logger_instance = get_logger_with_name("core", console_log_level, file_log_filepath, file_log_level)

    # Do prechecks to confirm the PRAW auth info isn't default
    praw_client_id = configuration.get_config_value("praw_client_id")
    praw_client_secret = configuration.get_config_value("praw_client_secret")
    if (praw_client_id == "" or praw_client_secret == ""):
        logger_instance.error("Reddit PRAW client ID and/or secret have not been set in the config!")
        logger_instance.error("Go to https://www.reddit.com/prefs/apps/ while logged in to generate auth info")

    # Start up PRAW
    logger_instance.info('Initializing PRAW instance...')
    reddit = praw.Reddit(client_id=praw_client_id,
                         client_secret=praw_client_secret,
                         user_agent='reddit-search-and-email')

    # define the results dictionary
    search_result_dict = {}  # could also say = dict()
    # get all the configured searches from the configuration and run them, adding results to the dict
    for search_params in configuration.get_config_value("searches"):
        if "email_recipient" in search_params:
            email_recipient = search_params.get("email_recipient")
        else:
            email_recipient = configuration.get_config_value("email_settings.email_recipient")
        run_search(logger_instance, reddit, search_result_dict, email_recipient, search_params.get("search_name"),
                   search_params.get("subreddits"), search_params.get("search_params"))

    # Dedupe the search results with the stored previous results if the skip argument is false (not passed in)
    # Alternative is to remove submissions with dates earlier than the last email date
    if not args.skipdedupe:
        dedupe_and_write_search_results(search_result_dict,"./old_results.csv")

    # Exit early if there are no results in the search dict
    if len(search_result_dict) == 0:
        # TODO expand this to be more verbose
        print("no new search results found")
        return

    email_sender = configuration.get_config_value("email_settings.email_sender")
    email_recipient = configuration.get_config_value("email_settings.email_recipient")

    email_tools = EmailTools(google_account_email=email_sender,
                             google_api_client_id=configuration.get_config_value("email_settings.google_api_client_id"),
                             google_api_client_secret=configuration.get_config_value(
                                 "email_settings.google_api_client_secret"),
                             google_refresh_token=configuration.get_config_value("email_settings.google_refresh_token"),
                             console_log_level=console_log_level,
                             file_log_filepath=file_log_filepath,
                             file_log_level=file_log_level)

    # TODO for loop iterates over the search result dict, check in on results by email and formatting an email for each
    for email_tuple in search_result_dict.items():
        # Construct the MD version of the email and then convert it to HTML with the Markdown package
        email_body_markdown = construct_email_markdown(email_tuple[1])
        email_body_html = markdown.markdown(email_body_markdown)
        # TODO use override search-specific email to send emails to different addresses based on the search result
        # TODO split out the markdown and html generation so it gets done per search maybe, depending on the email
        # TODO rather than search name partitioning the search results, use email recipient?
        mime_email = create_mime_email(email_body_markdown, email_body_html,
                                       email_subject_text=configuration.get_config_value(
                                           "email_settings.email_subject_text"),
                                       email_sender=configuration.get_config_value("email_settings.email_sender"),
                                       email_recipient=email_tuple[0])
        # Send the MIME mail using the email_tools configuration, having already been authenticated
        email_tools.send_mail(mime_email)

    # TODO configure the email client
    # TODO add scheduling system
    # format the email output
    print(email_body_markdown)
    print(email_body_html)


def run_search(logger_instance, reddit, search_dict, email_recipient, search_name, subreddits, search_string):
    # Define a temporary multireddit and perform a search as documented on https://praw.readthedocs.io/en/latest/code_overview/reddit/subreddits.html
    searchListingGenerator = reddit.subreddit(subreddits).search(search_string, sort='new', time_filter='week')
    # https: // www.w3schools.com / python / python_dictionaries.asp
    for submission in searchListingGenerator:
        if not (email_recipient in search_dict):
            search_dict[email_recipient] = {}
        # make sure a nested submission dict exists in the value of the search dict https://www.programiz.com/python-programming/nested-dictionary
        # only add the key/value to the dict if this search returned any values
        if not (search_name in search_dict[email_recipient]):
            search_dict[email_recipient][search_name] = {}
        search_dict[email_recipient][search_name][submission.id] = submission
        # TODO remove date formatting from here and just leave debug logs as link and/or title so we don't drag around the pytz
        logger_instance.debug('%s %s https://reddit.com%s',
                              to_zone.localize(datetime.fromtimestamp(submission.created_utc)).isoformat('T')
                              , submission.title, submission.permalink)
        # useful submission fields: title, created_utc, permalink, url (linked url or permalink) found on https://praw.readthedocs.io/en/latest/code_overview/models/submission.html

    logger_instance.info('Result count is %d in subreddit [%s] using search [%s]', len(search_dict[search_name]) if search_name in search_dict else 0,
                         subreddits, search_string)


# https://stackoverflow.com/questions/419163/what-does-if-name-main-do 
# Call main(sys.argv[1:]) this file is run. Pass the arg array from element 1 onwards to exclude the program name arg
if __name__ == "__main__": main(sys.argv[1:])


# Objectives:
# Scheduling mechnaism so I don't have to rely on a cron job and can disable/enable at will