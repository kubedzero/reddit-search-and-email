import json
from os import path
from util.log_setup import get_logger_with_name

# TODO function signature/constructor should take a list of files and parse them in order, with each one overwriting any previous values
# constructor to build the object
# function to get a value but also handle if it doesn't exist

# TODO read the base_config.json file into a map/json/whatever
# TODO then read in the defined user json file, overwriting any base_config values


# https://www.dummies.com/programming/python/how-to-create-a-constructor-in-python/
class JsonConfig:
    # Given a key of a value to look for, find it in the object and return it
    def get_config_value(self, key):
        if key == "":
            # https://realpython.com/python-exceptions/
            raise Exception("Empty key passed in, a value cannot be found")
        # iterate through the config_values list of tuples. If the value is present, return it.
        # for config_tuple in self.config_values:
        if key in self._config_tuples:
            return self._config_tuples[1].get(key)
        # Otherwise continue to the fallback config, until we have no more configs left to check
        # If there are no configs left to check, the key isn't defined. Throw an exception
        raise Exception("Value could not be found for key %s", key)

    def bootstrap_logger(self):
        self._logger_instance.info("Attempting to bootstrap JSON config parser logger with config values")
        config_console_log_level = self.get_config_value("console_log_level")
        config_file_log_level = self.get_config_value("file_log_level")
        config_file_log_filepath = self.get_config_value("file_log_filepath")
        self._logger_instance = get_logger_with_name(self._LOG_NAME, config_console_log_level, config_file_log_filepath,
                                               config_file_log_level)


    # parameterized constructor to pass in a list of JSON config file paths, with the override values first and fallback values after
    def __init__(self, file_path_list):
        self._LOG_NAME="json_config_parser"
        self._logger_instance = get_logger_with_name(self._LOG_NAME, "DEBUG")
        # Store a list of tuples of the format ("file_path",json) so we can track the source of each config
        self._config_tuples = []
        # iterate through the file path list
        for filename in file_path_list:
            # https://www.guru99.com/python-check-if-file-exists.html
            if not (path.exists(filename) or path.isfile(filename)):
                raise Exception("Path %s does not exist or is not a file! Please correct the path.", filename)
            with open(filename) as file_data:
                # Add a new tuple to the config values list
                self._config_tuples.append((filename, json.load(file_data)))
        self.bootstrap_logger()

#TODO bootstrap the console logger with the actual logger values if they're available
#TODO create nested JSON parser

# Function takes in a search string like "level1.level_2.level3" + a JSON object and wants the value stored there.
# Base case is if there are no dots in the search string, then return the value stored with the search string
# TODO needs to handle not passing through a dict but rather passing through a list (or handling the list and doing independent searches of the separate dicts, consolidating them at this level
# otherwise strip off the first search string up to and including the dot and recursively call with the reduced search string and the reduced JSON
# Throw an exception if the JSON at this level is an array TODO of sorts
# Throw an exception if the key isn't found at this level

# this will invoke parameterized constructor
obj = JsonConfig(["a","b","c"])

obj.get_config_value("")

