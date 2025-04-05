from src.types.template import MessagesTemplate, Template
from src.utility.utility import get_config_yaml, arson


def template(lang):
    _main_template = get_config_yaml("src/templates/template-{}.yml".format(lang))

    _message_template = MessagesTemplate(**_main_template.get("messages", {}))

    return Template(**arson(
        messages=_message_template
    ))