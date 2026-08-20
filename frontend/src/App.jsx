import { useState } from "react";
import "./App.css";

const COST_LABELS = {
  transportation: "交通費",
  accommodation: "宿泊費",
  food: "食費",
  activities: "観光費",
  other: "その他",
};

const MODE_LABELS = {
  drive: "車",
  transit: "公共交通",
  auto: "おまかせ",
};

const TRANSPORTATION_OPTIONS = [
  { value: "drive", mark: "車", label: "車" },
  { value: "transit", mark: "鉄", label: "公共交通" },
  { value: "auto", mark: "選", label: "おまかせ" },
];

const TRAVEL_STYLE_OPTIONS = [
  { value: "sightseeing", mark: "景", label: "観光重視" },
  { value: "gourmet", mark: "食", label: "グルメ重視" },
  { value: "budget", mark: "得", label: "安さ重視" },
];

const PLAN_LABELS = ["第一案", "第二案", "第三案"];

const formatCurrency = (value) =>
  `${Number(value ?? 0).toLocaleString("ja-JP")}円`;

const formatDuration = (minutes) => {
  if (minutes === null || minutes === undefined) return "取得不可";

  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;

  if (hours === 0) return `${remainingMinutes}分`;
  if (remainingMinutes === 0) return `${hours}時間`;
  return `${hours}時間${remainingMinutes}分`;
};

const formatDate = (value) => {
  if (!value) return "日付未設定";

  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat("ja-JP", {
    month: "long",
    day: "numeric",
    weekday: "short",
  }).format(date);
};

const getTripLengthLabel = (days) => {
  const numberOfDays = Array.isArray(days) ? days.length : 0;
  if (numberOfDays <= 0) return "日程未設定";
  if (numberOfDays === 1) return "日帰り";
  return `${numberOfDays - 1}泊${numberOfDays}日`;
};

function ChoiceGroup({ label, value, options, onChange }) {
  return (
    <fieldset className="choice-field">
      <legend>{label}</legend>
      <div className="choices">
        {options.map((option) => (
          <button
            className={`choice ${value === option.value ? "active" : ""}`}
            type="button"
            key={option.value}
            aria-pressed={value === option.value}
            onClick={() => onChange(option.value)}
          >
            <span aria-hidden="true">{option.mark}</span>
            {option.label}
          </button>
        ))}
      </div>
    </fieldset>
  );
}

function RouteDetails({ route }) {
  if (!route) return null;

  const distance =
    route.distance_km === null || route.distance_km === undefined
      ? "距離取得不可"
      : `${Number(route.distance_km).toLocaleString("ja-JP")}km`;
  const mode =
    route.route_available === false
      ? "経路取得不可"
      : MODE_LABELS[route.mode] ?? route.mode ?? "移動";

  return (
    <div className={`move ${route.route_available === false ? "move-unavailable" : ""}`}>
      <span className="move-mark" aria-hidden="true">移</span>
      <span>{mode}</span>
      <span>{formatDuration(route.duration_minutes)}</span>
      <span>{distance}</span>
    </div>
  );
}

function DaySchedule({ day, planId }) {
  const schedule = Array.isArray(day.schedule) ? day.schedule : [];
  const transportation = Array.isArray(day.transportation)
    ? day.transportation
    : [];

  return (
    <section className="day-section">
      <div className="day-title">
        <strong>{day.day}日目</strong>
        <time dateTime={day.date}>{formatDate(day.date)}</time>
      </div>

      <div className="timeline">
        {schedule.map((item, itemIndex) => {
          const routes = transportation.filter(
            (route) => route.from_schedule_index === itemIndex,
          );
          const itemKey = `${planId}-${day.day}-${item.time}-${item.place_id ?? item.name}-${itemIndex}`;

          return (
            <div className="event" key={itemKey}>
              <time className="event-time">{item.time || "--:--"}</time>
              <div className="rail" aria-hidden="true">
                <span className="dot" />
              </div>
              <div className="event-card">
                <strong>{item.name || "予定"}</strong>
                <small>
                  {item.description || "詳細情報はありません。"}
                  {item.duration_minutes !== null &&
                    item.duration_minutes !== undefined && (
                      <> ・ 滞在 {formatDuration(item.duration_minutes)}</>
                    )}
                </small>
                {routes.map((route, routeIndex) => (
                  <RouteDetails
                    key={`${itemKey}-${route.to}-${routeIndex}`}
                    route={route}
                  />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function CostBreakdown({ breakdown, total }) {
  const safeBreakdown = breakdown ?? {};

  return (
    <aside className="cost-panel">
      <div className="panel-kicker">旅の予算</div>
      <h3>費用内訳</h3>
      <dl>
        {Object.entries(COST_LABELS).map(([key, label]) => (
          <div className="cost-line" key={key}>
            <dt>{label}</dt>
            <dd>{formatCurrency(safeBreakdown[key])}</dd>
          </div>
        ))}
        <div className="cost-total">
          <dt>合計</dt>
          <dd>{formatCurrency(total)}</dd>
        </div>
      </dl>
      <p className="cost-notice">
        外部経路データとMVP用の基準単価から算出した概算です。
      </p>
    </aside>
  );
}

function PlanCard({ plan, planIndex, onSelect }) {
  const days = Array.isArray(plan.days) ? plan.days : [];
  const spots = Array.isArray(plan.main_spots) ? plan.main_spots : [];

  return (
    <article className={`summary-card plan-tone-${planIndex + 1}`}>
      <div className="card-top">
        <span className="plan-badge">{PLAN_LABELS[planIndex] ?? `第${planIndex + 1}案`}</span>
        <h3>{plan.title || `旅行プラン ${planIndex + 1}`}</h3>
      </div>

      <div className="card-body">
        <div className="meta-list">
          <span>{getTripLengthLabel(days)}</span>
          <span>{spots.length}スポット</span>
          <span>{MODE_LABELS[days[0]?.transportation?.[0]?.mode] ?? "旅程"}</span>
        </div>

        <div className="card-price">
          {formatCurrency(plan.estimated_cost)}
          <small>概算</small>
        </div>

        <p className="card-description">
          {plan.summary || "旅行プランの概要はありません。"}
        </p>

        {spots.length > 0 && (
          <div className="spot-tags" aria-label="主な観光地">
            {spots.slice(0, 3).map((spot, spotIndex) => (
              <span key={spot.id || `${plan.plan_id}-spot-${spotIndex}`}>
                {spot.name || "名称未設定"}
              </span>
            ))}
          </div>
        )}

        <button className="detail-button" type="button" onClick={onSelect}>
          この旅程を見る
          <span aria-hidden="true">→</span>
        </button>
      </div>
    </article>
  );
}

function App() {
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [travelers, setTravelers] = useState(1);
  const [transportation, setTransportation] = useState("transit");
  const [budget, setBudget] = useState("");
  const [travelStyle, setTravelStyle] = useState("sightseeing");

  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [screen, setScreen] = useState("planner");
  const [selectedPlanIndex, setSelectedPlanIndex] = useState(0);

  const selectedPlan = plans[selectedPlanIndex];

  const goToScreen = (nextScreen) => {
    setScreen(nextScreen);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const createPlans = async () => {
    setError("");

    if (!origin.trim()) {
      setError("出発地を入力してください。");
      return;
    }

    if (!destination.trim()) {
      setError("目的地を入力してください。");
      return;
    }

    if (!startDate || !endDate) {
      setError("開始日と終了日を入力してください。");
      return;
    }

    if (new Date(startDate) > new Date(endDate)) {
      setError("終了日は開始日以降にしてください。");
      return;
    }

    if (Number(travelers) < 1) {
      setError("人数は1人以上にしてください。");
      return;
    }

    if (!budget || Number(budget) <= 0) {
      setError("予算は1円以上で入力してください。");
      return;
    }

    setLoading(true);
    setPlans([]);

    const requestData = {
      origin: origin.trim(),
      destination: destination.trim(),
      start_date: startDate,
      end_date: endDate,
      travelers: Number(travelers),
      transportation,
      budget: Number(budget),
      travel_style: travelStyle,
    };

    try {
      const response = await fetch("http://localhost:8000/api/travel-plans", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestData),
      });

      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`);
      }

      const data = await response.json();
      const nextPlans = Array.isArray(data.plans) ? data.plans : [];
      setPlans(nextPlans);

      if (nextPlans.length === 0) {
        setError(data.message || "旅行プランを作成できませんでした。");
        return;
      }

      setSelectedPlanIndex(0);
      goToScreen("results");
    } catch (requestError) {
      console.error("旅行プラン生成エラー:", requestError);
      setError("旅行プランの生成に失敗しました。");
    } finally {
      setLoading(false);
    }
  };

  const showPlanDetail = (planIndex) => {
    setSelectedPlanIndex(planIndex);
    goToScreen("detail");
  };

  return (
    <>
      <header className="site-nav">
        <button className="brand" type="button" onClick={() => goToScreen("planner")}>
          <span className="brand-mark" aria-hidden="true">旅</span>
          <span>AI Travel Planner</span>
        </button>
        <span className="nav-note">一旅一会、あなただけの旅程</span>
      </header>

      {screen === "planner" && (
        <main className="planner-screen">
          <section className="hero-copy">
            <span className="eyebrow">AI TRAVEL CONCIERGE</span>
            <h1>次の旅を、<br />一枚の物語に。</h1>
            <p>
              行き先と好みを入力するだけ。観光地、移動、予算をひとつに綴り、
              あなたに合う三つの旅をご提案します。
            </p>
            <div className="hero-points" aria-label="サービスの特徴">
              <span>三案を比較</span>
              <span>移動時間を確認</span>
              <span>費用内訳つき</span>
              <span>日別の旅程</span>
            </div>
          </section>

          <section className="planner-panel" aria-labelledby="planner-heading">
            <div className="planner-title">
              <div>
                <span className="panel-kicker">旅のしおりを作る</span>
                <h2 id="planner-heading">旅行条件を入力</h2>
              </div>
              <span className="step-label">入力</span>
            </div>

            <div className="form-grid">
              <label className="field">
                出発地
                <input
                  type="text"
                  value={origin}
                  onChange={(event) => setOrigin(event.target.value)}
                  placeholder="例：横浜"
                />
              </label>

              <label className="field">
                目的地
                <input
                  type="text"
                  value={destination}
                  onChange={(event) => setDestination(event.target.value)}
                  placeholder="例：長野県伊那市"
                />
              </label>

              <label className="field">
                開始日
                <input
                  type="date"
                  value={startDate}
                  onChange={(event) => setStartDate(event.target.value)}
                />
              </label>

              <label className="field">
                終了日
                <input
                  type="date"
                  value={endDate}
                  min={startDate || undefined}
                  onChange={(event) => setEndDate(event.target.value)}
                />
              </label>

              <label className="field">
                人数
                <input
                  type="number"
                  min="1"
                  value={travelers}
                  onChange={(event) => setTravelers(event.target.value)}
                />
              </label>

              <label className="field">
                予算（円）
                <input
                  type="number"
                  min="1"
                  value={budget}
                  onChange={(event) => setBudget(event.target.value)}
                  placeholder="例：100000"
                />
              </label>

              <ChoiceGroup
                label="移動手段"
                value={transportation}
                options={TRANSPORTATION_OPTIONS}
                onChange={setTransportation}
              />

              <ChoiceGroup
                label="旅行スタイル"
                value={travelStyle}
                options={TRAVEL_STYLE_OPTIONS}
                onChange={setTravelStyle}
              />
            </div>

            {error && <p className="error-message" role="alert">{error}</p>}

            <button className="create-button" type="button" onClick={createPlans} disabled={loading}>
              AIで三つの旅を作る
            </button>
          </section>
        </main>
      )}

      {screen === "results" && (
        <main className="results-screen">
          <div className="screen-actions">
            <button className="text-button" type="button" onClick={() => goToScreen("planner")}>
              ← 条件を変更する
            </button>
          </div>

          <section className="results-heading">
            <div>
              <span className="eyebrow">THREE JOURNEYS</span>
              <h1>あなたへの三つのご提案</h1>
              <p>特徴の異なる旅程から、気になる一案をお選びください。</p>
            </div>
            <div className="trip-summary">
              <strong>{origin} → {destination}</strong>
              <span>{getTripLengthLabel(plans[0]?.days)} ・ {travelers}人 ・ {MODE_LABELS[transportation]}</span>
            </div>
          </section>

          <section className="summary-cards" aria-label="旅行プラン一覧">
            {plans.map((plan, planIndex) => (
              <PlanCard
                key={plan.plan_id || `plan-${planIndex}`}
                plan={plan}
                planIndex={planIndex}
                onSelect={() => showPlanDetail(planIndex)}
              />
            ))}
          </section>
        </main>
      )}

      {screen === "detail" && selectedPlan && (
        <main className="detail-screen">
          <div className="screen-actions">
            <button className="text-button" type="button" onClick={() => goToScreen("results")}>
              ← 三つのプランに戻る
            </button>
            <button className="text-button" type="button" onClick={() => goToScreen("planner")}>
              条件を変更する
            </button>
          </div>

          <header className="detail-heading">
            <span className="eyebrow">{PLAN_LABELS[selectedPlanIndex] ?? `第${selectedPlanIndex + 1}案`}</span>
            <h1>{selectedPlan.title || `旅行プラン ${selectedPlanIndex + 1}`}</h1>
            <p>{selectedPlan.summary || "旅行プランの概要はありません。"}</p>
            {selectedPlan.recommendation_reason && (
              <div className="recommendation">
                <strong>この旅の見どころ</strong>
                <span>{selectedPlan.recommendation_reason}</span>
              </div>
            )}
          </header>

          <div className="detail-layout">
            <section className="itinerary-panel" aria-label="日別スケジュール">
              <div className="panel-heading">
                <span className="panel-kicker">旅の道行き</span>
                <h2>日別スケジュール</h2>
              </div>

              {(Array.isArray(selectedPlan.days) ? selectedPlan.days : []).map(
                (day, dayIndex) => (
                  <DaySchedule
                    key={`${selectedPlan.plan_id}-${day.date || dayIndex}`}
                    day={day}
                    planId={selectedPlan.plan_id || `plan-${selectedPlanIndex}`}
                  />
                ),
              )}

              {Array.isArray(selectedPlan.main_spots) && selectedPlan.main_spots.length > 0 && (
                <section className="spot-list">
                  <h2>主な観光地</h2>
                  <ul>
                    {selectedPlan.main_spots.map((spot, spotIndex) => (
                      <li key={spot.id || `${selectedPlan.plan_id}-spot-${spotIndex}`}>
                        <strong>{spot.name || "名称未設定"}</strong>
                        {spot.address && <span>{spot.address}</span>}
                      </li>
                    ))}
                  </ul>
                </section>
              )}
            </section>

            <CostBreakdown
              breakdown={selectedPlan.cost_breakdown}
              total={selectedPlan.estimated_cost}
            />
          </div>
        </main>
      )}

      {loading && (
        <div className="loading-overlay" role="status" aria-live="polite">
          <div className="loading-box">
            <div className="loader" aria-hidden="true" />
            <span className="panel-kicker">旅支度の途中</span>
            <h2>あなたの旅を綴っています</h2>
            <p>観光地、経路、天気、予算を組み合わせています。</p>
            <div className="loading-list">
              <span>観光地の候補を確認</span>
              <span>移動経路と距離を計算</span>
              <span>三つの日別旅程を構成</span>
            </div>
          </div>
        </div>
      )}

      <footer>AI Travel Planner ・ 旅の一日一日を、丁寧に。</footer>
    </>
  );
}

export default App;
