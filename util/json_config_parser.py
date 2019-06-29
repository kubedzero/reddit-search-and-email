import json
from os import path

from util.log_setup import get_logger_with_name


# https://stackoverflow.com/questions/19078170/python-how-would-you-save-a-simple-settings-config-file
# https://martin-thoma.com/configuration-files-in-python/
# https://www.dummies.com/programming/python/how-to-create-a-constructor-in-python/
class JsonConfig:

    # Takes a list of nested lists (of nested lists) like [1, [3, [[], 6] ], 7] and flattens recursively
    # Functionally equivalent to:
    # def flattenlist(L):
    #   return [L] if not isinstance(L, list) else [x for X in L for x in flattenlist(X)]
    def __flatten_list(self, input_object):

        if isinstance(input_object, list):
            # declare an empty list
            flat_list = []

            # iterate through what we know to be a list
            for item in input_object:

                # recursively call each item in the list until the base case. Then add to the flat list and move upward
                for sub_item in self.__flatten_list(item):
                    flat_list.append(sub_item)
            return flat_list
        else:
            # Base case: wrap the object in a list so it can be iterated through and appended
            return [input_object]

    # Function takes in a search string like "level1.level_2.L3" + a dict and gets the value of the deepest key L3.
    def __parsed_json_search(self, search_string, remaining_obj):

        if isinstance(remaining_obj, list):

            # Handle the case where we get a list of objects by making a list of their inner contents
            return [self.__parsed_json_search(search_string, inner_obj)
                    if inner_obj else None for inner_obj in remaining_obj]
        else:
            # https://stackoverflow.com/questions/6903557/splitting-on-first-occurrence
            split_search_string = search_string.split(".", 1)

            if len(split_search_string) == 1:
                # base case of there being no further nested levels in the search string/dictionary
                # dict returns None if the value isn't found
                return [remaining_obj.get(search_string)]
            else:
                # Recursive case where a dot exists, indicating remaining levels of the search string
                current_search_string = split_search_string[0]
                remaining_search_string = split_search_string[1]

                # make the recursive call to search the remaining structure with the remaining search string
                if current_search_string in remaining_obj:
                    return self.__parsed_json_search(remaining_search_string, remaining_obj.get(current_search_string))
                else:
                    # Mirror the behavior of our base case by returning a list
                    return [None]

    # Given a key of a value to look for, find it in the object and return it
    def get_config_value(self, key, simplify_singleton=True, remove_none=False, fail_quietly=False):

        if key == "":
            # https://realpython.com/python-exceptions/
            raise Exception("Empty key passed in, a value cannot be found")

        # iterate through the config_values list of tuples. If the value is present, return it.
        # Otherwise continue to the fallback config, until we have no more configs left to check
        for config_tuple in self._config_tuples:
            # search_result list can be a nested list, so flatten it
            search_result = self.__flatten_list(self.__parsed_json_search(key, config_tuple[1]))

            # If parameter is set to True (default=False) remove None items from the search result
            if remove_none:
                search_result = list(filter(None, search_result))

            # Make sure our result is not empty or a list of only None
            # https://stackoverflow.com/questions/3844801/check-if-all-elements-in-a-list-are-identical
            if len(list(filter(None, search_result))) != 0 or '' in search_result:
                # For parsing ease by the caller, allow just a value to be returned if the result was a singleton list
                if len(search_result) == 1 and simplify_singleton:
                    return search_result[0]
                else:
                    return search_result

        # If there are no configs left to check, the key isn't defined. Throw an exception
        message = "Value could not be found for key [{}]".format(key)
        # Allow the function to exit cleanly if desired (Use case: value is optional)
        if fail_quietly:
            self._logger_instance.info(message)
            return None
        else:
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

        if isinstance(file_path_list, str):
            file_path_list = [file_path_list]
        elif not (isinstance(file_path_list, (list, tuple))):
            message = "Input [{}] is not a list or tuple!".format(file_path_list)
            self._logger_instance.critical(message)
            raise Exception(message)

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
