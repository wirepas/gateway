
import logging
import os
from time import time

from wirepas_gateway.utils import LoggerHelper
import wirepas_messaging

from wirepas_messaging.gateway.api import (
    GatewayResultCode,
)


class MaerskGatewayRequestParser():
    """
    
    """    

    def __init__(self, gw_id, firmware, imsi, wirepas_version, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.gw_id = gw_id
        self.epoch_ms = int(time() * 1000)
        self.firmware = firmware
        self.imsi = imsi
        self.wirepas_version = wirepas_version


    def parse(self, payload):
        """

        """ 

        message = wirepas_messaging.gateway.GenericMessage()
        message.ParseFromString(payload)

        # Check all the optional fields     
        if not message.HasField('customer'):
            raise MaerskParsingException("Cannot parse customer field")
        customer = message.customer
        
        if not customer.HasField('request'):
            raise MaerskParsingException("Cannot parse request field")
        request = customer.request
        
        if not request.HasField('gateway_req'):
            raise MaerskParsingException("Cannot parse gateway_req field")
        gateway_req = request.gateway_req
        
        # Check TTL
        if self.epoch_ms > request.header.time_to_live_epoch_ms:
            raise MaerskParsingException("ttl expired")
            
        # Parse request
        if gateway_req.HasField('gw_status_req'):
            return self._reply_gw_status_req(customer)
        
        else:
            raise MaerskParsingException("request not implemented")
        
    

    def _reply_gw_status_req(self, customerReq):
        """

        """ 

        reply = wirepas_messaging.gateway.GenericMessage()
        reply.customer.customer_name = customerReq.customer_name
        
        reply.customer.response.header.gateway_epoch_ms = self.epoch_ms 
        reply.customer.response.gateway_resp.header.req_id = customerReq.request.gateway_req.header.req_id
        reply.customer.response.gateway_resp.header.gw_id = self.gw_id
        reply.customer.response.gateway_resp.header.res = GatewayResultCode.GW_RES_OK.value
        reply.customer.response.gateway_resp.gw_status_resp.app_software = self.firmware;
        reply.customer.response.gateway_resp.gw_status_resp.wirepas_software = self.wirepas_version
        reply.customer.response.gateway_resp.gw_status_resp.imsi = self.imsi
        
        return reply.SerializeToString()
        
        
        
        
class MaerskParsingException(Exception):
    def __init__(self, msg):
        super().__init__(msg)
    