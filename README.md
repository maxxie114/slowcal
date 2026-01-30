# San Francisco Small Business Intelligence Platform

A comprehensive hackathon project providing AI-powered intelligence for small businesses in San Francisco. The platform includes three main features: Risk Prediction Engine, Lease Negotiation Intelligence, and City Fee Analysis. This project aims to empower local entrepreneurs with data-driven insights.

## 🎯 Features

### 1. Risk Prediction Engine
- **ML-powered risk assessment** using Random Forest and Gradient Boosting models
- Predicts business failure risk based on:
  - Business age and activity
  - Permit history
  - Code enforcement complaints
  - Location status
- Real-time risk alerts and recommendations

### 2. Lease Negotiation Intelligence
- **Market analysis** by neighborhood
- **AI-generated negotiation strategies** using Nemotron LLM
- Comparable lease rate analysis
- Counter-proposal generation
- Customized talking points and concession suggestions

### 3. City Negotiation Intelligence
- **Fee analysis and breakdown** for permits and licenses
- **Waiver opportunity identification** (small business, nonprofit, new business)
- **Compliance requirement checklist** with AI-powered advisor
- Renewal schedule tracking

## 🛠️ Tech Stack

- **Python 3.10+**
- **DGX Spark with Nvidia Nemotron LLM** (via OpenAI-compatible API)
- **SF.gov Open Data API** for business, permit, and complaint data
- **Streamlit** for interactive web UI
- **scikit-learn, pandas, numpy** for ML and data processing
- **OpenAI client library** (configured for local Nemotron endpoint)

## 📁 Project Structure

```
sf-business-intelligence/
├── data/
│   ├── raw/              # Raw data from SF.gov API
│   ├── processed/         # Cleaned and merged datasets
│   └── models/            # Trained ML models
├── src/
│   ├── data_pipeline/     # Data download, cleaning, merging
│   ├── risk_engine/       # Risk prediction model and alerts
│   ├── lease_intelligence/ # Lease market analysis and AI strategies
│   ├── city_intelligence/  # Fee analysis and compliance
│   └── utils/             # Config and Nemotron client
├── app/
│   ├── streamlit_app.py   # Main Streamlit app
│   └── pages/             # Feature pages
├── notebooks/             # Data exploration notebooks
├── requirements.txt
├── setup.py
└── README.md
```

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher
- Access to SF.gov Open Data API (optional app token)
- Nemotron LLM running locally or remotely (for AI features)

### Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd sf-business-intelligence
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables (optional):**
   Create a `.env` file in the project root:
   ```bash
   SF_DATA_APP_TOKEN=your_sf_data_token
   NEMOTRON_BASE_URL=http://localhost:8000/v1
   NEMOTRON_API_KEY=local-nemotron-key
   NEMOTRON_MODEL=nvidia/nemotron-4-340b-instruct
   ```

### Running the Application

1. **Start the Streamlit app:**
   ```bash
   streamlit run app/streamlit_app.py
   ```

2. **Access the app:**
   Open your browser to `http://localhost:8501`

3. **Navigate features:**
   - **Risk Dashboard**: Train models and analyze business risk
   - **Lease Negotiation**: Get market analysis and AI strategies
   - **City Fees**: Analyze fees and check compliance

## 📊 Data Sources

The platform uses SF.gov Open Data API:
- **Business Registry** (`rqzj-sfat`): Business registration and license data
- **Building Permits** (`p4e4-5k3y`): Permit applications and approvals
- **Code Enforcement Complaints** (`ktji-gkfc`): Complaint records

## 🤖 AI Features (Nemotron LLM)

The platform uses Nemotron LLM for:
- Generating lease negotiation strategies
- Creating counter-proposals
- Providing compliance requirement advice

**Note:** Ensure Nemotron is running and accessible at the configured endpoint. The OpenAI client library is used with a local Nemotron endpoint.

## 🔧 Configuration

Edit `src/utils/config.py` to customize:
- SF.gov API endpoints and datasets
- Nemotron LLM endpoint and model
- Risk thresholds
- Data directories

## 📝 Usage Examples

### Risk Prediction
1. Navigate to "Risk Dashboard"
2. Train or load a risk model
3. Enter business information or analyze trends
4. Review risk scores and alerts

### Lease Negotiation
1. Navigate to "Lease Negotiation"
2. Enter business and lease information
3. Get market analysis
4. Generate AI-powered negotiation strategy
5. Create counter-proposals

### City Fees
1. Navigate to "City Fees"
2. Enter business information
3. Select required permits
4. Review fee breakdown and waiver opportunities
5. Check compliance requirements

## 🧪 Development

### Running Tests
```bash
pytest tests/
```

### Data Exploration
```bash
jupyter notebook notebooks/exploration.ipynb
```

### Code Formatting
```bash
black src/
flake8 src/
```

## 📄 License

This project is created for hackathon purposes.

## 🙏 Acknowledgments

- SF.gov Open Data for providing public datasets
- Nvidia for Nemotron LLM
- Streamlit for the UI framework

## 🔮 Future Enhancements

- Real-time data updates
- Integration with more SF.gov datasets
- Advanced ML models (deep learning)
- Mobile app version
- API endpoints for programmatic access
- Multi-city support

---

**Built for SF Small Businesses | Powered by DGX Spark & Nemotron LLM**
