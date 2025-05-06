import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import torch


def append_zero(x):
    """在 Tensor x 的开头添加一个值为 0 的元素"""
    zero = torch.zeros(1, device=x.device, dtype=x.dtype)
    return torch.cat([zero, x], dim=0)


#############change###########
def get_sigmas(self, n=None):
    if n is None:
        return append_zero(self.sigmas.flip(0))
    t_max = len(self.sigmas) - 1
    t = torch.linspace(t_max, 0, n, device=self.sigmas.device)
    return append_zero(self.t_to_sigma(t))


#############change###########


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
    event = threading.Event()  # 线程协调事件

    def worker():
        try:
            with request_context() as session:
                # 将session传递给测试函数（如果需要）
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
            event.set()  # 标记线程已完成

    t = threading.Thread(target=worker)
    t.daemon = True  # 必须设置为守护线程

    start_time = time.time()
    t.start()

    # 等待线程完成或超时
    while time.time() - start_time < timeout:
        if event.is_set() or not result_queue.empty():
            break
        time.sleep(0.1)

    event.set()  # 通知线程终止

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


# 定义测试用例1
def testcase_1():
    class Dummy:
        pass

    self = Dummy()
    self.sigmas = torch.tensor([0.1, 0.2, 0.3, 0.4, 0.5])
    self.t_to_sigma = lambda t: t * 0.1
    n = 5

    return get_sigmas(self, n)


# 定义测试用例2
def testcase_2():
    class Dummy:
        pass

    self = Dummy()
    self.sigmas = torch.tensor([0.05, 0.1, 0.15, 0.2, 0.25, 0.3])
    self.t_to_sigma = lambda t: t * 0.05
    n = 10

    return get_sigmas(self, n)


# 定义测试用例3
def testcase_3():
    class Dummy:
        pass

    self = Dummy()
    self.sigmas = torch.tensor([0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07])
    self.t_to_sigma = lambda t: t * 0.01
    n = None

    return get_sigmas(self, n)


# 定义测试用例4
def testcase_4():
    class Dummy:
        pass

    self = Dummy()
    self.sigmas = torch.tensor([0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.035, 0.04])
    self.t_to_sigma = lambda t: t * 0.005
    n = 8

    return get_sigmas(self, n)


# 定义测试用例5
def testcase_5():
    class Dummy:
        pass

    self = Dummy()
    self.sigmas = torch.tensor([0.001, 0.002, 0.003, 0.004, 0.005, 0.006, 0.007, 0.008, 0.009, 0.01])
    self.t_to_sigma = lambda t: t * 0.001
    n = 20

    return get_sigmas(self, n)


def main():
    # 执行所有测试用例
    test_results = {
        "ans1": safe_execute_testcase(testcase_1, timeout=5),
        "ans2": safe_execute_testcase(testcase_2, timeout=5),
        "ans3": safe_execute_testcase(testcase_3, timeout=5),
        "ans4": safe_execute_testcase(testcase_4, timeout=5),
        "ans5": safe_execute_testcase(testcase_5, timeout=5)
    }

    def tensor_to_serializable(obj):
        if isinstance(obj, torch.Tensor):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: tensor_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [tensor_to_serializable(i) for i in obj]
        elif isinstance(obj, tuple):
            return tuple(tensor_to_serializable(i) for i in obj)
        else:
            return obj

    output = {
        "ans1": test_results["ans1"]["result"] if test_results["ans1"]["success"] else None,
        "ans2": test_results["ans2"]["result"] if test_results["ans2"]["success"] else None,
        "ans3": test_results["ans3"]["result"] if test_results["ans3"]["success"] else None,
        "ans4": test_results["ans4"]["result"] if test_results["ans4"]["success"] else None,
        "ans5": test_results["ans5"]["result"] if test_results["ans5"]["success"] else None
    }

    # print(json.dumps(tensor_to_serializable(output), indent=2))
    with open('output.json', 'w', encoding='utf-8') as f:
        json.dump(tensor_to_serializable(output), f, indent=2)


if __name__ == '__main__':
    main()
