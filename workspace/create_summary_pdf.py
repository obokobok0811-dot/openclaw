from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import textwrap

content = '''싱가포르 4박5일 여행 후기 요약

요약
- 주요 방문지: 마리나 베이 샌즈(야경·인피니티풀), 센토사(유니버설 스튜디오 등), 차이나타운·클라키(먹거리·야경), 주얼 창이, 가든스 바이 더 베이.
- 일정 팁: 날씨(우기) 고려, 일정 여유 있게. 하루에 많은 장소를 몰아넣지 마세요.
- 숙소: 마리나 베이 지역은 편리하지만 비용과 만족도 차이 존재.
- 식비·경비: 비교적 물가가 높음.

상위 링크
1) https://m.blog.naver.com/pnp524/223582347041 — 가족 여행 후기(센토사 중심)
2) https://triple.guide/trips/lounge/itineraries/ddadef14-97fe-4cca-97ee-7d5d233faa12 — 일정 공유(맛집·관광지)
3) https://developers-haven.tistory.com/36 — 1일차 코스·팁
4) https://m.blog.naver.com/dtk1234/223741487984 — 경비·숙소·맛집 후기
5) https://www.tourtoctoc.com/news/articleView.html?idxno=3229 — 코스·치안·팁 기사

원본 검색일: 2026-02-12
작성자: OpenClaw 에이전트
'''

output_path = 'workspace/singapore_4n5d_summary.pdf'

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
