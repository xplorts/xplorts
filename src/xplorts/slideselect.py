"""
Combined select and slider widget with support for javascript linking

Classes
-------
SlideSelect
    Combined select and slider widget with support for javascript linking

Functions
---------
flexi_method
    Return an instance method for a container or its first child
"""

# =============================================================================
# To do
# Allow options from dict
#
# Suppress hover display on slider
#
# =============================================================================

from bokeh.models import Column, CustomJS, Div, Select, Slider
from bokeh.layouts import column, row
from bokeh.io import show

from xplorts.ghostbokeh import GhostBokeh

#%%

class SlideSelect(GhostBokeh, Column):
    """
    A bokeh combination widget that can be linked to Javascript callbacks

    Includes support for options that are strings, or dictionaries
    that map to strings.

    This class helps to create interactive objects with Bokeh, but does not
    sync with those objects after they go live in a browser.

    Properties
    -------
    handle
        An object that can be linked to Javascript for interactively
        responding to changes in the selected value. Read-only.

    options: list
        List of select options.  Read-only.

    value: str
        Selected value.  Read/write.  Does not sync with the widget after it
        goes live in a browser.
    """

    #_js_option_array = None

    def __new__(cls, options, *args, title="Selection", **kwargs):
        option_keys = (
            list(options.keys()) if isinstance(options, dict)
            else options
        )

        bk_select = Select(options=option_keys, value=option_keys[0], title=title)
        bk_slider = Slider(start=0, end=len(options)-1, value=0, step=1, title=None)

        # Link select option to slider value.
        bk_select.js_on_change('value',
            CustomJS(args={"other": bk_slider},
                     code="other.value = this.options.indexOf(this.value) \n" \
                         + "console.log('Linking select to slider, ' + this.value + ' => ' + other.value)"
            )
        )

        # Link slider value to select option.
        bk_slider.js_on_change('value',
            CustomJS(args={"other": bk_select},
                     code="other.value = other.options[this.value] \n" \
                         + "console.log('Linking slider to other, ' + this.value + ' => ' + other.value)"
            )
        )

        children = [
            bk_select,
            bk_slider
        ]

        # Make a bokeh layout, and coerce the class type.
        obj = column(*args, children=children, **kwargs)  # Force consistent child sizing.
        obj.__class__ = cls

        # Use bokeh model for Column to generate javascript to display this object.
        obj.__qualified_model__ = "Column"

        return obj

    def __init__(self, options, *args, **kwargs):
        """
        Creates a subclass of Bokeh Column that contains a drop-down select
        widget and a slider widget for a common set of options.

        Parameters
        ----------
        options : dict, or iterable
            Options to be assigned to the browser-side `_js_option_array`.

        args, kwargs
            Other other arguments are used by `__new__`.
        """
        option_values = (
            list(options.values()) if isinstance(options, dict)
            else options
        )
        self._js_option_array = option_values


    @property
    def _js_value_str(self):
        """
        Javascript code snippet to retrieve selected value

        The selected value is placed in X_value, where X is
        the `.name` attribute of the selection widget.
        """
        if self._js_option_array is None:
            js_code = f"const {self.name}_value = {self.name}.value"
        else:
            js_code = f"""
                const {self.name}_lookup = {self._js_option_array}
                const {self.name}_value = {self.name}_lookup[{self.name}.value]
            """
        return js_code

    @property
    def handle(self):
        """
        Object that can be linked to Javascript for standalone interactivity
        """
        return self.children[0]

    @property
    def options(self):
        """
        List of options available for selection.
        """
        return self.handle.options

    @property
    def value(self):
        """
        Selected value.  Read/write.  Does not sync with the widget after it
        goes live in a browser.
        """
        return self.handle.value

    @value.setter
    def value(self, value):
        """Set server-side widget value"""
        bk_select, bk_slider = self.children
        bk_slider.value = bk_select.options.index(value)
        bk_select.value = value

## Define js_link() et al to access properties of select widget if necessary.

def flexi_method(method_name):
    """
    Return an instance method that applies a named method flexibly

    Parameters
    ----------
    method_name: str
        Method to apply.

    Return
    ------
    Instance method, with signature (self, *args, **kwargs).

        The named method is sought first in the instance's super-class.
        If not found in the super-class, or if found but it returns a
        ValueError, then the named method is sought in the first of the
        instance's .children.

    Examples
    --------
    class MyClass(Column):
        js_link = flexi_method("js_link")


    """
    def wrapper(self, *args, **kwargs):
        try:
            # Apply method to whole container, if possible.
            super_class = super(type(self), self)
            result = getattr(super_class, method_name)(*args, **kwargs)
        except (ValueError, AttributeError):
            # Apply to select widget.
            result = getattr(self.children[0], method_name)(*args, **kwargs)
        return result
    return wrapper

# Monkey patch SlideSelect.js_*() methods.
# js_methods = [method for method in dir(SlideSelect) if method.startswith("js_")]
js_methods = ["js_link", "js_on_change", "js_on_event"]
for method_name in js_methods:
    setattr(SlideSelect, method_name, flexi_method(method_name))


#%% Move to test?

if False:
    ss = SlideSelect(options=["a", "b", "c"])

    result = Div(
        text="""
            <p>?</p>
            """,
        width=200,
        height=30,
    )
    ss.js_link("value", result, "text")

    show(row(ss, result))


    get_ipython().magic('pinfo ss.js_on_change')

