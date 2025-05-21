from runner import Runner
from utils.config import load_config


def main():
    load_config("config.toml")
    runner = Runner()
    runner.run()

if __name__ == "__main__":
    main()