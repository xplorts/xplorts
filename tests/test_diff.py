"""
Unit tests for module diff

If run as a script, the tests are run

@author: Todd Bailey
"""

MODULE_NAME = "xplorts.diff"
OPTIONS = "-d date -b industry -i oph gva hours"
DATA = ["oph 2022Q4.csv", "oph 2023Q1.csv"]


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
