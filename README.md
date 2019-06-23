* Setup
 * Use Homebrew, Yum, Apt, etc. to install Python 3.x
  * Recommended is `pyenv` as per https://opensource.com/article/19/5/python-3-default-macos and make sure `$(pyenv root)/shims` is in your PATH
 * Use a package manager like `pip3` to install [PRAW](https://praw.readthedocs.io/en/latest/getting_started/installation.html). Note that PRAW is a Python3 package so the matching version of pip must be used. 
 * Run with `pip3 install praw` and then `python3 get-updates.py`
 * Create an API in Reddit and copy the app key and secret key into the praw.ini file in the same directory as the python script