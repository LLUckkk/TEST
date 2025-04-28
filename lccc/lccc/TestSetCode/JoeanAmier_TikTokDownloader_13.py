import json
import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import json
from pathlib import Path

from rich.console import Console


#############change###########
def __create(self) -> dict:
    with self.file.open("w", encoding=self.encode) as f:
        json.dump(self.default, f, indent=4, ensure_ascii=False)
    self.console.log(
        ("创建默认配置文件 settings.json 成功！\n"
         "请参考项目文档的快速入门部分，设置 Cookie 后重新运行程序！\n"
         "建议根据实际使用需求修改配置文件 settings.json！\n"),
    )
    return self.default


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
        pass

    self = Dummy()
    self.file = Path("settings.json")
    self.encode = "utf-8"
    self.default = {
        "api_key": "your_api_key",
        "timeout": 30,
        "retry": 3,
        "log_level": "INFO"
    }
    self.console = Console()

    return __create(self)


# 定义测试用例2
def testcase_2():
    class Dummy:
        pass

    self = Dummy()
    self.file = Path("settings.json")
    self.encode = "utf-8"
    self.default = {
        "username": "admin",
        "password": "password123",
        "host": "localhost",
        "port": 8080
    }
    self.console = Console()

    return __create(self)


# 定义测试用例3
def testcase_3():
    class Dummy:
        pass

    self = Dummy()
    self.file = Path("settings.json")
    self.encode = "utf-8"
    self.default = {
        "theme": "dark",
        "language": "en",
        "notifications": True,
        "auto_update": False
    }
    self.console = Console()

    return __create(self)


# 定义测试用例4
def testcase_4():
    class Dummy:
        pass

    self = Dummy()
    self.file = Path("settings.json")
    self.encode = "utf-8"
    self.default = {
        "max_connections": 10,
        "min_connections": 1,
        "connection_timeout": 60,
        "use_ssl": True
    }
    self.console = Console()

    return __create(self)


# 定义测试用例5
def testcase_5():
    class Dummy:
        pass

    self = Dummy()
    self.file = Path("settings.json")
    self.encode = "utf-8"
    self.default = {
        "backup_interval": "daily",
        "backup_location": "/backups",
        "backup_retention": 30,
        "backup_compression": "zip"
    }
    self.console = Console()

    return __create(self)


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
