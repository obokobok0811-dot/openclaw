#!/usr/bin/env python3
"""
time_gate.py - 시간대 게이트

알림 허용 시간대를 관리하여 방해받지 않는 시간에는 알림을 보류.

규칙:
  - 평일 (월~금): 17:00 ~ 21:00 KST
  - 주말 (토~일): 07:00 ~ 21:00 KST
  - 허용 시간대 밖 → 큐에 저장, 다음 허용 시간에 일괄 전송
"""

from datetime import datetime, timezone, timedelta
from typing import Optional

# KST = UTC+9
KST = timezone(timedelta(hours=9))


def is_alert_allowed(now: Optional[datetime] = None) -> bool:
    """
    현재 시간이 알림 허용 시간대인지 확인.

    Args:
        now: 기준 시각 (None이면 현재 KST)

    Returns:
        True이면 알림 즉시 발송 가능
    """
    if now is None:
        now = datetime.now(KST)
    else:
        # timezone-aware로 변환
        if now.tzinfo is None:
            now = now.replace(tzinfo=KST)
        else:
            now = now.astimezone(KST)

    weekday = now.weekday()  # 0=월 ~ 6=일
    hour = now.hour

    if weekday < 5:
        # 평일: 17:00 ~ 21:00 (17시 이상, 21시 미만)
        return 17 <= hour < 21
    else:
        # 주말: 07:00 ~ 21:00
        return 7 <= hour < 21


def next_allowed_time(now: Optional[datetime] = None) -> datetime:
    """
    다음 알림 허용 시간대 시작 시각 반환.

    Args:
        now: 기준 시각

    Returns:
        다음 허용 시간대 시작 datetime (KST)
    """
    if now is None:
        now = datetime.now(KST)
    else:
        if now.tzinfo is None:
            now = now.replace(tzinfo=KST)
        else:
            now = now.astimezone(KST)

    # 이미 허용 시간대면 현재 반환
    if is_alert_allowed(now):
        return now

    # 오늘 남은 시간대 확인
    weekday = now.weekday()
    hour = now.hour

    if weekday < 5:
        # 평일
        if hour < 17:
            # 오늘 17시
            return now.replace(hour=17, minute=0, second=0, microsecond=0)
        else:
            # 오늘 21시 이후 → 다음 허용 시간 찾기
            return _find_next_day_start(now)
    else:
        # 주말
        if hour < 7:
            # 오늘 07시
            return now.replace(hour=7, minute=0, second=0, microsecond=0)
        else:
            # 오늘 21시 이후 → 다음 허용 시간 찾기
            return _find_next_day_start(now)


def _find_next_day_start(now: datetime) -> datetime:
    """다음 날부터 허용 시간대 시작 시각 탐색."""
    for days_ahead in range(1, 8):
        candidate = now + timedelta(days=days_ahead)
        candidate = candidate.replace(hour=0, minute=0, second=0, microsecond=0)
        wd = candidate.weekday()

        if wd < 5:
            # 평일 → 17:00
            return candidate.replace(hour=17)
        else:
            # 주말 → 07:00
            return candidate.replace(hour=7)

    # fallback (shouldn't reach)
    return now + timedelta(days=1)


if __name__ == "__main__":
    now = datetime.now(KST)
    print(f"현재 시각 (KST): {now.strftime('%Y-%m-%d %H:%M %A')}")
    print(f"알림 허용: {is_alert_allowed(now)}")

    if not is_alert_allowed(now):
        nxt = next_allowed_time(now)
        print(f"다음 허용 시각: {nxt.strftime('%Y-%m-%d %H:%M %A')}")

    # 다양한 시간대 테스트
    print("\n시간대 테스트:")
    test_cases = [
        ("평일 09:00", datetime(2026, 2, 23, 9, 0, tzinfo=KST)),   # 월
        ("평일 17:00", datetime(2026, 2, 23, 17, 0, tzinfo=KST)),  # 월
        ("평일 20:59", datetime(2026, 2, 23, 20, 59, tzinfo=KST)), # 월
        ("평일 21:00", datetime(2026, 2, 23, 21, 0, tzinfo=KST)),  # 월
        ("주말 06:00", datetime(2026, 2, 22, 6, 0, tzinfo=KST)),   # 일
        ("주말 07:00", datetime(2026, 2, 22, 7, 0, tzinfo=KST)),   # 일
        ("주말 15:00", datetime(2026, 2, 22, 15, 0, tzinfo=KST)),  # 일
        ("주말 21:00", datetime(2026, 2, 22, 21, 0, tzinfo=KST)),  # 일
    ]
    for desc, dt in test_cases:
        allowed = is_alert_allowed(dt)
        status = "✅ 허용" if allowed else "🔇 차단"
        print(f"  {desc} ({dt.strftime('%A')}): {status}")
