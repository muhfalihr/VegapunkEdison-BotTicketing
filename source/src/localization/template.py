from src.types.template import MessagesTemplate, Template
from src.utility.utility import get_config_yaml, arson


_main_template = get_config_yaml("template.yml")

_message_template = MessagesTemplate(**_main_template.get("messages", {}))

template = Template(**arson(
    messages=_message_template
))