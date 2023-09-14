import logging
import uuid
from json import loads
from logging import getLogger
from re import search
from jsonpath_rw import parse
from os import path, listdir
from importlib import util
from inspect import getmembers, isclass

log = getLogger("service")

note_log = logging.getLogger('note')
loaded_extensions = {}


def fast_trace_id():
    """
    生成TraceId
    :return: trace_id
    """
    return ''.join(str(uuid.uuid4()).split('-'))


def get_value(expression, body=None, value_type="string", get_tag=False, expression_instead_none=False):
    if isinstance(body, str):
        body = loads(body)
    if not expression:
        return ''
    positions = search(r'\${(?:(.*))}', expression)
    if positions is not None:
        p1 = positions.regs[-1][0]
        p2 = positions.regs[-1][1]
    else:
        p1 = 0
        p2 = len(expression)
    target_str = str(expression[p1:p2])
    if get_tag:
        return target_str
    full_value = None
    try:
        if isinstance(body, dict) and target_str.split()[0] in body:
            if value_type.lower() == "string":
                full_value = expression[0: max(abs(p1 - 2), 0)] + body[target_str.split()[0]] + expression[
                                                                                                p2 + 1:len(
                                                                                                    expression)]
            else:
                full_value = body.get(target_str.split()[0])
        elif isinstance(body, (dict, list)):
            try:
                jsonpath_expression = parse(target_str)
                jsonpath_match = jsonpath_expression.find(body)
                if jsonpath_match:
                    full_value = jsonpath_match[0].value
            except Exception as e:
                log.debug(e)
        elif isinstance(body, (str, bytes)):
            search_result = search(expression, body)
            if search_result.groups():
                full_value = search_result.group(0)
        if expression_instead_none and full_value is None:
            full_value = expression
    except Exception as e:
        log.exception(e)
    return full_value


def check_and_import(extensions_paths, extension_type, module_name):
    """
     动态导入class
    :param extensions_paths: 导入文件夹路径
    :param extension_type: 文件扩展类型
    :param module_name: 文件class名称
    :return: class对象
    """
    if loaded_extensions.get(extension_type + module_name) is None:
        try:
            for extension_path in extensions_paths:
                if loaded_extensions.get(extension_type + module_name) is not None:
                    return loaded_extensions[extension_type + module_name]
                if path.exists(extension_path):
                    for file in listdir(extension_path):
                        if not file.startswith('__') and file.endswith('.py'):
                            try:
                                module_spec = util.spec_from_file_location(module_name,
                                                                           extension_path + path.sep + file)
                                log.debug(module_spec)

                                if module_spec is None:
                                    log.debug('Module: %s not found', module_name)
                                    continue

                                module = util.module_from_spec(module_spec)
                                log.debug(str(module))
                                module_spec.loader.exec_module(module)
                                for extension_class in getmembers(module, isclass):
                                    if module_name in extension_class:
                                        log.debug("Import %s from %s.", module_name, extension_path)
                                        # Save class into buffer
                                        loaded_extensions[extension_type + module_name] = extension_class[
                                            1]
                                        return extension_class[1]
                            except ImportError as e:
                                log.exception(e)
                                continue
                else:
                    log.error("Import %s failed, path %s doesn't exist", module_name, extension_path)
        except Exception as e:
            log.exception(e)
    else:
        log.debug("Class %s found in TBUtility buffer.", module_name)

    return loaded_extensions[extension_type + module_name]


def set_child_dic_value(dic, child_dic_name, key, value):
    if dic.get(child_dic_name) is None:
        dic[child_dic_name] = {}
    dic[child_dic_name][key] = value
