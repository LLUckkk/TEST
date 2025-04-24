import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import pandas as pd
from sqlalchemy import create_engine, Integer, String, Float, Text
from pandas.api.types import is_list_like
from typing import Any
import pymysql
import psycopg2


#############change###########
def _create_table_setup(self):
    from sqlalchemy import (
        Column,
        PrimaryKeyConstraint,
        Table,
    )
    from sqlalchemy.schema import MetaData

    column_names_and_types = self._get_column_names_and_types(self._sqlalchemy_type)

    columns: list[Any] = [
        Column(name, typ, index=is_index)
        for name, typ, is_index in column_names_and_types
    ]

    if self.keys is not None:
        if not is_list_like(self.keys):
            keys = [self.keys]
        else:
            keys = self.keys
        pkc = PrimaryKeyConstraint(*keys, name=self.name + "_pk")
        columns.append(pkc)

    schema = self.schema or self.pd_sql.meta.schema

    meta = MetaData()
    return Table(self.name, meta, *columns, schema=schema)


#############change###########

def _get_column_names_and_types(self, sqlalchemy_type):
    """模拟获取列名和类型的方法"""
    column_types = {
        'INTEGER': Integer,
        'TEXT': Text,
        'VARCHAR': String,
        'FLOAT': Float,
        'STRING': String
    }

    columns = []
    for col in self.frame.columns:
        if col in self.dtype:
            typ = column_types.get(self.dtype[col].upper(), String)
        else:
            typ = String  # 默认类型

        # 检查是否是索引列
        is_index = (self.index is True) or (is_list_like(self.index) and col in self.index)
        columns.append((col, typ, is_index))

    return columns


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
                print(e)
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
    self.name = "test_table"
    self.pd_sql = type('', (), {'meta': type('', (), {'schema': None})})()
    self.frame = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
    self.index = True
    self.if_exists = "fail"
    self.prefix = "pandas"
    self.index_label = None
    self.schema = None
    self.keys = ["col1"]
    self.dtype = {"col1": "INTEGER", "col2": "TEXT"}
    self._sqlalchemy_type = None
    self._get_column_names_and_types = lambda x: _get_column_names_and_types(self, x)

    return _create_table_setup(self)


# 定义测试用例2
def testcase_2():
    class Dummy:
        pass

    self = Dummy()
    self.name = "sample_table"
    self.pd_sql = type('', (), {'meta': type('', (), {'schema': None})})()
    self.frame = pd.DataFrame({"id": [1, 2, 3], "value": [10.5, 20.5, 30.5]})
    self.index = ["id"]
    self.if_exists = "replace"
    self.prefix = "sample"
    self.index_label = None
    self.schema = "public"
    self.keys = ["id"]
    self.dtype = {"id": "INTEGER", "value": "FLOAT"}
    self._sqlalchemy_type = None
    self._get_column_names_and_types = lambda x: _get_column_names_and_types(self, x)

    return _create_table_setup(self)


# 定义测试用例3
def testcase_3():
    class Dummy:
        pass

    self = Dummy()
    self.name = "data_table"
    self.pd_sql = type('', (), {'meta': type('', (), {'schema': None})})()
    self.frame = pd.DataFrame({"name": ["Alice", "Bob"], "age": [25, 30]})
    self.index = False
    self.if_exists = "append"
    self.prefix = "data"
    self.index_label = None
    self.schema = "public"
    self.keys = ["name"]
    self.dtype = {"name": "VARCHAR", "age": "INTEGER"}
    self._sqlalchemy_type = None
    self._get_column_names_and_types = lambda x: _get_column_names_and_types(self, x)

    return _create_table_setup(self)


# 定义测试用例4
def testcase_4():
    class Dummy:
        pass

    self = Dummy()
    self.name = "info_table"
    self.pd_sql = type('', (), {'meta': type('', (), {'schema': None})})()
    self.frame = pd.DataFrame({"id": [1, 2], "description": ["test1", "test2"]})
    self.index = ["id"]
    self.if_exists = "fail"
    self.prefix = "info"
    self.index_label = None
    self.schema = "test_schema"
    self.keys = ["id"]
    self.dtype = {"id": "INTEGER", "description": "TEXT"}
    self._sqlalchemy_type = None
    self._get_column_names_and_types = lambda x: _get_column_names_and_types(self, x)

    return _create_table_setup(self)


# 定义测试用例5
def testcase_5():
    class Dummy:
        pass

    self = Dummy()
    self.name = "records_table"
    self.pd_sql = type('', (), {'meta': type('', (), {'schema': None})})()
    self.frame = pd.DataFrame({"record_id": [100, 200], "record_value": [5.5, 6.5]})
    self.index = ["record_id"]
    self.if_exists = "replace"
    self.prefix = "records"
    self.index_label = None
    self.schema = None
    self.keys = ["record_id"]
    self.dtype = {"record_id": "INTEGER", "record_value": "FLOAT"}
    self._sqlalchemy_type = None
    self._get_column_names_and_types = lambda x: _get_column_names_and_types(self, x)

    return _create_table_setup(self)


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
        "ans1": str(test_results["ans1"]["result"]) if test_results["ans1"]["success"] else None,
        "ans2": str(test_results["ans2"]["result"]) if test_results["ans2"]["success"] else None,
        "ans3": str(test_results["ans3"]["result"]) if test_results["ans3"]["success"] else None,
        "ans4": str(test_results["ans4"]["result"]) if test_results["ans4"]["success"] else None,
        "ans5": str(test_results["ans5"]["result"]) if test_results["ans5"]["success"] else None
    }

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
