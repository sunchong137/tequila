from tequila.circuit.circuit import QCircuit
from tequila.objective.objective import Variable, assign_variable
from tequila.circuit._gates_impl import RotationGateImpl, PowerGateImpl, QGateImpl, MeasurementImpl, \
    ExponentialPauliGateImpl, TrotterizedGateImpl
from tequila import TequilaException
import typing, numbers
from dataclasses import dataclass
from tequila.hamiltonian.qubit_hamiltonian import PauliString, QubitHamiltonian
import functools


def wrap_gate(func):
    @functools.wraps(func)
    def doit(*args, **kwargs):
        return QCircuit.wrap_gate(func(*args, **kwargs))

    return doit


@wrap_gate
def RotationGate(axis, angle, target: typing.Union[list, int], control: typing.Union[list, int] = None):
    return RotationGateImpl(axis=axis, angle=angle, target=target, control=control)


@wrap_gate
def PowerGate(name, target: typing.Union[list, int], power: bool = None, control: typing.Union[list, int] = None):
    return PowerGateImpl(name=name, power=power, target=target, control=control)


@wrap_gate
def QGate(name, target: typing.Union[list, int], control: typing.Union[list, int] = None):
    return QGateImpl(name=name, target=target, control=control)


@wrap_gate
def Rx(angle, target: typing.Union[list, int], control: typing.Union[list, int] = None):
    return RotationGateImpl(axis=0, angle=angle, target=target, control=control)


@wrap_gate
def Ry(angle, target: typing.Union[list, int], control: typing.Union[list, int] = None):
    return RotationGateImpl(axis=1, angle=angle, target=target, control=control)


@wrap_gate
def Rz(angle, target: typing.Union[list, int], control: typing.Union[list, int] = None):
    return RotationGateImpl(axis=2, angle=angle, target=target, control=control)


@wrap_gate
def X(target: typing.Union[list, int], control: typing.Union[list, int] = None, power=None):
    return initialize_power_gate(name="X", power=power, target=target, control=control)


@wrap_gate
def H(target: typing.Union[list, int], control: typing.Union[list, int] = None, power=None):
    return initialize_power_gate(name="H", power=power, target=target, control=control)


@wrap_gate
def Y(target: typing.Union[list, int], control: typing.Union[list, int] = None, power=None):
    return initialize_power_gate(name="Y", power=power, target=target, control=control)


@wrap_gate
def Z(target: typing.Union[list, int], control: typing.Union[list, int] = None, power=None):
    return initialize_power_gate(name="Z", power=power, target=target, control=control)

def initialize_power_gate(name: str, target: typing.Union[list, int], control: typing.Union[list, int] = None, power=None):
    if power is None or power in [1, 1.0]:
        return QGateImpl(name=name, target=target, control=control)
    else:
        return PowerGateImpl(name=name, power=power, target=target, control=control)

@wrap_gate
def Measurement(target, name=None):
    if name is None:
        return MeasurementImpl(name="", target=target)
    else:
        return MeasurementImpl(name=name, target=target)


@wrap_gate
def ExpPauli(paulistring: typing.Union[PauliString, str], angle, control: typing.Union[list, int] = None,
             ):
    """
    Exponentiated Pauligate:

    ExpPauli(PauliString, angle) = exp(-i* angle/2* PauliString)

    :param paulistring: given as PauliString structure or as string or dict or list
    if given as string: Format should be like X(0)Y(3)Z(2)
    if given as list: Format should be like [(0,'X'),(3,'Y'),(2,'Z')]
    if given as dict: Format should be like { 0:'X', 3:'Y', 2:'Z' }
    :param angle: the angle (will be multiplied by paulistring coefficient if there is one)
    :param control: control qubits
    :return: Gate wrapped in circuit
    """

    if isinstance(paulistring, str):
        ps = PauliString.from_string(string=paulistring)
    elif isinstance(paulistring, list):
        ps = PauliString.from_openfermion(key=list)
    elif isinstance(paulistring, dict):
        ps = PauliString(data=paulistring)
    else:
        ps = paulistring

    return ExponentialPauliGateImpl(paulistring=ps, angle=angle, control=control)


@dataclass
class TrotterParameters:
    """
        DataClass to keep Trotter Parameters together
        See circuit._gate_impl.py:TrotterizedGateImpl

        threshold: neglect terms in the given Hamiltonians if their coefficients are below this threshold
        join_components: The generators are trotterized together. If False the first generator is trotterized, then the second etc
        Note that for steps==1 as well as len(generators)==1 this has no effect
        randomize_component_order: randomize the order in the generators order before trotterizing
        randomize: randomize the trotter decomposition of each generator
    """
    threshold: float = 0.0
    join_components: bool = True
    randomize_component_order: bool = False
    randomize: bool = False


@wrap_gate
def Trotterized(generators: typing.List[QubitHamiltonian],
                steps: int,
                angles: typing.Union[typing.List[typing.Hashable], typing.List[numbers.Real], typing.List[Variable]] = None,
                control: typing.Union[list, int] = None,
                parameters: TrotterParameters = None):
    """
    :param generators: list of generators
    :param angles: coefficients for each generator
    :param steps: trotter steps
    :param control: control qubits
    :param parameters: Additional Trotter parameters, if None then defaults are used
    """

    if parameters is None:
        parameters = TrotterParameters()

    assigned_angles = [assign_variable(angle) for angle in angles]

    return TrotterizedGateImpl(generators=generators, angles=assigned_angles, steps=steps, control=control,
                               **parameters.__dict__)


"""
Convenience for Two Qubit Gates
iSWAP will only work with cirq, the others will be recompiled
"""


@wrap_gate
def SWAP(q0: int, q1: int, control: typing.Union[int, list] = None, power: float = None):
    return initialize_power_gate(name="SWAP", target=[q0, q1], control=control, power=power)


@wrap_gate
def iSWAP(q0: int, q1: int, control: typing.Union[int, list] = None):
    return initialize_power_gate(name="ISWAP", target=[q0, q1], control=control)


"""
Convenience Initialization Routines for controlled gates
All following the patern: Gate(control_qubit, target_qubit, possible_parameter)
"""


def enforce_integer(function) -> int:
    """
    Replace if we have a qubit class at some point
    :param obj:
    :return: int(obj)
    """

    def wrapper(control, target, *args, **kwargs):
        try:
            control = int(control)
        except ValueError as e:
            raise TequilaException(
                "Could not initialize gate: Conversion of input type for control-qubit failed\n" + str(e))
        try:
            target = int(target)
        except ValueError as e:
            raise TequilaException(
                "Could not initialize gate: Conversion of input type for target-qubit failed\n" + str(e))
        return function(control, target, *args, **kwargs)

    return wrapper


@enforce_integer
def CNOT(control: int, target: int) -> QCircuit:
    return X(target=target, control=control)


@enforce_integer
def CX(control: int, target: int) -> QCircuit:
    return X(target=target, control=control)


@enforce_integer
def CY(control: int, target: int) -> QCircuit:
    return Y(target=target, control=control)


@enforce_integer
def CZ(control: int, target: int) -> QCircuit:
    return Z(target=target, control=control)


@enforce_integer
def CRx(control: int, target: int, angle: float) -> QCircuit:
    return Rx(target=target, control=control, angle=angle)


@enforce_integer
def CRy(control: int, target: int, angle: float) -> QCircuit:
    return Ry(target=target, control=control, angle=angle)


@enforce_integer
def CRz(control: int, target: int, angle: float) -> QCircuit:
    return Rz(target=target, control=control, angle=angle)


if __name__ == "__main__":
    G = CRx(1, 0, 2.0)

    print(G)