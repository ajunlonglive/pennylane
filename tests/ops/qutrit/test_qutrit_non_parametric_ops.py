# Copyright 2018-2022 Xanadu Quantum Technologies Inc.

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
Unit tests for the available non-parametric qutrit operations
"""
import pytest
import copy
import numpy as np
from scipy.stats import unitary_group

import pennylane as qml
from pennylane.wires import Wires

from gate_data import OMEGA, TSHIFT, TCLOCK, TADD, TSWAP, TH

NON_PARAMETRIZED_OPERATIONS = [
    (qml.TShift, TSHIFT, None),
    (qml.TClock, TCLOCK, None),
    (qml.TAdd, TADD, None),
    (qml.TSWAP, TSWAP, None),
    (qml.THadamard, TH, None),
    (qml.THadamard, np.array([[1, 1, 0], [1, -1, 0], [0, 0, np.sqrt(2)]]) / np.sqrt(2), [0, 1]),
    (qml.THadamard, np.array([[1, 0, 1], [0, np.sqrt(2), 0], [1, 0, -1]]) / np.sqrt(2), [0, 2]),
    (qml.THadamard, np.array([[np.sqrt(2), 0, 0], [0, 1, 1], [0, 1, -1]]) / np.sqrt(2), [1, 2]),
]

subspace_error_data = [
    ([1, 1], "Elements of subspace list must be unique."),
    ([1, 2, 3], "The subspace must be a sequence with"),
    ([3, 1], "Elements of the subspace must be 0, 1, or 2."),
    ([3, 3], "Elements of the subspace must be 0, 1, or 2."),
    ([1], "The subspace must be a sequence with"),
    (0, "The subspace must be a sequence with two unique"),
]


# TODO: Add tests for testing that the decomposition of non-parametric ops is correct


class TestOperations:
    @pytest.mark.parametrize("op_cls, mat, subspace", NON_PARAMETRIZED_OPERATIONS)
    def test_nonparametrized_op_copy(self, op_cls, mat, subspace, tol):
        """Tests that copied nonparametrized ops function as expected"""
        op = (
            op_cls(wires=range(op_cls.num_wires))
            if subspace is None
            else op_cls(wires=range(op_cls.num_wires), subspace=subspace)
        )
        copied_op = copy.copy(op)
        np.testing.assert_allclose(op.matrix(), copied_op.matrix(), atol=tol)

        op._inverse = True
        copied_op2 = copy.copy(op)
        np.testing.assert_allclose(op.matrix(), copied_op2.matrix(), atol=tol)

    @pytest.mark.parametrize("ops, mat, subspace", NON_PARAMETRIZED_OPERATIONS)
    def test_matrices(self, ops, mat, subspace, tol):
        """Test matrices of non-parametrized operations are correct"""
        op = (
            ops(wires=range(ops.num_wires))
            if subspace is None
            else ops(wires=range(ops.num_wires), subspace=subspace)
        )
        res_static = (
            op.compute_matrix() if subspace is None else op.compute_matrix(subspace=subspace)
        )
        res_dynamic = op.matrix()
        assert np.allclose(res_static, mat, atol=tol, rtol=0)
        assert np.allclose(res_dynamic, mat, atol=tol, rtol=0)

    @pytest.mark.parametrize("subspace, err_msg", subspace_error_data)
    @pytest.mark.parametrize("op_cls", [qml.THadamard])
    def test_subspace_op_errors(self, op_cls, subspace, err_msg):
        """Test that the correct errors are raised when subspace is incorrectly defined"""

        with pytest.raises(ValueError, match=err_msg):
            op = op_cls(wires=range(op_cls.num_wires), subspace=subspace)
            op.matrix()

        with pytest.raises(ValueError, match=err_msg):
            op_cls.compute_matrix(subspace=subspace)


class TestEigenval:
    def test_tshift_eigenval(self):
        """Tests that the TShift eigenvalue matches the numpy eigenvalues of the TShift matrix"""
        op = qml.TShift(wires=0)
        exp = np.linalg.eigvals(op.matrix())
        res = op.eigvals()
        assert np.allclose(res, exp)

    def test_tclock_eigenval(self):
        """Tests that the TClock eigenvalue matches the numpy eigenvalues of the TClock matrix"""
        op = qml.TClock(wires=0)
        exp = np.linalg.eigvals(op.matrix())
        res = op.eigvals()
        assert np.allclose(res, exp)

    def test_tadd_eigenval(self):
        """Tests that the TAdd eigenvalue matches the numpy eigenvalues of the TAdd matrix"""
        op = qml.TAdd(wires=[0, 1])
        exp = np.linalg.eigvals(op.matrix())
        res = op.eigvals()
        assert np.allclose(res, exp)

    def test_tswap_eigenval(self):
        """Tests that the TSWAP eigenvalue matches the numpy eigenvalues of the TSWAP matrix"""
        op = qml.TSWAP(wires=[0, 1])
        exp = np.linalg.eigvals(op.matrix())
        res = op.eigvals()
        assert np.allclose(res, exp)


period_three_ops = [
    qml.TShift(wires=0),
    qml.TClock(wires=0),
    qml.TAdd(wires=[0, 1]),
]

period_two_ops = [
    qml.TSWAP(wires=[0, 1]),
    qml.THadamard(wires=0, subspace=[0, 1]),
    qml.THadamard(wires=0, subspace=[0, 2]),
    qml.THadamard(wires=0, subspace=[1, 2]),
]

no_pow_method_ops = [
    qml.THadamard(wires=0, subspace=None),
]


class TestPowMethod:
    @pytest.mark.parametrize("op", period_three_ops)
    @pytest.mark.parametrize("offset", (-6, -3, 0, 3, 6))
    def test_period_three_pow(self, op, offset):
        """Tests that ops with period == 3 behave correctly when raised to various
        integer powers"""

        # When raising to power == 0 mod 3
        assert len(op.pow(0 + offset)) == 0

        # When raising to power == 1 mod 3
        op_pow_1 = op.pow(1 + offset)[0]
        assert op_pow_1.__class__ is op.__class__
        assert np.allclose(op_pow_1.matrix(), op.matrix())
        assert op_pow_1.inverse == False

        # When raising to power == 2 mod 3
        op_pow_2 = op.pow(2 + offset)[0]
        assert op_pow_2.__class__ is op.__class__
        assert np.allclose(op.matrix().conj().T, op_pow_2.matrix())
        assert op_pow_2.inverse == True

    @pytest.mark.parametrize("op", period_three_ops + period_two_ops)
    def test_period_two_three_noninteger_power(self, op):
        """Test that ops with a period of 2 or 3 raised to a non-integer power raise an error"""
        with pytest.raises(qml.operation.PowUndefinedError):
            op.pow(1.234)

    @pytest.mark.parametrize("offset", [0, 2, -2, 4, -4])
    @pytest.mark.parametrize("op", period_two_ops)
    def test_period_two_pow(self, offset, op):
        """Tests that ops with period == 2 behave correctly when raised to various
        integer powers"""

        assert len(op.pow(0 + offset)) == 0
        assert op.pow(1 + offset)[0].__class__ is op.__class__

    @pytest.mark.parametrize("op", no_pow_method_ops)
    def test_no_pow_ops(self, op):
        assert len(op.pow(0)) == 0

        op_pow = op.pow(1)
        assert len(op_pow) == 1
        assert op_pow[0].__class__ == op.__class__

        pows = [0.1, 2, -2, -2.5]

        for pow in pows:
            with pytest.raises(qml.operation.PowUndefinedError):
                op.pow(pow)


label_data = [
    (qml.TShift(0), "TShift", "TShift⁻¹"),
    (qml.TClock(0), "TClock", "TClock⁻¹"),
    (qml.TAdd([0, 1]), "TAdd", "TAdd⁻¹"),
    (qml.TSWAP([0, 1]), "TSWAP", "TSWAP"),
    (qml.THadamard(0), "TH", "TH⁻¹"),
    (qml.THadamard(0, subspace=[0, 1]), "TH", "TH"),
]


@pytest.mark.parametrize("op, label1, label2", label_data)
def test_label_method(op, label1, label2):
    assert op.label() == label1
    assert op.label(decimals=2) == label1

    op.inv()
    assert op.label() == label2


control_data = [
    (qml.TShift(0), Wires([])),
    (qml.TClock(0), Wires([])),
    (qml.TAdd([0, 1]), Wires([0])),
    (qml.TSWAP([0, 1]), Wires([])),
    (qml.THadamard(wires=0), Wires([])),
]


@pytest.mark.parametrize("op, control_wires", control_data)
def test_control_wires(op, control_wires):
    """Test ``control_wires`` attribute for non-parametrized operations."""

    assert op.control_wires == control_wires


adjoint_ops = [  # ops that are not their own inverses
    qml.TShift(wires=0),
    qml.TClock(wires=0),
    qml.TAdd(wires=[0, 1]),
    qml.THadamard(wires=0, subspace=None),
]

involution_ops = [  # ops that are their own inverses
    qml.TSWAP(wires=[0, 1]),
    qml.THadamard(wires=0, subspace=[0, 1]),
    qml.THadamard(wires=0, subspace=[0, 2]),
    qml.THadamard(wires=0, subspace=[1, 2]),
]


@pytest.mark.parametrize("op", adjoint_ops)
def test_adjoint_method(op, tol):
    adj_op = copy.copy(op)
    adj_op = adj_op.adjoint()

    assert adj_op.name == op.name + ".inv"
    assert np.allclose(adj_op.matrix(), op.matrix().conj().T)


@pytest.mark.parametrize("op", involution_ops)
def test_adjoint_method_involution(op, tol):
    adj_op = copy.copy(op)
    adj_op = adj_op.adjoint()

    assert adj_op.name == op.name
    assert np.allclose(adj_op.matrix(), op.matrix())
