import copy
import multiprocessing
import time
from datetime import datetime

from thingsboard_gateway.connectors.connector import Connector, log
from thingsboard_gateway.connectors.simulator.simulator_clinet import SimulatorClient
from thingsboard_gateway.connectors.simulator.simulator_uplink_converter import SimulatorUplinkConverter
from thingsboard_gateway.gateway.constant_enums import Status
from thingsboard_gateway.model.channel_cache import ChannelCache
from thingsboard_gateway.model.device import Device
from thingsboard_gateway.model.iiot_emum import TagType, TagQuality
from thingsboard_gateway.model.tag import Tag
from thingsboard_gateway.model.util import fast_trace_id
from apscheduler.executors.pool import ProcessPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler

"""
连接器变量：
gateway： 用于接收，发送数据
config: 用于读取本地通道配置，设备配置和物模型配置
connector_type: 连接起类型

实现目标：
连接器单通道
连接器多通道
"""


class SimulatorConnector(Connector):

    def __init__(self, gateway, config, channel_type):

        super().__init__()
        self.__gateway = gateway  # Reference to TB Gateway
        self._connector_type = 'simulator'  # Should be "simulator"
        self._channel_type = channel_type  # single or mutil

        # single
        self.config = config.get("server", config)  # simulator.json contents

        self.channel_id = config.get("channelId", "singleChannelConnector")
        self.channel_name = config.get("channelName", "singleChannelConnector")

        self.scheduler = BackgroundScheduler(timezone='Asia/Shanghai', executors={
            'processpool': ProcessPoolExecutor(multiprocessing.cpu_count())
        })
        self.scheduler.start()
        # 设备网络连接状态
        self.connected = False
        # 当前连接器实例状态
        self.stopped = False
        # 加载通道基本配置
        self.connection_config = self.config.get('connection')
        self.report_config = self.config.get('report')

        # 初始化监控数据
        self.start_time = int(time.time())  # 启动时间
        self.channel_read_count = 0  # 通道读取点位累积次数
        self.device_read_count = {}  # 设备读取点位累积次数
        self.reconnect_num = 0
        self.last_reconnect_time = 0
        self.reconnect_time = 0
        self.fail_num = 0
        self.statistics = {'MessagesReceived': 0, 'MessagesSent': 0}

        # 加载通道点位配置
        self.channel_cache = ChannelCache()
        self.load_config()
        self.uplink_converter = SimulatorUplinkConverter()

        # 网络连接客户端，能进行数据的read，write，rpc行为
        self.client = SimulatorClient()

        log.info("Chanel [%s] init ...", self.channel_name)

    def get_config(self):
        return self.config

    def open(self):
        # 设置启用状态
        self.stopped = False
        self.set_connected(True)
        self.start_collect()

    def start_collect(self):
        self.channel_cache.extension["job_ids"] = []
        log.info(f"simulator start collect {self.channel_cache.extension}")
        # note 数据采集策略： 对于模拟器，可以通过定时读取，
        # mqtt主动推送的，通过订阅topic事件采集
        # modbus请求响应的可以通过配置读取策略
        if self.report_config["type"] == "single":
            job = self.scheduler.add_job(
                func=self.read_tags,
                args=[self.report_config["scanPeriodInMillis"]],
                trigger="interval",
                seconds=self.report_config["scanPeriodInMillis"] / 1000,
                next_run_time=datetime.now()
            )
            self.channel_cache.extension["job_ids"].append(job.id)
        else:
            if self.channel_cache.extension.get("frequency") is not None:
                for frequency in self.channel_cache.extension["frequency"]:
                    job = self.scheduler.add_job(
                        func=self.read_tags,
                        args=[frequency],
                        trigger="interval",
                        seconds=frequency / 1000,
                        next_run_time=datetime.now()
                    )
                    self.channel_cache.extension["job_ids"].append(job.id)

    def remove_jobs(self):
        if self.scheduler is not None and self.channel_cache.extension.get('job_ids') is not None:
            for job_id in self.channel_cache.extension['job_ids']:
                self.scheduler.remove_job(job_id)

    def set_connected(self, connected, device_online=True):
        """
        设置通道连接状态
        :param connected: 通道状态
        :param device_online: 设备上线事件是否绑定在通道状态连接上
        :return:
        """
        if connected == self.connected:
            # 通道状态未发生改变
            pass
        else:
            self.connected = connected
            if self.connected:
                if device_online:
                    # 上线
                    for device_name, device in self.channel_cache.devices.items():
                        self.__gateway.add_device(device_name, {"connector": self},
                                                  device_type={"deviceName": device.device_name,
                                                               "deviceType": device.device_type})

            else:
                # 下线
                for device_name in self.channel_cache.devices:
                    self.__gateway.del_device(device_name=device_name)

    def close(self, remote=False):
        try:
            self.remove_jobs()
            self.stopped = True
            self.set_connected(False)
            log.info('%s has been stopped.', self.get_name())

        except Exception as e:
            self.fail_num += 1
            log.exception(e)

    @staticmethod
    def __get_tag_data_type(tag):
        """
        根据用户配置的数据类型转换为IOT平台可以识别的数据类型
        @param tag: 点位
        @return: 数据类型字符串
        """
        data_type = 'String'
        config_type = tag.config.get('extension').get('type')  # 用户配置在配置软件中的数据类型：bool,int,long,float,string
        if config_type == 'bool':
            data_type = 'Bool'
        elif config_type == 'int':
            data_type = 'Integer'
        elif config_type == 'long':
            data_type = 'Long'
        elif config_type == 'float':
            data_type = 'Double'
        return data_type

    def __load_timeseries(self, device, config):
        for timeseries_config in config['timeseries']:
            tag = Tag(name=timeseries_config['tag'], config=timeseries_config, device_id=device.device_id,
                      device_name=device.device_name,
                      device_type=device.device_type, tag_type=TagType.TIMESERIES,
                      frequency=timeseries_config.get('scanPeriodInMillis', 5000))
            tag.send_data_only_on_change = self.get_tag_send_data_only_on_change(tag, config)

            tag.config['dataType'] = self.__get_tag_data_type(tag)
            if device.tags.get(tag.name):
                log.warning("Tag %s already exists, check your config", tag.name)
            else:
                device.tags[tag.name] = tag
                device.timeseries[tag.name] = timeseries_config

            self.__save_tag_frequency(device, tag)

    def __load_attributes(self, device, config):
        for attributes_config in config['attributes']:
            tag = Tag(name=attributes_config['tag'], config=attributes_config, device_id=device.device_id,
                      device_name=device.device_name,
                      device_type=device.device_type, tag_type=TagType.ATTRIBUTES,
                      frequency=attributes_config.get('scanPeriodInMillis', 5000))
            tag.send_data_only_on_change = self.get_tag_send_data_only_on_change(tag, config)
            if device.tags.get(tag.name):
                log.warning("Tag %s already exists, check your config", tag.name)
            else:
                device.tags[tag.name] = tag
                device.attributes[tag.name] = attributes_config

            self.__save_tag_frequency(device, tag)

    def __save_tag_frequency(self, device, tag):
        if self.report_config["type"] != "single":
            if not self.channel_cache.extension.get('frequency'):
                self.channel_cache.extension['frequency'] = {}
            self.channel_cache.extension['frequency'][tag.frequency] = tag.frequency
            if device.frequency.get(tag.frequency) is None:
                device.frequency[tag.frequency] = []
            device.frequency[tag.frequency].append(tag)
        else:
            if device.frequency.get(self.report_config["scanPeriodInMillis"]) is None:
                device.frequency[self.report_config["scanPeriodInMillis"]] = []
            device.frequency[self.report_config["scanPeriodInMillis"]].append(tag)

    def load_config(self):
        for device_config in self.config["devices"]:
            device = Device(extension={}, channel_id=self.channel_id)

            config = copy.deepcopy(device_config)
            device.device_id = config['deviceId']
            device.device_name = config['deviceName']
            device.device_type = config['deviceType']

            self.__load_timeseries(device, config)
            self.__load_attributes(device, config)

            for attribute_update_config in device_config['attributesUpdates']:
                device.attribute_updates[attribute_update_config['tag']] = attribute_update_config

            for function_config in device_config['function']:
                device.function[function_config['method']] = function_config

            del config['timeseries']
            del config['attributes']
            del config['attributesUpdates']
            del config['function']
            device.config = config

            self.channel_cache.tag_count += device.get_tag_count()
            self.channel_cache.devices[device.device_id] = device

    def read_tags(self, frequency=None):
        if self.stopped:
            return
        if not self.connected:
            return
        trace_id = fast_trace_id()
        try:
            read_result = self.read_batch(frequency)
            self.convert_send_data_single(trace_id, read_result)

        except Exception as e:
            self.fail_num += 1
            log.exception(e)
            self.set_all_bad()
            self.check_connect()

    def set_all_bad(self):
        for device_id in self.channel_cache.devices:
            self.set_bad_quality(device_id)

    def set_bad_quality(self, device_id):
        device = self.channel_cache.devices.get(device_id)
        if device:
            for tag_key in device.tags:
                device.tags[tag_key].quality = TagQuality.BAD

    def get_tag_send_data_only_on_change(self, tag, device_config):
        # 优先级： 点位>设备>通道
        if tag.config.get("sendDataOnlyOnChange", False):
            return True
        if device_config.get("sendDataOnlyOnChange", False):
            return True
        return self.report_config.get("sendDataOnlyOnChange", False)

    def convert_send_data_single(self, trace_id, read_result):
        """
        单频率转换并发送数据
        :param trace_id: 链路id
        :param read_result: 读取的结果
        :return:
        """
        channel_cache = self.get_channel_cache()
        for device_id in read_result:
            device_name = channel_cache.devices[device_id].device_name
            device_type = channel_cache.devices[device_id].device_type

            converted_data = self.uplink_converter.convert(data=read_result[device_id])
            if converted_data is None:
                continue

            to_send = {
                "deviceName": device_id,
                "deviceType": device_type,
                "deviceId": device_id,
                "telemetry": [],
                "attributes": [],
            }

            send_data_only_on_change = self.report_config.get("sendDataOnlyOnChange")

            for telemetry_dict in converted_data["telemetry"]:
                for key, value in telemetry_dict.items():
                    tag = self.channel_cache.devices[device_id].tags[key]
                    if tag.send_data_only_on_change is not None:
                        send_data_only_on_change = tag.send_data_only_on_change
                    if send_data_only_on_change:
                        if tag.value != value:
                            to_send["telemetry"].append({key: value})
                    else:
                        to_send["telemetry"].append({key: value})
                    # note-更新tag数据
                    tag.value = value
                    tag.quality = TagQuality.GOOD
                    tag.time = int(time.time() * 1000)
            for attribute_dict in converted_data["attributes"]:
                for key, value in attribute_dict.items():
                    tag = self.channel_cache.devices[device_id].tags[key]
                    if tag.send_data_only_on_change is not None:
                        send_data_only_on_change = tag.send_data_only_on_change
                    if send_data_only_on_change:
                        if tag.value != value:
                            to_send["attributes"].append({key: value})
                    else:
                        to_send["attributes"].append({key: value})
                    tag.value = value
                    tag.quality = TagQuality.GOOD
                    tag.time = int(time.time() * 1000)
            to_send["trace_id"] = trace_id
            if to_send.get("attributes") or to_send.get("telemetry"):
                if self.__gateway.send_to_storage(self._connector_type, to_send) == Status.SUCCESS:
                    self.statistics['MessagesSent'] += 1

    def read_batch(self, frequency):
        """
        读取frequency对应的tag数据
        @param frequency: 频率key
        @return:
        {
        "deviceId1":[
           "tag1":{
           "type": "tagType", @{link TagType}
           "response":"data"
           },
           ...
        ],
        ...
        }
        """
        read_result = {}

        for device_id in self.channel_cache.devices:
            device = self.channel_cache.devices[device_id]
            tags = device.frequency.get(frequency)
            if tags is None:
                continue
            try:
                result = self.client.get_values(tags)
                for tag_key in result:
                    tag = device.tags[tag_key]
                    to_converted_data = {
                        "type": tag.tag_type,
                        "response": result[tag_key]
                    }

                    if read_result.get(tag.device_id) is None:
                        read_result[tag.device_id] = {}
                        read_result[tag.device_id][tag.config['tag']] = to_converted_data
                    else:
                        read_result[tag.device_id][tag.config['tag']] = to_converted_data

                    self.channel_read_count += 1
                    if self.device_read_count.get(tag.device_id) is None:
                        self.device_read_count[tag.device_id] = {
                            "name": tag.device_name,
                            "count": 0
                        }
                    self.device_read_count[tag.device_id]['count'] += 1
            except Exception as e:
                log.warning(e)
                self.set_bad_quality(device_id)

        return read_result

    def is_connected(self):
        return self.connected

    def get_name(self):
        return self.channel_name

    def get_id(self):
        return self.channel_id

    def on_attributes_update(self, content):
        device_id = content["device"]
        log.info("Simulator Channel received attributes_update request for %s with content: %s", device_id,
                 content)
        message_id = content["messageId"]
        attributes = content["data"]
        try:
            find_tag = False
            success = False
            message = ''
            ret = {}
            device = self.channel_cache.devices.get(device_id)
            if not device:
                message = '设备不存在'
                self.__gateway.send_rpc_reply(device=device_id, req_id=message_id, content=message)

                return False, message

            for key in attributes:
                attribute_update = device.attribute_updates.get(key)
                if not attribute_update:
                    log.warning("Simulator channel [%s] cannot found attribute_update tag [%s]", self.channel_id, key)
                    continue

                tag = device.tags.get(key)
                if not tag:
                    log.warning("Simulator channel [%s] cannot found attribute_update tag [%s]", self.channel_id,
                                key)
                    continue

                find_tag = True
                f, message = self.client.write_value(tag, attributes[key])
                if success:
                    success = True
                ret.__setitem__(f, message)
            if find_tag and success:

                message = '执行成功'
                self.__gateway.send_rpc_reply(device=device_id, req_id=message_id, content=message,
                                              success=True)
                return True, message

            elif not find_tag:
                message = '点位不存在'
                self.__gateway.send_rpc_reply(device=device_id, req_id=message_id, content=message)
                return False, message
            elif not success:
                self.__gateway.send_rpc_reply(device=device_id, req_id=message_id, content=message)

                return False, message
        except Exception as e:
            self.fail_num += 1
            log.exception(e)
            message = '执行失败'
            self.__gateway.send_rpc_reply(device=device_id, req_id=message_id, content=message)

            return False, message

    def server_side_rpc_handler(self, content):
        log.info("Simulator Channel received rpc request for %s with content: %s", content["deviceId"],
                 content)
        device_id = content['device']
        message_id = content['data']['id']

        try:
            function_key = content["data"]["method"]
            device = self.channel_cache.devices.get(device_id)

            if not device:
                message = "设备不存在"
                self.__gateway.send_rpc_reply(device=device_id, req_id=message_id, content=message)

                return False, message

            _function = device.function.get(function_key)
            if not _function:
                log.warning("Simulator channel [%s] cannot found function [%s]", self.channel_id, function_key)
                message = "方法不存在"
                self.__gateway.send_rpc_reply(device=device_id, req_id=message_id, content=message)

                return False, message

            tag_key = _function['extension']['tag']
            tag = device.tags.get(tag_key)
            if not tag:
                log.warning("Simulator channel [%s] cannot found function tag [%s]", self.channel_id,
                            tag_key)
                message = "点位不存在"
                self.__gateway.send_rpc_reply(device=device_id, req_id=message_id, content=message)

                return False, message

            arguments_from_config = _function['extension'].get("arg")
            arguments = content["data"].get("params") if content["data"].get(
                "params") is not None and content["data"].get(
                "params") != '' else arguments_from_config
            success, message = self.client.write_value(tag, arguments)
            if not success:
                self.__gateway.send_rpc_reply(device=device_id, req_id=message_id, content=message)

                return False, message

            message = "执行成功"
            self.__gateway.send_rpc_reply(device=device_id, req_id=message_id, content=message, success=True)
            return True, message
        except Exception as e:
            self.fail_num += 1
            log.exception(e)

            message = "执行失败"
            self.__gateway.send_rpc_reply(device=device_id, req_id=message_id, content=message)

            return False, message

    def on_attributes_read(self, content):
        log.info("Simulator Channel received attributes read request for %s with content: %s", content["deviceId"],
                 content)
        device_id = content['device']
        message_id = content['data']['id']

        try:
            result = {}
            read_value = False
            for tag_key in content['properties']:
                tag = self.channel_cache.devices[device_id].tags.get(tag_key)
                if tag:
                    try:
                        value = self.client.get_value(tag)
                        read_value = True
                        result[tag_key] = value
                    except Exception as e:
                        self.fail_num += 1
                        log.exception(e)
            if read_value:
                self.__gateway.send_rpc_reply(req_id=message_id, device_id=device_id,
                                              content=result, success=True)
            else:
                self.__gateway.send_rpc_reply(req_id=message_id, device_id=device_id,
                                              success=False, content="未读取到属性数据")

        except Exception as e:
            self.fail_num += 1
            log.exception(e)
            self.__gateway.send_rpc_reply(req_id=message_id, device_id=device_id,
                                          success=False, content="读取失败")

    def health_check_info(self):
        info_dict = {
            "connected": self.connected,
            "stopped": self.stopped,
            "last_reconnect_time": self.last_reconnect_time,
            "reconnect_time": self.reconnect_time,
            "reconnect_num": self.reconnect_num,
            "fail_num": self.fail_num
        }

        device_tag_count = {}
        for device_id in self.channel_cache.devices:
            device = self.channel_cache.devices[device_id]
            device_tag_count[device_id] = device.get_tag_count()

        health_dict = {
            "name": self.get_name(),
            "type": "opc",
            "server_type": "client",
            "report_type": self.report_config['type'],
            "connect_info": info_dict,
            "statistics": self.statistics,
            "running_time": int(time.time()) - self.start_time,
            "tag_statistics": {
                "channel_read_count": self.channel_read_count,
                "device_read_count": self.device_read_count,
                "channel_tag_count": self.channel_cache.tag_count,
                "device_tag_count": device_tag_count,
            }
        }
        return health_dict

    def check_connect(self):
        # 模拟器没有检查连接的功能
        pass

    def get_channel_cache(self):
        return self.channel_cache

    def update_converter_config(self, converter_name, config):
        log.info(f"receive simulator converter={converter_name} config={config}")
