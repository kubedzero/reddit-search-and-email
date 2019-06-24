import json
from os import path

from util.log_setup import get_logger_with_name


# https://www.dummies.com/programming/python/how-to-create-a-constructor-in-python/
class JsonConfig:

    # Function takes in a search string like "level1.level_2.L3" + a dict and gets the value of the deepest key L3.
    def __dict_search(self, search_string, remaining_dict):
        # https://stackoverflow.com/questions/6903557/splitting-on-first-occurrence
        split_search_string = search_string.split(".", 1)
        # base case of there being no further nested levels in the search string/dictionary
        if len(split_search_string) == 1:
            # dict returns None if the value isn't found
            return remaining_dict.get(search_string)
        else:
            # Recursive case where a dot exists, indicating remaining levels of the search string
            current_search_string = split_search_string[0]
            remaining_search_string = split_search_string[1]
            if current_search_string in remaining_dict:
                new_value = remaining_dict.get(current_search_string)
                # get the value and check if it's a list or a dict. if a list, spawn separate recursive and combine
                # TODO Refactor to support consecutive lists in lists
                if isinstance(new_value, list):
                    response_list = [self.__dict_search(remaining_search_string, inner_dict)
                                     if inner_dict else None for inner_dict in new_value]
                    if len(response_list) == 1:
                        return response_list[0]
                else:
                    return self.__dict_search(remaining_search_string, new_value)
            else:
                # Mirror the behavior of dict.get() when no value can be found
                return None

    # Given a key of a value to look for, find it in the object and return it
    def get_config_value(self, key):
        if key == "":
            # https://realpython.com/python-exceptions/
            raise Exception("Empty key passed in, a value cannot be found")

        # iterate through the config_values list of tuples. If the value is present, return it.
        # Otherwise continue to the fallback config, until we have no more configs left to check
        for config_tuple in self._config_tuples:
            # search_result can either be a single value or a list of values
            search_result = self.__dict_search(key, config_tuple[1])
            # Make sure the result isn't None or that we're not returning a whole list of None
            # https://stackoverflow.com/questions/3844801/check-if-all-elements-in-a-list-are-identical
            # TODO see if this can be simplified
            if not (isinstance(search_result, list) and search_result[1:] == search_result[:-1] and any(
                    element is None for element in search_result)) and not (
                    not isinstance(search_result, list) and search_result is None):
                return search_result
        # If there are no configs left to check, the key isn't defined. Throw an exception
        message = "Value could not be found for key [{}]".format(key)
        self._logger_instance.critical(message)
        raise Exception(message)

    # Called after config files are ingested, this private method replaces the logger with a configured version
    # Private Methods: https://linux.die.net/diveintopython/html/object_oriented_framework/private_functions.html
    def __bootstrap_logger(self):
        self._logger_instance.info("Attempting to bootstrap JSON config parser logger with config values")
        config_console_log_level = self.get_config_value("logging.console_log_level")
        config_file_log_level = self.get_config_value("logging.file_log_level")
        config_file_log_filepath = self.get_config_value("logging.file_log_filepath")
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
        self.__bootstrap_logger()
        self._logger_instance.debug("Ingested Config files are: {}".format(self._config_tuples))
        self._logger_instance.info("Config files successfully ingested!")
