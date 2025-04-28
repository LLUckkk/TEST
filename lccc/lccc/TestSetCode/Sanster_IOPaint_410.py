import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import torch.nn as nn


def module_to_dict(module):
    return {
        'type': type(module).__name__,
        'state_dict': {k: v.tolist() for k, v in module.state_dict().items()},
        'config': {k: v for k, v in module.__dict__.items()
                  if not k.startswith('_') and not callable(v)}
    }

#############change###########
def zero_module(module):
    for p in module.parameters():
        p.detach().zero_()
    return module


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
    module = nn.Conv2d(in_channels=3, out_channels=16, kernel_size=3, padding=1)

    return zero_module(module)


# 定义测试用例2
def testcase_2():
    module = nn.Linear(in_features=10, out_features=5)

    return zero_module(module)


# 定义测试用例3
def testcase_3():
    module = nn.BatchNorm2d(num_features=8)

    return zero_module(module)


# 定义测试用例4
def testcase_4():
    module = nn.LSTM(input_size=4, hidden_size=6, num_layers=2)

    return zero_module(module)


# 定义测试用例5
def testcase_5():
    module = nn.Sequential(
        nn.Conv2d(in_channels=3, out_channels=8, kernel_size=3, padding=1),
        nn.ReLU(),
        nn.Conv2d(in_channels=8, out_channels=16, kernel_size=3, padding=1)
    )

    return zero_module(module)


def main():
    # 执行所有测试用例
    test_results = {
        "ans1": safe_execute_testcase(testcase_1, timeout=5),
        "ans2": safe_execute_testcase(testcase_2, timeout=5),
        "ans3": safe_execute_testcase(testcase_3, timeout=5),
        "ans4": safe_execute_testcase(testcase_4, timeout=5),
        "ans5": safe_execute_testcase(testcase_5, timeout=5)
    }

    output = {
        "ans1": module_to_dict(test_results["ans1"]["result"]) if test_results["ans1"]["success"] else None,
        "ans2": module_to_dict(test_results["ans2"]["result"])if test_results["ans2"]["success"] else None,
        "ans3": module_to_dict(test_results["ans3"]["result"]) if test_results["ans3"]["success"] else None,
        "ans4": module_to_dict(test_results["ans4"]["result"]) if test_results["ans4"]["success"] else None,
        "ans5": module_to_dict(test_results["ans5"]["result"]) if test_results["ans5"]["success"] else None
    }

    # print(json.dumps(output, indent=2))
    with open('output.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)


if __name__ == '__main__':
    main()

