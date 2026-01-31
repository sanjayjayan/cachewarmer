# \# 🎬 IMDb Title ID Fetcher

A lightweight Streamlit app to fetch **IMDb Title IDs**, **season numbers**, and **episode numbers** for any web/TV series using IMDb datasets.

## 🔍 Features

- Search any TV/web series title from IMDb
- Paste episode names (or leave blank to get all episodes)
- Uses fuzzy matching for close title matches
- Outputs: **IMDb ID (tconst)**, **season number**, **episode number**, **matched episode title**
- Preserves your input title even when no match is found
- Download clean results as CSV


## 🖥 How to Use

1. Enter the series name
2. Paste episode names (one per line) or leave it blank
3. See fuzzy matches + download CSV

## 📦 Requirements

Install dependencies with:

```bash
pip install -r requirements.txt
```


## 🚀 Run the App

```bash
streamlit run imdb_epi_matcher.py
```


## 📁 IMDb Data Files Required

To run this app, you need two IMDb data files:

- [`title.basics.tsv.gz`](https://datasets.imdbws.com/title.basics.tsv.gz)
- [`title.episode.tsv.gz`](https://datasets.imdbws.com/title.episode.tsv.gz)

👉 You can download them directly from the official [IMDb Datasets Page](https://datasets.imdbws.com/)

After downloading:

1. **Unzip** both `.gz` files (you’ll get `.tsv` files)
2. Place the extracted `title.basics.tsv` and `title.episode.tsv` files in your project folder

> ℹ️ These datasets are free for non-commercial use and are regularly updated by IMDb.
> Full documentation: [IMDb Non-Commercial Datasets](https://www.imdb.com/interfaces/)

## 📸 Screenshot

![Screenshot](app_screenshot.png)

## 📤 Deploy

### Option 1: Locally

```bash
streamlit run imdb_epi_matcher.py
```


### Option 2: Streamlit Cloud (Free)

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub → Select this repo
4. Set the app file to `imdb_epi_matcher.py`

UPDATE THIS README. FILE TOO AND GIVE UPDATED ONE REST OF THINGS SAME JUST MAKE IT INTO THE UPDATED CODE VERSION

Certainly! Below is the **updated README.md** file reflecting the latest app version based on your updated code. The core behavior remains the same, but the README now explicitly mentions the new fuzzy matching improvements, expanded search options, and episode filtering features consistent with your recent code:

# 🎬 IMDb Title ID Fetcher

A lightweight Streamlit app to fetch **IMDb Title IDs**, **season numbers**, and **episode numbers** for any TV/web series using IMDb datasets.

## 🔍 Features

- Search for any TV/web series title from IMDb by name or IMDb ID (e.g., `tt0944947`)
- Intelligent fuzzy matching over primary and original titles, supporting partial and misspelled input
- Includes options to **include mini-series** and **specials** in series search
- Paste episode names (one per line) or leave blank to list all episodes of the selected series
- Supports fuzzy matching on episode titles with season/episode hints (e.g., `S02E03`)
- Optional filters on seasons to narrow episode output
- View matched episode info: **IMDb ID (tconst)**, **matched episode title**, **season number**, **episode number**, match status, and fuzzy match score
- Preserves your input titles even when no close match is found
- Clean, sortable, and filterable output table with clickable IMDb links
- Download all matched results as CSV


## 🖥 How to Use

1. Enter the series name or IMDb series ID (e.g., `tt0944947`)
2. Optionally, tweak search options to include mini-series or specials and adjust minimum match score threshold
3. Select the correct series from the fuzzy match suggestions
4. Optionally filter which seasons to include
5. Paste episode names (one per line) or leave blank to get all episodes for the selected scope
6. Review the results table with fuzzy match statuses and open IMDb links
7. Download your output as a CSV file for further use

## ⚙️ Search Options

- **Include mini-series** (`tvMiniSeries`) and **specials** (`tvSpecial`) in fuzzy search with checkboxes
- Minimum match score slider to control fuzzy matching sensitivity (default 70)
- Season filtering to narrow down episode list outputs to selected seasons


## 📦 Requirements

Install Python dependencies with:

```bash
pip install -r requirements.txt
```

Make sure your `requirements.txt` contains (at least) the following packages:

```
streamlit>=1.18.0
pandas>=1.3.0
numpy>=1.21.0
rapidfuzz>=2.13.7
```


## 🚀 Run the App

```bash
streamlit run imdb_epi_matcher.py
```


## 📁 IMDb Data Files Required

You must download and extract both files below, then place the extracted `.tsv` files in your project folder:

- [`title.basics.tsv.gz`](https://datasets.imdbws.com/title.basics.tsv.gz)
- [`title.episode.tsv.gz`](https://datasets.imdbws.com/title.episode.tsv.gz)

🚩 **Note:**
Be sure to unzip these files so you have the `.tsv` versions in your app folder, named exactly as `title.basics.tsv` and `title.episode.tsv`.

## 📸 Screenshot

## 📤 Deployment Options

### Option 1: Local Machine

Run the app locally:

```bash
streamlit run imdb_epi_matcher.py
```


### Option 2: Streamlit Community Cloud (Free)

1. Push this repo to **GitHub**
2. Visit [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub account and select this repository
4. Set the application file path to `imdb_epi_matcher.py`
5. Launch and share your app!

## ℹ️ Additional Notes

- The app’s fuzzy matching leverages multiple scorers and normalized titles for better results, including differences in original and primary titles.
- Season and episode hints (e.g., `S01E05`) can bias fuzzy matching when entering episode titles.
- Outputs include clickable IMDb links that open in new tabs.
- The app caches IMDb data on the first load to speed up subsequent searches.

If you encounter issues or want to request new features, feel free to open an issue in the repository!

**Enjoy exploring TV series and episodes with easy IMDb ID lookups!**

If you want me to help generate or improve files like `requirements.txt` or deployment config, just ask!

