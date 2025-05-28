import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

from typing import Optional


#############change###########
def load(
        self,
        mode: Optional[str] = None,
        vocab_parallel: bool = False,
        parallel_input_1d: bool = False,
        summa_dim: int = None,
        tesseract_dim: int = None,
        tesseract_dep: int = None,
        depth_3d: int = None,
        input_group_3d=None,
        weight_group_3d=None,
        output_group_3d=None,
        input_x_weight_group_3d=None,
        output_x_weight_group_3d=None,
):
    self.mode = mode
    self.vocab_parallel = vocab_parallel
    self.parallel_input_1d = parallel_input_1d
    self.summa_dim = summa_dim
    self.tesseract_dim = tesseract_dim
    self.tesseract_dep = tesseract_dep
    self.depth_3d = depth_3d
    self.input_group_3d = input_group_3d
    self.weight_group_3d = weight_group_3d
    self.output_group_3d = output_group_3d
    self.input_x_weight_group_3d = input_x_weight_group_3d
    self.output_x_weight_group_3d = output_x_weight_group_3d


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


def safe_serialize(obj):
    """安全的对象序列化：将对象转为字典并过滤不可序列化的属性"""
    try:
        if isinstance(obj, (int, float, str, bool, type(None))):
            return obj
        elif isinstance(obj, (list, tuple)):
            return [safe_serialize(i) for i in obj]
        elif isinstance(obj, dict):
            return {k: safe_serialize(v) for k, v in obj.items()}
        elif hasattr(obj, '__dict__'):
            return {k: safe_serialize(v) for k, v in vars(obj).items()}
        else:
            return str(obj)
    except Exception as e:
        return f"<Unserializable: {e}>"


# ✅ 修改每个测试用例，返回 self
def testcase_1():
    class Dummy: pass

    self = Dummy()
    load(self, "train", True, False, 4, 8, 2, 3, [1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12], [13, 14, 15])
    return self


def testcase_2():
    class Dummy: pass

    self = Dummy()
    load(self, "test", False, True, 2, 4, 1, 1, [1], [2], [3], [4], [5])
    return self


def testcase_3():
    class Dummy: pass

    self = Dummy()
    load(self, "validation", False, False, 6, 12, 3, 4, [1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12], [13, 14, 15, 16],
         [17, 18, 19, 20])
    return self


def testcase_4():
    class Dummy: pass

    self = Dummy()
    load(self, None, True, True, 3, 6, 2, 2, [1, 2], [3, 4], [5, 6], [7, 8], [9, 10])
    return self


def testcase_5():
    class Dummy: pass

    self = Dummy()
    load(self, "deploy", False, False, 5, 10, 4, 5, [1, 2, 3, 4, 5], [6, 7, 8, 9, 10], [11, 12, 13, 14, 15],
         [16, 17, 18, 19, 20], [21, 22, 23, 24, 25])
    return self


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
        key: safe_serialize(result["result"]) if result["success"] else {"error": result["error"]}
        for key, result in test_results.items()
    }

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
