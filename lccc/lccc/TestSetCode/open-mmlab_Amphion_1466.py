import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import torch


#############change###########

def predict_start_from_noise(self, x_t, t, noise):
    return (
            extract_into_tensor(self.sqrt_recip_alphas_cumprod, t, x_t.shape) * x_t
            - extract_into_tensor(self.sqrt_recipm1_alphas_cumprod, t, x_t.shape)
            * noise
    )

#############change###########


# 注意：extract_into_tensor放到change外面单独定义
def extract_into_tensor(arr, timesteps, broadcast_shape):
    """补充extract_into_tensor，保证外面predict_start_from_noise能正常用"""
    # timesteps是一个1D Tensor，比如 [10]
    res = arr[timesteps]  # 取出对应timestep位置的系数
    while len(res.shape) < len(broadcast_shape):
        res = res.unsqueeze(-1)
    return res.expand(broadcast_shape)


@contextmanager
def request_context():
    """确保requests会话被正确关闭的上下文管理器"""
    session = requests.Session()
    try:
        yield session
    finally:
        session.close()


def safe_execute_testcase(testcase_func, timeout):
    """完全解决线程残留问题的执行器"""
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
            'result': data.cpu().tolist() if status == 'success' else None,
            'error': None if status == 'success' else str(data),
            'traceback': traceback.format_exc() if status == 'error' else None
        }

    return {
        'success': False,
        'error': f'Timeout after {timeout} seconds',
        'traceback': 'Test execution timed out'
    }


# 辅助：创建一个带属性的Dummy类
def create_dummy():
    class Dummy:
        pass

    dummy = Dummy()
    dummy.sqrt_recip_alphas_cumprod = torch.linspace(0.8, 1.2, 1000)  # 0.8到1.2之间均匀1000个数
    dummy.sqrt_recipm1_alphas_cumprod = torch.linspace(0.1, 0.5, 1000)
    return dummy


# 定义测试用例1-5（调用 predict_start_from_noise）

def testcase_1():
    self = create_dummy()
    x_t = torch.randn(3, 256, 256)
    t = torch.tensor([10])
    noise = torch.randn(3, 256, 256)
    return predict_start_from_noise(self, x_t, t, noise)

def testcase_2():
    self = create_dummy()
    x_t = torch.randn(1, 128, 128)
    t = torch.tensor([5])
    noise = torch.randn(1, 128, 128)
    return predict_start_from_noise(self, x_t, t, noise)

def testcase_3():
    self = create_dummy()
    x_t = torch.randn(4, 64, 64)
    t = torch.tensor([20])
    noise = torch.randn(4, 64, 64)
    return predict_start_from_noise(self, x_t, t, noise)

def testcase_4():
    self = create_dummy()
    x_t = torch.randn(2, 512, 512)
    t = torch.tensor([15])
    noise = torch.randn(2, 512, 512)
    return predict_start_from_noise(self, x_t, t, noise)

def testcase_5():
    self = create_dummy()
    x_t = torch.randn(5, 32, 32)
    t = torch.tensor([8])
    noise = torch.randn(5, 32, 32)
    return predict_start_from_noise(self, x_t, t, noise)


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
