# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import unittest
from unittest import mock
from unittest.mock import mock_open

from helmparser.helm import commands


class TestCommands(unittest.TestCase):
    @mock.patch("subprocess.Popen")
    def test_add_repo(self, mock_subproc_popen):
        process_mock = mock.Mock()
        attrs = {
            "communicate.return_value": ("output", "error"),
        }
        process_mock.configure_mock(**attrs)
        mock_subproc_popen.return_value = process_mock

        commands.add_repo("name", "repo")
        self.assertTrue(mock_subproc_popen.called)

    @mock.patch("subprocess.Popen")
    def test_show(self, mock_subproc_popen):
        process_mock = mock.Mock()
        attrs = {
            "communicate.return_value": ("output", "error"),
        }
        process_mock.configure_mock(**attrs)
        mock_subproc_popen.return_value = process_mock

        commands.show("subcommand", "chart", "version")
        self.assertTrue(mock_subproc_popen.called)

    @mock.patch("shutil.rmtree")
    @mock.patch("builtins.open", mock_open(read_data="data"))
    @mock.patch("os.path.isdir")
    @mock.patch("subprocess.Popen")
    def test_show_subchart(self, mock_subproc_popen, patched_isfile, rm_mock):
        patched_isfile.return_value = True
        rm_mock.return_value = "REMOVED"
        process_mock = mock.Mock()
        attrs = {
            "communicate.return_value": ("output", "error"),
        }
        process_mock.configure_mock(**attrs)
        mock_subproc_popen.return_value = process_mock

        commands.show_subchart("project_path", "repo", "subcommand", "chart", "version")
        self.assertTrue(mock_subproc_popen.called)

    @mock.patch("subprocess.Popen")
    def test_update_repos(self, mock_subproc_popen):
        process_mock = mock.Mock()
        attrs = {
            "communicate.return_value": ("output", "error"),
        }
        process_mock.configure_mock(**attrs)
        mock_subproc_popen.return_value = process_mock

        commands.update_repos()
        self.assertTrue(mock_subproc_popen.called)


if __name__ == "__main__":
    unittest.main()

    print("Everything passed")
