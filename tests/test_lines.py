#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for lines.py

If run as a script, the tests are run

@author: Todd Bailey
"""

SCRIPT_NAME = "lines.py"
OPTIONS = "-d date -l lprod gva labour -b industry"
DATA = "oph annual by section.csv"

def test_lines(helper_class, show=False):
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
    # Run the test function, showing the figure.
    #test_lines(show=True)
    pass
