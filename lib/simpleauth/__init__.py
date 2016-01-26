"""
A simple auth handler for Google App Engine supporting
OAuth 1.0a, 2.0 and OpenID.
"""

__version__ = '0.1.5'
__license__ = 'MIT'
__author__ = 'Alex Vaghin (alex@cloudware.it)'

__all__ = []

from lib.simpleauth.handler import *
__all__ += handler.__all__
