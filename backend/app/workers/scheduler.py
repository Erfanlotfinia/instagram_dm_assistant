from __future__ import annotations

import logging
import signal
import sys
import time

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.services.order_expiration_service import OrderExpirationService
from app.services.product_semantic_search_service import ProductSemanticSearchService

logger = logging.getLogger(__name__)


class SchedulerWorker:
    def __init__(self) -> None:
        self.settings = get_settings()
        configure_logging(self.settings)
        self._should_stop = False

    def run_once(self) -> None:
        db = SessionLocal()
        try:
            expired = OrderExpirationService(db).expire_stale_orders()
            if expired:
                logger.info("Expired %s unpaid orders", expired)

            refreshed = self._refresh_embeddings(db)
            if refreshed:
                logger.info("Refreshed embeddings for %s products", refreshed)
        except Exception:
            db.rollback()
            logger.exception("Background job cycle failed")
        finally:
            db.close()

    def _refresh_embeddings(self, db) -> int:
        from app.repositories.product_repository import ProductRepository
        from app.repositories.variant_repository import VariantRepository

        products = ProductRepository(db)
        variants = VariantRepository(db)
        search = ProductSemanticSearchService(db, settings=self.settings)
        active = products.list_active(limit=self.settings.embedding_refresh_batch_size)
        count = 0
        for product in active:
            product_variants = variants.list_for_product(product.id)
            search.index_product(product, product_variants)
            count += 1
        if count:
            db.commit()
        return count

    def start(self) -> None:
        interval = self.settings.background_job_interval_seconds
        logger.info("Scheduler started interval_seconds=%s", interval)
        while not self._should_stop:
            self.run_once()
            for _ in range(interval):
                if self._should_stop:
                    break
                time.sleep(1)
        logger.info("Scheduler shutdown complete")

    def stop(self) -> None:
        self._should_stop = True


def main() -> None:
    worker = SchedulerWorker()

    def _shutdown(_signum, _frame) -> None:
        logger.info("Scheduler shutdown signal received")
        worker.stop()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        worker.start()
    except KeyboardInterrupt:
        worker.stop()
    except Exception:
        logger.exception("Scheduler crashed")
        sys.exit(1)


if __name__ == "__main__":
    main()
