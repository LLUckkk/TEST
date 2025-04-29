import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests
import dataclasses
from typing import Any


@dataclasses.dataclass
class ExampleClass:
    connector_id: str
    service: str
    schemas: dict
    name: str
    connector_url: str
    database: str

    def _asdict(self):
        return {
            "connector_id": self.connector_id,
            "service": self.service,
            "schemas": self.schemas,
            "name": self.name,
            "connector_url": self.connector_url,
            "database": self.database,
        }


#############change###########
def to_serializable_repr(self) -> Any:
    return self._asdict()


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
        def _asdict(self):
            return ExampleClass(
                connector_id="connector_123",
                service="example_service",
                schemas={"schemas": {"schema1": {"enabled": True, "name_in_destination": "schema1_dest", "tables": {
                    "table1": {"enabled": True, "name_in_destination": "table1_dest"}}}}},
                name="example_name",
                connector_url="http://example.com",
                database="example_db"
            )._asdict()

    return to_serializable_repr(Dummy())


# 定义测试用例2
def testcase_2():
    class Dummy:
        def _asdict(self):
            return ExampleClass(
                connector_id="connector_456",
                service="another_service",
                schemas={"schemas": {"schema2": {"enabled": False, "name_in_destination": "schema2_dest", "tables": {
                    "table2": {"enabled": False, "name_in_destination": "table2_dest"}}}}},
                name="another_name",
                connector_url="http://another.com",
                database="another_db"
            )._asdict()

    return to_serializable_repr(Dummy())


# 定义测试用例3
def testcase_3():
    class Dummy:
        def _asdict(self):
            return ExampleClass(
                connector_id="connector_789",
                service="third_service",
                schemas={"schemas": {"schema3": {"enabled": True, "name_in_destination": "schema3_dest", "tables": {
                    "table3": {"enabled": True, "name_in_destination": "table3_dest"}}}}},
                name="third_name",
                connector_url="http://third.com",
                database="third_db"
            )._asdict()

    return to_serializable_repr(Dummy())


# 定义测试用例4
def testcase_4():
    class Dummy:
        def _asdict(self):
            return ExampleClass(
                connector_id="connector_101",
                service="fourth_service",
                schemas={"schemas": {"schema4": {"enabled": False, "name_in_destination": "schema4_dest", "tables": {
                    "table4": {"enabled": True, "name_in_destination": "table4_dest"}}}}},
                name="fourth_name",
                connector_url="http://fourth.com",
                database="fourth_db"
            )._asdict()

    return to_serializable_repr(Dummy())


# 定义测试用例5
def testcase_5():
    class Dummy:
        def _asdict(self):
            return ExampleClass(
                connector_id="connector_202",
                service="fifth_service",
                schemas={"schemas": {"schema5": {"enabled": True, "name_in_destination": "schema5_dest", "tables": {
                    "table5": {"enabled": False, "name_in_destination": "table5_dest"}}}}},
                name="fifth_name",
                connector_url="http://fifth.com",
                database="fifth_db")._asdict()

    return to_serializable_repr(Dummy())


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
