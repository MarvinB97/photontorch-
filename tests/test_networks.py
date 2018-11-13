""" networks tests """

#############
## Imports ##
#############

import torch
import pytest
import numpy as np
import photontorch as pt

from fixtures import unw, nw, tenv, fenv, det, wg, twoportnw, rnw, reck, clements

###########
## Tests ##
###########


def test_network_creation(nw):
    pass


def test_frequency_initialization(nw, fenv):
    with fenv:
        nw.initialize()


def test_network_defined_in_class_creation():
    class NewNetwork(pt.Network):
        def __init__(self):
            super(NewNetwork, self).__init__()
            self.wg1 = pt.Waveguide()
            self.wg2 = pt.Waveguide()
            self.link("wg1:1", "0:wg2")

    nw = NewNetwork()


def test_network_with_component_not_defined_creation():
    class NewNetwork(pt.Network):
        def __init__(self):
            super(NewNetwork, self).__init__()
            self.wg1 = pt.Waveguide()
            self.wg2 = pt.Waveguide()
            self.link("wg3:1", "0:wg2")

    with pytest.raises(KeyError):
        nw = NewNetwork()


def test_network_with_component_with_different_name_as_attribute():
    with pytest.raises(ValueError):
        with pt.Network() as nw:
            nw.wg = pt.Waveguide(name="wg0")


def test_ringnetwork_creation(rnw):
    pass


def test_recknetwork_creation(reck):
    pass


def test_clementsnetwork_creation(clements):
    pass


def test_termination(unw):
    unw.terminate()
    unw.terminate([pt.Source("src"), pt.Detector("det")])
    if torch.cuda.is_available():  # pragma: no cover
        unw.cuda()
        unw.terminate()


def test_untermination(unw):
    nw2 = unw.terminate().unterminate()


def test_termination_on_terminated_network(nw):
    with pytest.raises(IndexError):
        nw.terminate()


def test_cuda(nw):
    if torch.cuda.is_available():  # pragma: no cover
        nw.cuda()
        assert nw.is_cuda


def test_cpu(nw):
    if torch.cuda.is_available():  # pragma: no cover
        nw.cuda().cpu()
        assert not nw.is_cuda


def test_reinitialize(nw, tenv):
    with tenv:
        nw.initialized = False  # fake the fact that the network is uninitialized
        nw.initialize()
        assert nw.initialized


def test_initialize_on_unterminated_network(unw, tenv):
    with tenv:
        unw.initialize()
    assert not unw.initialized


def test_initializion_with_too_big_simulation_timestep(nw, tenv):
    with pytest.warns(RuntimeWarning):
        with tenv.copy(dt=1):
            nw.initialize()


def test_forward_with_uninitialized_network(nw):
    with pytest.raises(RuntimeError):
        nw(source=1)


def test_forward_with_constant_source(nw, tenv):
    with tenv:
        nw(source=1)


def test_forward_with_timesource(nw, tenv):
    with tenv:
        nw(np.random.rand(tenv.num_timesteps))


def test_forward_with_different_value_for_each_source(nw, tenv):
    with tenv:
        nw.initialize()
        nw(np.random.rand(nw.num_sources))


def test_forward_with_batch_weights(nw, tenv):
    with tenv:
        nw.initialize()
        nw(
            np.random.rand(
                tenv.num_wavelengths, tenv.num_wavelengths, nw.num_sources, 3
            )
        )


def test_forward_with_power_false(nw, tenv):
    with tenv:
        nw(1, power=False)


def test_forward_with_detector(nw, tenv, det):
    with tenv:
        nw(1, detector=det)


def test_network_connection_with_equal_ports(wg):
    with pytest.raises(IndexError):
        nw = pt.Network(components={"wg1": wg, "wg2": wg}, connections=["wg1:1:wg1:1"])


def test_network_connection_with_too_high_port_index(wg):
    with pytest.raises(ValueError):
        nw = pt.Network(components={"wg1": wg, "wg2": wg}, connections=["wg1:1:wg2:2"])


def test_twoportnetwork_creation(twoportnw):
    pass


def test_twoportnetwork_with_delays():
    C, _, _ = np.linalg.svd(
        np.random.rand(5, 5) + 1j * np.random.rand(5, 5)
    )  # random unitary matrix
    C[range(5), range(5)] = 0  # no self connections
    nw = pt.TwoPortNetwork(
        twoportcomponents=[pt.Waveguide(loss=1000) for i in range(5)],
        conn_matrix=C,
        sources_at=[1, 0, 0, 0, 0],
        detectors_at=[0, 0, 0, 0, 1],
        delays=np.random.rand(5),
    )


def test_twoportnetwork_termination(twoportnw):
    with pytest.raises(RuntimeError):
        twoportnw.terminate()
    with pytest.raises(RuntimeError):
        twoportnw.unterminate()


def test_twoportnetwork_initialiation(twoportnw, tenv):
    with tenv:
        twoportnw.initialize()


def test_network_plot(tenv, fenv):
    tnw = pt.AddDrop(
        term_in=pt.Source(),
        term_pass=pt.Detector(),
        term_add=pt.Detector(),
        term_drop=pt.Detector(),
    )

    with tenv.copy(wls=np.array([1.5, 1.55, 1.6]) * 1e-6) as env:
        tnw.initialize()

        # test time mode 1
        detected = torch.tensor(np.random.rand(env.num_timesteps), dtype=torch.float32)
        tnw.plot(detected)

        # test time mode 0
        with pytest.raises(ValueError):
            detected = torch.tensor(np.random.rand(5), dtype=torch.float32)
            tnw.plot(detected)

        # test time mode 2
        detected = np.random.rand(env.num_timesteps, tnw.num_detectors)
        tnw.plot(detected)

        # test time mode 3
        detected = np.random.rand(env.num_timesteps, env.num_wavelengths)
        tnw.plot(detected)

        # test time mode 4
        detected = np.random.rand(
            env.num_timesteps, env.num_wavelengths, tnw.num_detectors
        )
        tnw.plot(detected)

        # test time mode 5
        detected = np.random.rand(env.num_timesteps, env.num_wavelengths, 11)
        tnw.plot(detected)

        # test time mode 6
        detected = np.random.rand(
            env.num_timesteps, tnw.num_detectors, 11
        )  # this one is not covered?
        tnw.plot(detected)

        # test time mode 6
        detected = np.random.rand(
            env.num_timesteps, env.num_wavelengths, tnw.num_detectors, 11
        )
        tnw.plot(detected)

        # test time mode 7
        with pytest.raises(RuntimeError):
            detected = np.random.rand(
                env.num_timesteps, env.num_wavelengths, tnw.num_detectors, 11, 2
            )
            tnw.plot(detected)

        # test wl mode 1
        detected = np.random.rand(env.num_wavelengths)
        tnw.plot(detected)

        # test wl mode 2
        detected = np.random.rand(env.num_wavelengths, tnw.num_detectors)
        tnw.plot(detected)

        # test wl mode 3
        detected = np.random.rand(env.num_wavelengths, 11)
        tnw.plot(detected)

        # test wl mode 4
        detected = np.random.rand(env.num_wavelengths, tnw.num_detectors, 11)
        tnw.plot(detected)

        # test wl mode 5
        with pytest.raises(RuntimeError):
            detected = np.random.rand(env.num_wavelengths, tnw.num_detectors, 11, 2)
            tnw.plot(detected)


###############
## Run Tests ##
###############

if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__])
