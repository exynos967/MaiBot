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


@dataclass
class SubClass(ConfigBase):
    sub_field: str


@dataclass
class ConfigExample(ConfigBase):
    int_field: int
    float_field: float
    str_field: str
    bool_field: bool
    list_field: list[int]
    set_field: set[str]
    tuple_field: tuple[int, str]
    sub_class: SubClass
    dict_field: dict[str, int] = field(default_factory=dict)
    optional_field: Optional[str] = "default_value"


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
    assert_values(config)


def test_config_base_from_file():
    file_path = Path(__file__).parent / "test_config.toml"
    with open(file_path.resolve().absolute(), "r", encoding="utf-8") as f:
        toml_content = tomlkit.load(f)

    config = ConfigExample.from_dict(toml_content)
    assert_values(config)


@pytest.mark.parametrize(
    "config_data, expected_exception, expected_message",
    [
        (
            {
                "int_field": "40",  # 会被转换，应该报AssertionError
                "float_field": 3.14, 
                "str_field": "111",
                "bool_field": True,
                "list_field": [1, 2, 3],
                "set_field": ["a", "b", "c"],
                "tuple_field": [7, "seven"],
                "dict_field": {"key1": 1, "key2": 2},
                "sub_class": {"sub_field": "sub_value"},
            },
            AssertionError,
            "wrong int_field value",
        ),
        (
            {
                "int_field": 42,
                "float_field": 3.14,
                "str_field": "example",
                "bool_field": True,
                "list_field": [1, 2, 3],
                "set_field": ("a", "b", "c"), # 错误类型
                "tuple_field": [7, "seven"],
                "dict_field": {"key1": 1, "key2": 2},
                "sub_class": {"sub_field": "sub_value"},
            },
            TypeError,
            "Expected a list for set",
        ),
        (
            {
                "int_field": 42,
                "float_field": 3.14,
                "str_field": "example",
                "bool_field": True,
                "list_field": [1, 2, 3],
                "set_field": ["a", "b", "c"],
                "tuple_field": [7, "seven"],
                "dict_field": {"key1": 1, "key2": 2},
                # 缺少关键字
            },
            ValueError,
            "Missing required field: 'sub_class'",
        ),
        (
            {
                "int_field": 42,
                "float_field": 3.14,
                "str_field": "example",
                "bool_field": True,
                "list_field": ["nan", 2, 3], # 元素类型错误
                "set_field": ["a", "b", "c"],
                "tuple_field": [7, "seven"],
                "dict_field": {"key1": 1, "key2": 2},
                "sub_class": {"sub_field": "sub_value"},
            },
            TypeError,
            "Cannot convert str to int",
        ),
        (
            {
                "int_field": 42,
                "float_field": 3.14,
                "str_field": "example",
                "bool_field": "False", # 错误类型
                "list_field": [1, 2, 3],
                "set_field": ["a", "b", "c"],
                "tuple_field": [7, "seven"],
                "dict_field": {"key1": 1, "key2": 2},
                "sub_class": {"sub_field": "sub_value"},
            },
            AssertionError,
            "wrong bool_field value",
        ),
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
