import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import torch
import torch.nn as nn


#############change###########
def init_weights(self):
    dw_max = self.kernel_size ** -0.5
    pw_max = self.channel ** -0.5
    torch.nn.init.uniform_(self.dw_conv.weight, -dw_max, dw_max)
    torch.nn.init.uniform_(self.dw_conv.bias, -dw_max, dw_max)
    torch.nn.init.uniform_(self.pw_conv.weight, -pw_max, pw_max)
    torch.nn.init.uniform_(self.pw_conv.bias, -pw_max, pw_max)


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
                    result_queue.put(('success', result))
        except Exception as e:
            # print(e)
            if not event.is_set():
                result_queue.put(('error', e))
        finally:
            event.set()

    t = threading.Thread(target=worker)
    t.daemon = True
    t.start()

    start_time = time.time()
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


# 通用创建 Dummy 工具
def create_dummy(channel, out_dim, kernel_size, stride):
    class Dummy:
        pass

    self = Dummy()
    self.channel = channel
    self.out_dim = out_dim
    self.kernel_size = kernel_size
    self.stride = stride

    # depthwise convolution
    self.dw_conv = nn.Conv2d(channel, channel, kernel_size=kernel_size, stride=stride, padding=kernel_size // 2,
                             groups=channel, bias=True)

    # pointwise convolution
    self.pw_conv = nn.Conv2d(channel, out_dim, kernel_size=1, stride=1, padding=0, bias=True)

    return self


def testcase_1():
    self = create_dummy(channel=64, out_dim=128, kernel_size=3, stride=2)
    init_weights(self)
    return {
        "dw_mean": self.dw_conv.weight.mean().item(),
        "dw_std": self.dw_conv.weight.std().item(),
        "pw_mean": self.pw_conv.weight.mean().item(),
        "pw_std": self.pw_conv.weight.std().item()
    }


def testcase_2():
    self = create_dummy(channel=32, out_dim=64, kernel_size=5, stride=1)
    init_weights(self)
    return {
        "dw_mean": self.dw_conv.weight.mean().item(),
        "dw_std": self.dw_conv.weight.std().item(),
        "pw_mean": self.pw_conv.weight.mean().item(),
        "pw_std": self.pw_conv.weight.std().item()
    }


def testcase_3():
    self = create_dummy(channel=128, out_dim=256, kernel_size=7, stride=3)
    init_weights(self)
    return {
        "dw_mean": self.dw_conv.weight.mean().item(),
        "dw_std": self.dw_conv.weight.std().item(),
        "pw_mean": self.pw_conv.weight.mean().item(),
        "pw_std": self.pw_conv.weight.std().item()
    }


def testcase_4():
    self = create_dummy(channel=16, out_dim=32, kernel_size=1, stride=1)
    init_weights(self)
    return {
        "dw_mean": self.dw_conv.weight.mean().item(),
        "dw_std": self.dw_conv.weight.std().item(),
        "pw_mean": self.pw_conv.weight.mean().item(),
        "pw_std": self.pw_conv.weight.std().item()
    }


def testcase_5():
    self = create_dummy(channel=256, out_dim=512, kernel_size=9, stride=4)
    init_weights(self)
    return {
        "dw_mean": self.dw_conv.weight.mean().item(),
        "dw_std": self.dw_conv.weight.std().item(),
        "pw_mean": self.pw_conv.weight.mean().item(),
        "pw_std": self.pw_conv.weight.std().item()
    }


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
