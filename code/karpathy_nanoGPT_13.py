import torch


def get_num_params(self, non_embedding=True):
    n_params = sum(p.numel() for p in self.parameters())
    if non_embedding:
        n_params -= self.transformer.wpe.weight.numel()
    return n_params


self = type('test', (object,), {
    'parameters': lambda self: [torch.randn(10, 10), torch.randn(20, 20)],
    'transformer': type('transformer', (object,), {'wpe': type('wpe', (object,), {'weight': torch.randn(30, 30)})})})()
non_embedding = True
print(get_num_params(self, non_embedding))

self = type('test', (object,), {
    'parameters': lambda self: [torch.randn(50, 50), torch.randn(100, 100)],
    'transformer': type('transformer', (object,), {'wpe': type('wpe', (object,), {'weight': torch.randn(40, 40)})})})()
non_embedding = False
print(get_num_params(self, non_embedding))

self = type('test', (object,), {
    'parameters': lambda self: [torch.randn(5, 5), torch.randn(15, 15)],
    'transformer': type('transformer', (object,), {'wpe': type('wpe', (object,), {'weight': torch.randn(10, 10)})})})()
non_embedding = True
print(get_num_params(self, non_embedding))

self = type('test', (object,), {
    'parameters': lambda self: [torch.randn(25, 25), torch.randn(35, 35)],
    'transformer': type('transformer', (object,), {'wpe': type('wpe', (object,), {'weight': torch.randn(20, 20)})})})()
non_embedding = False
print(get_num_params(self, non_embedding))

self = type('test', (object,), {
    'parameters': lambda self: [torch.randn(60, 60), torch.randn(80, 80)],
    'transformer': type('transformer', (object,), {'wpe': type('wpe', (object,), {'weight': torch.randn(50, 50)})})})()
non_embedding = True
print(get_num_params(self, non_embedding))
