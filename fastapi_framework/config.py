from typing import Dict, Any, Optional

from fastapi_framework import disabled_modules

CONFIG_BLOCKLIST = ["CONFIG_PATH", "CONFIG_TYPE"]
CONFIG_FILE_PATH_DEFAULT = "config.yaml"
CONFIG_TYPE_DEFAULT = "yaml"


class _ConfigField:
    name: str
    type_hint: Optional[type] = None
    default_value: Any

    def __init__(self, name: str = "", default_value: Any = None):
        self.name = name
        self.default_value = default_value


def ConfigField(name: str = "", default: Any = None) -> Any:
    return _ConfigField(name, default)


class ConfigMeta(type):
    def __new__(mcs, name, bases, dct):
        config_entries: Dict[str, _ConfigField] = {}
        config_class = super().__new__(mcs, name, bases, dct)
        annotations: Dict[str, type] = dct.get("__annotations__", {})

        for key in dct.keys():
            if key in CONFIG_BLOCKLIST:
                continue
            if not isinstance(dct[key], _ConfigField):
                continue
            type_hint: Optional[type] = None
            if key in annotations:
                type_hint = annotations[key]
            value: _ConfigField = dct[key]
            type_hint = type_hint if not getattr(type_hint, "__origin__", None) else type_hint.__origin__
            if type_hint is not None:
                try:
                    type_hint.__call__()
                except TypeError:
                    type_hint = None
            value.type_hint = type_hint
            if value.name == "":
                value.name = key
            config_entries[key] = value

        if "config" in disabled_modules:
            for config_entry in config_entries:
                setattr(config_class, config_entry, None)
            return config_class

        config_file_path = dct.get("CONFIG_PATH") or CONFIG_FILE_PATH_DEFAULT
        config_type = dct.get("CONFIG_TYPE") or CONFIG_TYPE_DEFAULT

        with open(config_file_path, "r") as file:
            data: str = file.read()

        config: Dict

        if config_type.lower() == "yaml":
            import yaml

            config = yaml.load(data, Loader=yaml.CLoader)
        elif config_type.lower() == "json":
            import json

            config = json.loads(data)
        elif config_type.lower() == "toml":
            import toml

            config = dict(toml.loads(data))
        else:
            raise Exception(f"Config Type '{config_type}' is not Supported")

        del data

        config = config or {}
        for key in config_entries.keys():
            config_key = config_entries[key].name
            if config_key in config.keys():
                type_hint = config_entries.get(key).type_hint
                if type_hint:
                    value = type_hint(config[config_key]) if config[config_key] is not None else None
                else:
                    value = config[config_key]
                setattr(config_class, key, value)
            else:
                value = config_entries.get(config_key).default_value
                setattr(config_class, key, value)

        return config_class


class Config(metaclass=ConfigMeta):
    pass
