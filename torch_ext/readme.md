# Torch Extensions for PhotonTorch

Since PhotonTorch is a photonic simulation framework in the first place,
we require some extra functionalities that PyTorch does not offer out of
the box.

Below you can find a short summary:

## Autograd Extensions
  * `pinv`: a differentiable implementation of the pseudo inverse of a matrix
  * `block_diag`: a differentiable implementation of a block diagonal matrix
  * `batch_block_diag`: a differentiable implementation of a block diagonal matrix
performed over a batch of matrices.

## Neural Network Extensions
  * `Buffer`: A special kind of tensor that automatically will
be added to the `._buffers` attribute of the Module. Buffers are typically used as
parameters of the model that do not require gradients.
  * `BoundedParameter`: A bounded parameter acts like a
`torch.nn.Parameter` that is bounded between a certain range. Under the hood it is
actually a `torch.nn.Module`, but for all intents and purposes it can be considered
to act like a `torch.nn.Parameter`.
  * `Module`: Extends `torch.nn.Module`, with some extra features (such as automatically)
registering a `[Buffer](.nn.Buffer)` in its `._buffers` attribute, modified `.cuda()` calls and some
extra functionalities.

## Tensor functions
Some non-differentiable, but useful functions that act on (or create) torch tensors.