import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager

from loguru import logger
import requests

import json
import pathlib
from typing import List
import shutil

path = "/path/to/api1"


def convert_result(result):
    if result is None:
        return None
    if isinstance(result, list):
        return [api.to_dict() for api in result]
    return result


def clean_test_dirs():
    test_dirs = [
        "/path/to/api1",
        "/path/to/api2",
        "/path/to/api3",
        "/path/to/api4",
        "/path/to/api5"
    ]
    for dir_path in test_dirs:
        shutil.rmtree(dir_path)

class API:
    def __init__(self, name, url, method):
        self.name = name
        self.url = url
        self.method = method

    def to_dict(self):
        return {
            "name": self.name,
            "url": self.url,
            "method": self.method
        }


#############change###########
def load_json() -> List[API]:
    json_path = pathlib.Path(path, 'api.json')
    if not json_path.exists():
        logger.error("Json file not exists!")
        raise ValueError

    with open(json_path.resolve(), mode="r", encoding="utf8") as j:
        try:
            datas = json.loads(j.read())
            APIs = [
                API(**data)
                for data in datas
            ]
            logger.success(f"api.json 加载完成 接口数:{len(APIs)}")
            return APIs
        except Exception as why:
            logger.error(f"Json file syntax error:{why}")
            raise ValueError


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
    global path
    path = "/path/to/api1"
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    with open(f'{path}/api.json', 'w', encoding='utf8') as f:
        json.dump([{"name": "API1", "url": "https://api1.example.com", "method": "GET"}], f)
    return load_json()


def testcase_2():
    global path
    path = "/path/to/api2"
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    with open(f'{path}/api.json', 'w', encoding='utf8') as f:
        json.dump([{"name": "API2", "url": "https://api2.example.com", "method": "POST"}], f)
    return load_json()


def testcase_3():
    global path
    path = "/path/to/api3"
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    with open(f'{path}/api.json', 'w', encoding='utf8') as f:
        json.dump([{"name": "API3", "url": "https://api3.example.com", "method": "PUT"}], f)
    return load_json()


def testcase_4():
    global path
    path = "/path/to/api4"
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    with open(f'{path}/api.json', 'w', encoding='utf8') as f:
        json.dump([{"name": "API4", "url": "https://api4.example.com", "method": "DELETE"}], f)
    return load_json()


def testcase_5():
    global path
    path = "/path/to/api5"
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    with open(f'{path}/api.json', 'w', encoding='utf8') as f:
        json.dump([{"name": "API5", "url": "https://api5.example.com", "method": "PATCH"}], f)
    return load_json()


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
        "ans1": convert_result(test_results["ans1"]["result"]),
        "ans2": convert_result(test_results["ans2"]["result"]),
        "ans3": convert_result(test_results["ans3"]["result"]),
        "ans4": convert_result(test_results["ans4"]["result"]),
        "ans5": convert_result(test_results["ans5"]["result"])
    }

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
    clean_test_dirs()
