from dataclasses import dataclass, fields, MISSING
from typing import TypeVar, Type, Any, get_origin, get_args, Literal
from pathlib import Path
import ast
import inspect

T = TypeVar("T", bound="ConfigBase")

TOML_DICT_TYPE = {
    int,
    float,
    str,
    bool,
    list,
    dict,
}


@dataclass
class ConfigBase:
    """配置类的基类"""

    @classmethod
    def from_dict(cls: Type[T], data: dict[str, Any]) -> T:
        """从字典加载配置字段"""
        if not isinstance(data, dict):
            raise TypeError(f"Expected a dictionary, got {type(data).__name__}")

        init_args: dict[str, Any] = {}

        for f in fields(cls):
            field_name = f.name

            if field_name.startswith("_"):
                # 跳过以 _ 开头的字段
                continue

            if field_name not in data:
                if f.default is not MISSING or f.default_factory is not MISSING:
                    # 跳过未提供且有默认值/默认构造方法的字段
                    continue
                else:
                    raise ValueError(f"Missing required field: '{field_name}'")

            value = data[field_name]
            field_type = f.type

            try:
                assert not isinstance(field_type, str)
                init_args[field_name] = cls._convert_field(value, field_type)
            except TypeError as e:
                raise TypeError(f"Field '{field_name}' has a type error: {e}") from e
            except AssertionError:
                raise TypeError(f"Field '{field_name}' has an unsupported type: {field_type}") from None
            except Exception as e:
                raise RuntimeError(f"Failed to convert field '{field_name}' to target type: {e}") from e

        return cls(**init_args)

    @classmethod
    def _convert_field(cls, value: Any, field_type: Type[Any]) -> Any:
        """
        转换字段值为指定类型

        1. 对于嵌套的 dataclass，递归调用相应的 from_dict 方法
        2. 对于泛型集合类型（list, set, tuple），递归转换每个元素
        3. 对于基础类型（int, str, float, bool），直接转换
        4. 对于其他类型，尝试直接转换，如果失败则抛出异常
        """

        # 如果是嵌套的 dataclass，递归调用 from_dict 方法
        if isinstance(field_type, type) and issubclass(field_type, ConfigBase):
            if not isinstance(value, dict):
                raise TypeError(f"Expected a dictionary for {field_type.__name__}, got {type(value).__name__}")
            return field_type.from_dict(value)

        # 处理泛型集合类型（list, set, tuple）
        field_origin_type = get_origin(field_type)
        field_type_args = get_args(field_type)

        if field_origin_type in {list, set, tuple}:
            # 检查提供的value是否为list
            if not isinstance(value, list):
                raise TypeError(f"Expected a list for {field_type.__name__}, got {type(value).__name__}")

            if field_origin_type is list:
                # 如果列表元素类型是ConfigBase的子类，则对每个元素调用from_dict
                if (
                    field_type_args
                    and isinstance(field_type_args[0], type)
                    and issubclass(field_type_args[0], ConfigBase)
                ):
                    return [field_type_args[0].from_dict(item) for item in value]
                return [cls._convert_field(item, field_type_args[0]) for item in value]
            elif field_origin_type is set:
                return {cls._convert_field(item, field_type_args[0]) for item in value}
            elif field_origin_type is tuple:
                # 检查提供的value长度是否与类型参数一致
                if len(value) != len(field_type_args):
                    raise TypeError(
                        f"Expected {len(field_type_args)} items for {field_type.__name__}, got {len(value)}"
                    )
                return tuple(cls._convert_field(item, arg) for item, arg in zip(value, field_type_args, strict=True))

        if field_origin_type is dict:
            # 检查提供的value是否为dict
            if not isinstance(value, dict):
                raise TypeError(f"Expected a dictionary for {field_type.__name__}, got {type(value).__name__}")

            # 检查字典的键值类型
            if len(field_type_args) != 2:
                raise TypeError(f"Expected a dictionary with two type arguments for {field_type.__name__}")
            key_type, value_type = field_type_args

            return {cls._convert_field(k, key_type): cls._convert_field(v, value_type) for k, v in value.items()}

        # 处理Optional类型
        if field_origin_type is type(None) and value is None:
            return None

        # 处理基础类型，例如 int, str 等
        if field_type is bool and isinstance(value, str):
            lowered = value.lower()
            if lowered in {"true", "1"}:
                return True
            elif lowered in {"false", "0"}:
                return False
            else:
                raise TypeError(f"Cannot convert string '{value}' to bool")

        # 处理Literal类型
        if field_origin_type is Literal or get_origin(field_type) is Literal:
            # 获取Literal的允许值
            allowed_values = get_args(field_type)
            if value in allowed_values:
                return value
            else:
                raise TypeError(f"Value '{value}' is not in allowed values {allowed_values} for Literal type")

        if field_type is Any or isinstance(value, field_type):
            return value

        # 其他类型，尝试直接转换
        try:
            return field_type(value)
        except (ValueError, TypeError) as e:
            raise TypeError(f"Cannot convert {type(value).__name__} to {field_type.__name__}") from e


@dataclass
class AttrDocConfigBase:
    def __post_init__(self):
        self.field_docs = self._get_field_docs()  # 全局仅获取一次并保留

    @classmethod
    def _get_field_docs(cls) -> dict[str, str]:
        """
        获取字段的说明字符串

        :param cls: 配置类
        :return: 字段说明字典，键为字段名，值为说明字符串
        """
        # 获取目标类的代码文件
        class_file = inspect.getfile(cls)
        class_source = Path(class_file).read_text(encoding="utf-8")

        # 解析源代码
        tree = ast.parse(class_source)
        doc_dict: dict[str, str] = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == cls.__name__:
                class_body = node.body
                for i in range(len(class_body)):
                    body_item = class_body[i]
                    if isinstance(body_item, ast.FunctionDef) and body_item.name != "__post_init__":
                        raise AttributeError(
                            f"Methods are not allowed in AttrDocConfigBase subclasses except __post_init__, found {str(body_item.name)}"
                        ) from None
                    if (
                        i + 1 < len(class_body)
                        and isinstance(body_item, ast.AnnAssign)
                        and isinstance(body_item.target, ast.Name)
                    ):
                        expr_item = class_body[i + 1]
                        if (
                            isinstance(expr_item, ast.Expr)
                            and isinstance(expr_item.value, ast.Constant)
                            and isinstance(expr_item.value.value, str)
                        ):
                            doc_string = expr_item.value.value.strip()
                            processed_doc_lines = [line.strip() for line in doc_string.splitlines()]
                            while processed_doc_lines and not processed_doc_lines[0]:
                                # 去除头部空行
                                processed_doc_lines.pop(0)
                            while processed_doc_lines and not processed_doc_lines[-1]:
                                # 去除尾部空行
                                processed_doc_lines.pop()
                            doc_dict[body_item.target.id] = "\n".join(processed_doc_lines)

        return doc_dict
