import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import re
from typing import Optional, List, Union, Literal


class ETag:
    def __init__(self, value: str):
        self.value = value
        self.is_weak = False

    def to_dict(self):
        return {
            'value': self.value,
            'is_weak': self.is_weak
        }

    @staticmethod
    def loads(value: str):
        return ETag(value)


_ENTITY_TAG_PATTERN = re.compile(r'(W/)?"([^"]+)"')


#############change###########
def _parse_etags(etag_str: str) -> Optional[List[Union[ETag, Literal['*']]]]:
    etag_str = etag_str.strip()
    if not etag_str:
        return None

    if etag_str == '*':
        return ['*']

    if ',' not in etag_str:
        return [ETag.loads(etag_str)]

    etags: List[Union[ETag, Literal['*']]] = []

    for weak, value in _ENTITY_TAG_PATTERN.findall(etag_str):
        t = ETag(value)
        t.is_weak = bool(weak)
        etags.append(t)

    return etags or None


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
    etag_str = 'W/"123456789"'

    return _parse_etags(etag_str)


# 定义测试用例2
def testcase_2():
    etag_str = '"abcdef", W/"123456789", "ghijkl"'

    return _parse_etags(etag_str)


# 定义测试用例3
def testcase_3():
    etag_str = '*'

    return _parse_etags(etag_str)


# 定义测试用例4
def testcase_4():
    etag_str = ''

    return _parse_etags(etag_str)


# 定义测试用例5
def testcase_5():
    etag_str = 'W/"weak-etag", "strong-etag"'

    return _parse_etags(etag_str)


def main():
    # 执行所有测试用例
    test_results = {
        "ans1": safe_execute_testcase(testcase_1, timeout=5),
        "ans2": safe_execute_testcase(testcase_2, timeout=5),
        "ans3": safe_execute_testcase(testcase_3, timeout=5),
        "ans4": safe_execute_testcase(testcase_4, timeout=5),
        "ans5": safe_execute_testcase(testcase_5, timeout=5)
    }

    def serialize_etags(etags):
        if etags is None:
            return None
        return [
            tag if tag == '*' else tag.to_dict()
            for tag in etags
        ]

    output = {
        "ans1": serialize_etags(test_results["ans1"]["result"]) if test_results["ans1"]["success"] else None,
        "ans2": serialize_etags(test_results["ans2"]["result"]) if test_results["ans2"]["success"] else None,
        "ans3": serialize_etags(test_results["ans3"]["result"]) if test_results["ans3"]["success"] else None,
        "ans4": serialize_etags(test_results["ans4"]["result"]) if test_results["ans4"]["success"] else None,
        "ans5": serialize_etags(test_results["ans5"]["result"]) if test_results["ans5"]["success"] else None,
    }

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
