import types


class MyClass:
    def __init__(self):
        self._dynamic_attrs = []

    def _set_dynamic_attr(self, attr_name, value):
        self._dynamic_attrs.append(attr_name)
        self.__dict__[attr_name] = value

    def set_dynamic_attr(self, attr_name, value):
        self._set_dynamic_attr(attr_name, value)


obj = MyClass()
attr_name = "dynamic_method_1"
value = types.MethodType(lambda self: "Hello, World!", obj)
obj.set_dynamic_attr(attr_name, value)
print("testcase1: " + obj.dynamic_method_1())

attr_name = "dynamic_method_2"
value = types.MethodType(lambda self: sum(range(10)), obj)
obj.set_dynamic_attr(attr_name, value)
print("testcase2: " + str(obj.dynamic_method_2()))

attr_name = "dynamic_method_3"
value = types.MethodType(lambda self: [i**2 for i in range(5)], obj)
obj.set_dynamic_attr(attr_name, value)
print("testcase3: " + str(obj.dynamic_method_3()))

attr_name = "dynamic_method_4"
value = types.MethodType(lambda self: {"key": "value"}, obj)
obj.set_dynamic_attr(attr_name, value)
print("testcase4: " + str(obj.dynamic_method_4()))

attr_name = "dynamic_method_5"
value = types.MethodType(lambda self: "Dynamic attribute test", obj)
obj.set_dynamic_attr(attr_name, value)
print("testcase5: " + obj.dynamic_method_5())