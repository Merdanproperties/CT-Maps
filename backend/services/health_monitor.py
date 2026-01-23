"""
Health Monitor Service - Monitors and automatically recovers backend services
"""
import asyncio
import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class HealthMonitor:
    """Monitors database and other critical services, attempts auto-recovery"""
    
    def __init__(self):
        self.db_connection_attempts = 0
        self.max_db_retries = 5
        self.is_monitoring = False
        
    async def check_database_health(self) -> bool:
        """Check if database is accessible"""
        try:
            from database import engine
            async with engine.begin() as conn:
                await conn.execute("SELECT 1")
            self.db_connection_attempts = 0
            return True
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            self.db_connection_attempts += 1
            return False
    
    async def recover_database_connection(self) -> bool:
        """Attempt to recover database connection"""
        if self.db_connection_attempts >= self.max_db_retries:
            logger.error("Max database recovery attempts reached")
            return False
            
        try:
            # Try to reconnect
            from database import engine
            # Force connection pool refresh
            await engine.dispose()
            # Wait a bit before retry
            await asyncio.sleep(2)
            # Test connection
            async with engine.begin() as conn:
                await conn.execute("SELECT 1")
            logger.info("Database connection recovered")
            self.db_connection_attempts = 0
            return True
        except Exception as e:
            logger.error(f"Database recovery failed: {e}")
            return False
    
    async def start_monitoring(self, interval: int = 30):
        """Start continuous health monitoring"""
        if self.is_monitoring:
            return
            
        self.is_monitoring = True
        logger.info("Starting health monitoring service")
        
        while self.is_monitoring:
            try:
                # Check database health
                if not await self.check_database_health():
                    logger.warning("Database unhealthy, attempting recovery...")
                    await self.recover_database_connection()
                
                # Wait before next check
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(interval)
    
    def stop_monitoring(self):
        """Stop health monitoring"""
        self.is_monitoring = False
        logger.info("Stopped health monitoring service")


# Global instance
health_monitor = HealthMonitor()
