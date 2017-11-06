#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""module DropboxCommand"""

import sys
import os
import argparse

from dropbox import dropbox
from dropbox import exceptions
from dropbox import files

class DropboxCommandException(Exception):
    pass

def command(login_required=True):
    """a decorator for handling authentication and exceptions"""
    def decorate(f):
        def wrapper(self, args):
            if login_required and self.api_client is None:
                self.stdout.write("Please 'login' to execute this command\n")
                return
            try:
                return f(self, args)
            except TypeError as e:
                print(str(e))
            except exceptions.ApiError as e:
                msg = e.user_message_text or str(e)
                print('Error: %s' % msg)

        wrapper.__doc__ = f.__doc__
        return wrapper
    return decorate

class DropboxCommand():
    def __init__(self, access_token):
        self.current_path = ''
        self.api_client = None
        try:
            self.api_client = dropbox.Dropbox(access_token)
            print("[loaded OAuth 2 access token]")
        except:
            pass

    @command()
    def do_cd(self, path):
        """change current working directory"""
        self.current_path = self.__change_path(self.current_path, path)

    @command()
    def do_ls(self):
        """list files in current remote directory"""
        resp = self.api_client.files_list_folder(self.current_path)
        while True:
            for entrie in resp.entries:
                if isinstance(entrie, dropbox.files.FolderMetadata):
                    print('Folder: ', end = '')
                elif isinstance(entrie, dropbox.files.FileMetadata):
                    print('File: ', end = '')
                print('%s' % entrie.name)
            if resp.has_more:
                resp = self.api_client.files_list_folder_continue(resp.cursor)
            else:
                break

    @command()
    def do_get(self, from_path, to_path):
        """
        Copy file from Dropbox to local file

        Examples:
        get file.txt ~/dropbox-file.txt
        """
        self.api_client.files_download_to_file(os.path.expanduser(to_path), self.__get_path(from_path))

    @command()
    def do_put(self, from_path, to_path, writemode=files.WriteMode.overwrite):
        """
        Copy local file to Dropbox

        Examples:
        put ~/test.txt dropbox-copy-test.txt
        """
        from_file = open(os.path.expanduser(from_path), "rb")
        # files.WriteMode.overwrite
        self.api_client.files_upload(from_file, self.__get_path(to_path), mode=writemode)

    @command()
    def do_mkdir(self, path):
        """create a new directory"""
        self.api_client.files_create_folder(self.__get_path(path))

    @command()
    def do_rm(self, path):
        """delete a file or directory"""
        self.api_client.files_delete(self.__get_path(path))

    @command()
    def do_mv(self, from_path, to_path):
        """move/rename a file or directory"""
        self.api_client.files_move(self.__get_path(from_path), self.__get_path(to_path))

    @command()
    def do_share(self, path):
        """Create a link to share the file at the given path."""
        url = self.api_client.sharing_create_shared_link(self.__get_path(path))
        print(url.url)

    @command()
    def do_account_info(self):
        """display account information"""
        f = self.api_client.users_get_current_account()
        print(f)

    @command()
    def do_search(self, string):
        """Search Dropbox for filenames containing the given string."""
        print(self.current_path)
        resp = self.api_client.files_search(self.current_path, string)
        while True:
            for match in resp.matches:
                print(match)
            if resp.more:
                resp = self.api_client.files_search(self.current_path, string, resp.start)
            else:
                break

    def __get_path(self, path):
        return self.__change_path(self.current_path, path)

    def __change_path(self, from_path, to_path):
        to_path = to_path.replace('\\', '/')
        if to_path and to_path[0] == '/':
            split_path = list()
        else:
            split_path = from_path.split('/')[1:]
        # можно сразу без пустых строк: str_list = filter(None, str_list)
        for s in to_path.split('/'):
            if s == '..':
                if split_path: split_path.pop()
            elif s and s != '.':
                split_path.append(s)
        if split_path: split_path.insert(0, '')
        return '/'.join(split_path)

    def __repr__(self):
        return 'DropboxCommand(current_path={!r})'.format(
            self.current_path
        )

class ArgumentParser():
    def __init__(self, args):
        parser = self.__createParser()
        self.namespace = parser.parse_args(args)
        if self.namespace.token:            
            self.dc = DropboxCommand(self.namespace.token)
            self.parser = self.__createParser(False)
        else:
            raise DropboxCommandException("Token isn't defined")

    def run(self):
        if self.namespace.command == "cmd":
            print('cmd')
            print(vars(self.namespace))
            # print(self.namespace.file)
            cmdfile = open(self.namespace.file)
            for line in cmdfile:
                line = line.strip()
                linesplit = line.split()
                # self.parser.convert_arg_line_to_args(line)
                self.namespace = self.parser.parse_args(linesplit)
                self.run()
            cmdfile.close()
        else:
            print(vars(self.namespace))
            # print(self.namespace.command)
            # print(dir(self.namespace))

    def __createParser(self, from_argv=True):
        """create argument parser"""
        argparser = argparse.ArgumentParser(fromfile_prefix_chars='@', add_help=from_argv)
        if from_argv:
            argparser.add_argument ('-t', '--token', required=False, help='access token')
        subparsers = argparser.add_subparsers(title='commands', dest='command')

        account_info_parser = subparsers.add_parser('account_info', help='show DropBox account info')

        ls_parser = subparsers.add_parser('ls', help='show content of current directory on remote system')

        cd_parser = subparsers.add_parser('cd', help='change current directory on remote system')
        cd_parser.add_argument('path', help='path to change')

        get_parser = subparsers.add_parser('get', help='get file from remote system to local system')
        get_parser.add_argument('remote_path', help='path on remote system')
        get_parser.add_argument('local_path', help='path on local system')

        put_parser = subparsers.add_parser('put', help='put file from local system to remote system')
        put_parser.add_argument('local_path', help='path on local system')
        put_parser.add_argument('remote_path', help='path on remote system')
        put_parser.add_argument('-wm', '--writemode', choices=['add', 'overwrite', 'update'], default='overwrite', help='write mode')

        mkdir_parser = subparsers.add_parser('mkdir', help='make a directory on remote system')
        mkdir_parser.add_argument('path', help='path to create')

        mv_parser = subparsers.add_parser('mv', help='move file on remote system')
        mv_parser.add_argument('from_path', help='path to move from')
        mv_parser.add_argument('to_path', help='path to move to')

        rm_parser = subparsers.add_parser('rm', help='remove file on remote system')
        rm_parser.add_argument('path', help='path to remove')

        share_parser = subparsers.add_parser('share', help='set remove file shared')
        share_parser.add_argument('path', help='path to share')
        share_parser.add_argument('-s', '--shorturl', action='store_const', const=True, default=False)

        search_parser = subparsers.add_parser('search', help='search data on remote system')
        search_parser.add_argument('string', help='string to search')
        search_parser.add_argument('-sm', '--searchmode', choices=['filename', 'content'], default='content', help='search mode')

        cmd_parser = subparsers.add_parser('cmd', help='run command file')
        cmd_parser.add_argument('file', help='command file')

        return argparser

if __name__ == '__main__':

    try:
        parser = ArgumentParser(sys.argv[1:])
        parser.run()
    except DropboxCommandException as e:
        print(e)