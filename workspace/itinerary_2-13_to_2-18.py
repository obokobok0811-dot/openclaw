from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import textwrap

content = '''싱가포르 가족여행(최적화) 일정
기간: 2026-02-13(금) ~ 2026-02-18(수)

요약
- 출발: 2/13 인천 출발 15:30 -> 싱가포르 도착
- 귀국: 2/18 싱가포르 출발 23:00
- 숙소: 첫날(2/13) 이미 예약됨, 2/14~ HOTEL MI ROCHOR
- 주요 일정: Gardens by the Bay, Universal Studios, Little India, Orchard, Sentosa (SEA/Aquarium)

일정 상세
2/13(금) 도착일
- 도착 후 공항 -> 택시 이동 권장(짐/피로 고려)
- 숙소 체크인(이미 예약된 첫날 숙소)
- 저녁: 근처 호커센터 간단히 식사
- 숙면: Bugis/Rochor 부근(1박)

2/14(토) MI ROCHOR 체크인 / 발렌타인 데이(가족)
- 오전: 여유로운 아침, HOTEL MI ROCHOR로 이동 및 체크인(가능하면 얼리 체크인 문의)
- 오전~오후: Little India 산책 및 점심
- 오후: Gardens by the Bay 방문(가능하면 오전 또는 일찍 방문), Children's Garden 물놀이 준비(수영복)
- 저녁(발렌타인): 가족 친화 레스토랑 사전 예약(권장 17:30)

2/15(일)
- 오전: Arab Street / Haji Lane 산책 및 카페
- 오후: Orchard 가벼운 쇼핑 또는 호텔 휴식
- 저녁: 리버사이드 짧은 산책(크루즈는 권장하지 않음)

2/16(월) 센토사 / Universal Studios
- 오전: 센토사 이동 → Universal Studios 개장 직후 입장 권장
- 유니버설 티켓 사전예매 필수(익스프레스 옵션 고려)
- 오후: 중간중간 휴식(어린이 고려)
- 저녁: 센토사 내 식사 후 숙소 복귀

2/17(화) 설 연휴 첫날 — 혼잡 대비 실내 활동 권장
- 오전: ArtScience Museum 또는 Singapore Zoo(조기 입장 권장)
- 오후: 호텔 휴식 및 근처 활동
- 저녁: 레스토랑 영업 확인 후 이용(호텔 컨시어지에 확인 권장)

2/18(수) 마무리
- 오전: S.E.A. Aquarium(센토사) 또는 가벼운 관광
- 오후: 여유 쇼핑 및 호텔 휴식
- 저녁: 짐 정리 후 공항 이동(23:00 출발 기준 최소 3시간 전 공항 도착 목표)
- 공항행 택시 사전 예약 권장

준비물 & 예약 체크리스트
- 유니버설 스튜디오 티켓(2/16) 온라인 사전구매
- 2/14 레스토랑 예약(발렌타인 대비 조기 예약 추천)
- 2/18 공항행 택시 사전 예약
- 어린이: 수영복, 여벌, 간단 간식, 자외선 차단제

비상 연락 및 팁
- 호텔 컨시어지에 설 연휴 영업정보 문의
- 현금 소액 준비, 카드 사용 가능
- 일정은 유동적으로 조정하세요(날씨·체력 고려)

작성: OpenClaw 에이전트
'''

output_path = 'workspace/itinerary_2026-02-13_to_02-18.pdf'

c = canvas.Canvas(output_path, pagesize=A4)
width, height = A4
margin = 40
max_width = width - 2*margin

lines = []
for paragraph in content.split('\n'):
    wrapped = textwrap.wrap(paragraph, 95)
    if not wrapped:
        lines.append('')
    else:
        lines.extend(wrapped)

y = height - margin
c.setFont('Helvetica', 11)
for line in lines:
    if y < margin + 20:
        c.showPage()
        c.setFont('Helvetica', 11)
        y = height - margin
    c.drawString(margin, y, line)
    y -= 14

c.save()
print(output_path)
