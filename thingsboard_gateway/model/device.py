# Example:
# device_id: 设备id
# device_name: 设备名称
# channel_id: 通道id
# config: 设备配置内容
# timeseries: 时序上报配置 数组
# attributes: 属性上报配置 数组
# attribute_updates: 属性更新配置 数组
# function: function 数组
# tags: 点位列表
# extension: 自定义数据


class Device:
    __slots__ = (
        '__device_id', '__device_name', '__device_type', '__channel_id', '__config', '__timeseries', '__attributes',
        '__attribute_updates', '__function', '__extension', '__tags', '__frequency')

    def __init__(self, device_id=None, device_name=None, device_type=None, channel_id=None, config=None,
                 timeseries=None, attributes=None,
                 attribute_updates=None, function=None, extension=None):
        if function is None:
            function = {}
        if attribute_updates is None:
            attribute_updates = {}
        if attributes is None:
            attributes = {}
        if timeseries is None:
            timeseries = {}
        self.__device_id = device_id
        self.__device_name = device_name
        self.__device_type = device_type
        self.__config = config
        self.__timeseries = timeseries
        self.__attributes = attributes
        self.__attribute_updates = attribute_updates
        self.__function = function
        self.__extension = extension
        self.__tags = {}
        self.__frequency = {}
        self.__channel_id = channel_id

    @property
    def device_type(self):
        return self.__device_type

    @device_type.setter
    def device_type(self, device_type):
        self.__device_type = device_type

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
    def channel_id(self):
        return self.__channel_id

    @channel_id.setter
    def channel_id(self, channel_id):
        self.__channel_id = channel_id

    @property
    def config(self):
        return self.__config

    @config.setter
    def config(self, config):
        self.__config = config

    @property
    def timeseries(self):
        return self.__timeseries

    @timeseries.setter
    def timeseries(self, timeseries):
        self.__timeseries = timeseries

    @property
    def attributes(self):
        return self.__attributes

    @attributes.setter
    def attributes(self, attributes):
        self.__attributes = attributes

    @property
    def attribute_updates(self):
        return self.__attribute_updates

    @attribute_updates.setter
    def attribute_updates(self, attribute_updates):
        self.__attribute_updates = attribute_updates

    @property
    def function(self):
        return self.__function

    @function.setter
    def function(self, function):
        self.__function = function

    @property
    def extension(self):
        return self.__extension

    @extension.setter
    def extension(self, extension):
        self.__extension = extension

    @property
    def tags(self):
        return self.__tags

    @tags.setter
    def tags(self, tags):
        self.__tags = tags

    def get_tag_count(self):
        return len(self.__tags)

    @property
    def frequency(self):
        return self.__frequency

    @frequency.setter
    def frequency(self, frequency):
        self.__frequency = frequency
