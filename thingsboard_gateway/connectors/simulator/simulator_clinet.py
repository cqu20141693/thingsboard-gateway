import datetime
import json
import random
import time
from decimal import Decimal

from faker import Faker

from thingsboard_gateway.connectors.connector import log
from thingsboard_gateway.model.iiot_emum import TagQuality

ERROR_TEXT = '数据类型非法，数据类型 %s ，数据 %s'


def verify_bool(data_value, data_type):
    if data_type is None:
        return True, False
    if data_value == "False" or data_value == "false":
        return True, False
    elif data_value == "True" or data_value == "true":
        return True, True
    else:
        if isinstance(data_value, bool):
            return True, data_value
        else:
            return False, False


def verify_int(data_value, data_type):
    if data_type is None:
        return True, 0
    try:
        data_value = int(data_value)
        if data_value < -2147483648 or data_value > 2147483647:
            return False, 0
        return True, data_value
    except Exception as e:
        log.error(ERROR_TEXT, "int", data_value)
        log.exception(e)
        return False, 0


def verify_long(data_value, data_type):
    if data_type is None:
        return True, 0
    try:
        data_value = int(data_value)
        if data_value < -9223372036854775808 or data_value > 9223372036854775807:
            return False, 0
        return True, data_value
    except Exception as e:
        log.error(ERROR_TEXT, "long", data_value)
        log.exception(e)
        return False, 0


def verify_float(data_value, data_type):
    if data_type is None:
        return True, 0.0
    try:
        data_value = float(data_value)
        return True, data_value
    except Exception as e:
        log.error(ERROR_TEXT, "float", data_value)
        log.exception(e)
        return False, 0


def verify_string(data_value, data_type):
    if data_type is None:
        return True, ""
    try:
        data_value = str(data_value)
        return True, data_value
    except Exception as e:
        log.error(ERROR_TEXT, "string", data_value)
        log.exception(e)
        return False, 0


class SimulatorClient:

    def __init__(self):
        self.fake = Faker(locale='zh_cn')
        self.json_array_index = {}

    def get_values(self, tags):
        read_result = {}
        for tag in tags:
            data_value = self.get_value(tag)
            read_result[tag.name] = data_value
        return read_result

    def get_value(self, tag):
        try:
            config = tag.config
            address_type = config['extension']['address']
            if address_type == "Static":
                data_type = config['extension']['type']
                if tag.value is not None:
                    return tag.value
                else:
                    default_value = config['extension'].get('default')
                    check, data_value = self.verify_value(data_value=default_value, data_type=data_type)
                    return data_value
            elif address_type == "Random":
                return self.get_random_value(tag)
            elif address_type == "Increment":
                return self.get_increment_value(tag)
            elif address_type == "Faker":
                return self.get_fake_value(tag)
            elif address_type == "Enum":
                return self.get_enum_value(tag)
            elif address_type == "JsonArray":
                return self.get_json_array_value(tag)
        except Exception as e:
            log.exception(e)

    def write_value(self, tag, data_value):
        config = tag.config
        address_type = config['extension']['address']
        if address_type != "Static":
            return False, "当前寄存器类型不支持写操作"
        data_type = config['extension']['type']

        check, data_value = self.verify_value(data_value=data_value, data_type=data_type)
        if check:
            tag.value = data_value
            tag.quality = TagQuality.GOOD
            tag.time = int(time.time() * 1000)
            return True, "ok"
        else:
            return False, "写入失败，检查写入数据数据类型是否正确"

    @staticmethod
    def verify_value(data_value, data_type):
        """
        检查数据类型是否正确，不正确返回默认值
        :param data_value:
        :param data_type:
        :return:
        """
        if data_type == "bool":
            return verify_bool(data_value, data_type)

        if data_type == "int":
            return verify_int(data_value, data_type)

        if data_type == "long":
            return verify_long(data_value, data_type)

        if data_type == "float":
            return verify_float(data_value, data_type)

        if data_type == "string":
            return verify_string(data_value, data_type)

    def get_random_value(self, tag):
        config = tag.config
        data_type = config['extension']['type']
        min_ = config['extension'].get('min')
        max_ = config['extension'].get('max')
        if data_type == "bool":
            bool_value = [True, False]
            return bool_value[random.randint(0, 1)]
        elif data_type == "int":
            return random.randint(min_, max_)
        elif data_type == "long":
            return random.randint(min_, max_)
        elif data_type == "float":
            min_ = config['extension']['min']
            max_ = config['extension']['max']
            return round(random.uniform(min_, max_), 4)
        elif data_type == "string":
            return self.fake.password(length=10, special_chars=True, digits=True, upper_case=True, lower_case=True)

    @staticmethod
    def get_increment_value(tag):
        config = tag.config
        min_ = Decimal(str(config['extension'].get('min_increment')))
        max_ = Decimal(str(config['extension'].get('max_increment')))
        step_ = Decimal(str(config['extension'].get('step_increment')))

        data_value = tag.value
        if data_value is None:
            data_value = min_
        else:
            if step_ >= 0:
                data_value = data_value + step_
                if data_value > max_:
                    data_value = min_
            else:
                data_value = data_value + step_
                if data_value < min_:
                    data_value = max_
        return data_value

    def get_fake_value(self, tag):
        config = tag.config
        fake_type = config['extension'].get('fake')

        if fake_type == "name":
            return self.fake.name()
        elif fake_type == "address":
            return self.fake.address()
        elif fake_type == "ssn":
            return self.fake.ssn()
        elif fake_type == "email":
            return self.fake.email()
        elif fake_type == "date":
            return self.fake.date()
        elif fake_type == "date_time":
            return self.fake.date_time()
        elif fake_type == "unix_time":
            return self.fake.unix_time()
        elif fake_type == "phone_number":
            return self.fake.phone_number()
        elif fake_type == "real_time":
            return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def get_enum_value(tag):
        config = tag.config
        enum_text = config['extension'].get('enum')
        enum_values = enum_text.split(',')
        if tag.value is None:
            return enum_values[0]
        else:
            index = enum_values.index(tag.value)
            if index == -1:
                return enum_values[0]
            else:
                index = index + 1
                if index >= len(enum_values):
                    return enum_values[0]
                else:
                    return enum_values[index]

    def get_json_array_value(self, tag):
        name = tag.name
        config = tag.config
        json_array_text = config['extension'].get('json_array')
        try:
            array_data = json.loads(json_array_text)
            if not isinstance(array_data, list):
                return None
            if len(array_data) == 0:
                return None
        except Exception:
            log.error("JsonArray 数据加载失败")
            return None

        index = self.json_array_index.get(name)
        if index is None:
            index = 0
            self.json_array_index[name] = index
            return array_data[index]
        else:
            index = index + 1
            if index <= (len(array_data) - 1):
                self.json_array_index[name] = index
                return array_data[index]
            else:
                index = 0
                self.json_array_index[name] = index
                return array_data[index]


if __name__ == '__main__':
    dt = datetime.datetime.now()
    print(dt.strftime("%Y-%m-%d %H:%M:%S"))
