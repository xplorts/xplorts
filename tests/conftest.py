"""
Configure unit tests for xplorts

Acknowledgements
----------------
Helpers and helpers() are informed by:
    https://stackoverflow.com/a/42156088/16327476
"""

import os
import pathlib
import pytest
import subprocess


def package_root(test_file):
    """Return package root from a unit test `__file__` attribute"""
    return pathlib.Path(test_file, '../..').resolve()


def package_src(test_file):
    """Return full pathname to xplorts src folder"""
    return package_root(test_file) / "src"


def data_file(test_file, fname):
    """Return full pathname to sample data"""
    return package_root(test_file) / "data" / fname


def py_file(test_file, fname):
    """Return full pathname to xplorts script"""
    return package_src(test_file) / "xplorts" / fname


class Helpers:
    """
    Class containing unit test helper functions
    """

    def __init__(self, test_file):
        """
        Parameters
        ----------
        test_file: str
            `__file__` attribute of the unit test script

        Examples
        --------
        # In unit test:
        def test_mytest(helper_class):
            helpers = helper_class(__file__)
            helpers.help_me()
        """

        self.test_file = test_file


    @staticmethod
    def help_me():
        """
        Sample helper function for use in unit tests
        """
        return "no"


    @property
    def package_src(self):
        return package_src(self.test_file)


    def data_file(self, fname):
        return data_file(self.test_file, fname)


    def py_file(self, fname):
        return py_file(self.test_file, fname)


    def run_script(self, *, script=None, module=None,
                   options=[], data=None, show=False):
        """
        Run script
        """
        # Use -s option to show a figure after creating it.
        OPTION_SHOW = "-s"

        assert (script is None or module is None), \
            "Conflicting script and module specifications--drop one"
        assert (script is not None or module is not None), \
            "Missing specification for script or module"

        if isinstance(script, str):
            # Make path to named script.
            script = self.py_file(script)
        elif isinstance(script, pathlib.Path):
            # Coerce Path to string.
            script = script.resolve().as_posix()

        if isinstance(module, str):
            # Insert module name into `script` string.
            script_args = ["-m", module]
        else:
            script_args = script

        if data is None:
            data = []
        elif isinstance(data, str):
            data = [data]

        # Make path to each named data file.
        data = [self.data_file(fname) for fname in data]

        if isinstance(options, str):
            # Split option string into list of options.
            options = str.split(options)

        xlp_options = data.copy()
        xlp_options.extend(options)

        if show and OPTION_SHOW not in options:
            # Use -s option to show the figure after creating it.
            xlp_options.append(OPTION_SHOW)

        # Make new environment with PYTHONPATH to our package.
        child_pythonpath = self.package_src
        if "PYTHONPATH" in os.environ:
            # Include current PYTHON_PATH.
            child_pythonpath = os.pathsep.join([
                child_pythonpath,
                os.environ["PYTHONPATH"]
            ])
        child_environ = os.environ.copy()
        child_environ["PYTHONPATH"] = child_pythonpath

        # Run python as a sub-process, directed to our script or module.
        return_code = subprocess.call(["python3",
                                       *script_args,
                                       *xlp_options,
                                      ],
                                      env=child_environ)
        return return_code


@pytest.fixture
def helper_class():
    """
    To use helper function `XX`, in a test_*.py do this:
        ```
        def test_with_help(helper_class):
            helper_class(__file__).XX()
        ```
    """
    return Helpers
