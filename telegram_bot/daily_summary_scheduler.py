#!/usr/bin/env python3
"""
Daily Summary Scheduler for Telegram Bot

Sends daily summary notification at 23:59 UTC.
Can be run as:
1. Cron job: `59 23 * * * /path/to/venv/bin/python3 /path/to/daily_summary_scheduler.py`
2. Standalone daemon with scheduling
3. Integrated into main bot loop
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def send_summary_now():
    """Send daily summary immediately."""
    try:
        from telegram_bot.telegram_notifier import notify_daily_summary

        logger.info("Sending daily summary...")
        notify_daily_summary()
        logger.info("Daily summary sent successfully")
        return True
    except Exception as e:
        logger.error(f"Error sending daily summary: {e}", exc_info=True)
        return False


def run_daemon():
    """Run as daemon, sending summary at 23:59 UTC daily."""
    logger.info("Starting daily summary scheduler daemon...")

    while True:
        try:
            now = datetime.utcnow()

            # Calculate next 23:59 UTC
            target_time = now.replace(hour=23, minute=59, second=0, microsecond=0)

            # If we've passed today's 23:59, schedule for tomorrow
            if now >= target_time:
                target_time += timedelta(days=1)

            # Calculate seconds until target
            time_until_send = (target_time - now).total_seconds()

            logger.info(f"Next summary scheduled for {target_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            logger.info(f"Waiting {time_until_send / 3600:.1f} hours...")

            # Sleep until target time
            time.sleep(time_until_send)

            # Send summary
            send_summary_now()

            # Wait 2 minutes to avoid double-sending
            time.sleep(120)

        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in scheduler loop: {e}", exc_info=True)
            # Sleep 5 minutes before retrying
            time.sleep(300)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--now":
        # Send immediately (useful for testing or cron jobs)
        success = send_summary_now()
        sys.exit(0 if success else 1)
    else:
        # Run as daemon
        run_daemon()
