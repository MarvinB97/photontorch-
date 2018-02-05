''' Ring Networks '''

#############
## Imports ##
#############

## Relative
from .network import Network
from ..components.waveguides import Waveguide
from ..components.directionalcouplers import DirectionalCoupler


#####################
## All Pass Filter ##
#####################

class AllPass(Network):
    ''' All Pass Filter

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
                 name='allpass'):
        '''
        AllPass Filter Initialization

        Parameters
        ----------
        ring_wg : waveguide for the ring
        dircoup : directional coupler for the connection to the ring
        '''
        connector = dircoup['ijkl']*ring_wg['jl']

        i,j = connector.idxs
        if in_wg is not None:
            connector = in_wg['a'+i]*connector
        if pass_wg is not None:
            connector = pass_wg['b'+j]*connector

        i,j = connector.idxs
        if in_term is not None:
            connector = in_term[i]*connector
        if pass_term is not None:
            connector = pass_term[j]*connector

        Network.__init__(self, connector)


#####################
## Add Drop Filter ##
#####################

class AddDrop(Network):
    ''' Add Drop Filter

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
                 in_wg = None,
                 pass_wg = None,
                 add_wg = None,
                 drop_wg = None,
                 in_term = None,
                 pass_term = None,
                 add_term = None,
                 drop_term = None,
                 name='adddrop'):
        '''
        AddDrop Filter Initialization

        Parameters
        ----------
        half_ring_wg : waveguide for a half ring (will be used twice to make the network)
        dircoup1 : bottom directional coupler for the connection to the ring
        dircoup2 : top directional coupler for the connection to the ring
        '''
        connector = dircoup1['wxyz']*dircoup2['efgh']
        connector = half_ring_wg['be']*half_ring_wg['dg']*connector

        for i,j, wg in zip('wxyz',connector.idxs,[in_wg, drop_wg, pass_wg, add_wg]):
            if wg is not None:
                connector = wg[i+j]*connector

        for i, term in zip(connector.idxs,[in_term, drop_term, pass_term, add_term]):
            if term is not None:
                connector = term[i]*connector

        Network.__init__(self, connector)
