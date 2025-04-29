import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import dagster
from dagster._core.definitions.events import AssetKey


#############change###########
def has_input_asset(self, key: "AssetKey") -> bool:
    return key in self.input_data_versions and key in self.input_storage_ids
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


# 定义测试用例1
def testcase_1():
    class Dummy:
        input_data_versions = {AssetKey(["asset_1"]): "v1"}
        input_storage_ids = {AssetKey(["asset_1"]): "id1"}

    self = Dummy()
    key = AssetKey(["asset_1"])
    return has_input_asset(self, key)


# 定义测试用例2
def testcase_2():
    class Dummy:
        input_data_versions = {AssetKey(["asset_2"]): "v2"}
        input_storage_ids = {AssetKey(["asset_2"]): "id2"}

    self = Dummy()
    key = AssetKey(["asset_2"])
    return has_input_asset(self, key)


# 定义测试用例3
def testcase_3():
    class Dummy:
        input_data_versions = {AssetKey(["asset_3"]): "v3"}
        input_storage_ids = {}  # 缺少storage_id

    self = Dummy()
    key = AssetKey(["asset_3"])
    return has_input_asset(self, key)


# 定义测试用例4
def testcase_4():
    class Dummy:
        input_data_versions = {}  # 缺少data_version
        input_storage_ids = {AssetKey(["asset_4"]): "id4"}

    self = Dummy()
    key = AssetKey(["asset_4"])
    return has_input_asset(self, key)


# 定义测试用例5
def testcase_5():
    class Dummy:
        input_data_versions = {AssetKey(["asset_5"]): "v5", AssetKey(["other_asset"]): "v6"}
        input_storage_ids = {AssetKey(["asset_5"]): "id5", AssetKey(["other_asset"]): "id6"}

    self = Dummy()
    key = AssetKey(["asset_5"])
    return has_input_asset(self, key)


def main():
    test_results = {
        "ans1": safe_execute_testcase(testcase_1, timeout=5),
        "ans2": safe_execute_testcase(testcase_2, timeout=5),
        "ans3": safe_execute_testcase(testcase_3, timeout=5),
        "ans4": safe_execute_testcase(testcase_4, timeout=5),
        "ans5": safe_execute_testcase(testcase_5, timeout=5)
    }

    output = {
        "ans1": test_results["ans1"]["result"],
        "ans2": test_results["ans2"]["result"],
        "ans3": test_results["ans3"]["result"],
        "ans4": test_results["ans4"]["result"],
        "ans5": test_results["ans5"]["result"]
    }

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()