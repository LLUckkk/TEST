import random
from unittest.mock import MagicMock
from contextlib import contextmanager


@contextmanager
def exempt(obj, pid: int):
    """改成 `@contextmanager` 方便 `with` 语句使用"""
    if obj.local:
        obj.local.trusted_pids.add(pid)
        try:
            yield
        finally:
            if obj.local:
                obj.local.trusted_pids.remove(pid)


def test_exempt(pid):
    """测试 `exempt` 方法"""
    print(f"Before: {obj.local.trusted_pids}")

    with exempt(obj, pid):  # 现在 `exempt` 可以正确使用 `with`
        print(f"Inside with: {obj.local.trusted_pids}")

    print(f"After: {obj.local.trusted_pids}")
    print("---------------")


# 创建 mock 对象
obj = MagicMock()
obj.local = MagicMock()
obj.local.trusted_pids = set()

# 运行测试
test_exempt(1234)
test_exempt(5678)
test_exempt(91011)
test_exempt(random.randint(1000, 9999))
test_exempt(31415)