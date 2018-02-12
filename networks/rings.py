''' Ring Networks '''

#############
## Imports ##
#############

## Other
import numpy as np

## Relative
from .network import Network
from .directionalcouplers import DirectionalCouplerNetwork


#####################
## All Pass Filter ##
#####################

class AllPass(Network):
    r''' All Pass Filter

    An AllPass filter is a memory-containging component with one input and one output.

    Connections
    -----------
    allpass['ij']
         ___
        /   \
        \___/
    i-----------j
    '''
    def __init__(self,
                 dircoup,
                 ring_wg,
                 in_wg=None,
                 pass_wg=None,
                 in_term=None,
                 pass_term=None,
                 name=None):
        '''
        AllPass Filter Initialization

        Parameters
        ----------
        ring_wg : waveguide for the ring
        dircoup : directional coupler for the connection to the ring
        '''
        connector = dircoup['ikjl']*ring_wg['jl']

        i, j = connector.idxs
        if in_wg is not None:
            connector = in_wg['a'+i]*connector
        if pass_wg is not None:
            connector = pass_wg['b'+j]*connector

        i, j = connector.idxs
        if in_term is not None:
            connector = in_term[i]*connector
        if pass_term is not None:
            connector = pass_term[j]*connector

        Network.__init__(self, connector, name=name)


#####################
## Add Drop Filter ##
#####################

class AddDrop(Network):
    r''' Add Drop Filter

    An AddDrop filter is a memory-containging component with one input and one output.

    Connections
    -----------
    adddrop['ijkl']
    j----===----l
        /   \
        \___/
    i-----------k
    '''
    def __init__(self,
                 dircoup1,
                 dircoup2,
                 half_ring_wg,
                 in_wg=None,
                 pass_wg=None,
                 add_wg=None,
                 drop_wg=None,
                 in_term=None,
                 pass_term=None,
                 add_term=None,
                 drop_term=None,
                 name=None):
        '''
        AddDrop Filter Initialization

        Parameters
        ----------
        half_ring_wg : waveguide for a half ring (will be used twice to make the network)
        dircoup1 : bottom directional coupler for the connection to the ring
        dircoup2 : top directional coupler for the connection to the ring
        '''
        connector = dircoup1['abcd']*dircoup2['efgh']
        connector = half_ring_wg['ce']*half_ring_wg['df']*connector

        for i, j, wg in zip('wxyz', connector.idxs, [in_wg, pass_wg, drop_wg, add_wg]):
            if wg is not None:
                connector = wg[i+j]*connector

        for i, term in zip(connector.idxs, [in_term, pass_term, drop_term, add_term]):
            if term is not None:
                connector = term[i]*connector
        print(connector)

        Network.__init__(self, connector, name=name)


class RingNetwork(DirectionalCouplerNetwork):
    ''' A network of rings made out of directional couplers and waveguides.
    A directional coupler is repeated periodically in a grid, with the ports flipped
    in odd locations to make rings in the network. The ports are connected by waveguides

    Network
    -------
         0    1    2    3
        ..   ..   ..   ..
         1    1    1    1
    11: 0 2--2 0--0 2--2 0 : 4
         3    3    3    3
         |    |    |    |
         3    3    3    3
    10: 0 2--2 0--0 2--2 0 : 5
         1    1    1    1
        ..   ..   ..   ..
         9    8    7    6

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
    network does contain loops and can thus be used as a reservoir.
    '''
    def __init__(self, couplings, dircoup, wg, terms=None, name='dircoupnw'):
        DirectionalCouplerNetwork.__init__(self, couplings, dircoup, wg, terms=terms, name=name)
        # Change default term order to term order of ring network
        I, J = self.shape
        k0 = (I%2 == 0) & (J%2 == 1)
        k1 = not k0
        self._order = np.hstack((
            np.arange(1, J, 1), # North row
            [J, J+1] if J%2 else [J+1, J], #North East Corner
            np.arange(J+3, 4+(J-2)+2*(J-2), 2), # East column
            [8+2*(I-2)+2*(J-2)-2+k0, 8+2*(I-2)+2*(J-2)-2+k1], # South-East Corner
            np.arange(4+(J-2)+2*(I-2), 8+2*(I-2)+2*(J-2)-2, 1)[::-1], #South Row
            np.arange(J+2, 4+(J-2)+2*(J-2), 2)[::-1], # left column
            [0], # half of north west corner
        ))

    def _parse_connections(self):
        connections = []
        I, J = self.shape
        for i in range(I):
            for j in range(J):
                if i < I-1:
                    if i%2 == 0:
                        top = (i*J+j, 3)
                        bottom = ((i+1)*J+j, 3)
                    if i%2 == 1:
                        top = (i*J+j, 1)
                        bottom = ((i+1)*J+j, 1)
                    connections.append(top + bottom)
                if j < J-1:
                    if j%2 == 0:
                        left = (i*J+j, 2)
                        right = (i*J+j+1, 2)
                    if j%2 == 1:
                        left = (i*J+j, 0)
                        right = (i*J+j+1, 0)
                    connections.append(left + right)
        return connections
