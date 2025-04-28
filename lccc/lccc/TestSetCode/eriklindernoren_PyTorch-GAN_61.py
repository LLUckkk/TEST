import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import torch.nn as nn


#############change###########
def initialize_weights(net):
    for m in net.modules():
        if isinstance(m, nn.Conv2d):
            m.weight.data.normal_(0, 0.02)
            m.bias.data.zero_()
        elif isinstance(m, nn.ConvTranspose2d):
            m.weight.data.normal_(0, 0.02)
            m.bias.data.zero_()
        elif isinstance(m, nn.Linear):
            m.weight.data.normal_(0, 0.02)
            m.bias.data.zero_()


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
                print(e)
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
    net = nn.Sequential(
        nn.Conv2d(1, 64, 4, stride=2, bias=True),
        nn.LeakyReLU(0.2, inplace=True),
        nn.Conv2d(64, 128, 4, stride=2, bias=True),
        nn.LeakyReLU(0.2, inplace=True),
        nn.ConvTranspose2d(128, 64, 4, stride=2, padding=1, bias=True),
        nn.BatchNorm2d(64),
        nn.LeakyReLU(0.2, inplace=True),
        nn.ConvTranspose2d(64, 1, 4, stride=2, padding=1, bias=True),
        nn.Sigmoid()
    )

    initialize_weights(net)
    return str(net)


# 定义测试用例2
def testcase_2():
    net = nn.Sequential(
        nn.Conv2d(3, 32, 3, stride=1, padding=1, bias=True),
        nn.ReLU(inplace=True),
        nn.Conv2d(32, 64, 3, stride=1, padding=1, bias=True),
        nn.ReLU(inplace=True),
        nn.Conv2d(64, 128, 3, stride=1, padding=1, bias=True),
        nn.ReLU(inplace=True),
        nn.Linear(128 * 32 * 32, 1000),
        nn.ReLU(inplace=True),
        nn.Linear(1000, 10)
    )

    initialize_weights(net)
    return str(net)


# 定义测试用例3
def testcase_3():
    net = nn.Sequential(
        nn.Linear(100, 256),
        nn.ReLU(inplace=True),
        nn.Linear(256, 512),
        nn.ReLU(inplace=True),
        nn.Linear(512, 1024),
        nn.ReLU(inplace=True),
        nn.Linear(1024, 2048),
        nn.ReLU(inplace=True),
        nn.Linear(2048, 4096),
        nn.ReLU(inplace=True),
        nn.Linear(4096, 8192),
        nn.ReLU(inplace=True)
    )

    initialize_weights(net)
    return str(net)


# 定义测试用例4
def testcase_4():
    net = nn.Sequential(
        nn.Conv2d(1, 16, 5, stride=1, padding=2, bias=True),
        nn.ReLU(inplace=True),
        nn.Conv2d(16, 32, 5, stride=1, padding=2, bias=True),
        nn.ReLU(inplace=True),
        nn.Conv2d(32, 64, 5, stride=1, padding=2, bias=True),
        nn.ReLU(inplace=True),
        nn.Linear(64 * 28 * 28, 100),
        nn.ReLU(inplace=True),
        nn.Linear(100, 10)
    )

    initialize_weights(net)
    return str(net)


# 定义测试用例5
def testcase_5():
    net = nn.Sequential(
        nn.ConvTranspose2d(1, 32, 4, stride=2, padding=1, bias=True),
        nn.BatchNorm2d(32),
        nn.ReLU(inplace=True),
        nn.ConvTranspose2d(32, 64, 4, stride=2, padding=1, bias=True),
        nn.BatchNorm2d(64),
        nn.ReLU(inplace=True),
        nn.ConvTranspose2d(64, 128, 4, stride=2, padding=1, bias=True),
        nn.BatchNorm2d(128),
        nn.ReLU(inplace=True),
        nn.ConvTranspose2d(128, 256, 4, stride=2, padding=1, bias=True),
        nn.BatchNorm2d(256),
        nn.ReLU(inplace=True),
        nn.ConvTranspose2d(256, 512, 4, stride=2, padding=1, bias=True),
        nn.BatchNorm2d(512),
        nn.ReLU(inplace=True)
    )

    initialize_weights(net)
    return str(net)


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
