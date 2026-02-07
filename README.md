# 🚗 Vehicle Maintenance Intelligence
> **Data-Driven Transparency for Car Ownership.**
> *Built by Revanth, Kamalaksha, & Raef.*

## 💡 The Problem
Car maintenance is broken and opaque.
1.  **"The Upsell":** Mechanics often recommend unnecessary services to pad profits.
2.  **"The Price Gap":** Drivers rarely know that an independent shop might be $200 cheaper than a dealership for the same work.
3.  **"The Data Void":** Generic manuals don't account for modern driving conditions or specific model defects (like the Ram TRX transmission issues).

## 🛠️ The Solution
**Vehicle Maintenance Intelligence** is a smart advisor that uses data science to:
* **Predict** exactly what maintenance is needed based on mileage and model-specific failure rates.
* **Compare** real-time quotes between Dealerships (High Trust/High Price) and Local Experts (High Savings).
* **Visualize** the market with an interactive "Cartoon Mode" map to make logistics fun and easy.

---

## ✨ Key Features 

### 1. 🧠 The "Smart Logic" Engine (Python + Pandas)
We don't just read a PDF. We ingest a raw maintenance dataset and use a **Python Logic Layer** to clean and modernize it in real-time.
* **Synthetic Oil Logic:** Automatically adjusts oil change intervals from 5k to 10k miles for modern engines.
* **Critical Alerts:** Flags "Severity: High" for specific high-performance models (e.g., TRX Diff Fluid at 15k miles) that generic manuals miss.

### 2. 🗺️ Geocentric "Cartoon" Map
A custom-styled Google Map implementation that strips away noise and focuses on what matters: **Location & Price**.
* **Dynamic Geocoding:** Converts any user Zip Code into real coordinates using `Geopy`.
* **Simulated Reality:** Mathematically places shops around the user's specific location to demonstrate hyper-local convenience.
* **Visuals:** Uses a custom JSON style to render a "Video Game/Sim City" look (Bright yellow roads, blue water).

### 3. 💸 Dynamic Quote Generation
Our backend algorithm calculates realistic price quotes based on:
* **Labor Rates:** Automatically adjusted for Dealer vs. Independent.
* **Luxury Tax:** Inputs like "BMW" or "Mercedes" trigger higher parts cost multipliers (1.5x).
* **Risk Factors:** Quotes include a "Trust Score" derived from shop reputation logic.

---

## 🏗️ Tech Stack

### **Frontend** (Client)
* **Framework:** React (Create React App) + TypeScript
* **Styling:** Tailwind CSS + Lucide Icons
* **Maps:** Google Maps JavaScript API + `@react-google-maps/api`
* **Vibes:** Custom "Retro" Map Style JSON

### **Backend** (Server)
* **Framework:** Python FastAPI
* **Database:** SQLite + SQLModel (ORM)
* **Data Processing:** Pandas (for CSV ingestion & logic application)
* **Geo-Location:** `geopy` (for Zip Code conversion)
* **AI/Logic:** OpenAI GPT-4o (Integration ready)

---

## 🚀 Getting Started

### Prerequisites
* Node.js & npm
* Python 3.9+
* Google Maps API Key
* OpenAI API Key

