from __future__ import (absolute_import, division, print_function)
from builtins import super
from future.utils import implements_iterator, string_types
from . import algorithms
from . import proxops
from itertools import count
from collections import namedtuple, defaultdict
from .utils import wrap, restruct, destruct
import numpy as np
import tableprint as tp
import sys
try:
    from time import perf_counter
except ImportError:
    from time import time as perf_counter


class Optimizer(object):
    def __init__(self, theta_init, display=sys.stdout):
        self.iteration = 0
        self.theta = theta_init
        self.runtimes = list()
        self.store = defaultdict(list)
        self.display = display

    def __next__(self):
        raise NotImplementedError

    def optional_print(self, message):
        if self.display:
            self.display.write(message + "\n")
            self.display.flush()

    def run(self, maxiter=None):
        maxiter = np.inf if maxiter is None else (maxiter + self.iteration)
        try:
            self.optional_print(tp.header(['Iteration', 'Objective', 'Runtime']))
            for k in count(start=self.iteration):

                self.iteration = k

                # get the next iteration, time how long it takes
                tstart = perf_counter()
                self.theta = next(self)
                self.runtimes.append(perf_counter() - tstart)

                # TODO: run callbacks
                self.store['objective'].append(self.objective(destruct(self.theta)))

                # Update display
                self.optional_print(tp.row([self.iteration,
                                    self.store['objective'][-1],
                                    tp.humantime(self.runtimes[-1])]))

                # TODO: check for convergence
                if k >= maxiter:
                    break

        except KeyboardInterrupt:
            pass

        # cleanup
        self.optional_print(tp.hr(3))
        self.optional_print(u'\u279b Final objective: {}'.format(self.store['objective'][-1]))
        self.optional_print(u'\u279b Total runtime: {}'.format(tp.humantime(sum(self.runtimes))))
        self.optional_print(u'\u279b Per iteration runtime: {} +/- {}'.format(
            tp.humantime(np.mean(self.runtimes)),
            tp.humantime(np.std(self.runtimes)),
        ))

    def restruct(self, x):
        return restruct(x, self.theta)


@implements_iterator
class GradientDescent(Optimizer):
    def __init__(self, theta_init, f_df, algorithm, options=None, proxop=None, rho=None):
        options = {} if options is None else options

        super().__init__(theta_init)
        self.objective, self.gradient = wrap(f_df, theta_init)

        if isinstance(algorithm, string_types):
            self.algorithm = getattr(algorithms, algorithm)(destruct(theta_init), **options)
        elif issubclass(algorithm, algorithms.Algorithm):
            self.algorithm = algorithm(destruct(theta_init), **options)
        else:
            raise ValueError('Algorithm not valid')

        if proxop is not None:

            assert isinstance(proxop, proxops.ProximalOperatorBaseClass), \
                "proxop must subclass the proximal operator base class"

            assert rho is not None, \
                "Must give a value for rho"

            self.proxop = proxop
            self.rho = rho

    def __next__(self):
        """
        Runs one step of the optimization algorithm

        """

        grad = self.gradient(destruct(self.theta))
        xk = self.algorithm(grad)

        if 'proxop' in self.__dict__:
            xk = destruct(self.proxop(self.restruct(xk), self.rho))

        return self.restruct(xk)


@implements_iterator
class Consensus(Optimizer):

    def __init__(self, theta_init, proxops=[], tau=(10., 2., 2.), tol=(1e-6, 1e-3)):
        """
        Proximal Consensus (ADMM)

        Parameters
        ----------
        theta_init : array_like
            Initial parameters

        proxops : list
            Proximal operators

        tau : (float, float, float)
            ADMM scheduling. The augmented Lagrangian quadratic penalty parameter,
            rho, is initialized to tau[0]. Depending on the primal and dual residuals,
            the parameter is increased by a factor of tau[1] or decreased by a factor
            of tau[2] at every iteration. (See Boyd et. al. 2011 for details)
        """

        super().__init__(theta_init)
        self.operators = proxops
        self.tau = namedtuple('tau', ('init', 'inc', 'dec'))(*tau)
        self.tol = namedtuple('tol', ('primal', 'dual'))(*tol)
        self.gradient = None

        # initialize
        self.primals = [destruct(theta_init) for _ in proxops]
        self.duals = [np.zeros_like(p) for p in self.primals]
        self.rho = self.tau.init
        # self.resid = defaultdict(list)

    def add(self, operator, *args):
        """Adds a proximal operator to the list of operators"""

        if isinstance(operator, string_types):
            op = getattr(proxops, operator)(*args)
        elif issubclass(operator, proxops.ProximalOperatorBaseClass):
            op = operator

        self.operators.append(op)

    def objective(self, theta):
        """TODO: decide what to use for the consensus objective"""
        return 0

    def __next__(self):

        # store the parameters from the previous iteration
        theta_prev = destruct(self.theta)

        # update each primal variable
        self.primals = [op(self.restruct(theta_prev - dual), self.rho).ravel()
                        for op, dual in zip(self.operators, self.duals)]

        # average primal copies
        theta_avg = np.mean(self.primals, axis=0)

        # update the dual variables (after primal update has finished)
        self.duals = [dual + primal - theta_avg
                      for dual, primal in zip(self.duals, self.primals)]

        # compute primal and dual residuals
        primal_resid = float(np.sum([np.linalg.norm(primal - theta_avg)
                                     for primal in self.primals]))
        dual_resid = len(self.operators) * self.rho ** 2 * \
            np.linalg.norm(theta_avg - theta_prev)

        # update penalty parameter according to primal and dual residuals
        # (see sect. 3.4.1 of the Boyd and Parikh ADMM paper)
        if primal_resid > self.tau.init * dual_resid:
            self.rho *= float(self.tau.inc)
        elif dual_resid > self.tau.init * primal_resid:
            self.rho /= float(self.tau.dec)

        # self.resid['primal'].append(primal_resid)
        # self.resid['dual'].append(dual_resid)
        # self.resid['rho'].append(rho)

        # check for convergence
        # if (primal_resid <= self.tol.primal) & (dual_resid <= self.tol.dual):
            # self.converged = True
            # raise StopIteration("Converged")

        return self.restruct(theta_avg)
