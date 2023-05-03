#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for xplor_lprod.py

If run as a script, the tests are run

@author: Todd Bailey
"""

SCRIPT_NAME = "xplor_lprod.py"
OPTIONS = "-d date -p lprod -v gva -l labour -b industry"
DATA = "oph annual by section.csv"


def test_xplor_lprod(helper_class, show=False):
    """
    Run script `SCRIPT_NAME` with data
    """
    helpers = helper_class(__file__)
    return_code = helpers.run_script(SCRIPT_NAME, 
                                     options=OPTIONS, 
                                     data=DATA,
                                     show=show)
    # Confirm it did not fall over.
    assert return_code == 0

#%%
    
if __name__ == "__main__":
    from conftest import Helpers
    
    # Run the test function, showing the figure.
    test_xplor_lprod(Helpers, show=True)
