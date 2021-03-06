"""
********************************************************************************
* Name: cli/__init__.py
* Author: Nathan Swain
* Created On: 2014
* Copyright: (c) Brigham Young University 2014
* License: BSD 2-Clause
********************************************************************************
"""
# Commandline interface for Tethys
import argparse
import subprocess
import os
import shutil

from tethys_apps.terminal_colors import TerminalColors
from .docker_commands import *
from .manage_commands import (manage_command, get_manage_path,
                              MANAGE_START, MANAGE_SYNCDB,
                              MANAGE_COLLECTSTATIC, MANAGE_COLLECTWORKSPACES,
                              MANAGE_COLLECT, MANAGE_CREATESUPERUSER)
from .gen_commands import GEN_SETTINGS_OPTION, GEN_APACHE_OPTION, generate_command
from tethys_apps.helpers import get_installed_tethys_apps

# Module level variables
VALID_GEN_OBJECTS = (GEN_SETTINGS_OPTION, GEN_APACHE_OPTION)
PREFIX = 'tethysapp'


def scaffold_command(args):
    """
    Create a new Tethys app projects in the current directory.
    """
    project_name = args.name

    # Only underscores
    if '-' in project_name:
        project_name = project_name.replace('-', '_')
        print('INFO: Dash ("-") characters changed to underscores ("_").')

    # Only lowercase
    contains_uppers = False
    for letter in project_name:
        if letter.isupper():
            contains_uppers = True

    if contains_uppers:
        project_name = project_name.lower()
        print('INFO: Uppercase characters changed to lowercase.')

    # Prepend prefix
    if PREFIX not in project_name:
        project_name = '{0}-{1}'.format(PREFIX, project_name)

    print('INFO: Initializing tethys app project with name "{0}".\n'.format(project_name))

    process = ['paster', 'create', '-t', 'tethys_app_scaffold', project_name]
    subprocess.call(process)


def uninstall_command(args):
    """
    Uninstall an app command.
    """
    app_name = args.app
    installed_apps = get_installed_tethys_apps()

    if PREFIX in app_name:
        prefix_length = len(PREFIX) + 1
        app_name = app_name[prefix_length:]

    if app_name not in installed_apps:
        print('WARNING: App with name "{0}" cannot be uninstalled, because it is not installed.'.format(app_name))
        exit(0)

    app_with_prefix = '{0}-{1}'.format(PREFIX, app_name)

    # Confirm
    valid_inputs = ('y', 'n', 'yes', 'no')
    no_inputs = ('n', 'no')

    overwrite_input = raw_input('Are you sure you want to uninstall "{0}"? (y/n): '.format(app_with_prefix)).lower()

    while overwrite_input not in valid_inputs:
        overwrite_input = raw_input('Invalid option. Are you sure you want to '
                                    'uninstall "{0}"? (y/n): '.format(app_with_prefix)).lower()

    if overwrite_input in no_inputs:
        print('Uninstall cancelled by user.')
        exit(0)

    try:
        # Remove directory
        shutil.rmtree(installed_apps[app_name])
    except OSError:
        # Remove symbolic link
        os.remove(installed_apps[app_name])

    # Uninstall using pip
    process = ['pip', 'uninstall', '-y', '{0}-{1}'.format(PREFIX, app_name)]

    try:
        subprocess.Popen(process, stderr=subprocess.STDOUT, stdout=subprocess.PIPE).communicate()[0]
    except KeyboardInterrupt:
        pass

    print('App "{0}" successfully uninstalled.'.format(app_with_prefix))


def docker_command(args):
    """
    Docker management commands.
    """
    if args.command == 'init':
        docker_init(container=args.container, defaults=args.defaults)

    elif args.command == 'start':
        docker_start(container=args.container)

    elif args.command == 'stop':
        docker_stop(container=args.container, boot2docker=args.boot2docker)

    elif args.command == 'status':
        docker_status()

    elif args.command == 'update':
        docker_update(container=args.container, defaults=args.defaults)

    elif args.command == 'remove':
        docker_remove(container=args.container)

    elif args.command == 'ip':
        docker_ip()

    elif args.command == 'restart':
        docker_restart(container=args.container)


def syncstores_command(args):
    """
    Sync persistent stores.
    """
    # Get the path to manage.py
    manage_path = get_manage_path(args)

    # This command is a wrapper for a custom Django manage.py method called syncstores.
    # See tethys_apps.mangement.commands.syncstores
    process = ['python', manage_path, 'syncstores']

    if args.refresh:
        valid_inputs = ('y', 'n', 'yes', 'no')
        no_inputs = ('n', 'no')
        proceed = raw_input('{1}WARNING:{2} You have specified the database refresh option. This will drop all of the '
                            'databases for the following apps: {0}. This could result in significant data loss and '
                            'cannot be undone. Do you wish to continue? (y/n): '.format(', '.join(args.app),
                                                                                        TerminalColors.WARNING,
                                                                                        TerminalColors.ENDC)).lower()

        while proceed not in valid_inputs:
            proceed = raw_input('Invalid option. Do you wish to continue? (y/n): ').lower()

        if proceed not in no_inputs:
            process.extend(['-r'])
        else:
            print('Operation cancelled by user.')
            exit(0)

    if args.firsttime:
        process.extend(['-f'])

    if args.database:
        process.extend(['-d', args.database])

    if args.app:
        process.extend(args.app)

    try:
        subprocess.call(process)
    except KeyboardInterrupt:
        pass


def tethys_command():
    """
    Tethys commandline interface function.
    """
    # Create parsers
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(title='Commands')

    # Setup scaffold command
    scaffold_parser = subparsers.add_parser('scaffold', help='Create a new Tethys app project from a scaffold.')
    scaffold_parser.add_argument('name', help='The name of the new Tethys app project to create. Only lowercase '
                                              'letters, numbers, and underscores allowed.')
    scaffold_parser.set_defaults(func=scaffold_command)

    # Setup generate command
    gen_parser = subparsers.add_parser('gen', help='Aids the installation of Tethys by automating the '
                                                   'creation of supporting files.')
    gen_parser.add_argument('type', help='The type of object to generate.', choices=VALID_GEN_OBJECTS)
    gen_parser.add_argument('-d', '--directory', help='Destination directory for the generated object.')
    gen_parser.set_defaults(func=generate_command)

    # Setup start server command
    manage_parser = subparsers.add_parser('manage', help='Management commands for Tethys Platform.')
    manage_parser.add_argument('command', help='Management command to run.',
                               choices=[MANAGE_START, MANAGE_SYNCDB, MANAGE_COLLECTSTATIC, MANAGE_COLLECTWORKSPACES, MANAGE_COLLECT, MANAGE_CREATESUPERUSER])
    manage_parser.add_argument('-m', '--manage', help='Absolute path to manage.py for Tethys Platform installation.')
    manage_parser.add_argument('-p', '--port', type=str, help='Host and/or port on which to bind the development server.')
    manage_parser.set_defaults(func=manage_command)

    # Setup uninstall command
    uninstall_parser = subparsers.add_parser('uninstall', help='Uninstall an app.')
    uninstall_parser.add_argument('app', help='Name of the app to uninstall.')
    uninstall_parser.set_defaults(func=uninstall_command)

    # Sync stores command
    syncstores_parser = subparsers.add_parser('syncstores', help='Management command for App Persistent Stores.')
    syncstores_parser.add_argument('app', help='Name of the target on which to perform persistent store sync OR "all" '
                                               'to sync all of them.',
                                   nargs='+')
    syncstores_parser.add_argument('-r', '--refresh',
                                   help='When called with this option, the tables will be dropped prior to syncing'
                                        ' resulting in a refreshed database.',
                                   action='store_true',
                                   dest='refresh')
    syncstores_parser.add_argument('-f', '--firsttime',
                                   help='Call with this option to force the initializer functions to be executed with '
                                        '"first_time" parameter True.',
                                   action='store_true',
                                   dest='firsttime')
    syncstores_parser.add_argument('-d', '--database', help='Name of database to sync.')
    syncstores_parser.add_argument('-m', '--manage', help='Absolute path to manage.py for Tethys Platform installation.')
    syncstores_parser.set_defaults(func=syncstores_command, refresh=False, firstime=False)

    # Setup the docker commands
    docker_parser = subparsers.add_parser('docker', help="Management commands for the Tethys Docker containers.")
    docker_parser.add_argument('command',
                               help='Docker command to run.',
                               choices=['init', 'start', 'stop', 'status', 'update', 'remove', 'ip', 'restart'])
    docker_parser.add_argument('-d', '--defaults',
                               action='store_true',
                               dest='defaults',
                               help="Run command without prompting without interactive input, using defaults instead.")
    docker_parser.add_argument('-c', '--container',
                               help="Execute the command only on the given container.",
                               choices=[POSTGIS_INPUT, GEOSERVER_INPUT, N52WPS_INPUT])
    docker_parser.add_argument('-b', '--boot2docker',
                               action='store_true',
                               dest='boot2docker',
                               help="Stop boot2docker on container stop. Only applicable to stop command.")
    docker_parser.set_defaults(func=docker_command)

    # Parse the args and call the default function
    args = parser.parse_args()
    args.func(args)