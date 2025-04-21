import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import os
import json

script_dir = os.path.dirname(__file__)  # 脚本所在目录
target_dir = os.path.join(script_dir, "Supplement")  # 目标目录


def check_file_exists(directory, filename):
    file_path = os.path.join(directory, filename)
    return os.path.isfile(file_path)


def compare_json_with_string(json_file_path, input_string):
    try:
        # 将输入字符串解析为Python对象
        input_obj = json.loads(input_string)

        # 读取并解析JSON文件
        with open(json_file_path, 'r', encoding='utf-8') as f:
            file_obj = json.load(f)

        # 比较两个Python对象
        return input_obj == file_obj
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}")
        return False
    except Exception as e:
        print(f"发生错误: {e}")
        return False


#############change###########
def write_json(self, name, str):
    try:
        os.mkdir(os.path.join(self.data_dir))
    except OSError:
        pass
    file_path = os.path.join(self.data_dir, name)
    with open(file_path, 'w') as f:
        f.write(str)


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
    class Dummy:
        pass

    self = Dummy()
    self.data_dir = target_dir
    name = 'test_cart.json'
    str = json.dumps(
        [{"name": "Product A", "skus": "SKU123", "url": "http://example.com/productA", "price": "100", "num": "2"}])

    write_json(self, name, str)
    return check_file_exists(self.data_dir, name) & compare_json_with_string(os.path.join(self.data_dir, name), str)


# 定义测试用例2
def testcase_2():
    class Dummy:
        pass

    self = Dummy()
    self.data_dir = target_dir
    name = 'test_follow_shops.json'
    str = json.dumps(
        [{"name": "Shop A", "url": "http://example.com/shopA"}, {"name": "Shop B", "url": "http://example.com/shopB"}])

    write_json(self, name, str)
    return check_file_exists(self.data_dir, name) & compare_json_with_string(os.path.join(self.data_dir, name), str)


# 定义测试用例3
def testcase_3():
    class Dummy:
        pass

    self = Dummy()
    self.data_dir = target_dir
    name = 'test_income.json'
    str = '{"income": "5000"}'

    write_json(self, name, str)
    return check_file_exists(self.data_dir, name) & compare_json_with_string(os.path.join(self.data_dir, name), str)


# 定义测试用例4
def testcase_4():
    class Dummy:
        pass

    self = Dummy()
    self.data_dir = target_dir
    name = 'test_user_info.json'
    str = json.dumps([{"name": "User A", "credit_score": "750"}, {"name": "User B", "credit_score": "800"}])

    write_json(self, name, str)
    return check_file_exists(self.data_dir, name) & compare_json_with_string(os.path.join(self.data_dir, name), str)


# 定义测试用例5
def testcase_5():
    class Dummy:
        pass

    self = Dummy()
    name = 'test_orders.json'
    self.data_dir = target_dir
    str = json.dumps([{"order_id": "12345", "amount": "250", "goods-number": "3", "consignee tooltip": "John Doe",
                       "order-shop": "Shop A"}])

    write_json(self, name, str)
    return check_file_exists(self.data_dir, name) & compare_json_with_string(os.path.join(self.data_dir, name), str)


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
