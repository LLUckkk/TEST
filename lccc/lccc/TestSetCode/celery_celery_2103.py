import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
from heapq import heappush

import requests

import time


class LimitedSet:
    def __init__(self, maxlen=None):
        self.maxlen = maxlen
        self._data = {}  # item -> (timestamp, item)
        self._heap = []  # list of (timestamp, item)

    def discard(self, item):
        """从数据字典中移除元素"""
        self._data.pop(item, None)

    def purge(self):
        """当数量超限时，移除时间最早的元素"""
        while self.maxlen and len(self._data) > self.maxlen:
            # 从堆中弹出旧的项，确保它依然在字典中才删除
            timestamp, item = self._heap[0]
            if self._data.get(item) == (timestamp, item):
                self.discard(item)
                self._heap.pop(0)  # 不使用 heapq.heappop 是为了更简单实现
            else:
                break  # 堆顶无效项，终止


#############change###########
def add(self, item, now=None):
    now = now or time.monotonic()
    if item in self._data:
        self.discard(item)
    entry = (now, item)
    self._data[item] = entry
    heappush(self._heap, entry)
    if self.maxlen and len(self._data) >= self.maxlen:
        self.purge()


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


def testcase_1():
    self = LimitedSet(maxlen=5)
    item = 'apple'
    now = time.monotonic()
    add(self, item, now)
    return list(self._data.keys())


def testcase_2():
    self = LimitedSet(maxlen=10)
    item = 'banana'
    now = None
    add(self, item, now)
    return list(self._data.keys())


def testcase_3():
    self = LimitedSet(maxlen=3)
    item = 42
    now = time.monotonic() + 100
    add(self, item, now)
    return list(self._data.keys())


def testcase_4():
    self = LimitedSet(maxlen=7)
    item = 'grape'
    now = None
    add(self, item, now)
    return list(self._data.keys())


def testcase_5():
    self = LimitedSet(maxlen=15)
    item = 'orange'
    now = time.monotonic() - 50
    add(self, item, now)
    return list(self._data.keys())


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
