import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests


#############change###########
def in_cache(self, organization_id, feature_id):
    org_key = self.key_tpl.format(organization_id)
    return self.get_client(org_key).sismember(org_key, feature_id)


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


# 伪造的 Redis 客户端
class FakeRedisClient:
    def __init__(self, data):
        self.data = data

    def sismember(self, key, feature_id):
        return feature_id in self.data.get(key, set())


# 为 Dummy 增加 key_tpl 和 get_client 方法
def make_dummy(data_map):
    class Dummy:
        key_tpl = "org:{}"

        def get_client(self, org_key):
            return FakeRedisClient(data_map)

    return Dummy()


# 组织的伪造数据：假设每个 org key 下都有一个 feature_id 集合
fake_data = {
    "org:1": {101},
    "org:2": {202},
    "org:3": set(),
    "org:4": {999},
    "org:5": {505, 506}
}


# 定义测试用例们
def testcase_1():
    self = make_dummy(fake_data)
    return in_cache(self, 1, 101)  # True

def testcase_2():
    self = make_dummy(fake_data)
    return in_cache(self, 2, 202)  # True

def testcase_3():
    self = make_dummy(fake_data)
    return in_cache(self, 3, 303)  # False

def testcase_4():
    self = make_dummy(fake_data)
    return in_cache(self, 4, 404)  # False

def testcase_5():
    self = make_dummy(fake_data)
    return in_cache(self, 5, 505)  # True



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
