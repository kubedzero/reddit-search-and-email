import json
from os import path
from util.log_setup import get_logger_with_name


# https://www.dummies.com/programming/python/how-to-create-a-constructor-in-python/
class JsonConfig:

    # Function takes in a search string like "level1.level_2.level3" + a JSON object and wants the value stored there.
    # Base case is if there are no dots in the search string, then return the value stored with the search string
    # TODO needs to handle not passing through a dict but rather passing through a list (or handling the list and doing independent searches of the separate dicts, consolidating them at this level
    # otherwise strip off the first search string up to and including the dot and recursively call with the reduced search string and the reduced JSON
    # Throw an exception if the JSON at this level is an array TODO of sorts
    # Throw an exception if the key isn't found at this level
    def dict_search(self, search_string, dict):
        if search_string in dict:
            return dict.get(search_string)

    # Given a key of a value to look for, find it in the object and return it
    def get_config_value(self, key):
        if key == "":
            # https://realpython.com/python-exceptions/
            raise Exception("Empty key passed in, a value cannot be found")

        # iterate through the config_values list of tuples. If the value is present, return it.
        # Otherwise continue to the fallback config, until we have no more configs left to check
        for config_tuple in self._config_tuples:
            self.dict_search(key,config_tuple[1])
        # If there are no configs left to check, the key isn't defined. Throw an exception
        raise Exception("Value could not be found for key %s", key)

    # Called after config files are ingested, this method replaces the logger with a configured version
    def bootstrap_logger(self):
        self._logger_instance.info("Attempting to bootstrap JSON config parser logger with config values")
        config_console_log_level = self.get_config_value("console_log_level")
        config_file_log_level = self.get_config_value("file_log_level")
        config_file_log_filepath = self.get_config_value("file_log_filepath")
        self._logger_instance = get_logger_with_name(self._LOG_NAME, config_console_log_level, config_file_log_filepath,
                                                     config_file_log_level)

    # Constructor to pass in a list of JSON config file paths, with override values first and fallback values after
    def __init__(self, file_path_list):
        self._LOG_NAME = "json_config_parser"
        self._logger_instance = get_logger_with_name(self._LOG_NAME, "DEBUG")
        # Store a list of tuples of the format ("file_path",dict) so we can track the source of each config
        self._config_tuples = []
        # iterate through the file path list
        for filename in file_path_list:
            # https://www.guru99.com/python-check-if-file-exists.html
            if not (path.exists(filename) or path.isfile(filename)):
                message = "Path [{}] does not exist or is not a file! Please correct the path.".format(filename)
                self._logger_instance.critical(message)
                raise Exception(message)
            with open(filename) as file_data:
                # Add a new tuple to the config values list
                self._config_tuples.append((filename, json.load(file_data)))
        self._logger_instance.debug("Ingested Config files are: %s", print(self._config_tuples))
        self.bootstrap_logger()

obj = JsonConfig(["../base_config.json"])
