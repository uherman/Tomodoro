import curses
import sys

from .ui import App


def main():
    try:
        app = App()
        curses.wrapper(app.run)
    except KeyboardInterrupt:
        pass
    finally:
        print("Tomodoro timer ended. Stay focused!")


if __name__ == "__main__":
    main()
