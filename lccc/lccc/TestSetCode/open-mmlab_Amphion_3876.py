import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import torch
import numpy as np
import os


def cleanup_saved_files(result_paths):
    for path in result_paths:
        if path and os.path.exists(path):
            os.remove(path)


def create_dummy(extractor_type="hubert", processed_dir="./processed"):
    class PreprocessConfig:
        def __init__(self, processed_dir):
            self.processed_dir = processed_dir

    class Config:
        def __init__(self, processed_dir):
            self.preprocess = PreprocessConfig(processed_dir)

    class Dummy:
        def __init__(self):
            self.extractor_type = extractor_type
            self.cfg = Config(processed_dir)

        # Mock 实现 get_valid_features，真实情况请替换为你自己的逻辑
        def get_valid_features(self, utt, content_feature):
            return content_feature

    return Dummy()


#############change###########
def save_feature(self, utt, content_feature):
    uid = utt["Uid"]
    assert self.extractor_type != None
    out_dir = os.path.join(
        self.cfg.preprocess.processed_dir, utt["Dataset"], self.extractor_type
    )
    os.makedirs(out_dir, exist_ok=True)
    save_path = os.path.join(out_dir, uid + ".npy")

    content_feature = self.get_valid_features(utt, content_feature)
    np.save(save_path, content_feature.cpu().detach().numpy())


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
    self = create_dummy()
    utt = {
        "Uid": "utterance_001",
        "Dataset": "dataset_A"
    }
    content_feature = torch.rand(256, 512)
    save_feature(self, utt, content_feature)
    return os.path.join("./processed", "dataset_A", "hubert", "utterance_001.npy")


# 定义测试用例2
def testcase_2():
    self = create_dummy()
    utt = {
        "Uid": "utterance_002",
        "Dataset": "dataset_B"
    }
    content_feature = torch.rand(128, 256)
    save_feature(self, utt, content_feature)
    return os.path.join("./processed", "dataset_B", "hubert", "utterance_002.npy")


# 定义测试用例3
def testcase_3():
    self = create_dummy()
    utt = {
        "Uid": "utterance_003",
        "Dataset": "dataset_C"
    }
    content_feature = torch.rand(512, 1024)
    save_feature(self, utt, content_feature)
    return os.path.join("./processed", "dataset_C", "hubert", "utterance_003.npy")


# 定义测试用例4
def testcase_4():
    self = create_dummy()
    utt = {
        "Uid": "utterance_004",
        "Dataset": "dataset_D"
    }
    content_feature = torch.rand(64, 128)
    save_feature(self, utt, content_feature)
    return os.path.join("./processed", "dataset_D", "hubert", "utterance_004.npy")


# 定义测试用例5
def testcase_5():
    self = create_dummy()
    utt = {
        "Uid": "utterance_005",
        "Dataset": "dataset_E"
    }
    content_feature = torch.rand(1024, 2048)
    save_feature(self, utt, content_feature)
    return os.path.join("./processed", "dataset_E", "hubert", "utterance_005.npy")


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

    cleanup_saved_files([output["ans1"], output["ans2"], output["ans3"], output["ans4"], output["ans5"]])


if __name__ == '__main__':
    main()
