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
r"""
This module contains all the measurements supported by PennyLane.

Description
-----------

Measurements
~~~~~~~~~~~~
The :class:`MeasurementProcess` class serves as a base class for measurements, and is inherited
from by the :class:`SampleMeasurement`, :class:`StateMeasurement` and :class:`MeasurementTransform`
classes. These classes are subclassed to implement measurements in PennyLane.

* Each :class:`SampleMeasurement` subclass represents a sample-based measurement, which contains a
  :meth:`SampleMeasurement.process_samples` method that processes the sequence of samples generated
  by the device. This method should always have the same arguments:

  * samples (Sequence[complex]): computational basis samples generated for all wires
  * wire_order (Wires): wires determining the subspace that ``samples`` acts on
  * shot_range (tuple[int]): 2-tuple of integers specifying the range of samples to use. If not
    specified, all samples are used.
  * bin_size (int): Divides the shot range into bins of size ``bin_size``, and returns the
    measurement statistic separately over each bin. If not provided, the entire shot range is treated
    as a single bin.

  See :class:`CountsMP` for an example.

* Each :class:`StateMeasurement` subclass represents a state-based measurement, which contains a
  :meth:`StateMeasurement.process_state` method that processes the quantum state generated by the
  device. This method should always have the same arguments:

  * state (Sequence[complex]): quantum state
  * wire_order (Wires): wires determining the subspace that ``state`` acts on; a matrix of dimension
    :math:`2^n` acts on a subspace of :math:`n` wires

  See :class:`StateMP` for an example.

* Each :class:`MeasurementTransform` subclass represents a measurement process that requires
  the application of a batch transform, which contains a :meth:`MeasurementTransform.process` method
  that converts the given quantum tape into a batch of quantum tapes and executes them using the
  device. This method should always have the same arguments:

  * tape (QuantumTape): quantum tape to transform
  * device (Device): device used to transform the quantum tape

  The main difference between a :class:`MeasurementTransform` and a
  :func:`~pennylane.batch_transform` is that a batch transform is tracked by the gradient transform,
  while a :class:`MeasurementTransform` process isn't.

  See :class:`ClassicalShadowMP` for an example.

.. note::

    A measurement process can inherit from both :class:`SampleMeasurement` and
    :class:`StateMeasurement` classes, defining the needed logic to process either samples or the
    quantum state. See :class:`VarianceMP` for an example.

Differentiation
^^^^^^^^^^^^^^^
In general, a :class:`MeasurementProcess` is differentiable with respect to a parameter if the domain of
that parameter is continuous. When using the analytic method of differentiation the output of the
measurement process must be a real scalar value for it to be differentiable.

Creating custom measurements
----------------------------
A custom measurement process can be created by inheriting from any of the classes mentioned above.

The following is an example for a sample-based measurement that computes the number of samples
obtained of a given state:

.. code-block:: python

    import pennylane as qml
    from pennylane.measurements import SampleMeasurement

    class CountState(SampleMeasurement):
        def __init__(self, state: str):
            self.state = state  # string identifying the state e.g. "0101"
            wires = list(range(len(state)))
            super().__init__(wires=wires)

        def process_samples(self, samples, wire_order, shot_range, bin_size):
            counts_mp = qml.counts(wires=self._wires)
            counts = counts_mp.process_samples(samples, wire_order, shot_range, bin_size)
            return counts.get(self.state, 0)

        def __copy__(self):
            return CountState(state=self.state)

.. note::

    The ``__copy__`` method needs to be overriden when new arguments are added into the ``__init__``
    method.

The measurement process in this example uses the :func:`~pennylane.counts` function, which is a
measurement process which returns a dictionary containing the number of times each quantum
state has been sampled.

We can now execute the new measurement in a :class:`~pennylane.QNode`. Let's use a simple circuit
so that we can verify our results mathematically.

.. code-block:: python

    dev = qml.device("default.qubit", wires=1, shots=10000)

    @qml.qnode(dev)
    def circuit(x):
        qml.RX(x, wires=0)
        return CountState(state="1")

The quantum state before the measurement will be:

.. math:: \psi = R_x(\theta) \begin{bmatrix} 1 \\ 0 \end{bmatrix} = \begin{bmatrix}
                \cos(\theta/2) & -i\sin(\theta/2) \\
                -i\sin(\theta/2) & \cos(\theta/2)
            \end{bmatrix} \begin{bmatrix} 1 \\ 0 \end{bmatrix} = \begin{bmatrix}
                \cos(\theta/2) \\ -i\sin(\theta/2)
            \end{bmatrix}

When :math:`\theta = 1.23`, the probability of obtaining the state
:math:`\begin{bmatrix} 1 \\ 0 \end{bmatrix}` is :math:`\sin^2(\theta/2) = 0.333`. Using 10000 shots
we should obtain the excited state 3333 times approximately.

>>> circuit(1.23)
tensor(3303., requires_grad=True)

Given that the measurement process returns a real scalar value, we can differentiate it
using the analytic method.

We know from the previous analysis that the analytic result of the measurement process is
:math:`r(\theta) = \text{nshots} \cdot \sin^2(\theta/2)`.

The gradient of the measurement process is
:math:`\frac{\partial r}{\partial \theta} = \text{nshots} \sin(\theta/2) \cos(\theta/2)`.

When :math:`\theta = 1.23`, :math:`\frac{\partial r}{\partial \theta} = 4712.444`

>>> x = qml.numpy.array(1.23, requires_grad=True)
>>> qml.grad(circuit)(x)
4715.000000000001

.. note::

    In PennyLane we use functions to define measurements (e.g. :func:`counts`). These
    functions will return an instance of the corresponding measurement process
    (e.g. :class:`CountsMP`). This decision is just for design purposes.
"""
from .classical_shadow import ClassicalShadowMP, ShadowExpvalMP, classical_shadow, shadow_expval
from .counts import CountsMP, counts
from .expval import ExpectationMP, expval
from .measurements import (
    AllCounts,
    Counts,
    Expectation,
    MeasurementProcess,
    MeasurementShapeError,
    MeasurementTransform,
    MidMeasure,
    MutualInfo,
    ObservableReturnTypes,
    Probability,
    Sample,
    SampleMeasurement,
    Shadow,
    ShadowExpval,
    State,
    StateMeasurement,
    Variance,
    VnEntropy,
)
from .mid_measure import MeasurementValue, MeasurementValueError, MidMeasureMP, measure
from .mutual_info import MutualInfoMP, mutual_info
from .probs import ProbabilityMP, probs
from .sample import SampleMP, sample
from .state import StateMP, density_matrix, state
from .var import VarianceMP, var
from .vn_entropy import VnEntropyMP, vn_entropy
