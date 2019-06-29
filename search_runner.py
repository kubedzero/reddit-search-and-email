# Reddit API
import praw
# Used for checking file existence and type
from os import path
# Used for running a function on an interval
import schedule
# Used for sleeping the thread
import time
# Used for formatting markdown to HTML
import markdown
# Used for getting more easily defined CLI args
import argparse
# Used for getting the list of arguments with which the program was called
import sys
# Used for getting the directory path of this script
import os

from util.email_tools import EmailTools, create_mime_email
from util.json_config_parser import JsonConfig
from util.log_setup import get_logger_with_name


# Returns a string of markdown formatted text
def construct_email_markdown(dict_of_searches_and_submissions):
    email_body_lines = []
    email_body_lines.append("## New Search Results Found!")
    for dict_entry_tuple in dict_of_searches_and_submissions.items():
        # Add the search name from the JSON
        email_body_lines.append('### {}'.format(dict_entry_tuple[0]))
        # Add all the separate submissions as their titles with hyperlinks to the post
        for submission in dict_entry_tuple[1].values():
            email_body_lines.append('* [{}](https://reddit.com{})'.format(submission.title, submission.permalink))
    # Aggregate the lines of markdown into a single string and return
    return "\n".join(email_body_lines)


# Class with internal fields for storing Email and Reddit instances along with all the necessary logging information
class SearchAndEmailExecutor:

    # Method to populate a list with MIME object emails and then use the instantiated Gmail class to send them
    def generate_and_send_emails(self):
        mime_email_list = []
        # Iterate through the search results, which at the top level are partitioned by email address recipient
        for email_tuple in self._search_result_dict.items():
            self._logger_instance.debug("Creating email Markdown and HTML for recipient: %s", email_tuple[0])
            email_body_markdown = construct_email_markdown(email_tuple[1])
            email_body_html = markdown.markdown(email_body_markdown)
            mime_email_list.append(create_mime_email(email_body_markdown, email_body_html,
                                                     # TODO change the subject to be more useful?
                                                     email_subject_text=self._configuration.get_config_value(
                                                         "email_settings.email_subject_text"),
                                                     email_sender=self._email_sender,
                                                     email_recipient=email_tuple[0]))

        # Send the MIME mail using the email_tools configuration, having already been authenticated
        self._email_tools.send_mail(mime_email_list)

    # Given a file path to a list of old submission IDs, remove any repeats from the search dict and add new submissions
    # to the CSV file. Then clean up the dict by removing empty dicts
    def __dedupe_and_write_search_results(self, path_to_old_results):
        # A HashSet to store all the values in the CSV file
        old_results_set = set()

        # Only run if the CSV file exists
        if (path.exists(path_to_old_results) or path.isfile(path_to_old_results)):

            # Open old results file and store its contents in a searchable Set
            with open(path_to_old_results, 'r') as opened_file:
                for string in opened_file:
                    # Use rstrip() to get rid of the trailing whitespace and newline. Then add to the Set
                    old_results_set.add(string.rstrip())
                self._logger_instance.info("Existing results file found at %s, %d unique values found",
                                           path_to_old_results, len(old_results_set))

        num_items_removed = 0
        new_results_to_write = set()

        # https://docs.python.org/3/library/stdtypes.html#dictionary-view-objects
        # Check each email address tuple in the search dict for individual searches going to that email
        for email_dict_tuple in list(self._search_result_dict.items()):
            for search_name_tuple in list(email_dict_tuple[1].items()):
                # Check each submission under each search name
                for submission_id in list(search_name_tuple[1].keys()):
                    log_message = "SubmissionID {} is ".format(submission_id)

                    if submission_id in old_results_set:
                        log_message += "already in the CSV file. Removing from result dictionary"
                        # If the submission was previously sent, remove it from the dict.
                        search_name_tuple[1].pop(submission_id)
                        # Increment the counter tracking the number of items removed
                        num_items_removed += 1
                    else:
                        log_message += "a not-seen before NEW result! Adding to the CSV file"
                        # Otherwise leave the dict untouched AND add it to the list of items to write
                        new_results_to_write.add(submission_id + '\n')
                    self._logger_instance.debug(log_message)

                # Remove the parent search dict from the search results if it's now empty after dedupe
                if len(search_name_tuple[1]) == 0:
                    email_dict_tuple[1].pop(search_name_tuple[0])

            # Remove the parent email dict from the search results if it's now empty after dedupe
            if len(email_dict_tuple[1]) == 0:
                self._search_result_dict.pop(email_dict_tuple[0])

        self._logger_instance.info("After dedupe there were %d submissions removed with %d NEW submissions",
                                       num_items_removed, len(new_results_to_write))

        # Open the CSV file (1 column schema [submission_id] no header) in append mode (creating if it didn't exist)
        with open(path_to_old_results, 'a+') as opened_file:
            opened_file.writelines(list(new_results_to_write))

    # Run a single PRAW search and put the results into the class search_result_dict
    def __run_search(self, email_recipient, search_name, subreddits, search_string):
        self._logger_instance.info("Running search: %s",search_name)
        # Define a temporary multireddit and perform a search as documented on https://praw.readthedocs.io/en/latest/code_overview/reddit/subreddits.html
        searchListingGenerator = self._reddit.subreddit(subreddits).search(search_string, sort='new', time_filter='week')

        # https://www.w3schools.com/python/python_dictionaries.asp
        # Add all returned search result submissions to the search_result_dict
        for submission in searchListingGenerator:
            # Make the search dict under the email if it didn't already exist
            if not (email_recipient in self._search_result_dict):
                self._search_result_dict[email_recipient] = {}

            # make sure a nested submission dict exists in the value of the search dict
            # https://www.programiz.com/python-programming/nested-dictionary
            if not (search_name in self._search_result_dict[email_recipient]):
                self._search_result_dict[email_recipient][search_name] = {}

            # Add the submission to the dict under the proper email and search name and submission ID
            self._search_result_dict[email_recipient][search_name][submission.id] = submission
            self._logger_instance.debug('https://reddit.com%s', submission.permalink)
            # useful submission fields: title, created_utc, permalink, url (linked url or permalink) found on
            # https://praw.readthedocs.io/en/latest/code_overview/models/submission.html

        self._logger_instance.info('Result count is %d in subreddit [%s] using search [%s]',
                                   len(self._search_result_dict[email_recipient][search_name])
                                   if search_name in self._search_result_dict[email_recipient] else 0,
                                   subreddits, search_string)

    # Run and dedupe the searches according to the CLI arguments and configuration
    def execute_searches(self):
        # Define the results dictionary, resetting every time this runs
        self._search_result_dict = {}  # could also say = dict()

        # Get all the configured searches from the configuration and run them, adding results to the dict
        # Searches are partitioned first by recipient email, then by search title, then by submission ID
        for search_params in self._configuration.get_config_value("searches"):
            # Use optional configuration for email recipient alongside each search, otherwise default to the fallback
            if "email_recipient" in search_params:
                email_recipient = search_params.get("email_recipient")
            else:
                email_recipient = self._configuration.get_config_value("email_settings.default_email_recipient")

            self.__run_search(email_recipient, search_params.get("search_name"),search_params.get("subreddits"),
                              search_params.get("search_params"))

        # Dedupe the search results with the stored previous results if the skip argument is false (not passed in)
        if not self._cli_args.skipdedupe:
            old_results_path = os.path.abspath(os.path.dirname(sys.argv[0])) + "/old_results.csv"
            self.__dedupe_and_write_search_results(old_results_path)

        # Return the number of populated top level dicts. If 0 are returned there are no results (after dedupe)
        return len(self._search_result_dict)

    # Initialize the Gmail Oauth2 EmailTools class, which may prompt for user input if a refresh token isn't defined
    def initialize_email(self):
        self._email_tools = EmailTools(self._email_sender,self._configuration.get_config_value(
            "email_settings.google_api_client_id"), self._configuration.get_config_value(
            "email_settings.google_api_client_secret"), self._configuration.get_config_value(
            "email_settings.google_refresh_token"), self._console_log_level, self._file_log_filepath,
                                       self._file_log_level)

    def initialize_praw(self):
        # https://github.com/praw-dev/praw
        # Do prechecks to confirm the PRAW auth info isn't default
        praw_client_id = self._configuration.get_config_value("praw_client_id")
        praw_client_secret = self._configuration.get_config_value("praw_client_secret")
        if (praw_client_id == "" or praw_client_secret == ""):
            self._logger_instance.error("Reddit PRAW client ID and/or secret have not been set in the config!")
            self._logger_instance.error("Go to https://www.reddit.com/prefs/apps/ while logged in to generate auth info")

        # Start up PRAW
        self._logger_instance.info('Initializing PRAW instance...')
        self._reddit = praw.Reddit(client_id=praw_client_id,
                                   client_secret=praw_client_secret,
                                   user_agent='reddit-search-and-email')
        self._logger_instance.info('PRAW Initialized')

    def __init__(self, cli_args, configuration):
        # Define and initialize class fields using the CLI arguments and JSON configuration
        self._search_result_dict = {}
        self._configuration = configuration
        self._cli_args = cli_args
        self._email_sender = configuration.get_config_value("email_settings.email_sender")
        self._console_log_level = configuration.get_config_value("logging.console_log_level")
        self._file_log_filepath = configuration.get_config_value("logging.file_log_absolute_path")
        self._file_log_level = configuration.get_config_value("logging.file_log_level")

        self._logger_instance = get_logger_with_name("Executor", self._console_log_level, self._file_log_filepath,
                                                     self._file_log_level)
        self._logger_instance.info("Executor Initialized")


# Method that repeatedly runs every interval, skipping over client and logger initialization
def run_loop(executor, logger_instance):
    # Get the number of results and populate the search_result_dict
    number_of_results = executor.execute_searches()

    # Exit early if there are no results in the search dict
    if number_of_results == 0:
        logger_instance.info("No new search results found.")
        return

    # Consolidate the search results into emails and send them
    executor.generate_and_send_emails()
    logger_instance.info("Scheduled run finished. Waiting until next run...")


# https://askubuntu.com/questions/396654/how-to-run-the-python-program-in-the-background-in-ubuntu-machine
def main(args):
    # https://docs.python.org/3/library/argparse.html
    # https://stackabuse.com/command-line-arguments-in-python/
    # Set up the argparse object that defines and handles program input arguments
    parser = argparse.ArgumentParser(description='A program to perform Reddit searches')

    parser.add_argument('--config', '-c', help="Path to a configuration file", type=str)

    # Interprets as true if passed in, false otherwise
    parser.add_argument('--skipdedupe', '-s', help="Skip deduping on existing results", action='store_true')

    parser.add_argument('--onerun', '-o', help="Run search once and don't schedule further jobs", action='store_true')
    args = parser.parse_args()

    # http://www.blog.pythonlibrary.org/2013/10/29/python-101-how-to-find-the-path-of-a-running-script/
    default_config_absolute_path = os.path.abspath(os.path.dirname(sys.argv[0])) + "/default_base_config.json"
    config_list = [default_config_absolute_path]
    # Add the passed-in config path if it is passed in
    if args.config is not None:
        config_list.insert(0,args.config)

    # Initialize the configuration reader using the list of configuration files
    configuration = JsonConfig(config_list)

    console_log_level = configuration.get_config_value("logging.console_log_level")
    file_log_filepath = configuration.get_config_value("logging.file_log_absolute_path")
    file_log_level = configuration.get_config_value("logging.file_log_level")

    logger_instance = get_logger_with_name("core", console_log_level, file_log_filepath, file_log_level)

    # Initialize the helper class along with its helper classes for Reddit and Gmail integration
    executor = SearchAndEmailExecutor(args,configuration)
    executor.initialize_praw()
    executor.initialize_email()

    # Set the interval to wait between running searches
    interval = configuration.get_config_value("search_interval_minutes")
    schedule.every(interval).minutes.do(run_loop, executor, logger_instance)

    # Run the search immediately
    run_loop(executor, logger_instance)

    if not args.onerun:
        try:
            # Loop forever, sleeping N seconds and then checking if any scheduled jobs need to be run
            while True:
                time.sleep(60)
                schedule.run_pending()
                logger_instance.debug("Sleeping until the next check for a pending scheduled job")
        except KeyboardInterrupt:
            message = 'Interrupted by user! Exiting...'
            logger_instance.warn(message)
            print(message)
    else:
        logger_instance.warn("Script was called with onerun argument and has run once. Exiting...")
        return

# https://stackoverflow.com/questions/419163/what-does-if-name-main-do
# Call main(sys.argv[1:]) this file is run. Pass the arg array from element 1 onwards to exclude the program name arg
if __name__ == "__main__": main(sys.argv[1:])