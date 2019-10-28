from __future__ import print_function

from six.moves import input
from pyhocon import ConfigFactory
from pathlib2 import Path
from six.moves.urllib.parse import urlparse

from trains_agent.backend_api.session.defs import ENV_HOST
from trains_agent.backend_config.defs import LOCAL_CONFIG_FILES


description = """
Please create new credentials using the web app: {}/profile
In the Admin page, press "Create new credentials", then press "Copy to clipboard"

Paste credentials here: """

def_host = 'http://localhost:8080'
try:
    def_host = ENV_HOST.get(default=def_host) or def_host
except Exception:
    pass

host_description = """
Editing configuration file: {CONFIG_FILE}
Enter the url of the trains-server's Web service, for example: {HOST}
""".format(
    CONFIG_FILE=LOCAL_CONFIG_FILES[0],
    HOST=def_host,
)


def main():
    print('TRAINS-AGENT setup process')
    conf_file = Path(LOCAL_CONFIG_FILES[0]).absolute()
    if conf_file.exists() and conf_file.is_file() and conf_file.stat().st_size > 0:
        print('Configuration file already exists: {}'.format(str(conf_file)))
        print('Leaving setup, feel free to edit the configuration file.')
        return

    print(host_description)
    web_host = input_url('Web Application Host', '')
    parsed_host = verify_url(web_host)

    if parsed_host.port == 8008:
        print('Port 8008 is the api port. Replacing 8080 with 8008 for Web application')
        api_host = parsed_host.scheme + "://" + parsed_host.netloc + parsed_host.path
        web_host = parsed_host.scheme + "://" + parsed_host.netloc.replace(':8008', ':8080', 1) + parsed_host.path
        files_host = parsed_host.scheme + "://" + parsed_host.netloc.replace(':8008', ':8081', 1) + parsed_host.path
    elif parsed_host.port == 8080:
        api_host = parsed_host.scheme + "://" + parsed_host.netloc.replace(':8080', ':8008', 1) + parsed_host.path
        web_host = parsed_host.scheme + "://" + parsed_host.netloc + parsed_host.path
        files_host = parsed_host.scheme + "://" + parsed_host.netloc.replace(':8080', ':8081', 1) + parsed_host.path
    elif parsed_host.netloc.startswith('demoapp.'):
        # this is our demo server
        api_host = parsed_host.scheme + "://" + parsed_host.netloc.replace('demoapp.', 'demoapi.', 1) + parsed_host.path
        web_host = parsed_host.scheme + "://" + parsed_host.netloc + parsed_host.path
        files_host = parsed_host.scheme + "://" + parsed_host.netloc.replace('demoapp.', 'demofiles.', 1) + parsed_host.path
    elif parsed_host.netloc.startswith('app.'):
        # this is our application server
        api_host = parsed_host.scheme + "://" + parsed_host.netloc.replace('app.', 'api.', 1) + parsed_host.path
        web_host = parsed_host.scheme + "://" + parsed_host.netloc + parsed_host.path
        files_host = parsed_host.scheme + "://" + parsed_host.netloc.replace('app.', 'files.', 1) + parsed_host.path
    elif parsed_host.netloc.startswith('demoapi.'):
        print('{} is the api server, we need the web server. Replacing \'demoapi.\' with \'demoapp.\''.format(
            parsed_host.netloc))
        api_host = parsed_host.scheme + "://" + parsed_host.netloc + parsed_host.path
        web_host = parsed_host.scheme + "://" + parsed_host.netloc.replace('demoapi.', 'demoapp.', 1) + parsed_host.path
        files_host = parsed_host.scheme + "://" + parsed_host.netloc.replace('demoapi.', 'demofiles.', 1) + parsed_host.path
    elif parsed_host.netloc.startswith('api.'):
        print('{} is the api server, we need the web server. Replacing \'api.\' with \'app.\''.format(
            parsed_host.netloc))
        api_host = parsed_host.scheme + "://" + parsed_host.netloc + parsed_host.path
        web_host = parsed_host.scheme + "://" + parsed_host.netloc.replace('api.', 'app.', 1) + parsed_host.path
        files_host = parsed_host.scheme + "://" + parsed_host.netloc.replace('api.', 'files.', 1) + parsed_host.path
    else:
        api_host = ''
        web_host = ''
        files_host = ''
        if not parsed_host.port:
            print('Host port not detected, do you wish to use the default 8008 port n/[y]? ', end='')
            replace_port = input().lower()
            if not replace_port or replace_port == 'y' or replace_port == 'yes':
                api_host = parsed_host.scheme + "://" + parsed_host.netloc + ':8008' + parsed_host.path
                web_host = parsed_host.scheme + "://" + parsed_host.netloc + ':8080' + parsed_host.path
                files_host = parsed_host.scheme + "://" + parsed_host.netloc + ':8081' + parsed_host.path
        if not api_host:
            api_host = parsed_host.scheme + "://" + parsed_host.netloc + parsed_host.path

    api_host = input_url('API Host', api_host)
    files_host = input_url('File Store Host', files_host)

    print('\nTRAINS Hosts configuration:\nAPI: {}\nWeb App: {}\nFile Store: {}\n'.format(
        api_host, web_host, files_host))

    while True:
        print(description.format(web_host), end='')
        parse_input = input()
        # check if these are valid credentials
        credentials = None
        # noinspection PyBroadException
        try:
            parsed = ConfigFactory.parse_string(parse_input)
            if parsed:
                credentials = parsed.get("credentials", None)
        except Exception:
            credentials = None

        if not credentials or set(credentials) != {"access_key", "secret_key"}:
            print('Could not parse user credentials, try again one after the other.')
            credentials = {}
            # parse individual
            print('Enter user access key: ', end='')
            credentials['access_key'] = input()
            print('Enter user secret: ', end='')
            credentials['secret_key'] = input()

        print('Detected credentials key=\"{}\" secret=\"{}\"'.format(credentials['access_key'],
                                                                     credentials['secret_key'], ))

        from trains_agent.backend_api.session import Session
        # noinspection PyBroadException
        try:
            print('Verifying credentials ...')
            Session(api_key=credentials['access_key'], secret_key=credentials['secret_key'], host=api_host)
            print('Credentials verified!')
            break
        except Exception:
            print('Error: could not verify credentials: host={} access={} secret={}'.format(
                api_host, credentials['access_key'], credentials['secret_key']))

    # get GIT User/Pass for cloning
    print('Enter git username for repository cloning (leave blank for SSH key authentication): [] ', end='')
    git_user = input()
    if git_user.strip():
        print('Enter password for user \'{}\': '.format(git_user), end='')
        git_pass = input()
        print('Git repository cloning will be using user={} password={}'.format(git_user, git_pass))
    else:
        git_user = None
        git_pass = None

    # noinspection PyBroadException
    try:
        conf_folder = Path(__file__).parent.absolute() / '..' / 'backend_api' / 'config' / 'default'
        default_conf = ''
        for conf in ('agent.conf', 'sdk.conf', ):
            conf_file_section = conf_folder / conf
            with open(str(conf_file_section), 'rt') as f:
                default_conf += conf.split('.')[0] + ' '
                default_conf += f.read()
            default_conf += '\n'
    except Exception:
        print('Error! Could not read default configuration file')
        return
    # noinspection PyBroadException
    try:
        with open(str(conf_file), 'wt') as f:
            header = '# TRAINS-AGENT configuration file\n' \
                     'api {\n' \
                     '    api_server: %s\n' \
                     '    web_server: %s\n' \
                     '    files_server: %s\n' \
                     '    # Credentials are generated in the webapp, %s/profile\n' \
                     '    # Override with os environment: TRAINS_API_ACCESS_KEY / TRAINS_API_SECRET_KEY\n' \
                     '    credentials {"access_key": "%s", "secret_key": "%s"}\n' \
                     '}\n\n' % (api_host, web_host, files_host,
                                web_host, credentials['access_key'], credentials['secret_key'])
            f.write(header)
            git_credentials = '# Set GIT user/pass credentials\n' \
                              '# leave blank for GIT SSH credentials\n' \
                              'agent.git_user=\"{}\"\n' \
                              'agent.git_pass=\"{}\"\n' \
                              '\n'.format(git_user or '', git_pass or '')
            f.write(git_credentials)
            f.write(default_conf)
    except Exception:
        print('Error! Could not write configuration file at: {}'.format(str(conf_file)))
        return

    print('\nNew configuration stored in {}'.format(str(conf_file)))
    print('TRAINS-AGENT setup completed successfully.')


def input_url(host_type, host=None):
    while True:
        print('{} configured to: [{}] '.format(host_type, host), end='')
        parse_input = input()
        if host and (not parse_input or parse_input.lower() == 'yes' or parse_input.lower() == 'y'):
            break
        if parse_input and verify_url(parse_input):
            host = parse_input
            break
    return host


def verify_url(parse_input):
    try:
        if not parse_input.startswith('http://') and not parse_input.startswith('https://'):
            # if we have a specific port, use http prefix, otherwise assume https
            if ':' in parse_input:
                parse_input = 'http://' + parse_input
            else:
                parse_input = 'https://' + parse_input
        parsed_host = urlparse(parse_input)
        if parsed_host.scheme not in ('http', 'https'):
            parsed_host = None
    except Exception:
        parsed_host = None
        print('Could not parse url {}\nEnter your trains-server host: '.format(parse_input), end='')
    return parsed_host


if __name__ == '__main__':
    main()