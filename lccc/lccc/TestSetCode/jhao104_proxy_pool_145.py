import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager

import requests
from requests.models import Response


#############change###########
def get(self, url, header=None, retry_time=3, retry_interval=5, timeout=5, *args, **kwargs):
    headers = self.header
    if header and isinstance(header, dict):
        headers.update(header)
    while True:
        try:
            self.response = requests.get(url, headers=headers, timeout=timeout, *args, **kwargs)
            return self
        except Exception as e:
            #self.log.error("requests: %s error: %s" % (url, str(e)))
            retry_time -= 1
            if retry_time <= 0:
                resp = Response()
                resp.status_code = 200
                return self
            self.log.info("retry %s second after" % retry_interval)
            time.sleep(retry_interval)
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
    event = threading.Event()

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
            if not event.is_set():
                result_queue.put(('error', e))
        finally:
            event.set()

    t = threading.Thread(target=worker)
    t.daemon = True
    start_time = time.time()
    t.start()

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


# 创建包含必要属性的 Dummy 对象
class Dummy:
    def __init__(self):
        self.header = {}
        self.response = None
        self.log = self.Logger()

    class Logger:
        def error(self, msg):
            print("[ERROR]", msg)

        def info(self, msg):
            print("[INFO]", msg)


# 构造测试用例函数
def create_testcase(url, header, retry_time, retry_interval, timeout):
    def testcase():
        obj = Dummy()
        return get(obj, url, header, retry_time, retry_interval, timeout).response
    return testcase


# 测试用例配置
testcases = {
    "ans1": create_testcase("https://example.com", {"User-Agent": "Mozilla/5.0"}, 3, 5, 10),
    "ans2": create_testcase("https://api.github.com", {"Authorization": "token YOUR_ACCESS_TOKEN"}, 2, 3, 7),
    "ans3": create_testcase("https://jsonplaceholder.typicode.com/posts", None, 5, 2, 8),
    "ans4": create_testcase("https://httpbin.org/get", {"Accept": "application/json"}, 1, 1, 4),
    "ans5": create_testcase("https://api.openweathermap.org/data/2.5/weather?q=London&appid=YOUR_API_KEY",
                            {"Content-Type": "application/json"}, 4, 6, 12)
}


def extract_response_content(response):
    if response is None:
        return None
    try:
        return response.json()
    except Exception:
        return response.text


def main():
    results = {}
    for key, testcase in testcases.items():
        outcome = safe_execute_testcase(testcase, timeout=5)
        if outcome["success"]:
            results[key] = extract_response_content(outcome["result"])
        else:
            results[key] = {
                "error": outcome["error"],
                "traceback": outcome["traceback"]
            }

    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
