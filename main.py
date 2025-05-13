from runner import Runner
from utils.config import Config

def main():
    config = Config.from_file("config.toml")
    runner = Runner(config)
    runner.run()

if __name__ == "__main__":
    main()