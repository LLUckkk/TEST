import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import numpy as np
import scipy.sparse as sp
from sklearn.svm import SVC
from sklearn.svm._base import LIBSVM_IMPL


#############mock sparse libsvm decision function###########
class libsvm_sparse:
    @staticmethod
    def libsvm_sparse_decision_function(*args, **kwargs):
        # 简单模拟返回值：根据输入行数返回一个浮点数组
        n_samples = len(args[3]) // 3  # 粗略估计样本数量
        return np.linspace(-1, 1, num=n_samples)  # dummy decision values


#############end mock###########


#############change###########
def _sparse_decision_function(self, X):
    X.data = np.asarray(X.data, dtype=np.float64, order="C")

    kernel = self.kernel
    if hasattr(kernel, "__call__"):
        kernel = "precomputed"

    kernel_type = self._sparse_kernels.index(kernel)

    return libsvm_sparse.libsvm_sparse_decision_function(
        X.data,
        X.indices,
        X.indptr,
        self.support_vectors_.data,
        self.support_vectors_.indices,
        self.support_vectors_.indptr,
        self._dual_coef_.data,
        self._intercept_,
        LIBSVM_IMPL.index(self._impl),
        kernel_type,
        self.degree,
        self._gamma,
        self.coef0,
        self.tol,
        self.C,
        getattr(self, "class_weight_", np.empty(0)),
        self.nu,
        self.epsilon,
        self.shrinking,
        self.probability,
        self._n_support,
        self._probA,
        self._probB,
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
    X = sp.csr_matrix([[0, 1, 2], [3, 4, 5]], dtype=np.float64)
    self = SVC(kernel='linear', probability=True)
    self._sparse = True
    self._impl = 'c_svc'
    self.classes_ = np.array([0, 1])
    self.support_vectors_ = sp.csr_matrix([[0, 1, 2], [3, 4, 5]], dtype=np.float64)
    self._dual_coef_ = sp.csr_matrix([[0.1, 0.2]], dtype=np.float64)
    self._intercept_ = np.array([0.5])
    self._sparse_kernels = ['linear', 'poly', 'rbf', 'sigmoid', 'precomputed']
    self.degree = 3
    self._gamma = 'scale'
    self.coef0 = 0.0
    self.tol = 1e-3
    self.C = 1.0
    self.class_weight_ = np.empty(0)
    self.nu = 0.5
    self.epsilon = 0.1
    self.shrinking = True
    self.probability = True
    self._n_support = np.array([1, 1])
    self._probA = np.array([0.1])
    self._probB = np.array([0.2])

    return _sparse_decision_function(self, X)


# 定义测试用例2
def testcase_2():
    class Dummy:
        pass

    self = Dummy()
    X = sp.csr_matrix([[1, 0, 0], [0, 1, 0]], dtype=np.float64)
    self = SVC(kernel='rbf', probability=False)
    self._sparse = True
    self._impl = 'nu_svc'
    self.classes_ = np.array([0, 1])
    self.support_vectors_ = sp.csr_matrix([[1, 0, 0], [0, 1, 0]], dtype=np.float64)
    self._dual_coef_ = sp.csr_matrix([[0.3, 0.4]], dtype=np.float64)
    self._intercept_ = np.array([0.6])
    self._sparse_kernels = ['linear', 'poly', 'rbf', 'sigmoid', 'precomputed']
    self.degree = 3
    self._gamma = 'auto'
    self.coef0 = 0.0
    self.tol = 1e-4
    self.C = 0.5
    self.class_weight_ = np.empty(0)
    self.nu = 0.3
    self.epsilon = 0.2
    self.shrinking = False
    self.probability = False
    self._n_support = np.array([1, 1])
    self._probA = np.array([0.2])
    self._probB = np.array([0.3])

    return _sparse_decision_function(self, X)


# 定义测试用例3
def testcase_3():
    class Dummy:
        pass

    self = Dummy()
    X = sp.csr_matrix([[0, 0, 1], [1, 1, 1]], dtype=np.float64)
    self = SVC(kernel='poly', probability=True)
    self._sparse = True
    self._impl = 'c_svc'
    self.classes_ = np.array([0, 1])
    self.support_vectors_ = sp.csr_matrix([[0, 0, 1], [1, 1, 1]], dtype=np.float64)
    self._dual_coef_ = sp.csr_matrix([[0.5, 0.6]], dtype=np.float64)
    self._intercept_ = np.array([0.7])
    self._sparse_kernels = ['linear', 'poly', 'rbf', 'sigmoid', 'precomputed']
    self.degree = 2
    self._gamma = 0.5
    self.coef0 = 1.0
    self.tol = 1e-3
    self.C = 1.0
    self.class_weight_ = np.empty(0)
    self.nu = 0.3
    self.epsilon = 0.1
    self.shrinking = True
    self.probability = True
    self._n_support = np.array([1, 1])
    self._probA = np.array([0.2])
    self._probB = np.array([0.3])

    return _sparse_decision_function(self, X)


# 定义测试用例4
def testcase_4():
    class Dummy:
        pass

    self = Dummy()
    X = sp.csr_matrix([[0, 0, 0], [1, 0, 0]], dtype=np.float64)
    self = SVC(kernel='sigmoid', probability=False)
    self._sparse = True
    self._impl = 'nu_svc'
    self.classes_ = np.array([0, 1])
    self.support_vectors_ = sp.csr_matrix([[0, 0, 0], [1, 0, 0]], dtype=np.float64)
    self._dual_coef_ = sp.csr_matrix([[0.2, 0.3]], dtype=np.float64)
    self._intercept_ = np.array([-0.4])
    self._sparse_kernels = ['linear', 'poly', 'rbf', 'sigmoid', 'precomputed']
    self.degree = 3
    self._gamma = 0.1
    self.coef0 = 0.0
    self.tol = 1e-3
    self.C = 0.5
    self.class_weight_ = np.empty(0)
    self.nu = 0.4
    self.epsilon = 0.05
    self.shrinking = True
    self.probability = False
    self._n_support = np.array([1, 1])
    self._probA = np.array([0.1])
    self._probB = np.array([0.1])

    return _sparse_decision_function(self, X)


# 定义测试用例5
def testcase_5():
    class Dummy:
        pass

    self = Dummy()
    X = sp.csr_matrix([[1, 1, 1], [0, 1, 0]], dtype=np.float64)
    self = SVC(kernel='linear', probability=True)
    self._sparse = True
    self._impl = 'c_svc'
    self.classes_ = np.array([0, 1])
    self.support_vectors_ = sp.csr_matrix([[1, 1, 1], [0, 1, 0]], dtype=np.float64)
    self._dual_coef_ = sp.csr_matrix([[0.6, 0.4]], dtype=np.float64)
    self._intercept_ = np.array([0.0])
    self._sparse_kernels = ['linear', 'poly', 'rbf', 'sigmoid', 'precomputed']
    self.degree = 3
    self._gamma = 1.0
    self.coef0 = 0.5
    self.tol = 1e-3
    self.C = 1.0
    self.class_weight_ = np.empty(0)
    self.nu = 0.3
    self.epsilon = 0.2
    self.shrinking = True
    self.probability = True
    self._n_support = np.array([1, 1])
    self._probA = np.array([0.4])
    self._probB = np.array([0.2])

    return _sparse_decision_function(self, X)


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
