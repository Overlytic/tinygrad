from tinygrad.tensor import Tensor

def batch_normalize(x, weight, bias, mean, var, eps):
  x = (x - mean.reshape(shape=[1, -1, 1, 1])) * weight.reshape(shape=[1, -1, 1, 1])
  return x.mul(var.add(eps).reshape(shape=[1, -1, 1, 1])**-0.5) + bias.reshape(shape=[1, -1, 1, 1])

class BatchNorm2D:
  def __init__(self, sz, eps=1e-5, affine=True, track_running_stats=True, momentum=0.1):
    assert affine == True, "BatchNorm2D is only supported with affine"
    self.eps, self.track_running_stats, self.momentum = eps, track_running_stats, momentum

    self.weight, self.bias = Tensor.ones(sz), Tensor.zeros(sz)

    self.running_mean, self.running_var = Tensor.zeros(sz, requires_grad=False), Tensor.ones(sz, requires_grad=False)
    self.num_batches_tracked = Tensor.zeros(1, requires_grad=False)

  def __call__(self, x):
    if Tensor.training:
      # This requires two full memory accesses to x
      # https://github.com/pytorch/pytorch/blob/c618dc13d2aa23625cb0d7ada694137532a4fa33/aten/src/ATen/native/cuda/Normalization.cuh
      # There's "online" algorithms that fix this
      x_detached = x.detach()
      batch_mean = x_detached.mean(axis=(0,2,3))
      y = (x_detached - batch_mean.reshape(shape=[1, -1, 1, 1]))
      batch_var = (y*y).mean(axis=(0,2,3))

      # NOTE: wow, this is done all throughout training in most PyTorch models
      if self.track_running_stats:
        self.running_mean = (1 - self.momentum) * self.running_mean + self.momentum * batch_mean
        self.running_var = (1 - self.momentum) * self.running_var + self.momentum * batch_var
        if self.num_batches_tracked is None: self.num_batches_tracked = Tensor.zeros(1, requires_grad=False)
        self.num_batches_tracked += 1

      return batch_normalize(x, self.weight, self.bias, batch_mean, batch_var, self.eps)

    return batch_normalize(x, self.weight, self.bias, self.running_mean, self.running_var, self.eps)

class Conv2d:
  def __init__(self, in_channels, out_channels, kernel_size, stride=1, padding=0, bias=True):
    self.kernel_size = (kernel_size, kernel_size) if isinstance(kernel_size, int) else (kernel_size[0], kernel_size[1])
    self.stride = (stride, stride) if isinstance(stride, int) else (stride[0], stride[1])
    self.padding = (padding, ) * 4 if isinstance(padding, int) else (padding[0], padding[0], padding[1], padding[1])
    self.weight = Tensor.uniform(out_channels, in_channels, self.kernel_size[0], self.kernel_size[1])
    self.bias = Tensor.uniform(out_channels) if bias else None

  def __call__(self, x):
    return x.conv2d(self.weight, self.bias, padding=self.padding, stride=self.stride)

