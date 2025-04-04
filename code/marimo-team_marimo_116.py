import numpy as np


def generate_synthetic_data(seed=42, samples=100):
    class Data:
        time: np.ndarray
        signal: np.ndarray

    np.random.seed(seed)
    t = np.linspace(0, 1000, samples)
    sine_wave = 1.5 * np.sin(2 * np.pi * t * 1 / (500.0))
    trend = np.linspace(0, 10, samples)
    noise = 0.1 * np.random.randn(len(sine_wave))
    X = np.vstack([sine_wave, noise, trend])
    data = Data()
    data.time = t
    data.signal = X.sum(axis=0)
    return data


def print_data(data):
    print("time shape:" + str(data.time.shape))
    print("time preview:" + str(data.time[:5]))
    print("signal shape:" + str(data.signal.shape))
    print("signal preview:" + str(data.signal[:5]))


seed = 42
samples = 100
d = generate_synthetic_data(seed, samples)
print_data(d)

seed = 123
samples = 200
d = generate_synthetic_data(seed, samples)
print_data(d)

seed = 7
samples = 50
d = generate_synthetic_data(seed, samples)
print_data(d)

seed = 99
samples = 500
d = generate_synthetic_data(seed, samples)
print_data(d)

seed = 2021
samples = 1000
d = generate_synthetic_data(seed, samples)
print_data(d)
