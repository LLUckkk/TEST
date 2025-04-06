import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import json
from typing import Any


#############change###########
def merge_stats(self, stats: dict[str, Any]) -> dict[str, Any]:
    for key, value in stats.items():
        if isinstance(value, dict):
            self.execution_stats.setdefault(key, {}).update(value)
        elif isinstance(value, (int, float)):
            self.execution_stats.setdefault(key, 0)
            self.execution_stats[key] += value
        elif isinstance(value, list):
            self.execution_stats.setdefault(key, [])
            self.execution_stats[key].extend(value)
        else:
            self.execution_stats[key] = value
    return self.execution_stats


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
        def __init__(self):
            self.execution_stats = {}

    self = Dummy()
    stats = {
        "input_token_count": 150,
        "output_token_count": 200,
        "llm_call_count": 1,
        "llm_retry_count": 0
    }

    return merge_stats(self, stats)


# 定义测试用例2
def testcase_2():
    class Dummy:
        def __init__(self):
            self.execution_stats = {}

    self = Dummy()
    stats = {
        "execution_time": 2.5,
        "errors": ["timeout", "invalid response format"],
        "input_token_count": 300,
        "output_token_count": 350
    }

    return merge_stats(self, stats)


# 定义测试用例3
def testcase_3():
    class Dummy:
        def __init__(self):
            self.execution_stats = {}

    self = Dummy()
    stats = {
        "input_token_count": 500,
        "output_token_count": 600,
        "additional_info": {
            "model_version": "v2.1",
            "api_version": "v1.0"
        }
    }

    return merge_stats(self, stats)


# 定义测试用例4
def testcase_4():
    class Dummy:
        def __init__(self):
            self.execution_stats = {}

    self = Dummy()
    stats = {
        "input_token_count": 1000,
        "output_token_count": 1200,
        "warnings": ["slow response", "high token usage"],
        "llm_call_count": 2
    }

    return merge_stats(self, stats)


# 定义测试用例5
def testcase_5():
    class Dummy:
        def __init__(self):
            self.execution_stats = {}

    self = Dummy()
    stats = {
        "input_token_count": 250,
        "output_token_count": 300,
        "llm_call_count": 3,
        "llm_retry_count": 1,
        "response_times": [0.5, 0.7, 0.6]
    }

    return merge_stats(self, stats)


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

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
