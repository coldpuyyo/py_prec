import logging
import uvicorn

from main import app
from services.app_logger import configure_logging, get_logger
from services.trial_guard import enforce_trial_or_exit

if __name__ == "__main__":
    configure_logging(logging.INFO)
    logger = get_logger(__name__)

    logger.info("server bootstrap start")
    #enforce_trial_or_exit(app_name="PyPrecApp", trial_days=30)
    logger.info("trial guard passed")

    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)