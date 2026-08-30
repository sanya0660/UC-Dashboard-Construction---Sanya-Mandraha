import streamlit as st
import pandas as pd
import plotly.express as px
import json

st.set_page_config(page_title="Berkeley Major Arbitrage", layout="wide")

@st.cache_data
def load_majors():
    df = pd.read_csv("uc_transfer_admission_by_major.csv")
    df = df[df.applicants > 0].copy()
    df["admit_rate_calc"] = df.admits / df.applicants
    df["nice"] = df.major.str.replace(r"(?<=[a-z])(?=[A-Z])", " ", regex=True)
    return df

majors_df = load_majors()
all_majors = sorted(majors_df.major.unique())

computing_cluster = [m for m in [
    "ComputerScience", "ElectricalEngineering-ComputerScience",
    "DataScience", "Statistics", "AppliedMathematics", "CognitiveScience"
] if m in all_majors]

GEMINI_MODEL = "gemini-flash-latest"

def connect_gemini(api_key):
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        return genai.GenerativeModel(GEMINI_MODEL)
    except Exception as err:
        st.sidebar.error(f"Couldn't connect to Gemini: {err}")
        return None

def find_related_majors(gemini, student_goal):
    ask = f"""A student describes what they want to study. From this exact list of
Berkeley majors, pick the 3 to 7 whose core skills genuinely overlap with their goal.
Reply with only a raw JSON list of exact strings from the list, nothing else.
MAJORS: {all_majors}
GOAL: {student_goal}"""
    reply = gemini.generate_content(ask).text
    reply = reply.replace("```json", "").replace("```", "").strip()
    return [m for m in json.loads(reply) if m in all_majors]

def write_report(gemini, student_goal, rows):
    lines = "\n".join(
        f"- {r.nice}: admit rate {r.admit_rate_calc:.0%}, "
        f"admit GPA {r.admit_gpa_p25}-{r.admit_gpa_p75}, {int(r.applicants)} applicants"
        for r in rows.itertuples()
    )
    ask = f"""You're an admissions strategist working only from the numbers below.
The student wants to: "{student_goal}". These Berkeley transfer majors (fall 2025)
share overlapping skills:
{lines}

In four tight sentences: name the cheapest door (highest admit rate) and how many
points easier it is than the toughest, say whether that easier door also has a lower
GPA bar, and give one honest risk of picking a major just for the admit rate."""
    return gemini.generate_content(ask, generation_config={"max_output_tokens": 260}).text

st.sidebar.header("Gemini")
saved_key = ""
try:
    saved_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    pass
api_key = st.sidebar.text_input("API key", value=saved_key, type="password", help="aistudio.google.com/apikey")
gemini = connect_gemini(api_key) if api_key else None

st.title("The Berkeley Major Arbitrage Engine")
st.caption("Admissions is a market, and near-identical skillsets are mispriced. "
           "Computer Science admits 3% of transfers. Applied Math admits 38%.")

chosen = computing_cluster
goal = "machine learning and working with data"
if gemini:
    typed = st.text_input("What do you actually want to study or do?",
                          placeholder="e.g. build ML models and analyze data")
    if typed:
        try:
            found = find_related_majors(gemini, typed)
            if len(found) >= 2:
                chosen, goal = found, typed
                st.success("Skill-adjacent majors: " + ", ".join(majors_df[majors_df.major == m].nice.iloc[0] for m in found))
            else:
                st.warning("Couldn't pin down a clear cluster, showing the computing example instead.")
        except Exception as err:
            st.warning(f"That didn't parse ({err}), showing the computing example instead.")
else:
    st.info("Drop a Gemini API key in the sidebar to ask in plain English and generate a strategy.")

picked = majors_df[majors_df.major.isin(chosen)].sort_values("admit_rate_calc", ascending=False)
easiest, hardest = picked.iloc[0], picked.iloc[-1]

col1, col2, col3 = st.columns(3)
col1.metric("Cheapest door", easiest.nice, f"{easiest.admit_rate_calc:.0%} admit")
col2.metric("Toughest door", hardest.nice, f"{hardest.admit_rate_calc:.0%} admit")
col3.metric("Arbitrage spread",
            f"{(easiest.admit_rate_calc - hardest.admit_rate_calc) * 100:.0f} pts",
            f"{easiest.admit_rate_calc / hardest.admit_rate_calc:.1f}x easier")

st.subheader("The arbitrage spread: admit rate by major")
spread = px.bar(picked, x="admit_rate_calc", y="nice", orientation="h",
                text=picked.admit_rate_calc.map(lambda v: f"{v:.0%}"),
                color="admit_rate_calc", color_continuous_scale="RdYlGn")
spread.update_layout(xaxis_tickformat=".0%", xaxis_title="Admit rate (how open the door is)",
                     yaxis_title="", yaxis={"categoryorder": "total ascending"},
                     coloraxis_showscale=False)
st.plotly_chart(spread, use_container_width=True)

st.subheader("The market map: crowded doors close")
market = px.scatter(picked, x="applicants", y="admit_rate_calc", text="nice",
                    size="applicants", color="admit_rate_calc",
                    color_continuous_scale="RdYlGn", size_max=55)
market.update_traces(textposition="top center")
market.update_layout(xaxis_title="Applicants (demand)", yaxis_title="Admit rate",
                     yaxis_tickformat=".0%", coloraxis_showscale=False)
st.plotly_chart(market, use_container_width=True)

st.caption("Same skillset, but the more applicants pile into a major name, the lower the "
           "admit rate, while the admit-GPA bar barely moves (3.8-4.0 across the board). "
           "The gap is competition volume, not student caliber.")

if gemini:
    st.subheader("Arbitrage Report")
    if st.button("Generate strategy"):
        with st.spinner("Reading the market..."):
            try:
                st.markdown(write_report(gemini, goal, picked))
            except Exception as err:
                st.error(f"Gemini call failed: {err}")

st.caption("Data: UC Information Center, Berkeley transfer admissions, fall 2025. "
           "Admit rate = admits / applicants. Fall-2025 snapshot, not a trend.")
