from pathlib import Path
import sqlite3

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "manual" / "hospital_registry_review.db"
CSV_EXPORT_PATH = PROJECT_ROOT / "data" / "manual" / "hospital_registry_review.csv"
SUGGESTIONS_PATH = PROJECT_ROOT / "data" / "manual" / "hospital_registry_review_suggestions.csv"

CATEGORY_OPTIONS = [
    "",
    "general_or_acute_care",
    "psychiatric_psychosomatic",
    "rehabilitation",
    "specialized_or_partial_acute",
    "unknown_needs_review",
]

STATUS_OPTIONS = [
    "needs_verification",
    "verified",
]


st.set_page_config(
    page_title="Hospital Registry Review",
    layout="wide",
)

st.title("Hospital Registry Review")


def load_db_data() -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query("SELECT * FROM hospital_review", conn)


def save_db_data(df: pd.DataFrame) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        df.to_sql("hospital_review", conn, if_exists="replace", index=False)


def load_suggestions() -> pd.DataFrame:
    if not SUGGESTIONS_PATH.exists():
        return pd.DataFrame()

    suggestions = pd.read_csv(SUGGESTIONS_PATH)

    suggestion_columns = [
        "hospital_id",
        "suggested_category",
        "suggested_acute_relevance_weight",
        "suggested_source_type",
        "suggested_source_url",
        "suggested_review_notes",
        "suggestion_confidence",
    ]

    return suggestions[suggestion_columns].copy()


def merge_suggestions(df: pd.DataFrame, suggestions: pd.DataFrame) -> pd.DataFrame:
    if suggestions.empty:
        return df.copy()

    return df.merge(
        suggestions,
        on="hospital_id",
        how="left",
        validate="one_to_one",
    )


def apply_high_confidence_suggestions(df: pd.DataFrame) -> pd.DataFrame:
    updated = df.copy()

    mask = (
        updated["verification_status"].ne("verified")
        & updated["suggested_category"].notna()
        & updated["suggested_category"].ne("unknown_needs_review")
        & updated["suggestion_confidence"].fillna(0).ge(0.85)
    )

    updated.loc[mask, "verified_category"] = updated.loc[mask, "suggested_category"]
    updated.loc[mask, "verified_acute_relevance_weight"] = updated.loc[
        mask, "suggested_acute_relevance_weight"
    ]
    updated.loc[mask, "source_type"] = updated.loc[mask, "suggested_source_type"]
    updated.loc[mask, "source_url"] = updated.loc[mask, "suggested_source_url"]
    updated.loc[mask, "review_notes"] = updated.loc[mask, "suggested_review_notes"]

    # Important: keep status as needs_verification.
    # Human reviewer still needs to confirm.
    updated.loc[mask, "verification_status"] = "needs_verification"

    return updated


db_df = load_db_data()
suggestions_df = load_suggestions()
df = merge_suggestions(db_df, suggestions_df)

st.sidebar.header("Filters")

city_options = ["All"] + sorted(df["city"].dropna().unique().tolist())
selected_city = st.sidebar.selectbox("City", city_options)

status_options = ["All"] + STATUS_OPTIONS
selected_status = st.sidebar.selectbox("Verification status", status_options)

category_options = ["All"] + CATEGORY_OPTIONS[1:]
selected_auto_category = st.sidebar.selectbox("Automatic category", category_options)

only_with_suggestions = st.sidebar.checkbox("Only rows with suggestions", value=False)

filtered_df = df.copy()

if selected_city != "All":
    filtered_df = filtered_df[filtered_df["city"] == selected_city]

if selected_status != "All":
    filtered_df = filtered_df[filtered_df["verification_status"] == selected_status]

if selected_auto_category != "All":
    filtered_df = filtered_df[filtered_df["automatic_category"] == selected_auto_category]

if only_with_suggestions and "suggested_category" in filtered_df.columns:
    filtered_df = filtered_df[filtered_df["suggested_category"].notna()]

DISPLAY_COLUMNS = [
    "hospital_id",
    "city",
    "hospital_name",
    "hospital_registry_type",
    "operator_name",
    "street",
    "verified_category",
    "verified_acute_relevance_weight",
    "verification_status",
    "source_type",
    "source_url",
    "review_notes",
    "suggested_category",
    "suggested_acute_relevance_weight",
    "suggestion_confidence",
    "suggested_source_url",
    "suggested_review_notes",
    "automatic_category",
    "automatic_acute_relevance_weight",
    "automatic_classification_reason",
]

existing_display_columns = [
    column for column in DISPLAY_COLUMNS if column in filtered_df.columns
]

filtered_df = filtered_df[existing_display_columns].copy()

st.caption(f"Showing {len(filtered_df)} of {len(df)} hospital rows.")

edited_df = st.data_editor(
    filtered_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "verified_category": st.column_config.SelectboxColumn(
            "verified_category",
            options=CATEGORY_OPTIONS,
        ),
        "verified_acute_relevance_weight": st.column_config.NumberColumn(
            "verified_acute_relevance_weight",
            min_value=0.0,
            max_value=1.0,
            step=0.1,
        ),
        "verification_status": st.column_config.SelectboxColumn(
            "verification_status",
            options=STATUS_OPTIONS,
        ),
        "source_url": st.column_config.LinkColumn("source_url"),
        "suggested_source_url": st.column_config.LinkColumn("suggested_source_url"),
        "suggestion_confidence": st.column_config.NumberColumn(
            "suggestion_confidence",
            min_value=0.0,
            max_value=1.0,
            step=0.05,
        ),
    },
    disabled=[
        "hospital_id",
        "city",
        "hospital_name",
        "hospital_registry_type",
        "operator_name",
        "street",
        "suggested_category",
        "suggested_acute_relevance_weight",
        "suggestion_confidence",
        "suggested_source_url",
        "suggested_review_notes",
        "automatic_category",
        "automatic_acute_relevance_weight",
        "automatic_classification_reason",
    ],
)

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("Save changes to DB", type="primary"):
        updated_db_df = db_df.copy()

        editable_columns = [
            "verified_category",
            "verified_acute_relevance_weight",
            "verification_status",
            "source_type",
            "source_url",
            "review_notes",
        ]

        for _, row in edited_df.iterrows():
            mask = updated_db_df["hospital_id"] == row["hospital_id"]
            for column in editable_columns:
                if column in row.index:
                    updated_db_df.loc[mask, column] = row[column]

        save_db_data(updated_db_df)
        st.success("Saved changes to SQLite DB.")

with col2:
    if st.button("Apply high-confidence suggestions"):
        merged = merge_suggestions(db_df, suggestions_df)
        updated = apply_high_confidence_suggestions(merged)

        db_columns = db_df.columns.tolist()
        updated_db_df = updated[db_columns].copy()

        save_db_data(updated_db_df)
        st.success(
            "Applied high-confidence suggestions to editable fields. "
            "Rows still need human verification."
        )

with col3:
    if st.button("Export DB to CSV"):
        export_df = load_db_data()
        export_df.to_csv(CSV_EXPORT_PATH, index=False)
        st.success(f"Exported review CSV to {CSV_EXPORT_PATH}")

st.divider()

st.subheader("Review progress")

progress = (
    load_db_data()["verification_status"]
    .value_counts()
    .rename_axis("status")
    .reset_index(name="count")
)

st.dataframe(progress, use_container_width=True)

if not suggestions_df.empty:
    st.subheader("Suggestion summary")

    suggestion_summary = (
        suggestions_df["suggested_category"]
        .value_counts(dropna=False)
        .rename_axis("suggested_category")
        .reset_index(name="count")
    )

    st.dataframe(suggestion_summary, use_container_width=True)
