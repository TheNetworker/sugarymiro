#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "Bassem Aly"
__email__ = "basim.alyy@gmail.com"
__company__ = "TheNetworker"
__version__ = 0.1



# -----
from requests.exceptions import RequestException
from json.decoder import JSONDecodeError

class IftttError(Exception):
    """
    Base class for Ifttt exceptions
    """
    pass

class NightScoutDataIsInvalid(JSONDecodeError):
    """
    Base class for the invalid data returned from the NightScout API
    """
    pass

class NightScoutDataIsOld(Exception):
    """
    Base class for the invalid data returned from the NightScout API
    """
    pass

class NightScoutConnectionError(RequestException):
    """
    Base class for the connection errors returned from the NightScout API
    """
    pass
