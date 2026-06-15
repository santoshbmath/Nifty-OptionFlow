# 🌊 OptionFlow Nifty | Live OI, Volume & Breakout Intelligence

A real-time, interactive Streamlit dashboard that fetches live Option Chain data directly from the National Stock Exchange (NSE) of India. The application bypasses basic bot protections to deliver live insights, visual data graphs, and automated trading signals based on Open Interest (OI) and Volume dynamics.

## ✨ Features

* **Live NSE Data Fetching:** Uses `curl_cffi` to bypass Akamai bot-protection and fetch live JSON data.
* **Auto-Expiry Calculation:** Automatically determines the next upcoming weekly expiry date.
* **Dynamic Data Filtering:** Isolates the active trading zone by filtering 11 strikes (+/- 5 strikes around the At-The-Money strike).
* **Automated Insights:** Generates human-readable market direction signals (Overall, ATM, and S/R Boundaries) with color-coded trend indicators.
* **Interactive Visualizations:** Renders interactive Plotly bar charts for Total OI, Change in OI, and Traded Volume.
* **Auto-Refresh:** Configurable background auto-refresh to keep data up-to-the-second without manual reloading.

---

## 🚀 How to Install and Run

### 1. Prerequisites
Ensure you have Python 3.8+ installed on your system. 

### 2. Install Required Libraries
Open your terminal or command prompt and run the following command to install the required dependencies:
```bash
pip install streamlit pandas curl_cffi plotly
```

### 3. Run the Application
Open your terminal or command prompt, navigate to the folder containing the script, and run the following command:
```bash
streamlit run app.py
```
This will automatically launch the dashboard in your default web browser (usually at `http://localhost:8501`).

---

## 🧠 Core Logic & Trading Algorithms

This application goes beyond raw data display by applying heuristic trading logic to generate insights. Here is a transparent breakdown of how the metrics and trend signals are calculated:

### 1. Support & Resistance Identification
* **Major Support / Resistance:** The application identifies structural boundaries by finding the strike with the **Highest Put Open Interest (Major Support)** and the **Highest Call Open Interest (Major Resistance)** across the active chain.
* **Immediate Support / Resistance:** It also calculates the nearest active S/R levels immediately above and below the current At-The-Money (ATM) strike to track intraday skirmishes. 

### 2. Max Pain Strike
Max Pain is the strike price at which option buyers will theoretically lose the most money, and option sellers (writers) will face the least financial pain upon expiry. 
* **Calculation:** The script loops through the active strikes, calculating the intrinsic value (loss) for all active Calls and Puts. The strike resulting in the absolute minimum combined loss is identified as the Max Pain point.

### 3. Trading Insight: Overall Trend
Determines the broader sentiment across the 11 active strikes.
* **Bullish 🟢:** If Total Put OI Addition > Total Call OI Addition **AND** Total Put Volume > Total Call Volume. (Indicates aggressive put writing across the board).
* **Bearish 🔴:** If Total Call OI Addition > Total Put OI Addition **AND** Total Call Volume > Total Put Volume. (Indicates aggressive call writing across the board).
* **Sideways 🟡:** If the data is mixed, contradictory, or indecisive.

### 4. Trading Insight: Trend at ATM (Immediate Action)
Analyzes the immediate next strike (At-The-Money) to detect localized momentum and execution timing.
* **Breakout ↗ 🟢:** Call writers are unwinding (negative change in CE OI, indicating panic) while Put writers are adding OI.
* **Breakdown ↘ 🔴:** Put writers are unwinding (negative change in PE OI, indicating panic) while Call writers are adding OI.
* **Resistance Building ↘ 🔴:** Strong Call OI addition backed by high Call Volume at the ATM strike.
* **Support Building ↗ 🟢:** Strong Put OI addition backed by high Put Volume at the ATM strike.

### 5. Trading Insight: Trend at Major S/R Boundaries
Analyzes behavior when the Nifty underlying price approaches within 50 points of the calculated Major Support or Resistance.
* **Reversal:** If price approaches Support/Resistance and writers at that strike **add** significant OI, it indicates strong defense and a likely reversal back into the range.
* **Breakout/Breakdown:** If price approaches Support/Resistance and writers at that strike **unwind** (negative OI change), it indicates the structural boundary is failing and a breakout/breakdown is highly probable.

### 6. Algorithmic Recommendation (Weighted Scoring)
The dashboard provides a final `LONG`, `SHORT`, or `WAIT` recommendation using a weighted confluence system:
* **Weighting:** 
  * **ATM Action** carries a **2x weight** (as it dictates immediate momentum).
  * **Overall Trend** carries a **1x weight**.
  * **S/R Boundary Action** carries a **1x weight**.
* **Triggers:** A combined Bullish score of 3 or higher triggers a **LONG** signal. A combined Bearish score of 3 or higher triggers a **SHORT** signal. If the signals are mixed, the app recommends **WAIT** to preserve capital.

---

## ⚠️ Disclaimer
This application is strictly for **educational and analytical purposes only**. Option trading carries significant financial risk. The signals and insights generated by this dashboard are based on heuristic mathematical models and do not constitute financial advice. Always perform your own due diligence and consult a certified financial advisor before executing trades.