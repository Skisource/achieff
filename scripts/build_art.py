from pathlib import Path

from achieff import artkit


def main() -> None:
    destination = (
        Path(__file__).resolve().parents[1] / "src" / "achieff" / "static" / "art"
    )
    artkit.write_sheets(destination)


if __name__ == "__main__":
    main()
