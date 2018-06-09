'''
# Mirrors

Mirrors are partly reflecting and partly transmitting.


## Todo
Create mirrors that are also partly absorbing.

'''

#############
## Imports ##
#############

## Torch
import torch

## Relative
from .component import Component


############
## Mirror ##
############

class Mirror(Component):
    ''' A mirror is a memory-less component with one input and one output.

    A mirror has one trainable parameter: the reflectivity R.

    Terms:
            |
        0 --|-- 1
            |
    '''

    num_ports = 2

    def __init__(self, R=0.5, trainable=True, name=None):
        ''' Mirror

        Args:
            R (float): Reflectivity of the mirror (between 0 and 1)
            trainable (bool): whether the reflectivity is trainable
            name (str): name of this specific mirror
        '''
        Component.__init__(self, name=name)

        self.R = self.bounded_parameter(
            data=R,
            bounds=(0,1),
            requires_grad=trainable,
        )

    def get_rS(self):
        ''' Real part of the scattering matrix with shape: (# wavelengths, # ports, # ports) '''
        r = torch.cat([(self.R**0.5).view(1,1,1)]*self.env.num_wl, dim=0)
        S = self.tensor([[[1, 0],
                          [0, 1]]])
        return r*S

    def get_iS(self):
        ''' Imag part of the scattering matrix with shape: (# wavelengths, # ports, # ports) '''
        t = torch.cat([((1-self.R)**0.5).view(1,1,1)]*self.env.num_wl, dim=0)
        S = self.tensor([[[0, 1],
                          [1, 0]]])
        return t*S
