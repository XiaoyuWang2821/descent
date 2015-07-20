"""
Main routines for the descent package
"""

from toolz.curried import curry, juxt
from .utils import wrap


@curry
def optimize(algorithm, f_df, x0, callbacks=[], maxiter=1e3, minibatches=[]):
    """
    Main optimization loop

    Parameters
    ----------
    algorithm : function
        A function which returns a generator that yields new iterates
        in a descent sequence (for example, any of the other functions
        in this module)

    f_df : function
        A function which takes one parameter (a numpy.ndarray of parameters)
        and returns the objective and gradient at that location

    x0 : array_like
        A numpy array consisting of the initial parameters

    callbacks : list, optional
        A list of functions, each which takes one parameter (a dictionary
        containing metadata). These functions should have side effects, for
        example, they can log the parameters or update a plot with the current
        objective value. Called at each iteration.

    maxiter : int, optional
        The maximum number of iterations (Default: 1000)

    minibatches : list, optional
        Used for minibatch optimization. An optional list of data (req)

    """

    # make sure the algorithm is valid
    if minibatches:
        valid = ['sag', 'adam', 'adagrad']
        assert algorithm.func_name in valid, \
            "Minibatch algorithm must be one of: " + ", ".join(valid)

    else:
        valid = ['gdm', 'rmsprop']
        assert algorithm.func_name in valid, \
            "Full batch algorithm must be one of: " + ", ".join(valid)

    # get functions for the objective and gradient of the function
    obj, grad = wrap(f_df)

    # build the joint callback function
    callback = juxt(*callbacks)

    # run the optimizer
    for k, xk in enumerate(algorithm(grad, x0, maxiter)):

        # get the objective and gradient and pass it to the callbacks
        callback({'obj': obj(xk), 'grad': grad(xk), 'params': xk, 'iter': k})

    # return the final parameters, reshaped in the original format
    return xk
