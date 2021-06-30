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
This file contains functionalities for kernel related costs.
See `here <https://www.doi.org/10.1007/s10462-012-9369-4>`_ for a review.
"""
from pennylane import numpy as np
import pennylane as qml
from ..utils import frobenius_inner_product
from .utils import square_kernel_matrix
from .utils import task_weights


def polarity(
    X,
    Y,
    kernel,
    assume_normalized_kernel=False,
    rescale_class_labels=True,
    normalize=False,
):
    r"""Polarity of a given kernel function.

    For a dataset with feature vectors :math:`\{x_i\}` and associated labels :math:`\{y_i\}`,
    the polarity of the kernel function :math:`k` is given by

    .. math ::

        \operatorname{P}(k) = \sum_{i,j=1}^n y_i y_j k(x_i, x_j)

    If the dataset is unbalanced, that is if the numbers of datapoints in the
    two classes :math:`n_+` and :math:`n_-` differ,
    ``rescale_class_labels=True`` will apply a rescaling according to
    :math:`\tilde{y}_i = \frac{y_i}{n_{y_i}}`. This is activated by default
    and only results in a prefactor that depends on the size of the dataset
    for balanced datasets.

    The keyword argument ``assume_normalized_kernel`` is passed to
    :func:`~.kernels.square_kernel_matrix`, for the computation
    :func:`~.utils.frobenius_inner_product` is used.

    Args:
        X (list[datapoint]): List of datapoints.
        Y (list[float]): List of class labels of datapoints, assumed to be either -1 or 1.
        kernel ((datapoint, datapoint) -> float): Kernel function that maps datapoints to kernel value.
        assume_normalized_kernel (bool, optional): Assume that the kernel is normalized, i.e.
            the kernel evaluates to 1 when both arguments are the same datapoint.
        rescale_class_labels (bool, optional): Rescale the class labels. This is important to take
            care of unbalanced datasets.
        normalize (bool): If True, rescale the polarity to the target_alignment.

    Returns:
        float: The kernel polarity.

    **Example:**

    Consider a simple kernel function based on :class:`~.templates.embeddings.AngleEmbedding`:

    .. code-block :: python

        dev = qml.device('default.qubit', wires=2, shots=None)
        @qml.qnode(dev)
        def circuit(x1, x2):
            qml.templates.AngleEmbedding(x1, wires=dev.wires)
            qml.adjoint(qml.templates.AngleEmbedding)(x2, wires=dev.wires)
            return qml.probs(wires=dev.wires)

        kernel = lambda x1, x2: circuit(x1, x2)[0]

    We can then compute the polarity on a set of 4 (random) feature
    vectors ``X`` with labels ``Y`` via

    >>> X = np.random.random((4, 2))
    >>> Y = np.array([-1, -1, 1, 1])
    >>> qml.kernels.polarity(X, Y, kernel)
    tensor(0.04361349, requires_grad=True)
    """
    K = square_kernel_matrix(X, kernel, assume_normalized_kernel=assume_normalized_kernel)

    if rescale_class_labels:
        nplus = np.count_nonzero(np.array(Y) == 1)
        nminus = len(Y) - nplus
        _Y = np.array([y / nplus if y == 1 else y / nminus for y in Y])
    else:
        _Y = np.array(Y)

    T = np.outer(_Y, _Y)

    return frobenius_inner_product(K, T, normalize=normalize)


def target_alignment(
    X,
    Y,
    kernel,
    assume_normalized_kernel=False,
    rescale_class_labels=True,
):
    r"""Target alignment of a given kernel function.

    This function is an alias for :func:`~.kernels.polarity` with ``normalize=True``.

    For a dataset with feature vectors :math:`\{x_i\}` and associated labels :math:`\{y_i\}`, the
    target alignment of the kernel function :math:`k` is given by

    .. math ::

        \operatorname{TA}(k) = \frac{\sum_{i,j=1}^n y_i y_j k(x_i, x_j)}
        {\sqrt{\sum_{i,j=1}^n y_i y_j} \sqrt{\sum_{i,j=1}^n k(x_i, x_j)^2}}

    If the dataset is unbalanced, that is if the numbers of datapoints in the
    two classes :math:`n_+` and :math:`n_-` differ,
    ``rescale_class_labels=True`` will apply a rescaling according to
    :math:`\tilde{y}_i = \frac{y_i}{n_{y_i}}`. This is activated by default
    and only results in a prefactor that depends on the size of the dataset
    for balanced datasets.

    Args:
        X (list[datapoint]): List of datapoints
        Y (list[float]): List of class labels of datapoints, assumed to be either -1 or 1.
        kernel ((datapoint, datapoint) -> float): Kernel function that maps datapoints to kernel value.
        assume_normalized_kernel (bool, optional): Assume that the kernel is normalized, i.e.
            the kernel evaluates to 1 when both arguments are the same datapoint.
        rescale_class_labels (bool, optional): Rescale the class labels. This is important to take
            care of unbalanced datasets.

    Returns:
        float: The kernel-target alignment.

    **Example:**

    Consider a simple kernel function based on :class:`~.templates.embeddings.AngleEmbedding`:

    .. code-block :: python

        dev = qml.device('default.qubit', wires=2, shots=None)
        @qml.qnode(dev)
        def circuit(x1, x2):
            qml.templates.AngleEmbedding(x1, wires=dev.wires)
            qml.adjoint(qml.templates.AngleEmbedding)(x2, wires=dev.wires)
            return qml.probs(wires=dev.wires)

        kernel = lambda x1, x2: circuit(x1, x2)[0]

    We can then compute the kernel-target alignment on a set of 4 (random)
    feature vectors ``X`` with labels ``Y`` via

    >>> X = np.random.random((4, 2))
    >>> Y = np.array([-1, -1, 1, 1])
    >>> qml.kernels.target_alignment(X, Y, kernel)
    tensor(0.01124802, requires_grad=True)

    We can see that this is equivalent to using ``normalize=True`` in
    ``polarity``:

    >>> target_alignment = qml.kernels.target_alignment(X, Y, kernel)
    >>> normalized_polarity = qml.kernels.polarity(X, Y, kernel, normalize=True)
    >>> np.isclose(target_alignment, normalized_polarity)
    tensor(True, requires_grad=True)
    """
    return polarity(
        X,
        Y,
        kernel,
        assume_normalized_kernel=assume_normalized_kernel,
        rescale_class_labels=rescale_class_labels,
        normalize=True,
    )


def task_model_alignment(
    N,
    task_weights,
    kernel_evals,
):
    r"""Task-model alignment for a given kernel function as proposed in [].

    This function measures how much of the target function producing a supervised dataset is
    captured in the kernel's first :math:`N` eigenvalues. More colloquially, it measures how much the basis functions
    available to the kernel are used by the target function that we seek to learn with the kernel.

    Let :math:`w_k` be the task weights for the target function that produced a supervised dataset as specified
    by the :doc:`pennylane.kernels.utils.task_weights` function, and :math:`\lambda_k` the eigenvalues of the kernel
    used to compute these weights. The task-model alignment is defined as:

    .. math::

        C(l) = \frac{\sum_{k \leq N} w_k^2 \lambda_k}{\sum_{k} w_k^2 \lambda_k}.

    Evidence put forward in Ref [] and other papers shows that this alignment is closely related to the generalization
    error of a kernel method.

    Args:
        N (int): compute the task-model alignment for components up this index; has to be smaller or equal to the
            number of data points

    Returns:
        float: The task-model alignment of the kernel on the dataset.

    **Example:**

    Consider a simple kernel function based on :class:`~.templates.embeddings.AngleEmbedding`:

    .. code-block :: python

        dev = qml.device('default.qubit', wires=2, shots=None)

        @qml.qnode(dev)
        def kernel(x1, x2):
            qml.templates.AngleEmbedding(x1, wires=dev.wires)
            qml.adjoint(qml.templates.AngleEmbedding)(x2, wires=dev.wires)
            return qml.expval(qml.Projector([0, 0]), wires=[0, 1]))

    We can then compute the task-model alignment on a set of 4 (random)
    feature vectors ``X`` via

    >>> X = np.random.random((4, 2))
    >>> qml.kernels.task_model_alignment(X, kernel)
    tensor(...)

    """
    numerator = qml.math.dot(task_weights[:N], kernel_evals[:N])
    denominator = qml.math.dot(task_weights, kernel_evals)
    return numerator / denominator
