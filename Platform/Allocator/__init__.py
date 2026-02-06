"""
Allocator - 資產配置器

使用方式:
>>> from Platform.Allocator import get_allocation
>>> 
>>> allocation = get_allocation(strategy, capital=1_000_000)
>>> print(allocation)
"""

from .allocator import Allocator, AllocationResult, get_allocation

__all__ = ['Allocator', 'AllocationResult', 'get_allocation']
