# reconcile_stripe.py
#
# Thin CLI wrapper around app/services/reconciliation_service.py.
#
#   docker compose exec api python reconcile_stripe.py
#
# The same logic runs automatically every night via the APScheduler job in
# app/jobs/scheduler.py (with retries + a failure alert). This script is the
# manual/on-demand entry point for demos and ops.
import asyncio
import logging

import stripe

from app.config.settings import settings
from app.db.session import async_session_maker
from app.services.reconciliation_service import reconcile

stripe.api_key = settings.STRIPE_SECRET_KEY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reconcile_stripe")


async def main(db_session=None):
    """Fetch subscriptions from Stripe and reconcile them into the local DB.

    ``db_session`` is injectable for tests; when omitted a session is opened
    and committed here.
    """
    logger.info("=== STRIPE SUBSCRIPTION RECONCILIATION (manual run) ===")
    try:
        stripe_subs = await asyncio.to_thread(
            stripe.Subscription.list, limit=100, status="all"
        )
    except Exception as e:  # noqa: BLE001
        logger.error("Error fetching subscriptions from Stripe: %s", e)
        return

    data = stripe_subs.data
    logger.info("Fetched %d subscriptions from Stripe.", len(data))

    if db_session is not None:
        summary = await reconcile(db_session, data)
    else:
        async with async_session_maker() as db:
            summary = await reconcile(db, data)
            await db.commit()

    logger.info("=== RECONCILIATION COMPLETE: %s ===", summary)
    return summary


if __name__ == "__main__":
    asyncio.run(main())
