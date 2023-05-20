"""
Unit tests for module dblprod

If run as a script, the tests are run

@author: Todd Bailey
"""

MODULE_NAME = "xplorts.dblprod"
OPTIONS = "-d date -p lprod -v gva -l labour -b industry"
DATA = "oph annual by section.csv"


def test_dblprod(helper_class, show=False):
    """
    Run module `MODULE_NAME` with data
    """
    helpers = helper_class(__file__)
    return_code = helpers.run_script(module=MODULE_NAME, 
                                     options=OPTIONS, 
                                     data=DATA,
                                     show=show)
    # Confirm it did not fall over.
    assert return_code == 0

#%%
    
if __name__ == "__main__":
    from conftest import Helpers
    
    # Run the test function, showing the figure.
    test_dblprod(Helpers, show=True)
