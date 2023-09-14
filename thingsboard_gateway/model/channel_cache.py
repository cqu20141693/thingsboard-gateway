# Example:
# devices: [device] 设备列表
# extension: 自定义数据


class ChannelCache:
    __slots__ = ('__devices', '__extension', '__tag_count', '__events')

    def __init__(self, devices=None, extension=None, events=None):
        if devices is None:
            devices = {}
        if events is None:
            events = {}
        if extension is None:
            extension = {}
        self.__devices = devices
        self.__extension = extension
        self.__events = events
        self.__tag_count = 0

    @property
    def devices(self):
        return self.__devices

    @devices.setter
    def devices(self, devices):
        self.__devices = devices

    @property
    def extension(self):
        return self.__extension

    @extension.setter
    def extension(self, extension):
        self.__extension = extension

    @property
    def tag_count(self):
        return self.__tag_count

    @tag_count.setter
    def tag_count(self, tag_count):
        self.__tag_count = tag_count

    @property
    def events(self):
        return self.__events

    @events.setter
    def events(self, events):
        self.__events = events
