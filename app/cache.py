"""
Redis 缓存管理器
"""
import json
import logging
import hashlib
from typing import Any, Optional, Callable
from functools import wraps
from datetime import timedelta

logger = logging.getLogger(__name__)


class CacheManager:
    """Redis 缓存管理器"""
    
    def __init__(self, redis_client=None):
        """
        初始化缓存管理器
        
        Args:
            redis_client: Redis 客户端实例（可选，如果为None则禁用缓存）
        """
        self.redis = redis_client
        self.enabled = redis_client is not None
        self.default_ttl = 300  # 默认缓存时间5分钟
        
        if self.enabled:
            logger.info("缓存管理器已启用")
        else:
            logger.info("缓存管理器未启用（Redis未配置）")
    
    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """生成缓存key"""
        key_data = f"{prefix}:{str(args)}:{str(sorted(kwargs.items()))}"
        return f"cache:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if not self.enabled:
            return None
        
        try:
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"获取缓存失败: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = None):
        """设置缓存"""
        if not self.enabled:
            return
        
        try:
            ttl = ttl or self.default_ttl
            await self.redis.setex(key, ttl, json.dumps(value, default=str))
        except Exception as e:
            logger.error(f"设置缓存失败: {e}")
    
    async def delete(self, key: str):
        """删除缓存"""
        if not self.enabled:
            return
        
        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.error(f"删除缓存失败: {e}")
    
    async def delete_pattern(self, pattern: str):
        """删除匹配模式的缓存"""
        if not self.enabled:
            return
        
        try:
            cursor = 0
            while True:
                cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
                if keys:
                    await self.redis.delete(*keys)
                if cursor == 0:
                    break
        except Exception as e:
            logger.error(f"删除缓存模式失败: {e}")
    
    def cached(self, ttl: int = None, key_prefix: str = None):
        """
        缓存装饰器
        
        Args:
            ttl: 缓存时间（秒）
            key_prefix: 缓存key前缀
        """
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                if not self.enabled:
                    return await func(*args, **kwargs)
                
                # 生成缓存key
                prefix = key_prefix or func.__name__
                cache_key = self._make_key(prefix, *args, **kwargs)
                
                # 尝试从缓存获取
                cached_result = await self.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"缓存命中: {prefix}")
                    return cached_result
                
                # 执行函数
                result = await func(*args, **kwargs)
                
                # 存入缓存
                await self.set(cache_key, result, ttl)
                logger.debug(f"缓存设置: {prefix}")
                
                return result
            return wrapper
        return decorator
    
    async def invalidate(self, key_prefix: str):
        """使指定前缀的缓存失效"""
        await self.delete_pattern(f"cache:{key_prefix}*")


class LocalCache:
    """本地内存缓存（用于单节点模式或无Redis场景）"""
    
    def __init__(self, max_size: int = 1000):
        self.cache = {}
        self.max_size = max_size
        self.access_order = []
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        import time
        if key in self.cache:
            value, expire_at = self.cache[key]
            if expire_at > time.time():
                # 更新访问顺序
                if key in self.access_order:
                    self.access_order.remove(key)
                self.access_order.append(key)
                return value
            else:
                # 过期了，删除
                del self.cache[key]
                if key in self.access_order:
                    self.access_order.remove(key)
        return None
    
    def set(self, key: str, value: Any, ttl: int = 300):
        """设置缓存"""
        import time
        
        # 检查容量，使用LRU淘汰
        while len(self.cache) >= self.max_size and self.access_order:
            oldest_key = self.access_order.pop(0)
            if oldest_key in self.cache:
                del self.cache[oldest_key]
        
        expire_at = time.time() + ttl
        self.cache[key] = (value, expire_at)
        
        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)
    
    def delete(self, key: str):
        """删除缓存"""
        if key in self.cache:
            del self.cache[key]
        if key in self.access_order:
            self.access_order.remove(key)
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
        self.access_order.clear()


# 全局缓存实例
_cache_manager: Optional[CacheManager] = None
_local_cache: Optional[LocalCache] = None


def get_cache() -> CacheManager:
    """获取全局缓存管理器"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


def init_cache(redis_client=None) -> CacheManager:
    """初始化缓存管理器"""
    global _cache_manager
    _cache_manager = CacheManager(redis_client)
    return _cache_manager


def get_local_cache() -> LocalCache:
    """获取本地缓存"""
    global _local_cache
    if _local_cache is None:
        _local_cache = LocalCache()
    return _local_cache

