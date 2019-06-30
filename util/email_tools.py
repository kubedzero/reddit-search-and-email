"""
Adapted from:
https://blog.macuyiko.com/post/2016/how-to-send-html-mails-with-oauth2-and-gmail-in-python.html
https://github.com/google/gmail-oauth2-tools/blob/master/python/oauth2.py
https://developers.google.com/identity/protocols/OAuth2

1. Generate and authorize an OAuth2 (generate_oauth2_token)
2. Generate a new access tokens using a refresh token(refresh_token)
3. Generate an OAuth2 string to use for login (access_token)
4. Create MIME emails
5. Send MIME emails
"""
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from util.log_setup import get_logger_with_name
import urllib.parse
import urllib.request
import json
import smtplib
import base64
import time
import sys
import argparse


def url_escape(text):
    return urllib.parse.quote(text, safe='~-._')


def url_format_params(params):
    param_fragments = []
    for param in sorted(params.items(), key=lambda x: x[0]):
        param_fragments.append('%s=%s' % (param[0], url_escape(param[1])))
    return '&'.join(param_fragments)


def generate_oauth2_string(username, access_token, as_base64=False):
    auth_string = 'user=%s\1auth=Bearer %s\1\1' % (username, access_token)
    if as_base64:
        auth_string = base64.b64encode(auth_string.encode('ascii')).decode('ascii')
    return auth_string


# Creates and returns a MIME multipart email
def create_mime_email(email_text, email_html, email_subject_text, email_sender, email_recipient):

    message = MIMEMultipart("alternative")
    message["Subject"] = email_subject_text
    message["From"] = email_sender
    message["To"] = email_recipient

    # Turn these into plain/html MIMEText objects
    part1 = MIMEText(email_text, "plain")
    part2 = MIMEText(email_html, "html")

    # Add HTML/plain-text parts to MIMEMultipart message
    # The email client will try to render the last part first
    message.attach(part1)
    message.attach(part2)
    return message


class EmailTools:

    GOOGLE_ACCOUNTS_BASE_URL = 'https://accounts.google.com'
    REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'
    GOOGLE_API_CLIENT_ID = ""
    GOOGLE_API_CLIENT_SECRET = ""
    GOOGLE_REFRESH_TOKEN = ""

    def command_to_url(self, command):
        return '%s/%s' % (self.GOOGLE_ACCOUNTS_BASE_URL, command)

    def call_refresh_token(self, client_id, client_secret, refresh_token):
        params = {}
        params['client_id'] = client_id
        params['client_secret'] = client_secret
        params['refresh_token'] = refresh_token
        params['grant_type'] = 'refresh_token'
        request_url = self.command_to_url('o/oauth2/token')
        response = urllib.request.urlopen(request_url, urllib.parse.urlencode(params).encode('UTF-8')).read().decode(
            'UTF-8')
        return json.loads(response)

    def refresh_authorization(self):
        self._logger_instance.debug("Refreshing authorization with Client ID, Secret, and Refresh Token")
        response = self.call_refresh_token(self.GOOGLE_API_CLIENT_ID, self.GOOGLE_API_CLIENT_SECRET,
                                           self.GOOGLE_REFRESH_TOKEN)
        return response['access_token'], response['expires_in']

    def send_mail(self, mime_message_list):
        access_token, expires_in = self.refresh_authorization()
        auth_string = generate_oauth2_string(self.GOOGLE_ACCOUNT_EMAIL, access_token, as_base64=True)
        server = smtplib.SMTP('smtp.gmail.com:587')
        server.ehlo(self.GOOGLE_API_CLIENT_ID)
        server.starttls()
        server.docmd('AUTH', 'XOAUTH2 ' + auth_string)
        for mime_message in mime_message_list:
            self._logger_instance.info("Sending email to: %s",mime_message["To"])
            server.sendmail(self.GOOGLE_ACCOUNT_EMAIL, mime_message["To"].replace(" ", "").split(","),
                        mime_message.as_string())
        server.quit()

    def call_authorize_tokens(self, client_id, client_secret, authorization_code):
        params = {}
        params['client_id'] = client_id
        params['client_secret'] = client_secret
        params['code'] = authorization_code
        params['redirect_uri'] = self.REDIRECT_URI
        params['grant_type'] = 'authorization_code'
        request_url = self.command_to_url('o/oauth2/token')
        response = urllib.request.urlopen(request_url, urllib.parse.urlencode(params).encode('UTF-8')).read().decode(
            'UTF-8')
        return json.loads(response)

    def generate_permission_url(self, client_id, scope='https://mail.google.com/'):
        params = {}
        params['client_id'] = client_id
        params['redirect_uri'] = self.REDIRECT_URI
        params['scope'] = scope
        params['response_type'] = 'code'
        return '%s?%s' % (self.command_to_url('o/oauth2/auth'), url_format_params(params))

    def get_authorization(self, google_client_id, google_client_secret):
        scope = "https://mail.google.com/"
        print('Navigate to the following URL to auth:', self.generate_permission_url(google_client_id, scope))
        authorization_code = input('Enter verification code: ')
        response = self.call_authorize_tokens(google_client_id, google_client_secret, authorization_code)
        return response['refresh_token'], response['access_token'], response['expires_in']

    # Constructor to pass in logging information
    def __init__(self, google_account_email, google_api_client_id, google_api_client_secret, google_refresh_token,
                 console_log_level, file_log_filepath, file_log_level):

        self._LOG_NAME = "EmailTools"
        self._logger_instance = get_logger_with_name(self._LOG_NAME, console_log_level,
                                                     file_log_filepath, file_log_level)
        self._logger_instance.debug("Initialized logger for EmailTools")

        # Store the credentials in the class
        self.GOOGLE_ACCOUNT_EMAIL = google_account_email
        self.GOOGLE_API_CLIENT_ID = google_api_client_id
        self.GOOGLE_API_CLIENT_SECRET = google_api_client_secret
        self.GOOGLE_REFRESH_TOKEN = google_refresh_token

        if google_refresh_token == "":
            # Throw an exception if the credentials are empty, providing information on how to fix
            if google_api_client_id == "" and google_api_client_secret == "":
                url1 = "https://developers.google.com/identity/protocols/OAuth2"
                url2 = "https://blog.macuyiko.com/post/2016/how-to-send-html-mails-with-oauth2-and-gmail-in-python.html"
                self._logger_instance.critical("Google Client ID, Client Secret, and Refresh token are empty. Populate "
                                               "them with your Oauth2 credentials found in the Google API Console. "
                                               "More details at {} and {}".format(url1,url2))
                raise ValueError("Google Credentials are all empty and need to be filled")

            # Base values are populated but refresh token is empty, signifying we need to create it
            self._logger_instance.info("Refresh token is empty, using Client ID and Secret to generate an auth link...")
            refresh_token, access_token, expires_in = self.get_authorization(google_api_client_id,
                                                                             google_api_client_secret)
            # TODO write this to the JSON automatically
            self._logger_instance.info("*" * 20)
            self._logger_instance.info('Credentials Valid. Set as your JSON email_settings.google_refresh_token: {}'
                                       .format(refresh_token))
            self._logger_instance.info("*" * 20)
            time.sleep(2)
            self.GOOGLE_REFRESH_TOKEN = refresh_token

        self._logger_instance.info("All Oauth2 credentials present. Checking for validity...")

        # Initialize vars outside of try block
        access_token, expires_in = [None] * 2

        # Test the authorization getting and swallow any exception, rethrowing our own exception
        try:
            access_token, expires_in = self.refresh_authorization()
        except Exception:
            message = "Exception thrown during initialization; Getting authorization didn't work! Check credentials."
            self._logger_instance.critical(message)
            raise ValueError(message, Exception)

        if access_token != "" and expires_in > 0:
            self._logger_instance.info("Credentials valid! Returning EmailTools class")
        else:
            raise Exception("Oauth2 credentials invalid! Clear your Refresh token and reauthenticate")

# Basic entry for getting a refresh token without going through the rest of the script
if __name__ == "__main__":

    # Set up the CLI parser
    # https://stackoverflow.com/questions/24180527/argparse-required-arguments-listed-under-optional-arguments
    parser = argparse.ArgumentParser(description='A program to set up Google/Gmail authentication')
    parser.add_argument('--token', '-t', help="API Refresh Token", type=str)
    requiredNamed = parser.add_argument_group('required named arguments')
    requiredNamed.add_argument('--id', '-i', help="API Client ID", type=str, required=True)
    requiredNamed.add_argument('--secret', '-s', help="API Client Secret", type=str, required=True)
    args = parser.parse_args()

    # If the token argument isn't passed in, use an empty string.
    token = ""
    if args.token is not None:
        token = args.token

    # Try to instantiate EmailTools with the provided values and generate a Refresh Token if one wasn't passed in
    email_tools = EmailTools("email", args.id, args.secret, token, "DEBUG", "", "DEBUG")