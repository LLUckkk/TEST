import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import argparse
from typing import Union, Dict, Any
import os

import logging

logger = logging.getLogger(__name__)  # 获取当前模块的 logger


def build_test_parser():
    parser = argparse.ArgumentParser(description="Test parser")
    parser.add_argument('--srtin', nargs='+', default=['input.srt'])
    parser.add_argument('--srtout', default='output.srt')
    parser.add_argument('--make_test_case', action='store_true')
    parser.add_argument('--log_dir_path', default=None)
    parser.add_argument('--gui_mode', action='store_true')
    parser.add_argument('--skip_ssa_info', action='store_true')
    return parser


def validate_and_transform_args(
        parser_or_args: Union[argparse.ArgumentParser, argparse.Namespace]) -> argparse.Namespace:
    """验证并转换传入的参数"""
    if isinstance(parser_or_args, argparse.ArgumentParser):
        return None  # 如果是解析器对象，返回 None
    return parser_or_args  # 如果是参数对象，直接返回


def _setup_logging(args: argparse.Namespace):
    """设置日志配置"""
    log_path = "default_log_path.log"  # 默认日志路径
    log_handler = logging.FileHandler(log_path)
    log_handler.setLevel(logging.DEBUG)
    logger = logging.getLogger()
    logger.addHandler(log_handler)
    return log_path, log_handler


def _run_impl(args: argparse.Namespace, result: Dict[str, Any]) -> bool:
    """实现具体的同步操作"""
    # 示例实现，可能需要根据实际需求进行修改
    # 假设 sync_was_successful 是同步成功与否的标志
    sync_was_successful = True
    if args.make_test_case:
        print("Making test case...")
    return sync_was_successful


def make_test_case(args: argparse.Namespace, npy_savename: str, sync_was_successful: bool) -> int:
    """生成测试用例"""
    if sync_was_successful:
        print(f"Test case {npy_savename} created successfully!")
        return 0
    else:
        print(f"Failed to create test case {npy_savename}.")
        return 1


def _npy_savename(args: argparse.Namespace) -> str:
    """生成保存 .npy 文件的文件名"""
    return "output.npy"


#############change###########
def run(
        parser_or_args: Union[argparse.ArgumentParser, argparse.Namespace]
) -> Dict[str, Any]:
    sync_was_successful = False
    result = {
        "retval": 0,
        "offset_seconds": None,
        "framerate_scale_factor": None,
    }
    args = validate_and_transform_args(parser_or_args)
    if args is None:
        result["retval"] = 1
        return result
    log_path, log_handler = _setup_logging(args)
    try:
        sync_was_successful = _run_impl(args, result)
        result["sync_was_successful"] = sync_was_successful
        return result
    finally:
        if log_handler is not None and log_path is not None:
            log_handler.close()
            logger.removeHandler(log_handler)
            if args.make_test_case:
                result["retval"] += make_test_case(
                    args, _npy_savename(args), sync_was_successful
                )
            if args.log_dir_path is None or not os.path.isdir(args.log_dir_path):
                os.remove(log_path)


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
# 改进版 testcases

def testcase_1():
    """基本正常流程，make_test_case = False, log_dir_path存在"""
    args = argparse.Namespace(
        srtin=['input1.srt', 'input2.srt'],
        srtout='output1.srt',
        make_test_case=False,
        log_dir_path='/tmp'  # 假设 /tmp 存在
    )
    return run(args)


def testcase_2():
    """测试 make_test_case = True，log_dir_path=None（测试自动删除log文件的逻辑）"""
    args = argparse.Namespace(
        srtin=['input2.srt'],
        srtout='output2.srt',
        make_test_case=True,
        log_dir_path=None
    )
    return run(args)


def testcase_3():
    """测试 log_dir_path 指向一个不存在的目录（应该会删除log文件）"""
    args = argparse.Namespace(
        srtin=['input3.srt'],
        srtout='output3.srt',
        make_test_case=False,
        log_dir_path='/nonexistent_directory_for_test'
    )
    return run(args)


def testcase_4():
    """测试输入文件列表为空（测试 validate_and_transform_args 的参数检查）"""
    args = argparse.Namespace(
        srtin=[],  # 故意传空
        srtout='output4.srt',
        make_test_case=True,
        log_dir_path='/tmp'
    )
    return run(args)


def testcase_5():
    """测试缺少 make_test_case 字段（测试兼容性）"""
    args = argparse.Namespace(
        srtin=['input5.srt'],
        srtout='output5.srt',
        log_dir_path='/tmp'
        # 故意不加 make_test_case，测试默认处理
    )
    return run(args)


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
