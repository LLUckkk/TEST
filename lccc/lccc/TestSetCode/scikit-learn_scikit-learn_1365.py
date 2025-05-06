import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import numpy as np
from numba.tests.test_parallel_backend import linalg
from sklearn.covariance import empirical_covariance
from sklearn.utils import check_random_state, check_array


def select_candidates(
        X,
        h,
        n_trials,
        select=1,
        n_iter=2,
        cov_computation_method=empirical_covariance,
        random_state=None
):
    """用于从子集中选择候选MCD估计值（位置和协方差）"""
    random_state = check_random_state(random_state)
    n_samples, n_features = X.shape

    # 如果传入的是预定义的候选
    if isinstance(n_trials, tuple):
        locations_init, covariances_init = n_trials
        n_candidates = len(locations_init)
    else:
        # 随机抽取多个子集
        locations_init = np.zeros((n_trials, n_features))
        covariances_init = np.zeros((n_trials, n_features, n_features))
        for i in range(n_trials):
            subset_indices = random_state.choice(n_samples, h, replace=False)
            subset = X[subset_indices]
            try:
                location = subset.mean(axis=0)
                covariance = cov_computation_method(subset)
            except Exception:
                location = np.full(n_features, np.nan)
                covariance = np.full((n_features, n_features), np.nan)
            locations_init[i] = location
            covariances_init[i] = covariance
        n_candidates = n_trials

    # refine candidates using C-step
    supports = np.zeros((n_candidates, n_samples), dtype=bool)
    dists = np.zeros((n_candidates, n_samples))
    for i in range(n_candidates):
        location = locations_init[i]
        covariance = covariances_init[i]
        if np.any(np.isnan(location)) or np.any(np.isnan(covariance)):
            dists[i] = np.inf
            continue
        try:
            precision = linalg.pinvh(covariance)
        except Exception:
            dists[i] = np.inf
            continue
        for _ in range(n_iter):
            X_centered = X - location
            dist = np.sum((X_centered @ precision) * X_centered, axis=1)
            best_indices = np.argsort(dist)[:h]
            subset = X[best_indices]
            location = subset.mean(axis=0)
            covariance = cov_computation_method(subset)
            precision = linalg.pinvh(covariance)
        dists[i] = dist
        supports[i, best_indices] = True
        locations_init[i] = location
        covariances_init[i] = covariance

    # 选择表现最好的几个候选（平均距离最小）
    avg_dists = np.array([
        dists[i][supports[i]].mean() if np.any(supports[i]) else np.inf
        for i in range(dists.shape[0])
    ])
    best_indices = np.argsort(avg_dists)[:select]

    return (
        locations_init[best_indices],
        covariances_init[best_indices],
        supports[best_indices],
        dists[best_indices]
    )


#############change###########
def fast_mcd(
        X,
        support_fraction=None,
        cov_computation_method=empirical_covariance,
        random_state=None,
):
    random_state = check_random_state(random_state)

    X = check_array(X, ensure_min_samples=2, estimator="fast_mcd")
    n_samples, n_features = X.shape

    if support_fraction is None:
        n_support = min(int(np.ceil(0.5 * (n_samples + n_features + 1))), n_samples)
    else:
        n_support = int(support_fraction * n_samples)

    if n_features == 1:
        if n_support < n_samples:
            X_sorted = np.sort(np.ravel(X))
            diff = X_sorted[n_support:] - X_sorted[: (n_samples - n_support)]
            halves_start = np.where(diff == np.min(diff))[0]
            location = (
                    0.5
                    * (X_sorted[n_support + halves_start] + X_sorted[halves_start]).mean()
            )
            support = np.zeros(n_samples, dtype=bool)
            X_centered = X - location
            support[np.argsort(np.abs(X_centered), 0)[:n_support]] = True
            covariance = np.asarray([[np.var(X[support])]])
            location = np.array([location])
            precision = linalg.pinvh(covariance)
            dist = (np.dot(X_centered, precision) * (X_centered)).sum(axis=1)
        else:
            support = np.ones(n_samples, dtype=bool)
            covariance = np.asarray([[np.var(X)]])
            location = np.asarray([np.mean(X)])
            X_centered = X - location
            precision = linalg.pinvh(covariance)
            dist = (np.dot(X_centered, precision) * (X_centered)).sum(axis=1)
    if (n_samples > 500) and (n_features > 1):
        n_subsets = n_samples // 300
        n_samples_subsets = n_samples // n_subsets
        samples_shuffle = random_state.permutation(n_samples)
        h_subset = int(np.ceil(n_samples_subsets * (n_support / float(n_samples))))
        n_trials_tot = 500
        n_best_sub = 10
        n_trials = max(10, n_trials_tot // n_subsets)
        n_best_tot = n_subsets * n_best_sub
        all_best_locations = np.zeros((n_best_tot, n_features))
        try:
            all_best_covariances = np.zeros((n_best_tot, n_features, n_features))
        except MemoryError:
            n_best_tot = 10
            all_best_covariances = np.zeros((n_best_tot, n_features, n_features))
            n_best_sub = 2
        for i in range(n_subsets):
            low_bound = i * n_samples_subsets
            high_bound = low_bound + n_samples_subsets
            current_subset = X[samples_shuffle[low_bound:high_bound]]
            best_locations_sub, best_covariances_sub, _, _ = select_candidates(
                current_subset,
                h_subset,
                n_trials,
                select=n_best_sub,
                n_iter=2,
                cov_computation_method=cov_computation_method,
                random_state=random_state,
            )
            subset_slice = np.arange(i * n_best_sub, (i + 1) * n_best_sub)
            all_best_locations[subset_slice] = best_locations_sub
            all_best_covariances[subset_slice] = best_covariances_sub
        n_samples_merged = min(1500, n_samples)
        h_merged = int(np.ceil(n_samples_merged * (n_support / float(n_samples))))
        if n_samples > 1500:
            n_best_merged = 10
        else:
            n_best_merged = 1
        selection = random_state.permutation(n_samples)[:n_samples_merged]
        locations_merged, covariances_merged, supports_merged, d = select_candidates(
            X[selection],
            h_merged,
            n_trials=(all_best_locations, all_best_covariances),
            select=n_best_merged,
            cov_computation_method=cov_computation_method,
            random_state=random_state,
        )
        if n_samples < 1500:
            location = locations_merged[0]
            covariance = covariances_merged[0]
            support = np.zeros(n_samples, dtype=bool)
            dist = np.zeros(n_samples)
            support[selection] = supports_merged[0]
            dist[selection] = d[0]
        else:
            locations_full, covariances_full, supports_full, d = select_candidates(
                X,
                n_support,
                n_trials=(locations_merged, covariances_merged),
                select=1,
                cov_computation_method=cov_computation_method,
                random_state=random_state,
            )
            location = locations_full[0]
            covariance = covariances_full[0]
            support = supports_full[0]
            dist = d[0]
    elif n_features > 1:
        n_trials = 30
        n_best = 10
        locations_best, covariances_best, _, _ = select_candidates(
            X,
            n_support,
            n_trials=n_trials,
            select=n_best,
            n_iter=2,
            cov_computation_method=cov_computation_method,
            random_state=random_state,
        )
        locations_full, covariances_full, supports_full, d = select_candidates(
            X,
            n_support,
            n_trials=(locations_best, covariances_best),
            select=1,
            cov_computation_method=cov_computation_method,
            random_state=random_state,
        )
        location = locations_full[0]
        covariance = covariances_full[0]
        support = supports_full[0]
        dist = d[0]

    return location, covariance, support, dist


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
    X = np.random.rand(100, 5)
    support_fraction = 0.5
    cov_computation_method = empirical_covariance
    random_state = 42

    return fast_mcd(X, support_fraction, cov_computation_method, random_state, )


# 定义测试用例2
def testcase_2():
    X = np.random.rand(50, 3)
    support_fraction = 0.7
    cov_computation_method = empirical_covariance
    random_state = None

    return fast_mcd(X, support_fraction, cov_computation_method, random_state, )


# 定义测试用例3
def testcase_3():
    X = np.random.rand(200, 10)
    support_fraction = None
    cov_computation_method = empirical_covariance
    random_state = np.random.RandomState(0)

    return fast_mcd(X, support_fraction, cov_computation_method, random_state, )


# 定义测试用例4
def testcase_4():
    X = np.random.rand(300, 8)
    support_fraction = 0.6
    cov_computation_method = empirical_covariance
    random_state = 123

    return fast_mcd(X, support_fraction, cov_computation_method, random_state, )


# 定义测试用例5
def testcase_5():
    X = np.random.rand(150, 4)
    support_fraction = 0.8
    cov_computation_method = empirical_covariance
    random_state = np.random.RandomState(1)

    return fast_mcd(X, support_fraction, cov_computation_method, random_state, )


def main():
    # 执行所有测试用例
    test_results = {
        "ans1": safe_execute_testcase(testcase_1, timeout=5),
        "ans2": safe_execute_testcase(testcase_2, timeout=5),
        "ans3": safe_execute_testcase(testcase_3, timeout=5),
        "ans4": safe_execute_testcase(testcase_4, timeout=5),
        "ans5": safe_execute_testcase(testcase_5, timeout=5)
    }

    def json_serializable(obj):
        if isinstance(obj, tuple) or isinstance(obj, list):
            return [json_serializable(o) for o in obj]
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (int, float, str, bool)) or obj is None:
            return obj  # 这些类型本身就可以序列化
        else:
            return str(obj)  # Fallback：防止出错

    output = {
        "ans1": json_serializable(test_results["ans1"]["result"]) if test_results["ans1"]["success"] else None,
        "ans2": json_serializable(test_results["ans2"]["result"]) if test_results["ans2"]["success"] else None,
        "ans3": json_serializable(test_results["ans3"]["result"]) if test_results["ans3"]["success"] else None,
        "ans4": json_serializable(test_results["ans4"]["result"]) if test_results["ans4"]["success"] else None,
        "ans5": json_serializable(test_results["ans5"]["result"]) if test_results["ans5"]["success"] else None
    }

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
