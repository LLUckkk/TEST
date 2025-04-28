import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import optuna
from optuna import create_study, Study
from optuna.samplers import RandomSampler
optuna.logging.set_verbosity(optuna.logging.WARNING)


def objective(trial: optuna.Trial) -> float:
    """单目标优化函数示例"""
    x = trial.suggest_float('x', -10, 10)
    return (x - 2) ** 2  # 简单的抛物线最小值在x=2处


def multi_objective_function(trial: optuna.Trial) -> list:
    """多目标优化函数示例"""
    x = trial.suggest_float('x', -10, 10)
    y = trial.suggest_float('y', -10, 10)
    obj1 = (x - 2) ** 2 + (y + 3) ** 2  # 第一个目标：最小化
    obj2 = (x + 1) ** 2 + (y - 4) ** 2  # 第二个目标：也最小化
    return [obj1, obj2]


#############change###########
def get_study(seed: int, n_trials: int, is_multi_obj: bool) -> Study:
    directions = ["minimize", "minimize"] if is_multi_obj else ["minimize"]
    study = create_study(sampler=RandomSampler(seed=seed), directions=directions)
    if is_multi_obj:
        study.optimize(multi_objective_function, n_trials=n_trials)
    else:
        study.optimize(objective, n_trials=n_trials)

    return study


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
    seed = 42
    n_trials = 10
    is_multi_obj = False

    return get_study(seed, n_trials, is_multi_obj)


# 定义测试用例2
def testcase_2():
    seed = 123
    n_trials = 50
    is_multi_obj = True

    return get_study(seed, n_trials, is_multi_obj)


# 定义测试用例3
def testcase_3():
    seed = 0
    n_trials = 5
    is_multi_obj = False

    return get_study(seed, n_trials, is_multi_obj)


# 定义测试用例4
def testcase_4():
    seed = 7
    n_trials = 20
    is_multi_obj = True

    return get_study(seed, n_trials, is_multi_obj)


# 定义测试用例5
def testcase_5():
    seed = 99
    n_trials = 100
    is_multi_obj = False

    return get_study(seed, n_trials, is_multi_obj)


def main():
    # 执行所有测试用例
    test_results = {
        "ans1": safe_execute_testcase(testcase_1, timeout=5),
        "ans2": safe_execute_testcase(testcase_2, timeout=5),
        "ans3": safe_execute_testcase(testcase_3, timeout=5),
        "ans4": safe_execute_testcase(testcase_4, timeout=5),
        "ans5": safe_execute_testcase(testcase_5, timeout=5)
    }

    output = {}

    for key, result in test_results.items():
        if result['success']:
            study = result['result']
            if isinstance(study, Study):
                if study.directions[0] == "minimize" and len(study.directions) == 1:
                    # 单目标
                    output[key] = study.best_value
                else:
                    # 多目标
                    output[key] = [trial.values for trial in study.best_trials]
            else:
                output[key] = str(study)  # 万一是别的奇怪的类型
        else:
            output[key] = None  # 超时或者异常

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    main()
