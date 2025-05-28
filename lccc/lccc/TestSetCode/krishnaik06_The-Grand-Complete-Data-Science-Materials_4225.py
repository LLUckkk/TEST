import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import re

from PIL.ImageMorph import ROTATION_MATRIX, MIRROR_MATRIX


#############change###########
def _pattern_permute(self, basic_pattern, options, basic_result):
    patterns = [(basic_pattern, basic_result)]

    if "4" in options:
        res = patterns[-1][1]
        for i in range(4):
            patterns.append(
                (self._string_permute(patterns[-1][0], ROTATION_MATRIX), res)
            )
    if "M" in options:
        n = len(patterns)
        for pattern, res in patterns[:n]:
            patterns.append((self._string_permute(pattern, MIRROR_MATRIX), res))

    if "N" in options:
        n = len(patterns)
        for pattern, res in patterns[:n]:
            pattern = pattern.replace("0", "Z").replace("1", "0").replace("Z", "1")
            res = 1 - int(res)
            patterns.append((pattern, res))

    return patterns


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
            print(e)
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


def clean_permutation_func():
    def reshape_pattern(pattern_str):
        return [pattern_str[i:i + 3] for i in range(0, 9, 3)]

    def apply_transform(pattern_str, matrix):
        pattern_str = ''.join(c for c in pattern_str if c in '01')  # 关键修复行
        grid = reshape_pattern(pattern_str)
        flat = [grid[i // 3][i % 3] for i in range(9)]
        return ''.join(flat[matrix[i]] for i in range(9))

    return apply_transform


# 定义测试用例1
def testcase_1():
    class Dummy:
        pass

    self = Dummy()
    self._string_permute = clean_permutation_func()
    basic_pattern = "010010111"
    options = "4M"
    basic_result = 1

    return _pattern_permute(self, basic_pattern, options, basic_result)


# 定义测试用例2
def testcase_2():
    class Dummy:
        pass

    self = Dummy()
    self._string_permute = clean_permutation_func()
    basic_pattern = "101001000"
    options = "M"
    basic_result = 0

    return _pattern_permute(self, basic_pattern, options, basic_result)


def testcase_3():
    class Dummy:
        pass

    self = Dummy()
    self._string_permute = clean_permutation_func()
    basic_pattern = "111000111"
    options = "4N"
    basic_result = 1

    return _pattern_permute(self, basic_pattern, options, basic_result)


# 定义测试用例4
def testcase_4():
    class Dummy:
        pass

    self = Dummy()
    self._string_permute = clean_permutation_func()
    basic_pattern = "000111000"
    options = "N"
    basic_result = 0

    return _pattern_permute(self, basic_pattern, options, basic_result)


# 定义测试用例5
def testcase_5():
    class Dummy:
        pass

    self = Dummy()
    self._string_permute = clean_permutation_func()
    basic_pattern = "110110110"
    options = "4MN"
    basic_result = 1

    return _pattern_permute(self, basic_pattern, options, basic_result)


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
