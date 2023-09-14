# Example:
# config: 点位内容
# device_id: 点位归属设备id
# tag_type: 点位类型 时序-属性
# frequency: 采集频率
# value: 数据值
# time: 数据的访问时间
# quality: 信号质量
# send_data_only_on_change: 数据变更上报
from iiot_emum import TagQuality


class Tag:
    __slots__ = ('__name', '__config', '__device_id', '__device_name', '__device_type', '__value',
                 '__time', '__quality', '__tag_type', '__frequency', '__extension', '__send_data_only_on_change')

    def __init__(self, name, config, device_id, device_name, device_type, tag_type, frequency):
        self.__name = name
        self.__value = None
        self.__time = None
        self.__quality = TagQuality.BAD

        self.__config = config
        self.__device_id = device_id
        self.__device_name = device_name
        self.__device_type = device_type
        self.__tag_type = tag_type
        self.__frequency = frequency
        self.__extension = None
        self.__send_data_only_on_change = None

    def __str__(self):
        return "Name:{name}, Value:{value}, Time:{time}, Quality:{quality}" \
            .format(name=self.name, value=self.value, time=self.time, quality=self.quality.value)

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, name):
        self.__name = name

    @property
    def value(self):
        return self.__value

    @value.setter
    def value(self, value):
        self.__value = value

    @property
    def time(self):
        return self.__time

    @time.setter
    def time(self, time):
        self.__time = time

    @property
    def quality(self):
        return self.__quality

    @quality.setter
    def quality(self, quality):
        self.__quality = quality

    @property
    def config(self):
        return self.__config

    @config.setter
    def config(self, config):
        self.__config = config

    @property
    def device_id(self):
        return self.__device_id

    @device_id.setter
    def device_id(self, device_id):
        self.__device_id = device_id

    @property
    def device_name(self):
        return self.__device_name

    @device_name.setter
    def device_name(self, device_name):
        self.__device_name = device_name

    @property
    def device_type(self):
        return self.__device_type

    @device_type.setter
    def device_type(self, device_type):
        self.__device_type = device_type

    @property
    def tag_type(self):
        return self.__tag_type

    @tag_type.setter
    def tag_type(self, tag_type):
        self.__tag_type = tag_type

    @property
    def frequency(self):
        return self.__frequency

    @frequency.setter
    def frequency(self, frequency):
        self.__frequency = frequency

    @property
    def send_data_only_on_change(self):
        return self.__send_data_only_on_change

    @send_data_only_on_change.setter
    def send_data_only_on_change(self, send_data_only_on_change):
        self.__send_data_only_on_change = send_data_only_on_change

    def set_extension(self, extension):
        self.__extension = extension

    def get_extension(self):
        return self.__extension
