"""
Helper interface encapsulating modified Bokeh source code for stacked bars

This module uses source code from Bokeh, with modification, to facilitate
bidirectional stacked bars in which positive values stack "up" and negative
values stack "down".

Functions
---------
double_stack
    Generate sequence of dict describing margins of stacked values

double_stack_updown
    Generate sequence of dict describing parallel positive and negative stacks

hbar_stack_updown
    Make lists of renderers for bidirectionl horizontal stacked values

stack_down
    Create a StackDown expression for stacking negative components of fields

stack_up
    Create a StackDown expression for stacking positive components of fields
    
vbar_stack_updown
    Make list of renderers for bidirectionl vertical stacked values
"""

# Acknowledge Bokeh source and retain source code copyright notice.
"""
Used here under the BSD license:
   https://github.com/bokeh/demo.bokeh.org/blob/main/LICENSE.txt


Copyright (c) 2012 - 2018, Anaconda, Inc., and Bokeh Contributors
All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer.

Redistributions in binary form must reproduce the above copyright notice,
this list of conditions and the following disclaimer in the documentation
and/or other materials provided with the distribution.

Neither the name of Anaconda nor the names of any contributors
may be used to endorse or promote products derived from this software
without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
THE POSSIBILITY OF SUCH DAMAGE.
"""
#%%

from bokeh.core.properties import expr

## Imports from this package
from xplorts.dutils import accumulate_list, pairwise
from xplorts.stacks.stacks_util import StackDown, StackUp

#%%

## stack_up() and stack_down() mimic bokeh stack(), but for rectified stacks.

def stack_up(*fields, min_value=0):
    ''' Create a ``DataSpec`` dict to generate a ``StackUp`` expression
    for a ``ColumnDataSource``.

    Examples:

        .. code-block:: python

            p.vbar(bottom=stack_up("gva", "jobs"), ...

        will generate a ``StackUp`` that sums positive values of ``"gva"`` and ``"jobs"``
        columns of a data source, and use those values as the ``bottom``
        coordinate for a ``VBar``.

    '''

    return expr(StackUp(fields=fields, min_value=min_value))

def stack_down(*fields, max_value=0):
    ''' Create a ``DataSpec`` dict to generate a ``StackDown`` expression
    for a ``ColumnDataSource``.

    Examples:

        .. code-block:: python

            p.vbar(bottom=stack_down("gva", "jobs"), ...

        will generate a ``StackDown`` that sums negative values of ``"gva"`` and ``"jobs"``
        columns of a data source, and use those values as the ``bottom``
        coordinate for a ``VBar``.

    '''

    return expr(StackDown(fields=fields, max_value=max_value))



## Reverse engineered `double_stack`, as described for Bokeh `vbar_stack()`.

def double_stack(stackers, key1, key2, **kwargs):
    """
    Generate sequence of dict describing margins of stacked values
    """
    list_generator = accumulate_list(stackers)
    for i, shorter_longer in enumerate(pairwise(list_generator)):
        shorter_list, longer_list = shorter_longer
        # If a keyword value is a list or tuple, then each call will get one
        # value from the sequence.
        other_args = {key: val[i] if isinstance(val, (list, tuple)) else val
                      for key, val in kwargs.items()
                     }
        yield {key1: shorter_list, 
               key2: longer_list,
               "name": longer_list[-1],
               **other_args}

def double_stack_updown(stackers, key1, key2, **kwargs):
    """
    Generate sequence of dict describing margins of birectional stacked values
    """
    for dstack in double_stack(stackers, key1, key2, **kwargs):
        for wrapper in (stack_up, stack_down):
            wrapped_keys = {
                key1: wrapper(*dstack[key1]),
                key2: wrapper(*dstack[key2])
            }
            dstack_wrapped = {**dstack, **wrapped_keys}
            yield dstack_wrapped


#%%
# hbar_stack_updown and vbar_stack_updown are derived from Bokeh Figure.hbar_stack
# and Figure.vbar_stack.
# https://docs.bokeh.org/en/latest/_modules/bokeh/plotting/_figure.html#figure.hbar_stack
# "Copyright (c) 2012 - 2018, Anaconda, Inc., and Bokeh Contributors"
# Used here under the BSD license:
#   https://github.com/bokeh/demo.bokeh.org/blob/main/LICENSE.txt


def hbar_stack_updown(fig, stackers, **kw):
    ''' Generate multiple ``HBar`` renderers for positive levels stacked bottom
    to top, and negative levels stacked bottom to top.

    Args:
        stackers (seq[str]) : a list of data source field names to stack
            successively for ``left`` and ``right`` bar coordinates.

            Additionally, the ``name`` of the renderer will be set to
            the value of each successive stacker (this is useful with the
            special hover variable ``$name``)

    Any additional keyword arguments are passed to each call to ``hbar``.
    If a keyword value is a list or tuple, then each call will get one
    value from the sequence.

    Returns:
        list[GlyphRenderer]

    Examples:

        Assuming a ``ColumnDataSource`` named ``source`` with columns
        *2016* and *2017*, then the following call to ``hbar_stack_updown`` will
        will create four ``HBar`` renderers that stack right and/or left:

        .. code-block:: python

            hbar_stack_updown(p, ['2016', '2017'], x=10, width=0.9, color=['blue', 'red'], source=source)

        This is equivalent to the following two separate calls:

        .. code-block:: python

            p.hbar(left=stack_up(),         right=stack_up('2016'),           x=10, width=0.9, color='blue', source=source, name='2016')
            p.hbar(left=stack_up('2016'),   right=stack_up('2016', '2017'),   x=10, width=0.9, color='red',  source=source, name='2017')
            p.hbar(left=stack_down(),       right=stack_down('2016'),         x=10, width=0.9, color='blue', source=source, name='2016')
            p.hbar(left=stack_down('2016'), right=stack_down('2016', '2017'), x=10, width=0.9, color='red',  source=source, name='2017')

    '''
    hbar_arg_list = double_stack_updown(stackers, "left", "right", **kw)
    result = [fig.hbar(**hbar_args) for hbar_args in hbar_arg_list]
    return result


# Derived from Bokeh Figure.vbar_stack().
# https://docs.bokeh.org/en/latest/_modules/bokeh/plotting/_figure.html#figure.vbar_stack
# "Copyright (c) 2012 - 2018, Anaconda, Inc., and Bokeh Contributors"
# Used here under the BSD license:
#   https://github.com/bokeh/demo.bokeh.org/blob/main/LICENSE.txt
def vbar_stack_updown(fig, stackers, **kw):
    ''' Generate multiple ``VBar`` renderers for positive levels stacked bottom
    to top, and negative levels stacked bottom to top.

    Args:
        stackers (seq[str]) : a list of data source field names to stack
            successively for ``bottom`` and ``top`` bar coordinates.

            Additionally, the ``name`` of the renderer will be set to
            the value of each successive stacker (this is useful with the
            special hover variable ``$name``)

    Any additional keyword arguments are passed to each call to ``vbar``.
    If a keyword value is a list or tuple, then each call will get one
    value from the sequence.

    Returns:
        list[GlyphRenderer]

    Examples:

        Assuming a ``ColumnDataSource`` named ``source`` with columns
        *2016* and *2017*, then the following call to ``vbar_stack_updown`` will
        will create four ``VBar`` renderers that stack up and/or down:

        .. code-block:: python

            vbar_stack_updown(p, ['2016', '2017'], x=10, width=0.9, color=['blue', 'red'], source=source)

        This is equivalent to the following two separate calls:

        .. code-block:: python

            p.vbar(bottom=stack_up(),       top=stack_up('2016'),         x=10, width=0.9, color='blue', source=source, name='2016')
            p.vbar(bottom=stack_up('2016'), top=stack_up('2016', '2017'), x=10, width=0.9, color='red',  source=source, name='2017')
            p.vbar(bottom=stack_down(),       top=stack_down('2016'),         x=10, width=0.9, color='blue', source=source, name='2016')
            p.vbar(bottom=stack_down('2016'), top=stack_down('2016', '2017'), x=10, width=0.9, color='red',  source=source, name='2017')

    '''
    vbar_arg_list = double_stack_updown(stackers, "bottom", "top", **kw)
    result = [fig.vbar(**vbar_args) for vbar_args in vbar_arg_list]
    return result
