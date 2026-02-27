"""Base model for CSV data with load/save functionality."""

import csv
import pathlib
from typing import TYPE_CHECKING, ClassVar

from craft_application.models import CraftBaseModel

if TYPE_CHECKING:
    from typing import Self


class CsvModel(CraftBaseModel):
    """Base model for CSV data with load and save functionality.

    Subclasses must define the CSV_HEADERS class variable with column names.
    """

    CSV_HEADERS: ClassVar[list[str]] = []
    """Column headers for the CSV file."""

    @classmethod
    def load_from_csv(cls, file_path: pathlib.Path) -> list["Self"]:
        """Load data from a CSV file.

        :param file_path: Path to the CSV file to load.
        :return: List of model instances loaded from the CSV.
        """
        if not file_path.exists():
            return []

        with file_path.open("r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            return [cls(**row) for row in reader]

    @classmethod
    def save_to_csv(
        cls,
        data: list["CsvModel"] | list,
        file_path: pathlib.Path,
        *,
        append: bool = False,
    ) -> None:
        """Save data to a CSV file.

        :param data: List of model instances to save.
        :param file_path: Path to the CSV file to write.
        :param append: If True, append to the file. If False, overwrite.
        """
        if not cls.CSV_HEADERS:
            raise ValueError(
                f"{cls.__name__} must define CSV_HEADERS class variable",
            )

        mode = "a" if append else "w"
        write_header = not append or not file_path.exists()

        with file_path.open(mode, encoding="utf-8") as file:
            writer = csv.writer(file, lineterminator="\n")
            if write_header:
                writer.writerow(cls.CSV_HEADERS)
            for item in data:
                writer.writerow(item.to_csv_row())

    def to_csv_row(self) -> list[str]:
        """Convert the model instance to a CSV row.

        Subclasses should override this method to return values in the correct order.

        :return: List of values for the CSV row.
        """
        raise NotImplementedError("Subclasses must implement to_csv_row()")
