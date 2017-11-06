#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

from dropbox import dropbox
from dropbox import exceptions
from dropbox import files

def command(login_required=True):
    """a decorator for handling authentication and exceptions"""
    def decorate(f):
        def wrapper(self, args):
            if login_required and self.api_client is None:
                self.stdout.write("Please 'login' to execute this command\n")
                return

            try:
                return f(self, *args)
            except TypeError as e:
                print(str(e))
            except exceptions.ApiError as e:
                #print("e:", e)
                #print("e.request_id:", e.request_id)
                #print("e.user_message_text:", e.user_message_text)
                msg = e.user_message_text or str(e)
                print('Error: %s' % msg)
                #print(e.error.get_path())

        wrapper.__doc__ = f.__doc__
        return wrapper
    return decorate

class DropboxCommand():
    TOKEN_FILE = "token_store.txt"

    def __init__(self, access_token = TOKEN_FILE):
        self.current_path = ''
        self.api_client = None
        try:
            if os.path.isfile(access_token):
                access_token = open(access_token).read()
            self.api_client = dropbox.Dropbox(access_token)
            print("[loaded OAuth 2 access token]")
        except:
            pass

    @command()
    def do_cd(self, path):
        """change current working directory"""
        self.current_path = self.change_path(self.current_path, path)

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
        self.api_client.files_download_to_file(os.path.expanduser(to_path), self.get_path(from_path))

    @command()
    def do_put(self, from_path, to_path):
        """
        Copy local file to Dropbox

        Examples:
        put ~/test.txt dropbox-copy-test.txt
        """
        from_file = open(os.path.expanduser(from_path), "rb")
        self.api_client.files_upload(from_file, self.get_path(to_path), mode=files.WriteMode.overwrite)

    @command()
    def do_mkdir(self, path):
        """create a new directory"""
        self.api_client.files_create_folder(self.get_path(path))

    @command()
    def do_rm(self, path):
        """delete a file or directory"""
        self.api_client.files_delete(self.get_path(path))

    @command()
    def do_mv(self, from_path, to_path):
        """move/rename a file or directory"""
        self.api_client.files_move(self.get_path(from_path), self.get_path(to_path))

    @command()
    def do_share(self, path):
        """Create a link to share the file at the given path."""
        url = self.api_client.sharing_create_shared_link(self.get_path(path))
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

    @command(login_required=False)
    def do_help(self):
        #Find every "do_" attribute with a non-empty docstring and print
        #out the docstring.
        """show this text"""
        all_names = dir(self)
        cmd_names = []
        for name in all_names:
            if name[:3] == 'do_':
                cmd_names.append(name[3:])
        cmd_names.sort()
        for cmd_name in cmd_names:
            f = getattr(self, 'do_' + cmd_name)
            if f.__doc__:
                print('%s: %s' % (cmd_name, f.__doc__))

    def run_cmd(self, args):
        try:
            f = getattr(self, 'do_' + args[0])
        except:
            print('*** Unknown command: %s' % args[0])
            return
        f(args[1:])

    def run_file(self, path):
        f = open(path, mode='rt')
        for line in f:
            args = line.split()
            self.run_cmd(args)
        f.close()

    def parse_args(self, args):
        if len(args) == 1 and os.path.exists(args[0]):
            self.run_file(args[0])
        else:
            self.run_cmd(args)

    def get_path(self, path):
        return self.change_path(self.current_path, path)

    def change_path(self, from_path, to_path):
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

def main():
    if len(sys.argv) > 1:
        dc = DropboxCommand()
        print(dc)
        dc.parse_args(sys.argv[1:])

if __name__ == '__main__':
    main()