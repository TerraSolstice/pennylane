# Copyright 2018-2021 Xanadu Quantum Technologies Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
This module contains functions for adding the Autograd interface
to a PennyLane Device class.
"""
import inspect

import autograd
from autograd.numpy.numpy_boxes import ArrayBox

import pennylane as qml
from pennylane import numpy as np


def execute(tapes, device, execute_fn, gradient_fn, _n=1):
    """Execute a batch of tapes with Autograd parameters on a device.

    Args:
        tapes (Sequence[.QuantumTape]): batch of tapes to execute
        device (.Device): Device to use to execute the batch of tapes.
            If the device does not provide a ``batch_execute`` method,
            by default the tapes will be executed in serial.
        execute_fn (callable): The execution function used to execute the tapes
            during the forward pass. This function must return a tuple ``(results, jacobians)``.
            If ``jacobians`` is an empty list, then ``gradient_fn`` is used to
            compute the gradients during the backwards pass.
        gradient_fn (callable): the gradient function to use to compute quantum gradients
        _n (int): a positive integer used to track nesting of derivatives, for example
            if the nth-order derivative is requested.

    Returns:
        list[list[float]]: A nested list of tape results. Each element in
        the returned list corresponds in order to the provided tapes.
    """

    parameters = autograd.builtins.tuple(
        [autograd.builtins.list(t.get_parameters()) for t in tapes]
    )

    return _execute(
        parameters,
        tapes=tapes,
        device=device,
        execute_fn=execute_fn,
        gradient_fn=gradient_fn,
        _n=_n,
    )[0]


@autograd.extend.primitive
def _execute(
    parameters, tapes=None, device=None, execute_fn=None, gradient_fn=None, _n=1
):  # pylint: disable=dangerous-default-value,unused-argument
    """Autodifferentiable wrapper around ``Device.batch_execute``.

    The signature of this function is designed to workaround Autograd restrictions.
    Note that the ``parameters`` argument is dependent on the ``tapes`` argument;
    this function should always be called as follows:

    >>> parameters = [autograd.builtins.list(t.get_parameters()) for t in tapes])
    >>> parameters = autograd.builtins.tuple(parameters)
    >>> _batch_execute(parameters, tapes=tapes, device=device)

    In particular:

    - ``parameters`` is dependent on the provided tapes: always extract them as above
    - ``tapes`` is a *required* argument
    - ``device`` is a *required* argument

    The private argument ``_n`` is used to track nesting of derivatives, for example
    if the nth-order derivative is requested. Do not set this argument unless you
    understand the consequences!
    """
    with qml.tape.Unwrap(*tapes):
        res, jacs = execute_fn(tapes)

    return [np.tensor(r) for r in res], jacs


def vjp(
    ans, parameters, tapes=None, device=None, execute_fn=None, gradient_fn=None, _n=1
):  # pylint: disable=dangerous-default-value,unused-argument
    """Returns the vector-Jacobian product operator for a batch of quantum tapes.

    Args:
        ans (array): the result of the batch tape execution
        parameters (list[list[Any]]): Nested list of the quantum tape parameters.
            This argument should be generated from the provided list of tapes.
        tapes (Sequence[.QuantumTape]): batch of tapes to execute
        device (.Device): Device to use to execute the batch of tapes.
            If the device does not provide a ``batch_execute`` method,
            by default the tapes will be executed in serial.
        execute_fn (callable): The execution function used to execute the tapes
            during the forward pass. This function must return a tuple ``(results, jacobians)``.
            If ``jacobians`` is an empty list, then ``gradient_fn`` is used to
            compute the gradients during the backwards pass.
        gradient_fn (callable): the gradient function to use to compute quantum gradients
        _n (int): a positive integer used to track nesting of derivatives, for example
            if the nth-order derivative is requested.

    Returns:
        function: this function accepts the backpropagation
        gradient output vector, and computes the vector-Jacobian product
    """

    def grad_fn(dy):
        """Returns the vector-Jacobian product with given
        parameter values p and output gradient dy"""

        dy = dy[0]
        jacs = ans[1]

        if jacs:
            # Jacobians were computed on the forward pass (accumulation="forward")
            # Simply compute the vjps classically here.
            vjps = qml.gradients._vector_jacobian_products(dy, jacs, reduction="append")

        else:
            # Need to compute the Jacobians on the backward pass (accumulation="backward")

            # Temporary: check if the gradient function is a differentiable transform.
            # For the moment, simply check if it is part of the `qml.gradients` package.
            # Longer term, we should have a way of checking this directly
            # (e.g., isinstance(gradient_fn, GradientTransform))

            if "pennylane.gradients" in inspect.getmodule(gradient_fn).__name__:

                # Generate and execute the required gradient tapes
                vjp_tapes, fn = qml.gradients.batch_vjp(tapes, dy, gradient_fn, reduction="append")

                # This is where the magic happens. Note that we call ``execute``.
                # This recursion, coupled with the fact that the gradient transforms
                # are differentiable, allows for arbitrary order differentiation.
                vjps = fn(execute(vjp_tapes, device, execute_fn, gradient_fn, _n=_n + 1))

            elif inspect.ismethod(gradient_fn) and gradient_fn.__self__ is device:
                # Gradient function is a device method.
                # Note that unlike the previous branch:
                #
                # - there is no recursion here
                # - gradient_fn is not differentiable
                #
                # so we cannot support higher-order derivatives.

                with qml.tape.Unwrap(*tapes):
                    jacs = gradient_fn(tapes)

                vjps = qml.gradients._vector_jacobian_products(dy, jacs, reduction="append")

            else:
                raise ValueError("Unknown gradient function!!!")

        return [qml.math.to_numpy(v, max_depth=_n) if isinstance(v, ArrayBox) else v for v in vjps]

    return grad_fn


autograd.extend.defvjp(_execute, vjp, argnums=[0])
