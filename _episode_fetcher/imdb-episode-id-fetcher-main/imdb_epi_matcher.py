import re
import numpy as np
import pandas as pd
import streamlit as st
from rapidfuzz import process, fuzz

# ---------- CONFIG ----------
st.set_page_config(page_title="IMDb Series/Episodes ID Fetcher", layout="wide")

# ---------- HELPERS ----------
IMDB_ID_PATTERN = re.compile(r"^tt\d{7,}$", re.IGNORECASE)

def normalize_title(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = s.lower().strip()
    s = re.sub(r'“|”|’|‚|‘|"|\'', ' ', s)
    s = re.sub(r'&', ' and ', s)
    s = re.sub(r'\bpart\b', 'pt', s)
    s = re.sub(r'[^a-z0-9\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip()

def parse_hint(s: str):
    if not isinstance(s, str):
        return None, None
    m = re.search(r'\bS(\d{1,2})E(\d{1,3})\b', s, flags=re.I)
    if m:
        try:
            return int(m.group(1)), int(m.group(2))
        except Exception:
            return None, None
    return None, None

def make_display_title(row):
    title = row.get("primaryTitle") or ""
    year = row.get("startYear")
    year_str = str(int(year)) if isinstance(year, (int, float)) and not pd.isna(year) else "N/A"
    tconst = row.get("tconst") or ""
    ttype = row.get("titleType") or ""
    return f"{title} ({year_str}) [{ttype}] [{tconst}]"

def clickable_link(tconst):
    if not tconst:
        return ""
    return f"https://www.imdb.com/title/{tconst}"

def best_fuzzy_match(query, candidates):
    scorers = [fuzz.WRatio, fuzz.token_set_ratio, fuzz.partial_ratio]
    best = (None, 0)
    for scorer in scorers:
        m = process.extractOne(query, candidates, scorer=scorer, score_cutoff=70)
        if m and m[1] > best[1]:
            best = (m[0], m[1])
    return best

# ---------- DATA LOADING ----------
@st.cache_data(show_spinner=True)
def load_data():
    usecols_basics = [
        "tconst", "titleType", "primaryTitle", "originalTitle", "startYear", "endYear"
    ]
    usecols_episodes = ["tconst", "parentTconst", "seasonNumber", "episodeNumber"]

    basics = pd.read_csv(
        "title.basics.tsv",
        sep="\t",
        dtype=str,
        na_values="\\N",
        usecols=usecols_basics
    )
    episodes = pd.read_csv(
        "title.episode.tsv",
        sep="\t",
        dtype=str,
        na_values="\\N",
        usecols=usecols_episodes
    )

    # Convert numeric columns
    for c in ["startYear", "endYear"]:
        basics[c] = pd.to_numeric(basics[c], errors="coerce")
    for c in ["seasonNumber", "episodeNumber"]:
        episodes[c] = pd.to_numeric(episodes[c], errors="coerce")

    # Normalized titles for matching
    basics["norm_primaryTitle"] = basics["primaryTitle"].apply(normalize_title)
    basics["norm_originalTitle"] = basics["originalTitle"].apply(normalize_title)

    return basics, episodes

@st.cache_data(show_spinner=False)
def get_series_basics(basics: pd.DataFrame, include_mini=False, include_special=False):
    valid_types = {"tvSeries"}
    if include_mini:
        valid_types.add("tvMiniSeries")
    if include_special:
        valid_types.add("tvSpecial")
    series_basics = basics[basics["titleType"].isin(valid_types)].copy()
    return series_basics

@st.cache_data(show_spinner=False)
def get_series_episodes(episodes: pd.DataFrame, basics: pd.DataFrame, series_id: str):
    series_episodes = episodes[episodes["parentTconst"] == series_id].copy()
    if series_episodes.empty:
        return pd.DataFrame()

    merged = series_episodes.merge(
        basics[["tconst", "primaryTitle", "originalTitle"]],
        on="tconst",
        how="left",
        suffixes=("_ep", "_base"),
    )

    merged["norm_primaryTitle"] = merged["primaryTitle"].apply(normalize_title)
    merged["norm_originalTitle"] = merged["originalTitle"].apply(normalize_title)
    merged = merged.drop_duplicates(subset=["tconst"], keep="first")
    merged = merged.sort_values(["seasonNumber", "episodeNumber"], na_position="last")
    return merged

def match_episode_list(input_lines, df_eps, min_score=70):
    results = []
    if df_eps.empty:
        return results

    cand_map = {}
    for idx, row in df_eps.iterrows():
        for t in [row.get("primaryTitle"), row.get("originalTitle")]:
            if isinstance(t, str) and t:
                cand_map.setdefault(t, set()).add(idx)
    candidate_titles = list(cand_map.keys())
    candidate_norms = [normalize_title(t) for t in candidate_titles]

    for raw in input_lines:
        title = raw.strip()
        s_hint, e_hint = parse_hint(title)
        norm_title = normalize_title(title)

        df_scope = df_eps
        if s_hint is not None and e_hint is not None:
            scoped = df_eps[
                (df_eps["seasonNumber"] == s_hint) & (df_eps["episodeNumber"] == e_hint)
            ]
            if not scoped.empty:
                df_scope = scoped

        exact_hits = df_scope[
            (df_scope["norm_primaryTitle"] == norm_title)
            | (df_scope["norm_originalTitle"] == norm_title)
        ]
        if not exact_hits.empty:
            row = exact_hits.iloc[0]
            results.append({
                "InputTitle": title,
                "MatchedTitle": row.get("primaryTitle", ""),
                "seasonNumber": row.get("seasonNumber", np.nan),
                "episodeNumber": row.get("episodeNumber", np.nan),
                "tconst": row.get("tconst", ""),
                "IMDb Link": clickable_link(row.get("tconst", "")),
                "Status": "Matched",
                "MatchScore": 100
            })
            continue

        match_title, score = best_fuzzy_match(norm_title, candidate_norms)
        if match_title is None or score < min_score:
            results.append({
                "InputTitle": title,
                "MatchedTitle": "",
                "seasonNumber": np.nan,
                "episodeNumber": np.nan,
                "tconst": "",
                "IMDb Link": "",
                "Status": "No Match",
                "MatchScore": int(score or 0)
            })
            continue

        try:
            pos = candidate_norms.index(match_title)
            original_title = candidate_titles[pos]
        except ValueError:
            original_title = None

        if original_title and original_title in cand_map:
            idxs = list(cand_map[original_title])
            sub = df_scope.loc[idxs] if s_hint is not None and e_hint is not None else df_eps.loc[idxs]
            if s_hint is not None and e_hint is not None:
                sub_pref = sub[
                    (sub["seasonNumber"] == s_hint) & (sub["episodeNumber"] == e_hint)
                ]
                if not sub_pref.empty:
                    sub = sub_pref
            sub = sub.sort_values(["seasonNumber", "episodeNumber"], na_position="last")
            row = sub.iloc[0]
            results.append({
                "InputTitle": title,
                "MatchedTitle": row.get("primaryTitle", original_title or ""),
                "seasonNumber": row.get("seasonNumber", np.nan),
                "episodeNumber": row.get("episodeNumber", np.nan),
                "tconst": row.get("tconst", ""),
                "IMDb Link": clickable_link(row.get("tconst", "")),
                "Status": "Matched",
                "MatchScore": int(score)
            })
        else:
            results.append({
                "InputTitle": title,
                "MatchedTitle": "",
                "seasonNumber": np.nan,
                "episodeNumber": np.nan,
                "tconst": "",
                "IMDb Link": "",
                "Status": "No Match",
                "MatchScore": int(score)
            })

    return results

# ---------- UI ----------
st.title("🎬 IMDb Series/Episodes ID Fetcher")
st.markdown("Enter a TV series name (partial OK, fuzzy match) or a known IMDb series ID (e.g., tt0944947).")

with st.expander("Search options"):
    include_mini = st.checkbox("Include mini-series (tvMiniSeries)", value=False)
    include_special = st.checkbox("Include specials (tvSpecial)", value=False)
    min_match_score = st.slider("Minimum match score", 0, 100, 70)

basics, episodes = load_data()
series_basics = get_series_basics(basics, include_mini=include_mini, include_special=include_special)

user_input = st.text_input("Series Name or IMDb Series ID:", key="series_input")
series_id = None
series_row = None

if user_input:
    user_input = user_input.strip()
    # IMDb ID path
    if IMDB_ID_PATTERN.match(user_input):
        matches = series_basics[series_basics["tconst"].str.lower() == user_input.lower()]
        if matches.empty:
            st.error(f"No TV series found with IMDb ID {user_input}.")
        else:
            series_row = matches.iloc[0]
            series_id = series_row["tconst"]
    else:
        # Fuzzy series search with aligned candidate list and multi-scorer aggregation
        candidates = series_basics.copy()

        # Build a single search string per row, preserving order with .tolist()
        search_strings = (
            candidates["primaryTitle"].fillna("") + " " +
            candidates["originalTitle"].fillna("") + " " +
            candidates["startYear"].fillna("").astype(str)
        ).tolist()
        search_norm = [normalize_title(s) for s in search_strings]
        qnorm = normalize_title(user_input)

        def top_matches(q, pool, limit=50, cutoff=60):
            out = []
            for scorer in (fuzz.WRatio, fuzz.token_set_ratio, fuzz.partial_ratio):
                res = process.extract(q, pool, scorer=scorer, limit=limit, score_cutoff=cutoff)
                # res is list of (match_str, score, index)
                out.extend(res)
            # Deduplicate by index with max score
            best = {}
            for _, score, idx in out:
                best[idx] = max(best.get(idx, 0), score)
            ranked = sorted(best.items(), key=lambda x: x[1], reverse=True)
            return ranked

        ranked = top_matches(qnorm, search_norm, limit=100, cutoff=60)

        if not ranked:
            st.error(f"No close match found for {user_input}.")
        else:
            # Build options, dedup by tconst, show top 10
            seen_tconst = set()
            options = []
            idx_map = {}

            for idx, score in ranked:
                row = candidates.iloc[idx]
                tconst = row["tconst"]
                if tconst in seen_tconst:
                    continue
                seen_tconst.add(tconst)

                year = int(row["startYear"]) if not pd.isna(row["startYear"]) else ""
                label = f"{row['primaryTitle']} ({year}) [{row['titleType']}] [{tconst}] (Score: {score})"
                options.append(label)
                idx_map[label] = idx
                if len(options) >= 10:
                    break

            chosen_option = st.selectbox("Select the correct series:", options, key="series_choice")
            if chosen_option:
                chosen_idx = idx_map[chosen_option]
                series_row = candidates.iloc[chosen_idx]
                series_id = series_row["tconst"]

if series_id:
    st.success(
        f"Series selected: {series_row['primaryTitle']} "
        f"(Year: {int(series_row['startYear']) if not pd.isna(series_row['startYear']) else 'N/A'}), IMDb ID: {series_id}"
    )

    df_eps = get_series_episodes(episodes, basics, series_id)
    if df_eps.empty:
        st.warning("No episodes found for this series.")
    else:
        with st.expander("Episode filters"):
            seasons = sorted([int(s) for s in df_eps["seasonNumber"].dropna().unique()])
            sel_seasons = st.multiselect("Filter seasons", seasons, default=seasons)

        if sel_seasons:
            df_scope = df_eps[df_eps["seasonNumber"].isin(sel_seasons)]
        else:
            df_scope = df_eps

        st.markdown("Enter episode names (one per line) to match episodes by title. Leave blank to list all episodes.")
        episode_input = st.text_area("Episodes (one per line):", value="", key="episode_input")

        with st.spinner("Processing episodes..."):
            your_episodes = [line.strip() for line in (episode_input or "").splitlines() if line.strip()]

            if your_episodes:
                matched_rows = match_episode_list(your_episodes, df_scope, min_score=min_match_score)
            else:
                matched_rows = []
                for _, row in df_scope.iterrows():
                    matched_rows.append({
                        "InputTitle": row.get("primaryTitle", ""),
                        "MatchedTitle": row.get("primaryTitle", ""),
                        "seasonNumber": row.get("seasonNumber", np.nan),
                        "episodeNumber": row.get("episodeNumber", np.nan),
                        "tconst": row.get("tconst", ""),
                        "IMDb Link": clickable_link(row.get("tconst", "")),
                        "Status": "Matched",
                        "MatchScore": 100
                    })

        if matched_rows:
            df_out = pd.DataFrame(matched_rows)
            df_out["seasonNumber"] = pd.to_numeric(df_out["seasonNumber"], errors="coerce")
            df_out["episodeNumber"] = pd.to_numeric(df_out["episodeNumber"], errors="coerce")
            df_out = df_out.sort_values(["Status", "seasonNumber", "episodeNumber"], ascending=[True, True, True], na_position="last")

            def highlight_no_match(row):
                color = "background-color: #ffe6e6;" if row.Status == "No Match" else ""
                return [color] * len(row)

            st.markdown("#### Results")
            try:
                st.dataframe(
                    df_out,
                    use_container_width=True,
                    column_config={
                        "IMDb Link": st.column_config.LinkColumn("IMDb Link")
                    }
                )
            except Exception:
                st.dataframe(df_out.style.apply(highlight_no_match, axis=1), use_container_width=True)

            matched_count = int((df_out["Status"] == "Matched").sum())
            st.info(f"Matched: {matched_count} / {len(df_out)} episodes")

            csv = df_out.to_csv(index=False).encode("utf-8")
            st.download_button("Download CSV", csv, "matched_episodes.csv", "text/csv")
        else:
            st.warning("No episodes to display.")

st.markdown("""
---
Usage Tips:
- Enter either an IMDb series ID (e.g. tt0944947) or a series name (partial or misspelled OK).
- Episode input: one title per line. You can add hints like S2E3 in a line to bias matching.
- Use the filters and minimum match score to refine results.
""")

