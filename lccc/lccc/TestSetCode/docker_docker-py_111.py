import base64
import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import docker


class auth:
    @staticmethod
    def resolve_repository_name(name):
        # 假设仓库名是 "registry/repo:tag"
        # 返回 registry 和 repo_name
        parts = name.split(":")
        if len(parts) == 2:
            tag = parts[1]
            repo_name = parts[0]
        else:
            tag = None
            repo_name = parts[0]
        registry = "docker.io"  # 示例中使用 docker.io
        return registry, repo_name

    @staticmethod
    def get_config_header(self, registry):
        # 模拟认证头部（这里仅是示例，真实应用中可能需要从环境变量或配置文件读取）
        username = "your_username"
        password = "your_password"
        auth_value = base64.b64encode(f"{username}:{password}".encode()).decode("utf-8")
        return f"Basic {auth_value}"


#############change###########
def plugin_privileges(self, name):
    params = {
        'remote': name,
    }

    headers = {}
    registry, repo_name = auth.resolve_repository_name(name)
    header = auth.get_config_header(self, registry)
    if header:
        headers['X-Registry-Auth'] = header

    url = self._url('/plugins/privileges')
    return self._result(
        self._get(url, params=params, headers=headers), True
    )


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


# 定义测试用例1
def testcase_1():
    class Dummy:
        def _url(self, endpoint):
            # 模拟生成 URL，可以根据需要调整
            return f"http://localhost:5000{endpoint}"  # 示例 URL

        def _get(self, url, params=None, headers=None):
            # 模拟 GET 请求，这里可以使用 requests 来发送真实请求
            print(f"GET request to {url} with params={params} and headers={headers}")
            return {"status": "success"}  # 示例响应

        def _result(self, response, parse_json=True):
            # 模拟处理响应结果
            if parse_json:
                return response
            return response

    self = Dummy()
    name = "myplugin:latest"

    return plugin_privileges(self, name)


# 定义测试用例2
def testcase_2():
    class Dummy:
        def _url(self, endpoint):
            # 模拟生成 URL，可以根据需要调整
            return f"http://localhost:5000{endpoint}"  # 示例 URL

        def _get(self, url, params=None, headers=None):
            # 模拟 GET 请求，这里可以使用 requests 来发送真实请求
            print(f"GET request to {url} with params={params} and headers={headers}")
            return {"status": "success"}  # 示例响应

        def _result(self, response, parse_json=True):
            # 模拟处理响应结果
            if parse_json:
                return response
            return response

    self = Dummy()
    name = "exampleplugin"

    return plugin_privileges(self, name)


# 定义测试用例3
def testcase_3():
    class Dummy:
        def _url(self, endpoint):
            # 模拟生成 URL，可以根据需要调整
            return f"http://localhost:5000{endpoint}"  # 示例 URL

        def _get(self, url, params=None, headers=None):
            # 模拟 GET 请求，这里可以使用 requests 来发送真实请求
            print(f"GET request to {url} with params={params} and headers={headers}")
            return {"status": "success"}  # 示例响应

        def _result(self, response, parse_json=True):
            # 模拟处理响应结果
            if parse_json:
                return response
            return response

    self = Dummy()
    name = "customplugin:1.0"

    return plugin_privileges(self, name)


# 定义测试用例4
def testcase_4():
    class Dummy:
        def _url(self, endpoint):
            # 模拟生成 URL，可以根据需要调整
            return f"http://localhost:5000{endpoint}"  # 示例 URL

        def _get(self, url, params=None, headers=None):
            # 模拟 GET 请求，这里可以使用 requests 来发送真实请求
            print(f"GET request to {url} with params={params} and headers={headers}")
            return {"status": "success"}  # 示例响应

        def _result(self, response, parse_json=True):
            # 模拟处理响应结果
            if parse_json:
                return response
            return response

    self = Dummy()
    name = "networkplugin:2.3"

    return plugin_privileges(self, name)


# 定义测试用例5
def testcase_5():
    class Dummy:
        def _url(self, endpoint):
            # 模拟生成 URL，可以根据需要调整
            return f"http://localhost:5000{endpoint}"  # 示例 URL

        def _get(self, url, params=None, headers=None):
            # 模拟 GET 请求，这里可以使用 requests 来发送真实请求
            print(f"GET request to {url} with params={params} and headers={headers}")
            return {"status": "success"}  # 示例响应

        def _result(self, response, parse_json=True):
            # 模拟处理响应结果
            if parse_json:
                return response
            return response

    self = Dummy()
    name = "storageplugin"

    return plugin_privileges(self, name)


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
