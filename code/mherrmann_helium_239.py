import unittest
from unittest.mock import MagicMock


class FakeImpl:
    def __init__(self, enabled):
        self.enabled = enabled

    def is_enabled(self):
        return self.enabled


class Example:
    def __init__(self, impl):
        self._impl = impl

    def is_enabled(self):
        return self._impl.is_enabled()


class TestIsEnabled(unittest.TestCase):
    def test_is_enabled_true(self):
        fake_impl = FakeImpl(True)  # 模拟 _impl.is_enabled() 返回 True
        obj = Example(fake_impl)
        self.assertTrue(obj.is_enabled())  # 断言返回 True

    def test_is_enabled_false(self):
        fake_impl = FakeImpl(False)  # 模拟 _impl.is_enabled() 返回 False
        obj = Example(fake_impl)
        self.assertFalse(obj.is_enabled())  # 断言返回 False


if __name__ == "__main__":
    unittest.main()