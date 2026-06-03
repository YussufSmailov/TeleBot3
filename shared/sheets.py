"""
Google Sheets клиент.

Структура листов:
  Streams   — A:name, B:start_date (YYYY-MM-DD или DD.MM.YYYY)
  Groups    — A:stream_name, B:group_name
  Lessons   — A:lesson_number, B:week_number, C:title
  Tests     — A:week_number, B:title
  Facts     — A:week_number, B:stream_name (пусто=все), C:text
  Quotes    — A:week_number (пусто=любая), B:author, C:text
  Practices — A:stream_name, B:group_name (пусто=все), C:datetime (DD.MM.YYYY HH:MM)
  Curators  — A:full_name, B:stream_name, C:group_name
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

import gspread
import pytz
from google.oauth2.service_account import Credentials

from config import settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

TZ = pytz.timezone(settings.timezone)


@dataclass
class StreamData:
    name: str
    start_date: date

    @property
    def current_week(self) -> int:
        delta = (date.today() - self.start_date).days
        return max(1, min(delta // 7 + 1, 25))

    def deadline_for_week(self, week: int) -> datetime:
        from datetime import timedelta
        sunday = self.start_date + timedelta(weeks=week - 1, days=6)
        return datetime(sunday.year, sunday.month, sunday.day, 12, 0, 0)


@dataclass
class LessonData:
    lesson_number: int
    week_number: int
    title: str


@dataclass
class TestData:
    week_number: int
    title: str


@dataclass
class FactData:
    week_number: int
    stream_name: Optional[str]
    text: str


@dataclass
class QuoteData:
    week_number: Optional[int]
    author: str
    text: str


@dataclass
class PracticeSheetData:
    stream_name: str
    group_name: Optional[str]
    scheduled_at: datetime


class SheetsClient:
    def __init__(self) -> None:
        creds = Credentials.from_service_account_file(
            settings.google_sheets_key_file, scopes=SCOPES
        )
        self._gc = gspread.authorize(creds)
        self._wb = None

    def _wb_open(self):
        if self._wb is None:
            self._wb = self._gc.open_by_key(settings.google_sheet_id)
        return self._wb

    def _get_rows(self, sheet_name: str) -> list[list]:
        try:
            ws = self._wb_open().worksheet(sheet_name)
            rows = ws.get_all_values()
            return rows[1:] if rows else []
        except Exception as e:
            logger.error(f"Sheets error [{sheet_name}]: {e}")
            return []

    def get_streams(self) -> list[StreamData]:
        result = []
        for row in self._get_rows("Streams"):
            if len(row) < 2 or not row[0]:
                continue
            try:
                raw = row[1].strip()
                try:
                    parsed = datetime.strptime(raw, "%Y-%m-%d").date()
                except ValueError:
                    parsed = datetime.strptime(raw, "%d.%m.%Y").date()
                result.append(StreamData(name=row[0].strip(), start_date=parsed))
            except ValueError as e:
                logger.warning(f"Streams parse error: {e} row={row}")
        return result

    def get_groups_for_stream(self, stream_name: str) -> list[str]:
        result = []
        for row in self._get_rows("Groups"):
            if len(row) < 2 or not row[0]:
                continue
            if row[0].strip() == stream_name:
                result.append(row[1].strip())
        return result

    def get_lessons(self, week_number: int) -> list[LessonData]:
        result = []
        for row in self._get_rows("Lessons"):
            if len(row) < 3 or not row[0]:
                continue
            try:
                if int(row[1]) == week_number:
                    result.append(LessonData(
                        lesson_number=int(row[0]),
                        week_number=int(row[1]),
                        title=row[2].strip(),
                    ))
            except ValueError:
                continue
        return sorted(result, key=lambda l: l.lesson_number)

    def get_test(self, week_number: int) -> Optional[TestData]:
        for row in self._get_rows("Tests"):
            if len(row) < 2 or not row[0]:
                continue
            try:
                if int(row[0]) == week_number:
                    return TestData(week_number=week_number, title=row[1].strip())
            except ValueError:
                continue
        return None

    def get_facts(self, week_number: int, stream_name: str) -> list[FactData]:
        result = []
        for row in self._get_rows("Facts"):
            if len(row) < 3 or not row[0]:
                continue
            try:
                week = int(row[0])
                s_name = row[1].strip() or None
                if week == week_number and (s_name is None or s_name == stream_name):
                    result.append(FactData(week_number=week, stream_name=s_name, text=row[2].strip()))
            except ValueError:
                continue
        return result

    def get_quotes(self, week_number: int) -> list[QuoteData]:
        result = []
        for row in self._get_rows("Quotes"):
            if len(row) < 3 or not row[1]:
                continue
            week = int(row[0]) if row[0].strip() else None
            if week is None or week == week_number:
                result.append(QuoteData(week_number=week, author=row[1].strip(), text=row[2].strip()))
        return result

    def get_tomiris_practices(self) -> list[PracticeSheetData]:
        result = []
        for row in self._get_rows("Practices"):
            if len(row) < 2 or not row[0]:
                continue
            try:
                dt = TZ.localize(datetime.strptime(row[1].strip(), "%d.%m.%Y %H:%M"))
                group = row[2].strip() if len(row) > 2 and row[2].strip() else None
                result.append(PracticeSheetData(
                    stream_name=row[0].strip(),
                    group_name=group,
                    scheduled_at=dt,
                ))
            except (ValueError, IndexError) as e:
                logger.warning(f"Practices parse error: {e} row={row}")
        return result

    def get_curator_names(self) -> list[str]:
        names = []
        for row in self._get_rows("Curators"):
            if len(row) < 3 or not row[0]:
                continue
            if row[0].strip() not in names:
                names.append(row[0].strip())
        return names

    def get_curator_groups(self, full_name: str) -> list[dict]:
        result = []
        for row in self._get_rows("Curators"):
            if len(row) < 3 or not row[0]:
                continue
            if row[0].strip() == full_name:
                result.append({
                    "full_name": row[0].strip(),
                    "stream_name": row[1].strip(),
                    "group_name": row[2].strip(),
                })
        return result


_client: Optional[SheetsClient] = None


def get_sheets() -> SheetsClient:
    global _client
    if _client is None:
        _client = SheetsClient()
    return _client
