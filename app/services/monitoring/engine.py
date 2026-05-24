import logging
from typing import List
from sqlalchemy.orm import Session
from app.models.guardian import GuardianWatchlist, GuardianAlert
from app.services.guardian import GuardianService
from app.services.monitoring.wallet_service import WalletIntelligenceService

logger = logging.getLogger(__name__)

class MonitoringEngine:
    @staticmethod
    async def process_watchlist_updates(db: Session):
        """
        Iterates through active watchlist items and triggers fresh scans.
        Generates alerts if significant security changes are detected.
        """
        active_items = db.query(GuardianWatchlist).filter(GuardianWatchlist.is_active == True).all()

        for item in active_items:
            try:
                if item.target_type == "contract":
                    # Perform a fresh scan
                    new_scan = await GuardianService.scan_contract(db, item.target_address)

                    # Logic to compare with previous states could go here
                    # For now, we rely on scan_contract's internal alert logic
                    logger.info(f"Monitoring: Scanned contract {item.target_address} for user {item.user_id}")

                elif item.target_type == "wallet":
                    result = await WalletIntelligenceService.analyze_wallet(db, item.target_address)
                    if result.get("is_malicious"):
                        logger.warning(f"Monitoring: Malicious wallet detected in watchlist: {item.target_address}")

            except Exception as e:
                logger.error(f"Monitoring Engine failed for {item.target_address}: {e}")

    @staticmethod
    def trigger_periodic_check(db: Session):
        """
        This would be called by a cron job or background task manager.
        """
        import asyncio
        asyncio.create_task(MonitoringEngine.process_watchlist_updates(db))
