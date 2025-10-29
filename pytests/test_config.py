# 本文件为测试文件，请忽略Lint error，内含大量的ignore标识

# 依赖导入
from typing import Optional
from dataclasses import dataclass, field
from pathlib import Path
from importlib import util
import tomlkit
import pytest

# 测试对象导入
module_path = Path(__file__).parent.parent / "src" / "config" / "config_base.py"
spec = util.spec_from_file_location("src.config.config_base", module_path.resolve().absolute())
module = util.module_from_spec(spec)  # type: ignore
spec.loader.exec_module(module)  # type: ignore
ConfigBase = module.ConfigBase
AttrDocConfigBase = module.AttrDocConfigBase

standard_config_data = {
    "int_field": 42,
    "float_field": 3.14,
    "str_field": "example",
    "bool_field": True,
    "list_field": [1, 2, 3],
    "set_field": ["a", "b", "c"],
    "tuple_field": [7, "seven"],
    "dict_field": {"key1": 1, "key2": 2},
    "sub_class": {"sub_field": "sub_value"},
}


@dataclass
class SubClass(ConfigBase, AttrDocConfigBase):
    sub_field: str
    """sub_field is a string field in SubClass"""


@dataclass
class ConfigExample(ConfigBase, AttrDocConfigBase):
    int_field: int
    """The value is integer type"""
    float_field: float
    """The value is float type"""
    str_field: str
    """
    multi-line annotation
    The value is string type
    """
    bool_field: bool
    """
    The value is boolean type
    """
    list_field: list[int]
    set_field: set[str]
    tuple_field: tuple[int, str]
    sub_class: SubClass
    dict_field: dict[str, int] = field(default_factory=dict)
    optional_field: Optional[str] = "default_value"


@dataclass
class ErrorConfig(ConfigBase, AttrDocConfigBase):
    value: int

    def a_method(self):  # 应该抛出异常
        pass


@dataclass
class GoodConfig(ConfigBase, AttrDocConfigBase):
    value: int

    def __post_init__(self):  # 唯一允许的方法
        pass


def assert_values(config: ConfigExample):
    assert config.int_field == 42, "wrong int_field value"
    assert config.float_field == 3.14, "wrong float_field value"
    assert config.str_field == "example", "wrong str_field value"
    assert config.bool_field is True, "wrong bool_field value"
    assert config.list_field == [1, 2, 3], "wrong list_field value"
    assert config.set_field == {"a", "b", "c"}, "wrong set_field value"
    assert config.tuple_field == (7, "seven"), "wrong tuple_field value"
    assert config.dict_field == {"key1": 1, "key2": 2}, "wrong dict_field value"
    assert config.optional_field == "default_value", "wrong optional_field value"
    assert config.sub_class.sub_field == "sub_value", "wrong sub_class.sub_field value"
    assert isinstance(config.int_field, int)
    assert isinstance(config.float_field, float)
    assert isinstance(config.str_field, str)
    assert isinstance(config.bool_field, bool)
    assert isinstance(config.list_field, list)
    assert isinstance(config.set_field, set)
    assert isinstance(config.tuple_field, tuple)
    assert isinstance(config.tuple_field[0], int)
    assert isinstance(config.tuple_field[1], str)
    assert isinstance(config.dict_field, dict)
    assert isinstance(config.optional_field, str)
    assert isinstance(config.sub_class.sub_field, str)


def test_config_base_from_dict():
    config = ConfigExample.from_dict(standard_config_data)
    assert_values(config)


def test_config_base_from_file():
    file_path = Path(__file__).parent / "test_config.toml"
    with open(file_path.resolve().absolute(), "r", encoding="utf-8") as f:
        toml_content = tomlkit.load(f)

    config = ConfigExample.from_dict(toml_content)
    assert_values(config)


e_int_config_data = standard_config_data.copy()
e_int_config_data["int_field"] = "40"  # 会被转换，应该报AssertionError
e_list_config_data = standard_config_data.copy()
e_list_config_data["list_field"] = []  # 列表为空，应该被覆盖并报AssertionError
e_set_config_data = standard_config_data.copy()
e_set_config_data["set_field"] = ("a", "b", "c")  # 错误类型
e_subclass_config_data = standard_config_data.copy()
e_subclass_config_data.pop("sub_class")  # 缺少关键字
e_list_type_config_data = standard_config_data.copy()
e_list_type_config_data["list_field"] = ["nan", 2, 3]  # 元素类型错误
e_bool_config_data = standard_config_data.copy()
e_bool_config_data["bool_field"] = "False"  # 会被转换，应该报AssertionError
multiline_str_config_data = standard_config_data.copy()
multiline_str_config_data["str_field"] = """
line1
line2
line3
"""

@pytest.mark.parametrize(
    "config_data, expected_exception, expected_message",
    [
        (e_int_config_data, AssertionError, "wrong int_field value"),
        (e_list_config_data, AssertionError, "wrong list_field value"),
        (e_set_config_data, TypeError, "Expected a list for set"),
        (e_subclass_config_data, ValueError, "Missing required field: 'sub_class'"),
        (e_list_type_config_data, TypeError, "Cannot convert str to int"),
        (e_bool_config_data, AssertionError, "wrong bool_field value"),
    ],
)
def test_multiple_exceptions(config_data, expected_exception, expected_message):
    with pytest.raises(expected_exception) as exc_info:
        config = ConfigExample.from_dict(config_data)
        assert_values(config)
    # 确保异常类型正确
    assert exc_info.type == expected_exception
    # 确保异常消息包含预期内容
    assert expected_message in str(exc_info.value)

def test_multiline_string():
    config = ConfigExample.from_dict(multiline_str_config_data)
    assert config.str_field == "\nline1\nline2\nline3\n", "wrong multiline str_field value"

def test_doc_strings():
    config_data = {
        "int_field": 42,
        "float_field": 3.14,
        "str_field": "example",
        "bool_field": True,
        "list_field": [1, 2, 3],
        "set_field": ["a", "b", "c"],
        "tuple_field": [7, "seven"],
        "dict_field": {"key1": 1, "key2": 2},
        "sub_class": {"sub_field": "sub_value"},
    }

    config = ConfigExample.from_dict(config_data)
    field_docs = config.field_docs
    assert field_docs["int_field"] == "The value is integer type"
    assert field_docs["float_field"] == "The value is float type"
    assert field_docs["str_field"] == "multi-line annotation\nThe value is string type"
    assert field_docs["bool_field"] == "The value is boolean type"
    field_docs_sub = config.sub_class.field_docs
    assert field_docs_sub["sub_field"] == "sub_field is a string field in SubClass"


@pytest.mark.parametrize(
    "target_class, config_data, expected_exception, expected_message",
    [
        (
            ErrorConfig,
            {"value": 10},
            AttributeError,
            "Methods are not allowed in AttrDocConfigBase subclasses except __post_init__",
        ),
        (GoodConfig, {"value": 10}, None, ""),
    ],
)
def test_method_exception(target_class, config_data, expected_exception, expected_message):
    if expected_exception:
        with pytest.raises(expected_exception) as exc_info:
            _ = target_class.from_dict(config_data)
        # 确保异常类型正确
        assert exc_info.type == expected_exception
        # 确保异常消息包含预期内容
        assert expected_message in str(exc_info.value)
    else:
        target_class.from_dict(config_data)
