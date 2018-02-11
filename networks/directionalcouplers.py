''' Ring Networks '''

#############
## Imports ##
#############

## Other
import torch
import numpy as np
from collections import OrderedDict

## Relative
from .network import Network
from ..components.terms import Source, Detector, Term
from ..components.connection import Connection
from ..components.component import Component
from ..torch_ext.autograd import block_diag
from ..torch_ext.tensor import where

#####################
## All Pass Filter ##
#####################

class DirectionalCouplerWithLength(Component):
    '''
    A directional coupler with length is a memory-containing component with 4 ports.

    It is merely a holder of a directional coupler and a waveguide, and combines both
    in a 4-port component.

    Connections
    ------------
    dircoup['ijkl']:
     k        l
      \______/
      /------\
     i        j

    Note
    ----
     * This version of a directional coupler is prefered over a wg-wg-wg-wg-dc network
       becuase it only has 4 ports in stead of 12.
     * This Component is part of the networks module, because it acts as a network.
    '''

    num_ports = 4

    def __init__(self, dircoup, wg, name=None):
        '''
        Directional Coupler initialization

        Parameters
        ----------
        dircoup : DirectionalCoupler instance without length
        wg : yields the full length and the resulting delays of the directional coupler
        '''
        Component.__init__(self, name=None)
        self.wg = wg
        self.dircoup = dircoup

    def initialize(self, env):
        ''' Initialize Component '''
        self.wg.initialize(env)
        self.dircoup.initialize(env)

    def cuda(self):
        new = self.copy()
        new.dircoup = new.dircoup.cuda()
        new.wg = new.wg.cuda()
        new.is_cuda = True
        return new

    def cpu(self):
        new = self.copy()
        new.dircoup = new.dircoup.cpu()
        new.wg = new.wg.cpu()
        new.is_cuda = False
        return new

    @property
    def delays(self):
        return torch.cat((self.wg.delays, self.wg.delays))

    @property
    def rS(self):
        ''' real part of the scattering matrix '''
        k = self.dircoup.R**0.5 # coupling
        t = (1-self.dircoup.R)**0.5 # Transmission
        rS_wg_t = self.wg.rS*t
        iS_wg_k = self.wg.iS*k
        rS = self.new_variable([[0,0,0,0],[0,0,0,0],[0,0,0,0],[0,0,0,0]])
        rS[:2,:2] = rS_wg_t # Transmission from i < - > j
        rS[2:,2:] = rS_wg_t # Transmission from k < - > l
        rS[::2,::2] = -iS_wg_k
        rS[1::2,1::2] = -iS_wg_k
        return rS

    @property
    def iS(self):
        ''' imag part of the scattering matrix '''
        k = self.dircoup.R**0.5 # coupling
        t = (1-self.dircoup.R)**0.5 # Transmission
        iS_wg_t = self.wg.iS*t
        rS_wg_k = self.wg.rS*k
        iS = self.new_variable([[0,0,0,0],[0,0,0,0],[0,0,0,0],[0,0,0,0]])
        iS[:2,:2] = iS_wg_t # Transmission from i < - > j
        iS[2:,2:] = iS_wg_t # Transmission from k < - > l
        iS[::2,::2] = rS_wg_k
        iS[1::2,1::2] = rS_wg_k
        return iS

class DirectionalCouplerNetwork(Network, Component):
    ''' A network of directional couplers.
    A directional coupler with normal port ordering is repeated periodically in a grid,
    with the ports connected by waveguides:

    Network
    -------
         1    2    3    4
        ..   ..   ..   ..
         1    1    1    1
    0 : 0 2--0 2--0 2--0 2 : 5
         3    3    3    3
         |    |    |    |
         1    1    1    1
    6 : 0 2--0 2--0 2--0 2 : 10
         3    3    3    3
        ..   ..   ..   ..
         7    8    9   11

    Legend
    ------
        0: -> term locations
        1
       0 2 -> directional coupler
        3
        -- or | -> waveguides

    Note
    ----
    Because of the connection order of the directional coupler (0<->1 and 2<->3), this
    network does not contain any loops and can thus be used as a weight matrix.
    '''
    def __init__(self, couplings, dircoup, wg, terms={}, name='dircoupnw'):
        ''' DirectionalCouplerNetwork __init__

        Arguments
        ---------
        couplings: (numpy ndarray) : Desired couplings for the grating couplers
        dircoup : DirectionalCoupler : zero length directional coupler.
        wg : Waveguide : a waveguide containing all the properties of a single directional
                         coupler arm, such as the length and the effective index.
        terms : A dictionary with source and Detector locations in the form
                terms = {3:Source(), 15:Detector(), ...}.
                any other not specified terms will be terminated by terms['default'].
                If the 'default' key is not specified in terms, the other free nodes will
                be terminated by a Term().

        Note
        ----
        The directional coupler and the waveguide will be combined in a
        DirectionalCouplerWithLength. This conversion happens internally and is not
        required up front.
        '''

        Component.__init__(self, name=name)

        # Handle shape of network
        I,J = couplings.shape
        if I < 2 or J < 2:
            raise ValueError('2D Network is required.')

        # Get directional coupler with length
        self.dircoup = DirectionalCouplerWithLength(dircoup=dircoup, wg=wg)

        # Create directional coupler array
        self.dircoup_array = np.zeros((I,J), dtype=object)
        for i in range(I):
            for j in range(J):
                # Create copy of directional coupler:
                dircoup_copy = self.dircoup.copy()
                dircoup_copy.name = '+'
                dircoup_copy.dircoup.R = couplings[i,j]
                # Put copy in dircoup array
                self.dircoup_array[i,j] = dircoup_copy

        # Create term array
        self.num_terms = 8 + 2*(I-2) + 2*(J-2)
        self.terms = OrderedDict(terms)

    def terminate(self, term=None):
        ''' Directional Coupler Networks are terminated by default '''
        if term is None:
            term = Term()
        for t in range(self.num_terms):
            if t not in self.terms:
                term = term.copy()
                term.name = 't'+str(t)
                self.terms[t] = term
        return self

    @property
    def couplings(self):
        I,J = self.dircoup_array.shape
        couplings = self.new_variable(np.zeros((I,J)))
        for i in range(I):
            for j in range(J):
                couplings[i,j] = self.dircoup_array[i,j].dircoup.R
        return couplings

    @property
    def C(self):
        Ns = np.cumsum([0]+[comp.num_ports for comp in self.components])
        free_idxs = [comp.free_idxs for comp in self.components]
        C = block_diag(*(comp.C for comp in self.components))

        # add connections
        for i1, j1, i2, j2  in self._parse_connections():
            idxs1 = free_idxs[i1]
            idxs2 = free_idxs[i2]
            i = Ns[i1] + idxs1[j1]
            j = Ns[i2] + idxs2[j2]
            C[i,j] = C[j,i] = 1.0

        # find term connection locations
        I,J = self.shape
        K = self.num_terms
        idxs = where(((C.sum(0)>0) | (C.sum(1)>0)).ne(1).data)[:K]

        # connect terms
        for k, i in enumerate(self.terms):
            idx = idxs[i]
            C[-K+k,idx] = C[idx,-K+k] = 1.0

        return C

    def _parse_connections(self):
        connections = []
        I,J = self.shape
        for i in range(I):
            for j in range(J):
                if i < I-1:
                    top = (i*J+j,3)
                    bottom = ((i+1)*J+j,1)
                    connections.append(top + bottom)
                if j < J-1:
                    left = (i*J+j,2)
                    right = (i*J+j+1,0)
                    connections.append(left + right)
        return connections

    @property
    def shape(self):
        return self.dircoup_array.shape

    @property
    def components(self):
        return tuple(self.dircoup_array.ravel()) + tuple(self.terms.values())

    def cuda(self):
        ''' Transform Network to live on the GPU '''
        new = self.copy()
        I, J = self.shape
        for i in range(I):
            for j in range(J):
                new.dircoup_array[i,j] = new.dircoup_array[i,j].cuda()
        terms = OrderedDict()
        for k, v in new.terms.items():
            terms[k] = v.cuda()
        new.terms = terms
        new.is_cuda = True
        return new

    def cpu(self):
        ''' Transform Network to live on the CPU '''
        new = self.copy()
        I, J = self.shape
        for i in range(I):
            for j in range(J):
                new.dircoup_array[i,j] = new.dircoup_array[i,j].cpu()
        terms = OrderedDict()
        for k, v in new.terms.items():
            terms[k] = v.cpu()
        new.terms = terms
        new.is_cuda = False
        return new

    def copy(self, couplings = None):
        ''' Copy the directional coupler network '''
        if couplings is None:
            couplings = self.couplings.data.cpu().numpy()
        new = self.__class__(
            couplings=couplings,
            dircoup=self.dircoup.dircoup,
            wg=self.dircoup.wg,
            name=self.name,
        )
        new.terms = self.terms
        return new

    @staticmethod
    def _parse_string(s):
        s.replace('+','d')
        lines = [_s.strip() for _s in s.lower().splitlines()]
        while lines[0] == '':
            lines = lines[1:]
        while lines[-1] == '':
            lines = lines[:-1]
        array = np.array([list(_s) for _s in lines], dtype=object)
        return array

    def __getitem__(self, key):
        if isinstance(key, str):
            return Component.__getitem__(self, key)
        else:
            return self.dircoup_array.__getitem__(key)
