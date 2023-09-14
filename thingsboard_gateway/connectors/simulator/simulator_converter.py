import logging
from abc import abstractmethod

from thingsboard_gateway.connectors.converter import Converter

class SimulatorConverter(Converter):
    def __init__(self):
        self.__result = {}

    @abstractmethod
    def convert(self, config, data):
        pass
