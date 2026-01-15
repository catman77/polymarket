#!/bin/bash
#
# Install ML Dependencies for Polymarket AutoTrader
#
# This script installs all Python packages needed for machine learning analysis.
#

echo "========================================="
echo "Installing ML Dependencies"
echo "========================================="
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"
echo ""

# Core scientific stack
echo "Installing core scientific stack..."
pip3 install --upgrade pip
pip3 install numpy>=1.24.0
pip3 install pandas>=2.0.0
pip3 install scipy>=1.10.0

echo ""
echo "Installing machine learning libraries..."
pip3 install scikit-learn>=1.3.0

echo ""
echo "Installing XGBoost (optional but recommended)..."
pip3 install xgboost>=2.0.0 || echo "⚠️  XGBoost install failed (optional)"

echo ""
echo "Installing visualization libraries..."
pip3 install matplotlib>=3.7.0
pip3 install seaborn>=0.12.0

echo ""
echo "Verifying installations..."
python3 -c "import numpy; print(f'✅ NumPy {numpy.__version__}')"
python3 -c "import pandas; print(f'✅ Pandas {pandas.__version__}')"
python3 -c "import sklearn; print(f'✅ scikit-learn {sklearn.__version__}')"
python3 -c "import matplotlib; print(f'✅ Matplotlib {matplotlib.__version__}')"
python3 -c "import seaborn; print(f'✅ Seaborn {seaborn.__version__}')"
python3 -c "import xgboost; print(f'✅ XGBoost {xgboost.__version__}')" || echo "⚠️  XGBoost not installed (optional)"

echo ""
echo "========================================="
echo "Installation Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Ensure you have historical data:"
echo "     python3 analysis/historical_dataset.py --stats"
echo ""
echo "  2. Run the full ML analysis:"
echo "     python3 analysis/ml_full_analysis.py"
echo ""
