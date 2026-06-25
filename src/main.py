from __future__ import annotations

from src.pipeline import WeatherPipelineRunner


def main() -> None:
    runner = WeatherPipelineRunner()
    runner.run_all()


if __name__ == "__main__":
    main()