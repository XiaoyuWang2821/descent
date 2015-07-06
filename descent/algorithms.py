"""
First order gradient descent algorithms
"""

from toolz.curried import curry, do, map, pipe
from descent.utils import wrap


@curry
def gd(df, x0, eta=0.1):
    """Gradient descent"""

    xk = x0
    while True:
        xk -= eta * df(xk)
        yield xk


@curry
def agd(df, x0, eta=0.1, gamma=0.1):
    """Accelerated gradient descent"""

    xk = x0
    vk = 0
    while True:

        vnext = xk - eta * df(xk)
        xk = (1-gamma) * vnext + gamma * vk
        vk = vnext

        yield xk


@curry
def loop(algorithm, f_df, x0, callbacks=[], maxiter=10000):
    """
    Main loop

    Parameters
    ----------
    algorithm : function
        A function which returns a generator that yields new iterates
        in a descent sequence (for example, any of the other functions
        in this module)

    df : function
        A function which takes one parameter (a numpy.ndarray of parameters)
        and returns the gradient of the objective at that location

    x0 : array_like
        A numpy array consisting of the initial parameters

    callbacks : [function]
        A list of functions, each which takes one parameter (the current
        parameter values as an array). These functions should have side
        effects, for example, they can log the parameters or compute the error
        in the objective and store it somewhere. Called at each iteration.

    maxiter : int
        The maximum number of iterations

    """

    obj, grad = wrap(f_df)

    opt = algorithm(grad, x0)
    funcs = list(map(do, callbacks))

    for k in range(int(maxiter)):

        # get the next iterate
        xk = next(opt)

        # get the objective and gradient and pass it to the callbacks
        data = {'f': obj(xk), 'grad': grad(xk), 'iter': k}
        pipe(data, *funcs)

    return xk
