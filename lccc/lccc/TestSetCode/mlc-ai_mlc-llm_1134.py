import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import torch
from torch import Tensor
import torch.nn.functional as F


# Dummy operation module
class op:
    sigmoid = torch.sigmoid
    relu = F.relu
    square = lambda x: x * x


class StateID:
    FFN_X = "ffn_x"


class RNNState:
    def __init__(self):
        self.storage = {}

    def get(self, layer_id, key, shape, dtype):
        return self.storage.get((layer_id, key), torch.zeros(*shape, dtype=dtype))

    def set(self, layer_id, key, value):
        self.storage[(layer_id, key)] = value
        return self


def token_shift(a: Tensor, b: Tensor) -> Tensor:
    # 假设 a.shape = (B, H), b.shape = (B, T, H)
    # 目标是返回 (B, T, H)，将 a 复制到 T 个位置上
    B, T, H = b.shape
    return a.unsqueeze(1).expand(B, T, H)


def last_token(x: Tensor) -> Tensor:
    return x[:, -1]


#############change###########
def forward(self, x: Tensor, state: RNNState):
    batch, _, hidden_size = x.shape
    state_x = state.get(self.layer_id, StateID.FFN_X, (batch, hidden_size), x.dtype)
    state_x = token_shift(state_x, x)

    state_x = state_x - x
    xk = x + state_x * self.time_maa_k
    xr = x + state_x * self.time_maa_r

    last_x = last_token(x).reshape(batch, hidden_size)
    state = state.set(self.layer_id, StateID.FFN_X, last_x)

    r = op.sigmoid(self.receptance(xr))
    xv = op.square(op.relu(self.key(xk)))
    return r * self.value(xv), state


#############change###########


@contextmanager
def request_context():
    session = requests.Session()
    try:
        yield session
    finally:
        session.close()


def safe_execute_testcase(testcase_func, timeout):
    result_queue = queue.Queue()
    event = threading.Event()

    def worker():
        try:
            with request_context() as session:
                if 'session' in testcase_func.__code__.co_varnames:
                    result = testcase_func(session=session)
                else:
                    result = testcase_func()
                if not event.is_set():
                    result_queue.put(('success', result[0].mean().item()))  # 只序列化一个float结果
        except Exception as e:
            print(e)
            if not event.is_set():
                result_queue.put(('error', e))
        finally:
            event.set()

    t = threading.Thread(target=worker)
    t.daemon = True
    start_time = time.time()
    t.start()

    while time.time() - start_time < timeout:
        if event.is_set() or not result_queue.empty():
            break
        time.sleep(0.1)

    event.set()

    if not result_queue.empty():
        status, data = result_queue.get_nowait()
        return {
            'success': status == 'success',
            'result': data if status == 'success' else None,
            'error': None if status == 'success' else str(data),
            'traceback': traceback.format_exc() if status == 'error' else None
        }

    return {
        'success': False,
        'error': f'Timeout after {timeout} seconds',
        'traceback': 'Test execution timed out'
    }


# 定义测试用例模板
def make_testcase(batch, seq_len, hidden, layer_id):
    class Dummy:
        def __init__(self):
            self.layer_id = layer_id
            self.time_maa_k = 0.5
            self.time_maa_r = 0.5
            self.receptance = torch.nn.Linear(hidden, hidden)
            self.key = torch.nn.Linear(hidden, hidden)
            self.value = torch.nn.Linear(hidden, hidden)

    def testcase():
        self = Dummy()
        x = torch.randn(batch, seq_len, hidden)
        state = RNNState()
        state.set(layer_id, StateID.FFN_X, torch.randn(batch, hidden))
        return forward(self, x, state)

    return testcase


# 构造5个测试用例
testcase_1 = make_testcase(32, 10, 128, 0)
testcase_2 = make_testcase(64, 15, 256, 1)
testcase_3 = make_testcase(16, 20, 64, 2)
testcase_4 = make_testcase(128, 5, 512, 3)
testcase_5 = make_testcase(8, 25, 32, 4)


def main():
    test_results = {
        "ans1": safe_execute_testcase(testcase_1, timeout=5),
        "ans2": safe_execute_testcase(testcase_2, timeout=5),
        "ans3": safe_execute_testcase(testcase_3, timeout=5),
        "ans4": safe_execute_testcase(testcase_4, timeout=5),
        "ans5": safe_execute_testcase(testcase_5, timeout=5)
    }

    output = {
        "ans1": test_results["ans1"]["result"] if test_results["ans1"]["success"] else None,
        "ans2": test_results["ans2"]["result"] if test_results["ans2"]["success"] else None,
        "ans3": test_results["ans3"]["result"] if test_results["ans3"]["success"] else None,
        "ans4": test_results["ans4"]["result"] if test_results["ans4"]["success"] else None,
        "ans5": test_results["ans5"]["result"] if test_results["ans5"]["success"] else None
    }

    with open('output.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)


if __name__ == '__main__':
    main()
