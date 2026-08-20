import os

from openai import OpenAI
from fastapi import HTTPException
import json

def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not configured",
        )

    return OpenAI(api_key=api_key)


def generate_test_response():
    client = get_openai_client()

    response = client.responses.create(
        model="gpt-5-mini",
        input="長野旅行のおすすめを3つ、簡潔に日本語で教えてください。",
    )

    return {
        "text": response.output_text
    }


def generate_travel_plans(request, places, weather, routes):
    client = get_openai_client()

    number_of_days = (request.end_date - request.start_date).days + 1
    allowed_places = [
        {
            "id": place.get("id", ""),
            "name": place.get("displayName", {}).get("text", ""),
            "address": place.get("formattedAddress", ""),
        }
        for place in places
    ]

    prompt = f"""
あなたは旅行プラン作成AIです。

以下のユーザー条件、Google Placesの候補、天気情報をもとに、
特徴の異なる現実的な旅行プランを必ず3つ作成してください。

【ユーザー条件】
出発地: {request.origin}
目的地: {request.destination}
開始日: {request.start_date}
終了日: {request.end_date}
人数: {request.travelers}
移動手段: {request.transportation}
予算: {request.budget} 円
旅行スタイル: {request.travel_style}
旅行日数: {number_of_days}日

【使用可能な観光地候補】
{json.dumps(allowed_places, ensure_ascii=False)}

【天気情報】
{json.dumps(weather, ensure_ascii=False)}

【重要な制約】
- daysは{number_of_days}件にし、{request.start_date}から{request.end_date}まで1日ずつ作成してください。
- 1日目の最初は「{request.origin}」からのdeparture、最終日の最後は「{request.origin}」へのarrivalにしてください。
- typeがspotの予定は、上の観光地候補だけを使用してください。
- spotには候補と完全に同じplace_idとnameを入れてください。
- 存在しない観光地、住所、ホテル、店舗を作らないでください。
- 各spotのduration_minutesは、その場所で過ごす時間だけを整数で指定してください。
- 距離、移動時間、交通費、宿泊費、食費、費用合計は出力しないでください。
- 経路と費用は、このJSONを受け取ったbackendが実データと計算ルールで付与します。
- 同じ日の時刻が大きく前後しないよう、朝から夜の順に並べてください。
- plan_idはplan_1、plan_2、plan_3を使用してください。

以下のJSON形式だけを出力してください。Markdownのコードブロックは付けないでください。

{{
  "plans": [
    {{
      "plan_id": "plan_1",
      "title": "",
      "summary": "",
      "recommendation_reason": "",
      "days": [
        {{
          "day": 1,
          "date": "{request.start_date}",
          "schedule": [
            {{
              "time": "08:00",
              "type": "departure",
              "place_id": null,
              "name": "{request.origin}",
              "description": "出発",
              "duration_minutes": null
            }},
            {{
              "time": "10:00",
              "type": "spot",
              "place_id": "候補のID",
              "name": "候補と完全に同じ名前",
              "description": "観光内容の説明",
              "duration_minutes": 90
            }}
          ]
        }}
      ]
    }}
  ]
}}
"""

    response = client.responses.create(
        model="gpt-5-mini",
        input=prompt,
    )

    try:
        output_text = response.output_text.strip()
        if output_text.startswith("```"):
            output_text = output_text.removeprefix("```json").removeprefix("```")
            output_text = output_text.removesuffix("```").strip()
        return json.loads(output_text)

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "AI出力をJSONとして解析できませんでした。",
                "raw_output": response.output_text,
            },
        )
