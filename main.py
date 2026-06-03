import logging
import sys

from src.bot import build_application

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    try:
        app = build_application()
    except RuntimeError as exc:
        logger.error("%s", exc)
        sys.exit(1)

    logger.info("Бот «Центр Красок #1» запущен. Ожидание сообщений...")
    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
