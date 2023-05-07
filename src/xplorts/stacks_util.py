"""
Low level utilities for bidirectional stacked bars

Classes
-------
StackDown
    Subclass of StackRectified for stacking negative values

StackRectified
    Subclass of CustomJSExpr for conditionally stacking data columns up or down

StackUp
    Subclass of StackRectified for stacking positive values
"""

#%%

from bokeh.models import CustomJSExpr

## Imports from this package
from xplorts.ghostbokeh import GhostBokeh

#%%

class StackRectified(GhostBokeh, CustomJSExpr):
    """
    An expression for stacking data columns with values above or below a threshold 
    
    Useful for making stacked bar charts with data involving both positive and negative
    values.
    """
    
    # Define javascript code template to sum deviations above (or below) a 
    # threshold, across a
    # list of source fields.  Deviations below (or above) the threshold are
    # ignored.
    # 
    # Needs Python `format()` field `{comparator}` to be substituted
    # (e.g. by '>' or '<') to make valid JS code.
    #
    # Uses {{}} to protect JS brackets from Python .format().
    _code_template = """
        // Assume `this.data`.
        // Expect args: `fields`, `threshold`.
        console.log("> Entering {name}, fields:", fields, "threshold:", threshold);
        
        const data_length = this.data[Object.keys(this.data)[0]].length;
        const stacked_xs = new Array(data_length).fill(threshold);
        var field = "";
        var field_value = 0;
        for (var i = 0; i < data_length; i++) {{
            // Calculate stack at row `i` of `this.data`.
            for (var j = 0; j < fields.length; j++) {{
                // Add value for measure j.
                field = fields[j];
                if (field in this.data) {{
                    field_value = this.data[field][i];
                    if (field_value {comparator} threshold)
                        stacked_xs[i] += field_value - threshold;
                }} else
                  console.log("Unknown field ignored", field);
            }}
        }}
        return stacked_xs;
    """
    
    def __new__(cls, fields, min_value=None, max_value=None, **kwargs):
        # Use bokeh model for CustomJSExpr to generate javascript to display this object.
        obj = super().__new__(cls, fields, **kwargs)
        #obj.__qualified_model__ = "CustomJSExpr"
        return obj
    
    def __init__(self, fields,
                 min_value=0, max_value=None,
                 name=None,
                 **kwargs):
        if max_value is None:
            comparator = ">"
            threshold = min_value
        else:
            comparator = "<"
            threshold = max_value
        code = self._code_template.format(
            comparator=comparator,
            name=name
        )
        super().__init__(
            args=dict(fields=fields,
                      threshold=threshold),
            code=code,
            name=name,
            **kwargs
        )

## StackUp and StackDown mimic bokeh Stack, but for rectified stacks.

class StackUp(StackRectified):
    """
    A JS Expression for stacking data columns with values exceeding a threshold 
    
    Useful for making stacked bar charts with data involving both positive and negative
    values.
    """
    def __init__(self, fields,
                 min_value=0,
                 name=None,
                 **kwargs):
        if kwargs.get("max_value") is not None:
            raise ValueError(f"max_value not allowed for StackUp, was {kwargs[max_value]}")
        super().__init__(fields,
                         min_value=min_value,
                         name=name,
                         **kwargs)


class StackDown(StackRectified):
    """
    A JS Expression for stacking data columns with values below a threshold 
    
    Useful for making stacked bar charts with data involving both positive and negative
    values.
    """
    def __init__(self, fields,
                 max_value=0,
                 name=None,
                 **kwargs):
        if kwargs.get("min_value", 0) != 0:
            raise ValueError(f"min_value not allowed for StackDown, was {kwargs[min_value]}")
        super().__init__(fields,
                         max_value=max_value,
                         name=name,
                         **kwargs)

