"""
Home Computer Power Sharing System

Desktop-to-phone bridge with local compute marketplace,
neighbor discovery, and automatic cloud failover.
"""

from .compute_bridge import ComputeBridge, DeviceType, ConnectionMethod
from .local_marketplace import LocalMarketplace, ComputeResource, PricingModel
from .neighbor_discovery import NeighborDiscovery, NetworkDevice, TrustLevel
from .cloud_failover import CloudFailoverManager, FailoverTrigger, CloudProvider

__all__ = [
    "ComputeBridge",
    "DeviceType", 
    "ConnectionMethod",
    "LocalMarketplace",
    "ComputeResource",
    "PricingModel", 
    "NeighborDiscovery",
    "NetworkDevice",
    "TrustLevel",
    "CloudFailoverManager",
    "FailoverTrigger",
    "CloudProvider"
]