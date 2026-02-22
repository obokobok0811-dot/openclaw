from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import ttfonts, pdfmetrics
import textwrap

font_path = 'workspace/fonts/NanumGothic-Regular.ttf'
font_name = 'NanumGothic'
pdfmetrics.registerFont(ttfonts.TTFont(font_name, font_path))

content = '''최종(권장) 일정 — 싱가포르 가족 여행
기간: 2026-02-13(금) ~ 2026-02-18(수)

주요 변경점
- 아이 낮잠 없이 이동: 활동을 오전에 집중, 오후는 실내·가벼운 활동으로 구성
- 저녁 쇼/야간 활동은 대부분 생략 또는 선택적(피로도에 따라)
- 유니버설·동물원·주요 레스토랑은 사전예약 권장

일정(시간대별, 권장)
2/13 (금) — 도착일
- 15:30 인천 출발(항공)
- 20:00–21:00: 싱가포르 도착 → 입국
- 21:00–22:00: 가족 합류 후 택시로 호텔 이동 및 간단 정리
- 22:00: 조기 취침 권장

2/14 (토) — MI ROCHOR 체크인 / 발렌타인(가족)
- 08:00–09:00: 체크아웃 → HOTEL MI ROCHOR로 이동, 짐 맡기기
- 09:30–10:30: Port Canning 공원(짧은 산책)
- 12:00–13:30: 점보 씨푸드(리버워크) — 점심(예약 권장)
- 13:30–15:00: 호텔 복귀 및 실내 활동(휴식 대신 가벼운 실내 놀이권장)
- 15:30–17:00: 멀라이언 파크(짧은 산책·사진)
- 17:30–18:30: 발렌타인 저녁(가족 레스토랑, 시간 단축)
- 19:00: 호텔 귀환 및 휴식

2/15 (일) — 가든스 & 리버 지역
- 07:30–09:30: Gardens by the Bay (돔 또는 수퍼트리 중 1곳 집중)
- 10:00–11:30: 점심(마리나 인근)
- 12:00–15:30: 쇼핑몰 실내(마리나 스퀘어/마리나 샌즈 몰) — 아이가 놀 수 있는 실내 공간 우선
- 16:00–17:30: 가벼운 시내 산책(Orchard 선택 가능)
- 18:00: 조기 저녁 및 호텔 귀환

2/16 (월) — 센토사 / Universal Studios
- 07:00–08:00: 아침 준비
- 08:30–09:00: 센토사 이동(택시 권장)
- 09:00–12:00: Universal Studios (핵심 어트랙션 위주)
- 12:00–13:00: 파크 내 점심
- 13:00–15:00: 파크 활동 후 조기 퇴장
- 15:30–17:30: 센토사 실내 활동(리조트월드, 쇼핑)
- 18:00: 호텔 복귀 및 휴식

2/17 (화) — 동물원 (나이트사파리는 선택적)
- 06:30–07:30: 조기 이동
- 07:30–11:30: Singapore Zoo(주요 포인트만 집중 관람)
- 12:00–15:30: 호텔 복귀 및 실내 자유시간
- 16:00–18:00: 가벼운 근처 활동
- 19:00: 호텔 귀환(나이트사파리는 아이 컨디션에 따라 생략 권장)

2/18 (수) — 마무리 & 출국 (23:00)
- 08:30–10:00: 체크아웃 준비 / Little India(짧은 산책·기념품)
- 10:30–12:30: 주얼 창이(쇼핑·점심, 2시간 권장)
- 13:00–17:00: 호텔 라운지 이용 또는 공항 이동 준비
- 17:00–19:00: 간단 저녁
- 20:00: 공항 수속 시작 권장(3시간 전 여유)
- 23:00: 싱가포르 출발

예약·체크리스트
- Universal Studios(2/16): 날짜 지정 온라인 예매(익스프레스 옵션 고려)
- 점보 씨푸드(2/14): 예약 필수
- Night Safari·Wings of Time: 선택적 예매(취소 가능성 염두)
- 2/18 공항행 택시 사전 예약 권장

추가 팁
- 이동은 택시 우선(아이·짐 고려). MRT는 가까운 구간만 사용
- 실내 플레이존·키즈 코너 위치 미리 파악(갑작스런 에너지 방출 대비)
- 간식·물·여벌·작은 장난감 휴대 권장

작성: OpenClaw 에이전트
'''

output_path = 'workspace/itinerary_final_2026-02-13_to_02-18_korean.pdf'

c = canvas.Canvas(output_path, pagesize=A4)
width, height = A4
margin = 40

lines = []
for paragraph in content.split('\n'):
    wrapped = textwrap.wrap(paragraph, 60)
    if not wrapped:
        lines.append('')
    else:
        lines.extend(wrapped)

y = height - margin
c.setFont(font_name, 12)
for line in lines:
    if y < margin + 20:
        c.showPage()
        c.setFont(font_name, 12)
        y = height - margin
    c.drawString(margin, y, line)
    y -= 16

c.save()
print(output_path)
