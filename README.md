# BIST Profile Analysis

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/flask-2.3+-green.svg)](https://flask.palletsprojects.com/)
[![CI/CD](https://github.com/Ataberkan/BIST_Profiling/workflows/CI/CD%20Pipeline/badge.svg)](https://github.com/your-username/BIST_Profiling/actions)


> An advanced data analysis and visualization platform that provides artificial intelligence-supported investment analysis and risk profiling for BIST (Borsa Istanbul) stocks.

## 🎯 Project Overview

This project develops a comprehensive analytical tool that enables smart investment decisions by analyzing BIST stocks using machine learning algorithms. The platform groups stocks by risk-return characteristics and helps users determine the most suitable investment strategy.

## ✨ Key Features

### 📊 **Advanced Data Analysis**
- K-Means clustering algorithm for stock grouping
- Risk-return analysis with statistical metrics
- Technical and fundamental analysis tools
- Sector-based performance analysis

### 🤖 **Machine Learning Integration**
- Automated stock clustering
- Risk profile determination
- Predictive analytics for price movements
- AI-powered investment recommendations

### 💼 **Investment Tools**
- Interactive portfolio builder
- Real-time risk profiling
- Stock comparison tools
- Market observation dashboard

### 📈 **Data Visualization**
- Interactive charts and graphs
- Real-time market data display
- Risk heat maps
- Cluster analysis visualizations

## 🏗️ Technical Architecture

### Backend
- **Flask**: Main web framework
- **SQLAlchemy**: Database ORM
- **Pandas & NumPy**: Data processing
- **Scikit-learn**: Machine learning algorithms
- **Matplotlib & Plotly**: Data visualization

### Frontend
- **HTML5 & CSS3**: Modern responsive design
- **JavaScript & Alpine.js**: Interactive user interface
- **TailwindCSS**: Utility-first CSS framework
- **Chart.js**: Interactive data visualization

### Database
- **SQLite**: Development database
- **PostgreSQL**: Production database support

## 📁 Project Structure

```
BIST_Profiling/
├── src/
│   ├── app/                    # Main Flask application
│   │   ├── __init__.py        # App factory and configuration
│   │   ├── models.py          # Database models
│   │   ├── routes.py          # Web routes
│   │   ├── api.py            # API endpoints
│   │   ├── config.py         # Configuration settings
│   │   ├── default_data.py   # Default data definitions
│   │   ├── templates/        # HTML templates
│   │   └── static/           # CSS, JS, images
│   ├── analysis/             # Data analysis modules
│   │   ├── data_analysis_preprocessing.py
│   │   └── feature_engineering.py
│   ├── models/               # Machine learning models
│   │   └── clustering_model.py
│   ├── data/                 # Data files
│   │   ├── *.csv             # Stock data files
│   │   └── load_real_data.py # Data loading scripts
│   └── scraping/             # Web scraping tools
│       └── scrape_uzmanpara.py
├── instance/                 # Database files
├── logs/                     # Application logs
├── requirements.txt          # Python dependencies
├── run_app.py               # Application startup
└── README.md
```

## 🚀 Installation and Setup

### Requirements
- Python 3.8+
- pip package manager
- Git

### Quick Start

1. **Clone the repository**
```bash
git clone <repository-url>
cd BIST_Profiling
```

2. **Create virtual environment**
```bash
python -m venv bist_env
source bist_env/bin/activate  # Linux/Mac
# or
bist_env\Scripts\activate     # Windows
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Run the application**
```bash
python run_app.py
```

5. **Access the application**
- Open your browser and go to: `http://localhost:5000`

## 🎮 Usage

### 1. Risk Profiling
- Complete the interactive risk assessment
- Get your investor profile (Conservative, Balanced, Growth-Oriented, Aggressive)
- View recommended stock clusters based on your profile

### 2. Stock Analysis
- Explore BIST-30 stocks with detailed analytics
- Filter by cluster, volatility, and other metrics
- View individual stock details and historical data

### 3. Cluster Analysis
- Examine AI-generated stock clusters
- Understand risk-return characteristics
- Compare cluster performances

### 4. Market Observation
- Real-time market updates
- News and analysis
- Sector performance tracking

## 🔧 Configuration

### Environment Variables
```bash
# Database URL
DATABASE_URL=sqlite:///instance/bist_profiling.db

# Secret key for sessions
SECRET_KEY=your-secret-key-here

# API configuration
API_KEY=your-api-key
```

### Configuration File
Detailed settings can be modified in `src/app/config.py`

## 📊 Data Sources

- **BIST Market Data**: Official market data and historical prices
- **Financial Indicators**: P/E ratios, volatility, beta values
- **Technical Indicators**: Moving averages, RSI, MACD
- **Sector Information**: Industry classifications and sector performance

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the project
2. Create a feature branch (`git checkout -b feature/NewFeature`)
3. Commit your changes (`git commit -m 'Add: New feature'`)
4. Push to branch (`git push origin feature/NewFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License. See `LICENSE` file for details.

## 🐛 Known Issues

- Some data may have delays due to API limitations
- Mobile responsiveness can be improved
- Additional technical indicators are being developed

## 🔮 Future Plans

- [ ] Real-time data integration
- [ ] Mobile application development
- [ ] Advanced machine learning models
- [ ] Social trading features
- [ ] Options and derivatives analysis

## 📞 Support

For questions and support:
- Create an Issue on GitHub
- Contact: [email]
- Documentation: [wiki/docs link]

## 🙏 Acknowledgments

- BIST for market data
- Open source community for tools and libraries
- Contributors and testers

---

**⚠️ Disclaimer**: This tool is for educational and informational purposes only. It does not constitute investment advice. Always consult with a qualified financial advisor before making investment decisions. 
