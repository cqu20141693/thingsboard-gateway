import logging

from thingsboard_gateway.connectors.converter import Converter
from thingsboard_gateway.connectors.simulator.simulator_converter import SimulatorConverter

log = logging.getLogger('connector')


class SimulatorUplinkConverter(SimulatorConverter):
    def __init__(self):
        self.__result = {}

    def convert(self, config=None,data=None):
        """

        @param config: None
        @param data: 读取的数据
        @return:
        {
        "tagType":{
        "tag1":"data",
        ...
        }
        }
        """
        self.__result["telemetry"] = []
        self.__result["attributes"] = []
        for tag in data:
            try:
                response = data[tag]['response']
                tag_type = data[tag]['type'].value
                self.__result[tag_type].append({tag: response})
            except Exception as e:
                log.error("Simulator Uplink Converter Fail, tag is %s, data is %s", str(tag), data)
                log.exception(e)
        return self.__result
