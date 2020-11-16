# Reddit Search and Email

This is a small project written in Python 3.x to tie together a few different packages and APIs to accomplish the goal of quickly sending an email when a new Reddit post appears.



At a high level, this project offers scheduled independently-defined Reddit searches for new posts and automated email notifications of those posts. 



Some of the technical offerings of the project are:

* Integration with Reddit via the Reddit API by way of the PRAW Python package.
  * Used to perform searches on Reddit and return submission objects containing a post's metadata
* Integration with Gmail via Google APIs and the Oauth2 protocol
  * Used to perform a first time interactive authentication given an API ID and Secret to grant access to the Google account
  * Used to integrate with Gmail to send emails
* Extensible JSON configuration parser to read in and parse a set of hierarchical parameters from an ordered set of configuration files
  * Provides a nested object search to quickly search multiple nested JSON levels
* Extensible logging class to provide verbose console and file based logging for the project's classes
* Configurable search schedule to check for new results
* Stateful tracking of previous results sent out to prevent repeated content in emails
* Minimal third party library dependencies
  * Python 3 (tested with 3.8 on CentOS 8 and 3.9 on macOS)
  * [Markdown](https://github.com/Python-Markdown/markdown) 3.3.3
  * [PRAW](https://github.com/praw-dev/praw) 7.1.0
  * [schedule](https://github.com/dbader/schedule) 0.6.0
  * [urllib3](https://github.com/urllib3/urllib3) 1.26.2



## Setup (Getting Started)

### Python3 and Pip Installation

* macOS
  * Install [pyenv](https://github.com/pyenv/pyenv) to easily manage different pre- and post-installed Python versions. Make sure it's close to the front of your environment `PATH` so calling `which python3` directs you to a folder under its shim
  * Make sure `pip3` is also installed along with `python3`. Pip will help get other packages and dependencies installed
  * JetBrains PyCharm (if using it as an IDE) should be pointing to this `pyenv` shim directory for its interpreter, so package installations occur in the same place as `pip3` via the CLI
* CentOS 7
  * Use Software Collections (SCL)  to install Python 3 alongside the already-installed Python 2. SCL can be installed with `sudo yum install centos-release-scl` and then Python 3 can be installed with `sudo yum install rh-python36`. 
  * Finally, enabling the Python 3 installalation via adding it to the `PATH` can be done by launching an SCL shell with `scl enable rh-python36 bash`. 
  * I also added `scl enable rh-python36 bash` to the `~/.bash_profile` configuration file on the last line, after the `PATH` is set
  * [Here](https://phoenixnap.com/kb/how-to-install-python-3-centos-7) is a more comprehensive guide on how to do it
* CentOS 8
 * The default repositories installed seem to have Python. I ran `dnf install python38` after trying to run it for generic python and seeing `There are following alternatives for "python": python2, python36, python38`

After setup, running `which python3` should return a valid executable

###  JSON configuration

This project allows you to specify a personal JSON file and pass it in to the executable. If values aren't defined in the personal JSON file, they will be picked up by the `default_base_config.json` file that came with the project. That way, if the value in the default file is what you prefer, you can leave it be. Or you can edit the default JSON file to your heart's content. Take care not to share your API keys and personal information! 

* Searches
  * It's expected that you will add a number of searches to the JSON file. You can refer to the Reddit search API to learn fancy ways of searching. 
  * At a basic level, you can combine subreddits to search with a "temporary multireddit" by defining the search subreddits like `"subreddits":"redditdev+learnpython"`. 
  * You can then search for exact matches in the subreddit with backslash-escaped quotes like `"search_params":"looking for an \"EXACT MATCH\""`
  * Finally, you can add one or more emails for those results to be emailed to. This setting can be added per search so different searches go to different people. To override the default email and send a search result to a different email, add `"email_recipient":"another_email_address@gmail.com"` to the search
* Reddit API Key
  * PRAW and Reddit both require an API key in order to use the API. 
  * Go to https://www.reddit.com/prefs/apps/ while logged in or click on the "Apps" tab at the top of your Reddit preferences page
  * Click "create another app" and fill out the information
    * Give it a Name and Description so you know what the API key is used for. This isn't used for anything but the Name is required
    * Choose "script" for the purpose
    * A redirect URI is required. I just set it to my username page (https://www.reddit.com/user/spez), as it isn't used for our purposes.
    * Finally, click "create app" and make sure the app is created
  * Open your App for editing and note the alphanumeric string under the App name and "personal use script." It should look like `3Y6aB66notreal` (15 characters at the time of writing). Add this to the JSON config with the `praw_client_id` key like `"praw_client_id":"3Y6aB66notreal",`
  * Also in your App you should see a longer string, the Secret. Add it to your Config like `"praw_client_secret":"GsR8notAhpfTmXIdqP2pqrealx8"`
* Google API Key
  * Use the Google API console to create a new project and set of Oauth Client ID credentials. The code will create a URL from those credentials. Navigate to it in a browser to authenticate. A verification code will be generated for you to paste into the Python executable (it watches the CLI for keyboard input). Then, a new "refresh token" will be generated for you to add to your JSON config
  * Go to the Google API Console and make a new project using the dropdown in the upper left. You may have to activate/agree beforehand
  * Then on the left side, go to Credentials and use the Create dropdown to make a new Oauth client ID. On the next screen, choose Other and give it a name (doesn't really matter) Click OK
  * A Client ID and Client secret should now appear. Copy those into your JSON as `google_api_client_id` and `google_api_client_secret`, contained in an object under the "email_settings" key. At this time you should also add the `email_sender` key and value, which is the email address of the Google account. 
  * Next, run `search_runner.py` using the instructions in the Execution section of this README to start the main script. As part of the script, it will check if the Google refresh token already exists.
    * If the token exists and you get an error like 400 bad request or 401 unauthorized, it's likely the email address + client ID + client secret + refresh token is mistyped somewhere or expired. 
    * If the token hasn't yet been filled in the JSON (existing as `"google_refresh_token":""`) you will see a URL printed out in the CLI when you try to run it.
    * ALTERNATIVE: You can skip the JSON entry and just pass the values directly into the `email_tools.py` script! Call it with arguments to pass in the Client ID and Secret like `email_tools.py -i <your_client_id_here> -s <your_client_secret_here>`
  * Follow the generated link in a browser on any computer. Note that an "Unverified App" warning will appear since you just made this API/project/credential. Log into your account and authenticate, and get the verification code. Paste it into the CLI where it asks you to `Enter verification code: ` and press Enter/Return. If all was configured properly you should now see a "Credentials Valid!" message. 
  * A new alphanumeric string will be printed out before the "Credentials Valid" message. This is your Refresh Token. Copy and paste it into your JSON configuration and try to run the program again. If all goes well, you should not see an error when EmailTools initializes, as it does a check to validate the credentials when starting up (regardless of if an email will be sent)
  * [This](https://blog.macuyiko.com/post/2016/how-to-send-html-mails-with-oauth2-and-gmail-in-python.html) was the inspiration and guide for this style of Gmail integration
* Other Settings
  * `search_interval_minutes` defines the number of minutes to wait before running all the searches on Reddit again. This starts counting from the time the program is started, and is not guaranteed to run on even minutes (:10, :20, etc.). An Integer should be passed in without quotes, like `"search_interval_minutes":30`
  * `logging.file_log_level` and `logging.console_log_level` define the log level to print outputs at. For most verbose logging, use "DEBUG" and for less logging, "INFO" should be used. For almost no logging, "WARN" should be used.
  * `logging.file_log_absolute_path` defines the location and name of the log file. This file is created from the working directory where `search_runner.py` is called from
  * `email_settings.email_subject_text` defines the String used in the subject of every email sent
  * `email_settings.default_email_recipient` defines the email recipient if one isn't specified in the Reddit searches described above. This is the "fallback" email

## Execution

This project uses [argparse](https://docs.python.org/3/library/argparse.html) to configure and consume command line arguments. The `search_runner.py` script is the heart of the project, and spins up everything it needs to run. The script is configured with the following parameters:

* `--config` or `-c` plus a string containing the path to a JSON configuration. The path will be constructed from the current working directory, NOT from the location of the script
* `--skipdedupe` or `-s` to ignore the existing and previous search results and send the full set of search results every time the script runs. No additional argument needed Useful for testing search parameters or tweaking other parts of the JSON
* `--onerun` or `-o` which avoids scheduling the job to run repeatedly on the interval specified in the JSON. Instead, the script runs one time and then exits

All together, this could mean a script call could look like `python3 search_runner.py --skipdedupe -o --config ~/path/to/some/file.json` which would run once, return all results, and use `~/path/to/some/file.json` as the primary config, falling back on the `default_base_config.json` in the project directory if a value isn't defined.



However, the script is most useful when it runs on an interval, and you might not want to leave a terminal session up and running for as long as you want the script watching your searches.

To handle the long-term (or run-at-startup) use case, a `launch.sh` shell script is provided. It passes through any arguments it was called with, meaning the script does not need to be modified to specify your config and other runtime options. It then runs `search_runner.py` with your arguments in a [Screen](https://linuxize.com/post/how-to-use-linux-screen/) named "search_runner" with a separate process ID (PID) than the session the Bash script is running in. It then exits the script, leaving the Python code running in the background for you to check in on either with the file log or by reattaching the screen session. 