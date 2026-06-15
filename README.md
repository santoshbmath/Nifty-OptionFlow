# 🌊 Nifty OptionFlow | Live OI, Volume & Breakout Intelligence

A real-time, interactive Streamlit dashboard that fetches live Option Chain data directly from the National Stock Exchange (NSE) of India. The application bypasses basic bot protections to deliver live insights, visual data graphs, and automated trading signals based on Open Interest (OI) and Volume dynamics.

## ✨ Features

* **Live NSE Data Fetching:** Uses `curl_cffi` to bypass Akamai bot-protection and fetch live JSON data.
* **Auto-Expiry Calculation:** Automatically determines the next upcoming weekly expiry date.
* **Dynamic Data Filtering:** Isolates the active trading zone by filtering 11 strikes (+/- 5 strikes around the At-The-Money strike).
* **Automated Insights:** Generates human-readable market direction signals (Overall, ATM, and S/R Boundaries) with color-coded trend indicators.
* **Interactive Visualizations:** Renders side-by-side Plotly bar charts for Total OI, Change in OI, and Traded Volume.
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
### 3. Run the application
Open your terminal or command prompt and run the following command
```bash
streamlit run app.py
```