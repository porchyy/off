"""Daily and monthly OffSyn Tech Excel report generation."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from io import BytesIO
from pathlib import Path
import re
from typing import Any
from zoneinfo import ZoneInfo

from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .models import Alert, DailySummary, MinuteSummary, Sample

LOCAL_TZ = ZoneInfo("Asia/Bangkok")
HEADER_FILL = PatternFill("solid", fgColor="1E3A5F")
RISK_FILL = PatternFill("solid", fgColor="FDE2E2")


def local_day_bounds(report_date: date) -> tuple[str, str]:
    start = datetime.combine(report_date, time.min, tzinfo=LOCAL_TZ).astimezone(timezone.utc)
    end = start + timedelta(days=1)
    return start.isoformat(), end.isoformat()


def local_month_bounds(report_month: date) -> tuple[str, str]:
    """Return UTC ISO bounds for the Bangkok calendar month containing report_month."""
    start_local = datetime(report_month.year, report_month.month, 1, tzinfo=LOCAL_TZ)
    if report_month.month == 12:
        end_local = datetime(report_month.year + 1, 1, 1, tzinfo=LOCAL_TZ)
    else:
        end_local = datetime(report_month.year, report_month.month + 1, 1, tzinfo=LOCAL_TZ)
    return start_local.astimezone(timezone.utc).isoformat(), end_local.astimezone(timezone.utc).isoformat()


def local_today() -> date:
    return datetime.now(LOCAL_TZ).date()


def _utc_minute(timestamp: str) -> str:
    parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(second=0, microsecond=0).isoformat()


def local_day_label(timestamp: str) -> str:
    parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(LOCAL_TZ).date().isoformat()


def compact_legacy_samples(db: Session, risk_threshold: int) -> int:
    """Move old high-frequency rows into one aggregate per minute exactly once."""
    samples = list(db.scalars(select(Sample).order_by(Sample.id)))
    if not samples:
        return 0
    existing = {row.minute_start: row for row in db.scalars(select(MinuteSummary))}
    for sample in samples:
        minute_start = _utc_minute(sample.created_at)
        row = existing.get(minute_start)
        if row is None:
            row = MinuteSummary(
                minute_start=minute_start,
                score_sum=0.0,
                score_min=sample.score,
                score_max=sample.score,
                neck_sum=0.0,
                shoulders_sum=0.0,
                torso_sum=0.0,
                measurements=0,
                risk_measurements=0,
            )
            existing[minute_start] = row
            db.add(row)
        row.score_sum += sample.score
        row.score_min = min(row.score_min, sample.score)
        row.score_max = max(row.score_max, sample.score)
        row.neck_sum += sample.neck or 0.0
        row.shoulders_sum += sample.shoulders or 0.0
        row.torso_sum += sample.torso or 0.0
        row.measurements += 1
        row.risk_measurements += int(sample.score < risk_threshold)
    db.execute(delete(Sample))
    db.commit()
    return len(samples)


def prune_expired_reports(report_dir: Path, days: int) -> int:
    """Remove only dated OffSyn Tech or legacy PostureAI reports outside the retention window."""
    if not report_dir.exists():
        return 0
    cutoff = local_today() - timedelta(days=days)
    removed = 0
    pattern = re.compile(r"(?:OffSynTech|PostureAI)_(\d{4}-\d{2}-\d{2})\.xlsx$")
    for report in report_dir.iterdir():
        match = pattern.fullmatch(report.name)
        if not report.is_file() or match is None:
            continue
        try:
            report_date = date.fromisoformat(match.group(1))
        except ValueError:
            continue
        if report_date < cutoff:
            report.unlink()
            removed += 1
    return removed


def _minute_rows(db: Session, report_date: date, risk_threshold: int) -> list[dict[str, Any]]:
    start, end = local_day_bounds(report_date)
    return _minute_rows_between(db, start, end, risk_threshold)


def _minute_rows_between(db: Session, start: str, end: str, risk_threshold: int) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}

    for row in db.scalars(
        select(MinuteSummary).where(MinuteSummary.minute_start >= start, MinuteSummary.minute_start < end)
    ):
        buckets[row.minute_start] = {
            "minute_start": row.minute_start,
            "score_sum": row.score_sum,
            "score_min": row.score_min,
            "score_max": row.score_max,
            "neck_sum": row.neck_sum,
            "shoulders_sum": row.shoulders_sum,
            "torso_sum": row.torso_sum,
            "measurements": row.measurements,
            "risk_measurements": row.risk_measurements,
        }

    # Include historical samples written before minute aggregation was introduced.
    legacy = db.scalars(select(Sample).where(Sample.created_at >= start, Sample.created_at < end))
    for row in legacy:
        minute = _utc_minute(row.created_at)
        bucket = buckets.setdefault(
            minute,
            {
                "minute_start": minute,
                "score_sum": 0.0,
                "score_min": row.score,
                "score_max": row.score,
                "neck_sum": 0.0,
                "shoulders_sum": 0.0,
                "torso_sum": 0.0,
                "measurements": 0,
                "risk_measurements": 0,
            },
        )
        bucket["score_sum"] += row.score
        bucket["score_min"] = min(bucket["score_min"], row.score)
        bucket["score_max"] = max(bucket["score_max"], row.score)
        bucket["neck_sum"] += row.neck or 0.0
        bucket["shoulders_sum"] += row.shoulders or 0.0
        bucket["torso_sum"] += row.torso or 0.0
        bucket["measurements"] += 1
        bucket["risk_measurements"] += int(row.score < risk_threshold)

    rows = []
    for bucket in buckets.values():
        count = max(1, bucket["measurements"])
        local_time = datetime.fromisoformat(bucket["minute_start"]).astimezone(LOCAL_TZ)
        risk_seconds = round(60 * bucket["risk_measurements"] / count)
        rows.append(
            {
                "time": local_time.replace(tzinfo=None),
                "score": bucket["score_sum"] / count,
                "score_min": bucket["score_min"],
                "score_max": bucket["score_max"],
                "neck": bucket["neck_sum"] / count,
                "shoulders": bucket["shoulders_sum"] / count,
                "torso": bucket["torso_sum"] / count,
                "measurements": count,
                "risk_seconds": risk_seconds,
                "status": "เสี่ยง" if risk_seconds else "ดี",
            }
        )
    return sorted(rows, key=lambda row: row["time"])


def _alert_rows(db: Session, report_date: date) -> list[Alert]:
    start, end = local_day_bounds(report_date)
    return _alert_rows_between(db, start, end)


def _alert_rows_between(db: Session, start: str, end: str) -> list[Alert]:
    return list(db.scalars(select(Alert).where(Alert.created_at >= start, Alert.created_at < end).order_by(Alert.created_at)))


def _history_bounds(start_date: date | None, end_date: date | None) -> tuple[str, str]:
    start = local_day_bounds(start_date)[0] if start_date else "0001-01-01T00:00:00+00:00"
    end = local_day_bounds(end_date)[0] if end_date else "9999-12-31T23:59:59+00:00"
    return start, end


def _raw_daily_aggregates(
    db: Session,
    risk_threshold: int,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, dict[str, float | int | None]]:
    """Aggregate retained minute/alert rows by Bangkok day; end_date is exclusive."""
    start, end = _history_bounds(start_date, end_date)
    daily: dict[str, dict[str, float | int | None]] = {}
    for row in _minute_rows_between(db, start, end, risk_threshold):
        label = row["time"].date().isoformat()
        bucket = daily.setdefault(
            label,
            {
                "score_sum": 0.0,
                "score_min": None,
                "score_max": None,
                "measurements": 0,
                "periods": 0,
                "risk_seconds": 0,
                "alerts": 0,
            },
        )
        measurements = int(row["measurements"])
        bucket["score_sum"] = float(bucket["score_sum"]) + float(row["score"]) * measurements
        bucket["measurements"] = int(bucket["measurements"]) + measurements
        bucket["periods"] = int(bucket["periods"]) + 1
        bucket["risk_seconds"] = int(bucket["risk_seconds"]) + int(row["risk_seconds"])
        bucket["score_min"] = (
            float(row["score_min"])
            if bucket["score_min"] is None
            else min(float(bucket["score_min"]), float(row["score_min"]))
        )
        bucket["score_max"] = (
            float(row["score_max"])
            if bucket["score_max"] is None
            else max(float(bucket["score_max"]), float(row["score_max"]))
        )

    for alert in _alert_rows_between(db, start, end):
        label = local_day_label(alert.created_at)
        bucket = daily.setdefault(
            label,
            {
                "score_sum": 0.0,
                "score_min": None,
                "score_max": None,
                "measurements": 0,
                "periods": 0,
                "risk_seconds": 0,
                "alerts": 0,
            },
        )
        bucket["alerts"] = int(bucket["alerts"]) + 1
    return daily


def daily_history(
    db: Session,
    risk_threshold: int,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, float | int | str | None]]:
    """Merge persisted summaries with retained raw days, preferring current raw values."""
    statement = select(DailySummary)
    if start_date is not None:
        statement = statement.where(DailySummary.day >= start_date.isoformat())
    if end_date is not None:
        statement = statement.where(DailySummary.day < end_date.isoformat())
    merged: dict[str, dict[str, float | int | str | None]] = {
        row.day: {
            "label": row.day,
            "score_sum": row.score_sum,
            "score_min": row.score_min,
            "score_max": row.score_max,
            "measurements": row.measurements,
            "periods": row.periods,
            "risk_seconds": row.risk_seconds,
            "alerts": row.alert_count,
        }
        for row in db.scalars(statement)
    }
    for label, values in _raw_daily_aggregates(db, risk_threshold, start_date, end_date).items():
        merged[label] = {"label": label, **values}
    return [merged[label] for label in sorted(merged)]


def capture_daily_summaries(
    db: Session,
    risk_threshold: int,
    start_date: date | None = None,
    end_date: date | None = None,
) -> int:
    """Upsert raw aggregates before detailed rows are removed; end_date is exclusive."""
    raw = _raw_daily_aggregates(db, risk_threshold, start_date, end_date)
    updated_at = datetime.now(timezone.utc).isoformat()
    for label, values in raw.items():
        row = db.get(DailySummary, label)
        if row is None:
            row = DailySummary(day=label)
            db.add(row)
        row.score_sum = float(values["score_sum"])
        row.score_min = float(values["score_min"]) if values["score_min"] is not None else None
        row.score_max = float(values["score_max"]) if values["score_max"] is not None else None
        row.measurements = int(values["measurements"])
        row.periods = int(values["periods"])
        row.risk_seconds = int(values["risk_seconds"])
        row.alert_count = int(values["alerts"])
        row.updated_at = updated_at
    db.commit()
    return len(raw)


def prune_daily_summaries(db: Session, days: int) -> int:
    """Keep compact daily aggregates for a longer, independent retention window."""
    cutoff = (local_today() - timedelta(days=days)).isoformat()
    removed = db.execute(delete(DailySummary).where(DailySummary.day < cutoff)).rowcount or 0
    db.commit()
    return removed


def build_daily_report(db: Session, report_date: date, risk_threshold: int) -> bytes:
    """Create a readable Excel workbook for one Bangkok calendar day."""
    minute_rows = _minute_rows(db, report_date, risk_threshold)
    alerts = _alert_rows(db, report_date)
    history = daily_history(db, risk_threshold, report_date, report_date + timedelta(days=1))
    day_summary = history[0] if history else None
    workbook = Workbook()
    summary = workbook.active
    summary.title = "สรุปรายวัน"
    detail = workbook.create_sheet("รายละเอียดรายนาที")
    alert_sheet = workbook.create_sheet("เหตุการณ์แจ้งเตือน")

    summary.merge_cells("A1:H1")
    summary["A1"] = "Ergo Agent — รายงานท่านั่งรายวัน"
    summary["A1"].font = Font(bold=True, color="FFFFFF", size=14)
    summary["A1"].fill = HEADER_FILL
    summary["A1"].alignment = Alignment(horizontal="center")
    summary["A2"] = "วันที่รายงาน"
    summary["B2"] = report_date
    summary["B2"].number_format = "dd/mm/yyyy"
    summary["A3"] = "หมายเหตุ"
    summary["B3"] = "ข้อมูลรายนาทีเก็บตามนโยบายระบบ ส่วนสรุปรายวันเก็บระยะยาว ไม่รวมภาพหรือวิดีโอ"
    summary["B3"].alignment = Alignment(wrap_text=True)
    if minute_rows:
        last_row = len(minute_rows) + 1
        summary_rows = [
            ("คะแนนเฉลี่ย", f"=IFERROR(SUMPRODUCT('รายละเอียดรายนาที'!B2:B{last_row},'รายละเอียดรายนาที'!H2:H{last_row})/SUM('รายละเอียดรายนาที'!H2:H{last_row}),0)"),
            ("คะแนนต่ำสุด", f"=IFERROR(MIN('รายละเอียดรายนาที'!C2:C{last_row}),0)"),
            ("คะแนนสูงสุด", f"=IFERROR(MAX('รายละเอียดรายนาที'!D2:D{last_row}),0)"),
            ("เวลาที่เสี่ยง (นาที)", f"=IFERROR(SUM('รายละเอียดรายนาที'!I2:I{last_row})/60,0)"),
            ("จำนวนช่วงเวลาที่มีข้อมูล", len(minute_rows)),
        ]
    elif day_summary:
        measurements = int(day_summary["measurements"])
        summary_rows = [
            ("คะแนนเฉลี่ย", float(day_summary["score_sum"]) / measurements if measurements else 0),
            ("คะแนนต่ำสุด", day_summary["score_min"] or 0),
            ("คะแนนสูงสุด", day_summary["score_max"] or 0),
            ("เวลาที่เสี่ยง (นาที)", int(day_summary["risk_seconds"]) / 60),
            ("จำนวนช่วงเวลาที่มีข้อมูล", int(day_summary["periods"])),
        ]
    else:
        summary_rows = [
            ("คะแนนเฉลี่ย", 0), ("คะแนนต่ำสุด", 0), ("คะแนนสูงสุด", 0),
            ("เวลาที่เสี่ยง (นาที)", 0), ("จำนวนช่วงเวลาที่มีข้อมูล", 0),
        ]
    alert_count = int(day_summary["alerts"]) if day_summary else len(alerts)
    summary_rows.extend([("จำนวน Alert", alert_count), ("เกณฑ์คะแนนเสี่ยง", risk_threshold)])
    for row_index, (label, value) in enumerate(summary_rows, start=4):
        summary.cell(row_index, 1, label).font = Font(bold=True)
        summary.cell(row_index, 2, value)
        if row_index <= 7:
            summary.cell(row_index, 2).number_format = "0.0"
    summary.column_dimensions["A"].width = 28
    summary.column_dimensions["B"].width = 44

    detail_headers = [
        "เวลา", "คะแนนเฉลี่ย", "คะแนนต่ำสุด", "คะแนนสูงสุด", "คอเฉลี่ย", "ไหล่เฉลี่ย",
        "ลำตัวเฉลี่ย", "จำนวนการวัด", "เวลาที่เสี่ยง (วินาที)", "สถานะ",
    ]
    detail.append(detail_headers)
    for cell in detail[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = HEADER_FILL
    for row in minute_rows:
        detail.append([
            row["time"], row["score"], row["score_min"], row["score_max"], row["neck"],
            row["shoulders"], row["torso"], row["measurements"], row["risk_seconds"], row["status"],
        ])
    for row in detail.iter_rows(min_row=2, max_col=9):
        row[0].number_format = "hh:mm"
        for cell in row[1:7]:
            cell.number_format = "0.0"
    detail.conditional_formatting.add(
        f"B2:B{max(2, len(minute_rows) + 1)}",
        CellIsRule(operator="lessThan", formula=[str(risk_threshold)], fill=RISK_FILL),
    )
    for column, width in enumerate((12, 14, 14, 14, 12, 12, 12, 16, 20, 12), start=1):
        detail.column_dimensions[get_column_letter(column)].width = width
    detail.freeze_panes = "A2"

    if minute_rows:
        trend_chart = LineChart()
        trend_chart.title = "แนวโน้มคะแนนท่านั่งตลอดวัน"
        trend_chart.y_axis.title = "คะแนน"
        trend_chart.x_axis.title = "เวลา"
        trend_chart.y_axis.scaling.min = 0
        trend_chart.y_axis.scaling.max = 100
        trend_chart.height = 8
        trend_chart.width = 18
        trend_chart.add_data(Reference(detail, min_col=2, min_row=1, max_row=len(minute_rows) + 1), titles_from_data=True)
        trend_chart.set_categories(Reference(detail, min_col=1, min_row=2, max_row=len(minute_rows) + 1))
        summary.add_chart(trend_chart, "D3")

    alert_sheet.append(["เวลา", "ระดับ", "ข้อความ"])
    for cell in alert_sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = HEADER_FILL
    for alert in alerts:
        alert_sheet.append([
            datetime.fromisoformat(alert.created_at).astimezone(LOCAL_TZ).replace(tzinfo=None),
            alert.severity,
            alert.message,
        ])
    for cell in alert_sheet["A"][1:]:
        cell.number_format = "hh:mm"
    alert_sheet.column_dimensions["A"].width = 12
    alert_sheet.column_dimensions["B"].width = 12
    alert_sheet.column_dimensions["C"].width = 70
    alert_sheet.freeze_panes = "A2"

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def write_daily_report(db: Session, report_date: date, risk_threshold: int, report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    target = report_dir / f"OffSynTech_{report_date.isoformat()}.xlsx"
    temporary = target.with_suffix(".xlsx.tmp")
    temporary.write_bytes(build_daily_report(db, report_date, risk_threshold))
    temporary.replace(target)
    return target


def build_monthly_report(db: Session, report_month: date, risk_threshold: int) -> bytes:
    """Create an Excel workbook summarising one Bangkok calendar month."""
    month_start = report_month.replace(day=1)
    month_end = date(month_start.year + 1, 1, 1) if month_start.month == 12 else date(month_start.year, month_start.month + 1, 1)
    start, end = local_month_bounds(month_start)
    alerts = _alert_rows_between(db, start, end)
    history = daily_history(db, risk_threshold, month_start, month_end)
    daily = {
        str(row["label"]): {
            "score_sum": float(row["score_sum"]),
            "measurements": int(row["measurements"]),
            "minutes": int(row["periods"]),
            "risk_seconds": int(row["risk_seconds"]),
        }
        for row in history
    }
    alerts_by_day = {str(row["label"]): int(row["alerts"]) for row in history}

    workbook = Workbook()
    summary = workbook.active
    summary.title = "สรุปรายเดือน"
    daily_sheet = workbook.create_sheet("สรุปรายวัน")
    alert_sheet = workbook.create_sheet("เหตุการณ์แจ้งเตือน")

    summary.merge_cells("A1:H1")
    summary["A1"] = "Ergo Agent — รายงานท่านั่งรายเดือน"
    summary["A1"].font = Font(bold=True, color="FFFFFF", size=14)
    summary["A1"].fill = HEADER_FILL
    summary["A1"].alignment = Alignment(horizontal="center")
    summary["A2"] = "เดือนรายงาน"
    summary["B2"] = report_month.replace(day=1)
    summary["B2"].number_format = "mmmm yyyy"
    summary["A3"] = "หมายเหตุ"
    summary["B3"] = "สรุปรายวันเก็บระยะยาว 1 ปี; รายละเอียดรายนาทีและ Alert เป็นไปตามช่วงเก็บข้อมูล ไม่รวมภาพหรือวิดีโอ"
    summary["B3"].alignment = Alignment(wrap_text=True)
    period_count = sum(int(row["periods"]) for row in history)
    measurement_count = sum(int(row["measurements"]) for row in history)
    average = sum(float(row["score_sum"]) for row in history) / measurement_count if measurement_count else 0
    risk_minutes = sum(int(row["risk_seconds"]) for row in history) / 60
    alert_count = sum(int(row["alerts"]) for row in history)
    summary_rows = [
        ("คะแนนเฉลี่ยทั้งเดือน", average),
        ("วันที่มีข้อมูล", sum(int(row["measurements"]) > 0 for row in history)),
        ("ช่วงเวลาที่บันทึก", period_count),
        ("เวลาที่เสี่ยง (นาที)", risk_minutes),
        ("จำนวน Alert", alert_count),
        ("เกณฑ์คะแนนเสี่ยง", risk_threshold),
    ]
    for row_index, (label, value) in enumerate(summary_rows, start=4):
        summary.cell(row_index, 1, label).font = Font(bold=True)
        summary.cell(row_index, 2, value)
        if row_index in (4, 7):
            summary.cell(row_index, 2).number_format = "0.0"
    summary.column_dimensions["A"].width = 28
    summary.column_dimensions["B"].width = 44

    daily_sheet.append(["วันที่", "คะแนนเฉลี่ย", "ช่วงเวลาที่บันทึก", "เวลาที่เสี่ยง (นาที)", "จำนวน Alert"])
    for cell in daily_sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = HEADER_FILL
    for label in sorted(set(daily) | set(alerts_by_day)):
        values = daily.get(label, {"score_sum": 0.0, "measurements": 0, "minutes": 0, "risk_seconds": 0})
        minutes = int(values["minutes"])
        measurements = int(values["measurements"])
        daily_sheet.append([
            date.fromisoformat(label),
            float(values["score_sum"]) / measurements if measurements else 0,
            minutes,
            int(values["risk_seconds"]) / 60,
            alerts_by_day.get(label, 0),
        ])
    for row in daily_sheet.iter_rows(min_row=2):
        row[0].number_format = "dd/mm/yyyy"
        row[1].number_format = "0.0"
        row[3].number_format = "0.0"
    daily_sheet.conditional_formatting.add(
        f"B2:B{max(2, daily_sheet.max_row)}",
        CellIsRule(operator="lessThan", formula=[str(risk_threshold)], fill=RISK_FILL),
    )
    for column, width in enumerate((14, 16, 20, 20, 14), start=1):
        daily_sheet.column_dimensions[get_column_letter(column)].width = width
    daily_sheet.freeze_panes = "A2"
    if daily_sheet.max_row > 1:
        trend_chart = LineChart()
        trend_chart.title = "แนวโน้มคะแนนเฉลี่ยรายวัน"
        trend_chart.y_axis.title = "คะแนน"
        trend_chart.x_axis.title = "วันที่"
        trend_chart.y_axis.scaling.min = 0
        trend_chart.y_axis.scaling.max = 100
        trend_chart.height = 8
        trend_chart.width = 18
        trend_chart.add_data(Reference(daily_sheet, min_col=2, min_row=1, max_row=daily_sheet.max_row), titles_from_data=True)
        trend_chart.set_categories(Reference(daily_sheet, min_col=1, min_row=2, max_row=daily_sheet.max_row))
        summary.add_chart(trend_chart, "D3")

    alert_sheet.append(["เวลา", "ระดับ", "ข้อความ"])
    for cell in alert_sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = HEADER_FILL
    for alert in alerts:
        alert_sheet.append([
            datetime.fromisoformat(alert.created_at).astimezone(LOCAL_TZ).replace(tzinfo=None),
            alert.severity,
            alert.message,
        ])
    for cell in alert_sheet["A"][1:]:
        cell.number_format = "dd/mm/yyyy hh:mm"
    alert_sheet.column_dimensions["A"].width = 20
    alert_sheet.column_dimensions["B"].width = 12
    alert_sheet.column_dimensions["C"].width = 70
    alert_sheet.freeze_panes = "A2"

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()
