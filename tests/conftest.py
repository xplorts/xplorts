"""
Configure unit tests for xplorts

Acknowledgements
----------------
Helpers and helpers() are informed by:
    https://stackoverflow.com/a/42156088/16327476
"""

import pathlib
import pytest
import subprocess


def package_root(test_file):
    """Return package root from a unit test `__file__` attribute"""
    return pathlib.Path(test_file, '../..').resolve()


def data_file(test_file, fname):
    """Return full pathname to sample data"""
    return package_root(test_file) / "data" / fname


def py_file(test_file, fname):
    """Return full pathname to xplorts script"""
    return package_root(test_file) / "src/xplorts" / fname


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
    
    
    def data_file(self, fname):
        return data_file(self.test_file, fname)
    
    
    def py_file(self, fname):
        return py_file(self.test_file, fname)
    
    
    def run_script(self, script, options, data=None, show=False):
        """
        Run script
        """
        # Use -s option to show a figure after creating it.
        OPTION_SHOW = "-s"
        
        if isinstance(script, str):
            # Make path to named script.
            script = self.py_file(script)
        
        if isinstance(data, str):
            # Make path to named data file.
            data = self.data_file(data)
        
        if isinstance(options, str):
            # Split option string into list of options.
            options = str.split(options)
            
        xlp_options = [data] if data is not None else []
        xlp_options.extend(options)
        
        if show and OPTION_SHOW not in options:
            # Use -s option to show the figure after creating it.
            xlp_options.append(OPTION_SHOW)
        
        # Run python as a sub-process, directed to our script.
        return_code = subprocess.call(["python3", 
                                       script, 
                                       *xlp_options,
                                      ])
        # Confirm it did not fall over.
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
