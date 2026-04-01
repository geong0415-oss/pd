"""
===============================================================
  파이프 내부 유동 압력 강하 계산기 (Streamlit)
  Pipe Internal Flow Pressure Drop Calculator
===============================================================
  실행 방법:
      pip install streamlit
      streamlit run pressure_drop_streamlit.py

  [데이터 출처]
  ▪ 액체 밀도   : Engineering ToolBox (liquids-densities-d_743)
  ▪ 액체 점도   : Engineering ToolBox (absolute-viscosity-liquids-d_1259)
  ▪ 파이프 규격 : ASTM A312/A358/A778/A53/A106, API 5L
                  ASME/ANSI B36.19 / B36.10
                  (출처: Wellgrow Industries Corp. - pipe_dimensions.pdf)

  [계산 방법]
  1. 유속        V  = Q / (π D² / 4)
  2. 레이놀즈 수  Re = ρ · V · D / μ
  3. 마찰계수    f  (Moody Chart, ε = 0)
       층류  Re < 2300  : f = 64 / Re
       전이  2300~4000  : 선형 보간
       난류  Re ≥ 4000  : Colebrook-White 반복법
  4. 압력 강하   ΔP = f · (L/D) · (ρ V² / 2)  [Darcy-Weisbach]
===============================================================
"""

import math
import streamlit as st

# ───────────────────────────────────────────────────────────────
#  1. 액체 물성 데이터 (밀도 + 점도)
#     출처: Engineering ToolBox
# ───────────────────────────────────────────────────────────────
LIQUIDS = {
    "Acetone (아세톤)":                      (787.0,   0.316e-3),
    "Benzene (벤젠)":                        (876.0,   0.601e-3),
    "Carbon disulfide (이황화탄소)":          (1265.0,  0.360e-3),
    "Carbon tetrachloride (사염화탄소)":      (1590.0,  0.910e-3),
    "Castor oil (피마자유)":                  (960.0,   650.0e-3),
    "Chloroform (클로로폼)":                  (1470.0,  0.530e-3),
    "Decane (데칸)":                         (728.0,   0.859e-3),
    "Ether (에테르)":                        (715.0,   0.223e-3),
    "Ethyl alcohol (에틸알코올)":             (787.0,   1.095e-3),
    "Ethylene glycol (에틸렌글리콜)":         (1100.0,  16.2e-3),
    "Glycerine (글리세린)":                  (1263.0,  950.0e-3),
    "Heptane (헵탄)":                        (681.0,   0.376e-3),
    "Hexane (헥산)":                         (657.0,   0.297e-3),
    "Kerosene (등유)":                       (823.0,   1.640e-3),
    "Linseed oil (아마인유)":                (930.0,   33.1e-3),
    "Mercury (수은)":                        (13600.0, 1.530e-3),
    "Methyl alcohol (메틸알코올)":            (789.0,   0.560e-3),
    "Octane (옥탄)":                         (701.0,   0.510e-3),
    "Propane (프로판)":                      (495.0,   0.110e-3),
    "Propyl alcohol (프로필알코올)":          (802.0,   1.920e-3),
    "Propylene (프로필렌)":                  (516.0,   0.090e-3),
    "Propylene glycol (프로필렌글리콜)":      (968.0,   42.0e-3),
    "Turpentine (테레빈유)":                 (870.0,   1.375e-3),
    "Water (물)":                            (1000.0,  0.890e-3),
    "Custom (직접 입력)":                    (0.0,     0.0),
}

# ───────────────────────────────────────────────────────────────
#  2. 파이프 규격 데이터 (ASME/ANSI B36.10 / B36.19)
#     (외경 mm, {스케줄명: 두께 mm})
# ───────────────────────────────────────────────────────────────
PIPE_DB = {
    "1/8":   (10.29,  {"5S":1.24,"10S":1.73,"10":1.24,"STD":1.73,"40S":1.73,"40":1.73,"80S":2.41,"80":2.41,"XS":2.41}),
    "1/4":   (13.72,  {"5S":1.65,"10S":2.24,"10":1.65,"30":1.85,"STD":2.24,"40S":2.24,"40":2.24,"80S":3.02,"80":3.02,"XS":3.02}),
    "3/8":   (17.15,  {"5S":1.65,"10S":2.31,"10":1.65,"30":1.85,"STD":2.31,"40S":2.31,"40":2.31,"80S":3.20,"80":3.20,"XS":3.20}),
    "1/2":   (21.34,  {"5S":1.65,"10S":2.11,"10":2.11,"40":2.77,"STD":2.77,"40S":2.77,"80":3.73,"XS":3.73,"80S":3.73,"160":4.78,"XXS":7.47}),
    "3/4":   (26.67,  {"5S":1.65,"10S":2.11,"10":2.11,"40":2.87,"STD":2.87,"40S":2.87,"80":3.91,"XS":3.91,"80S":3.91,"160":5.56,"XXS":7.82}),
    "1":     (33.40,  {"5S":1.65,"10S":2.77,"10":2.77,"30":2.90,"40":3.38,"STD":3.38,"40S":3.38,"80":4.55,"XS":4.55,"80S":4.55,"160":6.35,"XXS":9.09}),
    "1-1/4": (42.16,  {"5S":1.65,"10S":2.77,"10":2.77,"30":2.97,"40":3.56,"STD":3.56,"40S":3.56,"80":4.85,"XS":4.85,"80S":4.85,"160":6.35,"XXS":9.70}),
    "1-1/2": (48.26,  {"5S":1.65,"10S":2.77,"10":2.77,"30":3.18,"40":3.68,"STD":3.68,"40S":3.68,"80":5.08,"XS":5.08,"80S":5.08,"160":7.14,"XXS":10.15}),
    "2":     (60.33,  {"5S":1.65,"10S":2.77,"10":2.77,"30":3.18,"40":3.91,"STD":3.91,"40S":3.91,"80":5.54,"XS":5.54,"80S":5.54,"160":8.74,"XXS":11.07}),
    "2-1/2": (73.03,  {"5S":2.11,"10S":3.05,"10":3.05,"30":4.78,"40":5.16,"STD":5.16,"40S":5.16,"80":7.01,"XS":7.01,"80S":7.01,"160":9.35,"XXS":14.02}),
    "3":     (88.90,  {"5S":2.11,"10S":3.05,"10":3.05,"30":4.78,"40":5.49,"STD":5.49,"40S":5.49,"80":7.62,"XS":7.62,"80S":7.62,"160":11.13,"XXS":15.24}),
    "3-1/2": (101.60, {"5S":2.11,"10S":3.05,"10":3.05,"30":4.78,"40":5.74,"STD":5.74,"40S":5.74,"80":8.08,"XS":8.08,"80S":8.08}),
    "4":     (114.30, {"5S":2.11,"10S":3.05,"10":3.05,"30":4.78,"40":6.02,"STD":6.02,"40S":6.02,"60":8.56,"80":8.56,"XS":8.56,"80S":8.56,"100":11.13,"120":13.49,"160":17.12}),
    "5":     (141.30, {"5S":2.77,"10S":3.40,"10":3.40,"40":6.55,"STD":6.55,"40S":6.55,"80":9.53,"XS":9.53,"80S":9.53,"120":12.70,"160":15.88,"XXS":19.05}),
    "6":     (168.28, {"5S":2.77,"10S":3.40,"10":3.40,"40":7.11,"STD":7.11,"40S":7.11,"80":10.97,"XS":10.97,"80S":10.97,"120":14.27,"160":18.26,"XXS":21.95}),
    "8":     (219.08, {"5S":2.77,"10S":3.76,"10":3.76,"20":6.35,"30":7.04,"40":8.18,"STD":8.18,"40S":8.18,"60":10.31,"80":12.70,"XS":12.70,"80S":12.70,"100":15.09,"120":18.26,"140":20.62,"160":23.01,"XXS":22.23}),
    "10":    (273.05, {"5S":3.40,"10S":4.19,"10":4.19,"20":6.35,"30":7.80,"40":9.27,"STD":9.27,"40S":9.27,"60":12.70,"80":15.09,"XS":12.70,"80S":12.70,"100":18.26,"120":21.44,"140":25.40,"160":28.58,"XXS":25.40}),
    "12":    (323.85, {"5S":3.96,"10S":4.57,"10":4.57,"20":6.35,"30":8.38,"STD":9.53,"40":10.31,"40S":9.52,"60":14.27,"80":17.48,"XS":12.70,"80S":12.70,"100":21.44,"120":25.40,"140":28.58,"160":33.32,"XXS":25.40}),
    "14":    (355.60, {"5S":3.96,"10S":4.78,"10":6.35,"20":7.92,"30":9.53,"STD":9.53,"40":11.13,"60":15.09,"80":19.05,"XS":12.70,"100":23.83,"120":27.79,"140":31.75,"160":35.71,"XXS":35.71}),
    "16":    (406.40, {"5S":4.19,"10S":4.78,"10":6.35,"20":7.92,"30":9.53,"STD":9.53,"40":12.70,"60":16.66,"80":21.44,"XS":12.70,"100":26.19,"120":30.96,"140":36.53,"160":40.49,"XXS":40.49}),
    "18":    (457.20, {"5S":4.19,"10S":7.78,"10":6.35,"20":7.92,"STD":9.53,"30":11.13,"40":14.27,"60":19.05,"80":23.88,"XS":12.70,"100":29.36,"120":34.93,"140":39.67,"160":45.24,"XXS":45.24}),
    "20":    (508.00, {"5S":4.78,"10S":5.54,"10":6.35,"20":9.53,"STD":9.53,"30":12.70,"40":15.09,"60":20.62,"80":26.19,"XS":12.70,"100":32.54,"120":38.10,"140":44.45,"160":50.01,"XXS":50.01}),
    "22":    (558.80, {"5S":4.78,"10S":5.54,"10":6.35,"20":9.53,"STD":9.53,"30":12.70,"60":22.23,"80":28.58,"XS":12.70,"100":34.93,"120":41.28,"140":47.63,"160":53.98,"XXS":53.97}),
    "24":    (609.60, {"5S":5.54,"10S":6.35,"10":6.35,"20":9.53,"STD":9.53,"30":14.27,"40":17.48,"60":24.61,"80":30.96,"XS":12.70,"100":38.89,"120":46.02,"140":52.37,"160":59.54,"XXS":59.54}),
    "26":    (660.00, {"10":6.35,"20":12.70,"STD":9.53,"XS":12.70}),
    "28":    (711.20, {"10":6.35,"20":12.70,"30":15.88,"STD":9.53,"XS":12.70}),
    "30":    (762.00, {"5S":6.35,"10S":7.92,"10":6.35,"20":12.70,"30":15.88,"STD":9.53,"XS":12.70}),
    "32":    (812.80, {"10":6.35,"20":12.70,"30":15.88,"STD":9.53,"40":17.48,"XS":12.70}),
    "34":    (863.60, {"10":6.35,"20":12.70,"30":15.88,"STD":9.53,"40":17.48,"XS":12.70}),
    "36":    (914.40, {"10":6.35,"20":12.70,"30":15.88,"STD":9.53,"40":19.05,"XS":12.70}),
    "38":    (965.20, {"STD":9.53,"XS":12.70}),
    "40":    (1016.00,{"STD":9.53,"XS":12.70}),
}

SCH_ORDER = ["5S","5","10S","10","20","30","STD","40S","40","60","80S","80","XS","100","120","140","160","XXS"]

FLOW_UNIT_FACTORS = {
    "m³/h":          1 / 3600,
    "m³/s":          1.0,
    "m³/min":        1 / 60,
    "L/h":           1e-3 / 3600,
    "L/min":         1e-3 / 60,
    "L/s":           1e-3,
    "gal/min (GPM)": 6.30902e-5,
    "ft³/s":         0.0283168,
}

# ───────────────────────────────────────────────────────────────
#  3. 유체역학 계산 함수
# ───────────────────────────────────────────────────────────────

def _colebrook_smooth(Re):
    f = 0.316 * Re**-0.25 if Re < 1e5 else 0.184 * Re**-0.2
    for _ in range(100):
        f_new = 1.0 / (-2.0 * math.log10(2.51 / (Re * math.sqrt(f))))**2
        if abs(f_new - f) < 1e-12:
            break
        f = f_new
    return f

def friction_factor(Re):
    """
    반환: (f or None, regime_str, is_transitional)
    전이 구간(2300 ≤ Re < 4000)이면 f=None, is_transitional=True
    """
    if Re < 2300:
        return 64.0 / Re, "🟢 층류 (Laminar)", False
    if Re < 4000:
        return None, "🟡 전이 (Transitional)", True
    return _colebrook_smooth(Re), "🔴 난류 (Turbulent)", False

# ───────────────────────────────────────────────────────────────
#  4. Streamlit 앱
# ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="파이프 압력 강하 계산기",
    page_icon="🔧",
    layout="wide",
)

# ── 헤더 ──
st.markdown("""
<div style="background:#1E3A5F;padding:20px 28px;border-radius:10px;margin-bottom:24px">
  <h2 style="color:white;margin:0">🔧 파이프 내부 유동 압력 강하 계산기</h2>
  <p style="color:#94A3B8;margin:4px 0 0 0;font-size:13px">
    ASME B36.10 / B36.19 &nbsp;|&nbsp; Moody Chart &nbsp;|&nbsp; Darcy-Weisbach
  </p>
</div>
""", unsafe_allow_html=True)

# ── 2열 레이아웃 ──
col_left, col_right = st.columns([1, 1], gap="large")

# ════════════════════════════════════════════
#  왼쪽: 입력 패널
# ════════════════════════════════════════════
with col_left:

    # ── 1. 액체 물성 ──
    st.subheader("1. 액체 물성 (Fluid Properties)")

    liquid_name = st.selectbox("액체 선택", list(LIQUIDS.keys()), index=23)  # Water 기본

    rho_default, mu_default = LIQUIDS[liquid_name]
    is_custom = (rho_default == 0.0)

    c1, c2 = st.columns(2)
    with c1:
        rho = st.number_input(
            "밀도 ρ (kg/m³)",
            value=float(rho_default) if not is_custom else 1000.0,
            min_value=0.001,
            format="%.4f",
            disabled=not is_custom,
        )
    with c2:
        mu = st.number_input(
            "점도 μ (Pa·s)",
            value=float(mu_default) if not is_custom else 0.001,
            min_value=1e-10,
            format="%.6e",
            disabled=not is_custom,
        )

    # Custom일 때 실제 입력값 사용
    if is_custom:
        pass  # number_input 값 그대로 사용
    else:
        rho = rho_default
        mu  = mu_default

    st.divider()

    # ── 2. 파이프 규격 ──
    st.subheader("2. 파이프 규격 (Pipe Specification)")
    st.caption("ASTM A312 / A53 / A106 · API 5L · ASME/ANSI B36.10 / B36.19")

    pipe_mode = st.radio(
        "입력 방식",
        ["규격 선택 (NPS + Schedule)", "내경 직접 입력 (mm)"],
        horizontal=True,
    )

    if pipe_mode == "규격 선택 (NPS + Schedule)":
        c1, c2 = st.columns(2)
        with c1:
            nps = st.selectbox("NPS (공칭 크기)", list(PIPE_DB.keys()), index=8)  # 2" 기본
        od, sch_dict = PIPE_DB[nps]
        available_sch = [s for s in SCH_ORDER if s in sch_dict]
        default_sch = "40" if "40" in available_sch else available_sch[0]
        with c2:
            sch = st.selectbox("Schedule", available_sch,
                               index=available_sch.index(default_sch))
        t     = sch_dict[sch]
        d_mm  = od - 2 * t

        # 파이프 치수 표시
        m1, m2, m3 = st.columns(3)
        m1.metric("외경 OD (mm)", f"{od}")
        m2.metric("두께 t (mm)",  f"{t}")
        m3.metric("내경 ID (mm)", f"{d_mm:.3f}")

        pipe_str = f"NPS {nps}\"  SCH {sch}  |  OD={od} mm  t={t} mm  ID={d_mm:.3f} mm"

    else:
        d_mm = st.number_input("내경 ID (mm)", value=52.5, min_value=0.1, format="%.3f")
        pipe_str = f"직접 입력  ID = {d_mm:.3f} mm"

    st.divider()

    # ── 3. 유동 조건 ──
    st.subheader("3. 유동 조건 (Flow Conditions)")

    c1, c2 = st.columns([2, 1])
    with c1:
        flow_val = st.number_input("유량 Q", value=10.0, min_value=1e-10, format="%.6g")
    with c2:
        flow_unit = st.selectbox("단위", list(FLOW_UNIT_FACTORS.keys()), index=0)

    pipe_length = st.number_input("파이프 길이 L (m)", value=100.0, min_value=0.001, format="%.4f")

    st.divider()

    # ── 계산 버튼 ──
    calc_btn = st.button("▶  계산 실행 (Calculate)", type="primary", use_container_width=True)

# ════════════════════════════════════════════
#  오른쪽: 결과 패널
# ════════════════════════════════════════════
with col_right:
    st.subheader("4. 계산 결과 (Results)")

    if calc_btn:
        try:
            # 검증
            if rho <= 0 or mu <= 0:
                st.error("❌ 밀도와 점도는 양수여야 합니다.")
                st.stop()
            if d_mm <= 0:
                st.error("❌ 내경이 0 이하입니다. 규격을 확인하세요.")
                st.stop()
            if flow_val <= 0 or pipe_length <= 0:
                st.error("❌ 유량과 파이프 길이는 양수여야 합니다.")
                st.stop()

            # 단위 변환
            Q = flow_val * FLOW_UNIT_FACTORS[flow_unit]  # m³/s
            D = d_mm / 1000.0                             # m
            L = pipe_length

            # 계산
            A  = math.pi * D**2 / 4.0
            V  = Q / A
            Re = rho * V * D / mu
            f, regime, is_transitional = friction_factor(Re)

            # ── 입력 요약 ──
            st.markdown("**📋 입력 요약**")
            st.info(
                f"**파이프:** {pipe_str}  \n"
                f"**유체:** {liquid_name}  |  ρ = {rho} kg/m³  |  μ = {mu:.4e} Pa·s  \n"
                f"**유량:** {flow_val} {flow_unit}  =  {Q:.5e} m³/s  \n"
                f"**길이:** {L} m"
            )

            st.divider()

            # ── 중간 계산값 (Re, V, 유동형태 항상 표시) ──
            st.markdown("**⚙️ 중간 계산값**")
            r1, r2, r3 = st.columns(3)
            r1.metric("유속 V", f"{V:.4f}", "m/s")
            r2.metric("레이놀즈 수 Re", f"{Re:,.1f}")
            r3.metric("유동 형태", regime)

            st.divider()

            # ════════════════════════════════════════
            #  전이 구간 → 경고 + 재입력 안내
            # ════════════════════════════════════════
            if is_transitional:
                st.markdown("**⚙️ 마찰계수 f**")
                st.metric("마찰계수 f", "계산 불가")

                st.warning(
                    f"⚠️  **전이 구간 (Transitional Flow) 감지**\n\n"
                    f"현재 레이놀즈 수 **Re = {Re:,.1f}** 는 전이 구간 **(2,300 ~ 4,000)** 에 해당합니다.\n\n"
                    f"전이 구간에서는 유동이 층류와 난류 사이를 불규칙하게 오가기 때문에 "
                    f"마찰계수(f)를 신뢰성 있게 결정할 수 없습니다.\n\n"
                    f"**압력 강하 계산을 수행하지 않습니다.**"
                )

                st.error(
                    "🔄  **입력값을 다시 조정해 주세요.**\n\n"
                    "아래 두 가지 방향 중 하나를 선택하세요:\n\n"
                    f"- **층류로 낮추기** → Re < 2,300 이 되도록 유량을 줄이거나 파이프 직경을 늘려주세요.\n"
                    f"  (현재 Re = {Re:,.1f} → 목표 Re < 2,300)\n\n"
                    f"- **난류로 높이기** → Re ≥ 4,000 이 되도록 유량을 늘리거나 파이프 직경을 줄여주세요.\n"
                    f"  (현재 Re = {Re:,.1f} → 목표 Re ≥ 4,000)"
                )

                # 참고 유량 안내
                st.divider()
                st.markdown("**💡 참고: 경계 레이놀즈 수에 해당하는 유량**")

                A_ref = math.pi * D**2 / 4.0

                # 층류 경계: Re = 2300
                V_lam  = 2300 * mu / (rho * D)
                Q_lam  = V_lam * A_ref
                # 난류 경계: Re = 4000
                V_turb = 4000 * mu / (rho * D)
                Q_turb = V_turb * A_ref

                # 현재 단위로 역변환
                inv_factor = 1.0 / FLOW_UNIT_FACTORS[flow_unit]
                Q_lam_disp  = Q_lam  * inv_factor
                Q_turb_disp = Q_turb * inv_factor

                ref1, ref2 = st.columns(2)
                ref1.info(
                    f"**층류 유지 (Re < 2,300)**\n\n"
                    f"유량 < **{Q_lam_disp:.4f} {flow_unit}**\n\n"
                    f"({Q_lam:.5e} m³/s)"
                )
                ref2.info(
                    f"**난류 진입 (Re ≥ 4,000)**\n\n"
                    f"유량 ≥ **{Q_turb_disp:.4f} {flow_unit}**\n\n"
                    f"({Q_turb:.5e} m³/s)"
                )

            # ════════════════════════════════════════
            #  층류 / 난류 → 정상 계산 결과 표시
            # ════════════════════════════════════════
            else:
                dP = f * (L / D) * (rho * V**2 / 2.0)

                # 단위 변환
                dP_kPa   = dP / 1e3
                dP_bar   = dP / 1e5
                dP_psi   = dP / 6894.757
                dP_mmH2O = dP / 9.80665
                dP_atm   = dP / 101325.0

                # 마찰계수
                st.markdown("**⚙️ 마찰계수 f**")
                st.metric("마찰계수 f (Darcy)", f"{f:.7f}")

                st.divider()

                # ── 압력 강하 결과 ──
                st.markdown("**📊 압력 강하  ΔP = f · (L/D) · (ρV²/2)**")

                p1, p2, p3 = st.columns(3)
                p1.metric("Pa",   f"{dP:,.4f}")
                p2.metric("kPa",  f"{dP_kPa:,.6f}")
                p3.metric("bar",  f"{dP_bar:,.8f}")

                p4, p5, p6 = st.columns(3)
                p4.metric("psi",   f"{dP_psi:,.6f}")
                p5.metric("mmH₂O", f"{dP_mmH2O:,.4f}")
                p6.metric("atm",   f"{dP_atm:,.8f}")

                st.divider()

                # ── 전체 결과 테이블 ──
                st.markdown("**📄 전체 결과 요약표**")
                import pandas as pd
                df = pd.DataFrame({
                    "항목": [
                        "유속 V", "레이놀즈 수 Re", "유동 형태", "마찰계수 f (Darcy)",
                        "표면조도 ε/D",
                        "압력강하 ΔP", "압력강하 ΔP", "압력강하 ΔP",
                        "압력강하 ΔP", "압력강하 ΔP", "압력강하 ΔP",
                    ],
                    "값": [
                        f"{V:.6f}", f"{Re:,.2f}", regime, f"{f:.7f}",
                        "0  (매끈한 파이프)",
                        f"{dP:,.4f}", f"{dP_kPa:,.6f}", f"{dP_bar:,.8f}",
                        f"{dP_psi:,.6f}", f"{dP_mmH2O:,.4f}", f"{dP_atm:,.8f}",
                    ],
                    "단위": [
                        "m/s", "", "", "",
                        "",
                        "Pa", "kPa", "bar",
                        "psi", "mmH₂O", "atm",
                    ],
                })
                st.dataframe(df, use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"❌ 계산 오류: {e}")

    else:
        # 계산 전 안내
        st.markdown("""
        <div style="
            background:#F1F5F9;
            border-left:4px solid #2563EB;
            border-radius:6px;
            padding:20px 24px;
            color:#334155;
        ">
        <b>👈 왼쪽에서 입력 후 계산 버튼을 눌러주세요.</b><br><br>
        <b>계산 순서</b><br>
        1️⃣ 액체 종류 선택<br>
        2️⃣ 파이프 규격 선택 (NPS + Schedule)<br>
        3️⃣ 유량 및 파이프 길이 입력<br>
        4️⃣ <b>▶ 계산 실행</b> 클릭
        </div>
        """, unsafe_allow_html=True)

# ── 하단 수식 ──
st.divider()
st.markdown("""
<div style="
    background:#EFF6FF;
    border-radius:8px;
    padding:10px 20px;
    text-align:center;
    font-family:monospace;
    font-size:13px;
    color:#1E3A5F;
">
Re = ρ·V·D/μ &nbsp;&nbsp;&nbsp; f: Colebrook-White (ε=0) &nbsp;&nbsp;&nbsp; ΔP = f·(L/D)·(ρV²/2)
&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;
밀도 출처: Engineering ToolBox (d_743) &nbsp;&nbsp; 점도 출처: Engineering ToolBox (d_1259) &nbsp;&nbsp; 파이프 규격: ASME B36.10/B36.19
</div>
""", unsafe_allow_html=True)