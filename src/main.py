import logging
from src.gui.app import HttpGuiApp


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler("http_gui.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def main() -> None:
    setup_logging()
    app = HttpGuiApp()
    app.mainloop()


if __name__ == "__main__":
    main()
