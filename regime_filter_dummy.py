#!/usr/bin/env python3
import json
from pathlib import Path

# Dummy prices: chronological oldest->newest
# We'll construct 20+ days with latest price intentionally above SMA20
prices = [75000, 75200, 75500, 76000, 75800, 76200, 76500, 76800, 77000, 77200,
          77500, 77800, 78000, 78200, 78500, 78800, 79000, 79500, 80000, 82500]
# prices is chronological oldest->newest; latest is last element
if len(prices) < 20:
    raise SystemExit('need 20 prices')

sma20 = sum(prices[-20:]) / 20.0
current = prices[-1]
regime = 'BULL' if current > sma20 else 'BEAR'

# persist state
state_dir = Path(__file__).parent / 'state'
state_dir.mkdir(exist_ok=True)
state_file = state_dir / 'market_regime.json'
with open(state_file, 'w') as f:
    json.dump({'market_regime': regime, 'current': current, 'sma20': sma20}, f)

# Output required lines
print(f"더미 데이터 기준 종가: {current}, SMA20: {round(sma20,2)}")
print(f"Market_Regime: {regime} 판별 완료")
if regime == 'BULL':
    print("메인 라우터 스위치 작동: BULL 장세 확인. 무기 B(데이 트레이딩) 셧다운, 무기 A(가치/스윙 매매) 모듈 가동 준비 완료.")
else:
    print("메인 라우터 스위치 작동: BEAR 장세 확인. 무기 A 셧다운, 무기 B 제한적 가동 준비 완료.")
