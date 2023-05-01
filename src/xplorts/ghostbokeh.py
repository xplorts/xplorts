"""
ghostbokeh
----------
Defines a mixin to build a subclass of a Bokeh class

Classes
-------
GhostBokeh
    Abstract base class mixin to build pseudo-subclass of a Bokeh class
"""

class GhostBokeh():
    """
    Abstract base class to a build pseudo-subclass of a Bokeh class
    
    Used to customise a Bokeh class, while relying on the original
    Bokeh class client-side implementation.
    
    A ghost Bokeh class is defined using multiple inheritance, where
    `GhostBokeh` is the first parent and the Bokeh class is the second
    parent in the class definition.
    
    GhostBokeh defines a `__new__()` method that invokes the parent
    method and then sets the object's `__qualified_model__` property
    to the Bokeh class.  This tells the Bokeh object compiler to use the
    client-side implementation of the existing Bokeh class.
    
    Examples
    --------
    from bokeh.models import CustomJSExpr
    class MyClass(GhostBokeh, CustomJSExpr):
        pass
    my_obj = MyClass()
    type(my_obj).__name__, my_obj.__qualified_model__
    # ('MyClass', 'CustomJSExpr')
    """
    
    def __new__(cls, *args, **kwargs):
        """
        Invokes parent __new__() and then sets `__qualified_model__` property
        
        Examines the method resolution order of the target class, and
        sets the qualified model to the name of the class that follows
        'GhostBokeh' in the resolution order.
        """
        obj = super().__new__(cls, *args, **kwargs)
        
        where_am_i = [t.__name__ for t in cls.__mro__].index("GhostBokeh")
        bokeh_parent = cls.__mro__[where_am_i + 1]
        obj.__qualified_model__ = bokeh_parent.__name__
        return obj
