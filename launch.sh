#!/bin/bash
# https://vaneyckt.io/posts/safer_bash_scripts_with_set_euxo_pipefail/
set -euo pipefail

# Script to assist with running the search in the background.
# Manual method would be to open a screen to run the script and then disconnect from the screen with CTRL+A and D

# Change directory to the location of this script
# https://stackoverflow.com/questions/6393551/what-is-the-meaning-of-0-in-a-bash-script
# https://stackoverflow.com/questions/3349105/how-to-set-current-working-directory-to-the-directory-of-the-script
cd "${0%/*}"

# Consume the first argument which is this script's name
# https://stackoverflow.com/questions/9057387/process-all-arguments-except-the-first-one-in-a-bash-script
# https://stackoverflow.com/questions/3995067/passing-second-argument-onwards-from-a-shell-script-to-java
# Not necessary on macOS
#first_arg="$1"
#shift

# https://stackoverflow.com/questions/1908610/how-to-get-pid-of-background-process
# https://www.devdungeon.com/content/taking-command-line-arguments-bash
# https://janakiev.com/til/python-background/
# Run the script in the background and pass the bash arguments through (throwing away console output)
#nohup python3 ./search_runner.py "$@" > /dev/null &
# https://superuser.com/questions/454907/how-to-execute-a-command-in-screen-and-detach
# Run the script in a detached screen
screen -S search_runner -dm python3 ./search_runner.py "$@"

echo "Search runner started in screen, its name is is 'search_runner. Use 'screen -S search_runner -X quit' to quit"
