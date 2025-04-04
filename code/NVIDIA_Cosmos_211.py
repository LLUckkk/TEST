import torch


class Codebook:
    def __init__(self, codebook_dim: int):
        self.codebook_dim = codebook_dim
        self._basis = torch.arange(codebook_dim).float()

    def _scale_and_shift(self, zhat):
        return zhat

    def codes_to_indices(self, zhat: torch.Tensor) -> torch.Tensor:
        assert zhat.shape[-1] == self.codebook_dim
        zhat = self._scale_and_shift(zhat).float()
        return (zhat * self._basis).sum(dim=-1).to(torch.int32)


def print_ans(indices):
    print(indices.shape)
    print(indices.dtype)
    print(indices[0, 0, :5])


zhat = torch.randn(2, 4, 8, 16)
obj = Codebook(zhat.shape[-1])
indices = obj.codes_to_indices(zhat)
print_ans(indices)

zhat = torch.randn(5, 10, 32, 64)
obj = Codebook(zhat.shape[-1])
indices = obj.codes_to_indices(zhat)
print_ans(indices)

zhat = torch.randn(3, 6, 12, 24)
obj = Codebook(zhat.shape[-1])
indices = obj.codes_to_indices(zhat)
print_ans(indices)

zhat = torch.randn(8, 16, 32, 64)
obj = Codebook(zhat.shape[-1])
indices = obj.codes_to_indices(zhat)
print_ans(indices)

zhat = torch.randn(1, 2, 4, 8)
obj = Codebook(zhat.shape[-1])
indices = obj.codes_to_indices(zhat)
print_ans(indices)
