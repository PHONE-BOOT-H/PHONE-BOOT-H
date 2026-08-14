![AI Usage](https://raw.githubusercontent.com/PHONE-BOOT-H/PHONE-BOOT-H/master/cards/ai-usage.svg)

위 카드는 이 저장소의 `ai_usage_card.py`가 매일 다시 그린다. Claude Code가 로컬에
남기는 대화 기록(`~/.claude/projects/*.jsonl`)을 읽어 토큰 사용량을 집계하고,
공개 API 단가로 환산한 금액과 26주치 사용 이력을 SVG 한 장으로 만든다.

<details>
<summary>어떻게 도는가</summary>

**집계 방식**

- 스트리밍 중 같은 응답이 여러 줄로 기록되므로 `message.id` 기준으로 한 번만 센다
  (실측: 63,052줄 중 34,838줄이 중복).
- 입력·출력·캐시 읽기·캐시 쓰기를 나눠 세고, 캐시 쓰기는 5분(1.25배)과
  1시간(2배) TTL을 구분해 단가를 매긴다.
- 금액은 **API 환산가**다. 구독 요금제로 쓴 것을 같은 양의 API 호출로 바꿨다면
  얼마였을지를 뜻하며, 실제 지불액이 아니다.

**한계**

- Claude Code 기록만 잡힌다. claude.ai 웹·데스크톱 대화는 로컬 파일이 없어
  집계에서 빠진다.
- 삭제된 프로젝트 폴더는 복구되지 않는다. 남아 있는 기록이 전부다.
- 환율은 코드에 상수로 박혀 있어 실시간이 아니다.

**실행**

```bash
python ai_usage_card.py cards/ai-usage.svg   # 카드 생성
python ai_usage_card.py --demo               # 단가·격자 로직 자체 검증
```

갱신은 Windows 작업 스케줄러가 `update.cmd`를 하루 한 번 실행해 처리한다.
SVG가 실제로 바뀐 날에만 커밋한다.

**구조**

| 파일 | 역할 |
|---|---|
| `ai_usage_card.py` | 집계 + SVG 렌더 (표준 라이브러리만) |
| `update.cmd` | 재생성 → 변경 시 commit + push |
| `cards/ai-usage.svg` | 카드 결과물 |

주요 설정은 `ai_usage_card.py` 상단 상수에 모여 있다 — `WEEKS`(잔디 주 수, 카드
폭이 따라 늘어남), `FX`(환율), `PRICES`(모델별 단가).

</details>
