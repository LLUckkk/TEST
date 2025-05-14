import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
from enum import Enum
from pathlib import Path

import requests

import tempfile
import os

from mlflow.utils.environment import _PythonEnv


#############change###########
def from_conda_yaml(cls, path):
    return cls.from_dict(cls.get_dependencies_from_conda_yaml(path))


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
    cls = _PythonEnv
    path = tempfile.NamedTemporaryFile(delete=False)
    path.write(b"""
    name: test_env
    channels:
      - defaults
    dependencies:
      - python=3.8
      - numpy
      - pip:
        - pandas
    """)
    path.close()
    path = path.name

    return from_conda_yaml(cls, path)


# 定义测试用例2
def testcase_2():
    cls = _PythonEnv
    path = tempfile.NamedTemporaryFile(delete=False)
    path.write(b"""
    name: example_env
    channels:
      - conda-forge
    dependencies:
      - python=3.9
      - scipy
      - pip:
        - scikit-learn
    """)
    path.close()
    path = path.name

    return from_conda_yaml(cls, path)


# 定义测试用例3
def testcase_3():
    cls = _PythonEnv
    path = tempfile.NamedTemporaryFile(delete=False)
    path.write(b"""
    name: data_env
    channels:
      - anaconda
    dependencies:
      - python=3.7
      - matplotlib
      - pip:
        - seaborn
    """)
    path.close()
    path = path.name

    return from_conda_yaml(cls, path)


# 定义测试用例4
def testcase_4():
    cls = _PythonEnv
    path = tempfile.NamedTemporaryFile(delete=False)
    path.write(b"""
    name: ml_env
    channels:
      - bioconda
    dependencies:
      - python=3.6
      - tensorflow
      - pip:
        - keras
    """)
    path.close()
    path = path.name

    return from_conda_yaml(cls, path)


# 定义测试用例5
def testcase_5():
    cls = _PythonEnv
    path = tempfile.NamedTemporaryFile(delete=False)
    path.write(b"""
    name: analysis_env
    channels:
      - conda-forge
    dependencies:
      - python=3.10
      - pandas
      - pip:
        - jupyter
    """)
    path.close()
    path = path.name

    return from_conda_yaml(cls, path)


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

    def python_env_serializer(obj):
        # 处理 pathlib.Path 类型
        if isinstance(obj, Path):
            return str(obj)

        # 处理 Enum 类型
        if isinstance(obj, Enum):
            return obj.value

        # 处理 _PythonEnv 或类似的对象
        if hasattr(obj, "__dict__"):
            return {
                key: python_env_serializer(value)
                for key, value in obj.__dict__.items()
                if not key.startswith("_")  # 可选：跳过私有属性
            }

        # 默认无法序列化的类型
        return str(obj)

    print(json.dumps(output, default=python_env_serializer, indent=2))


if __name__ == '__main__':
    main()
