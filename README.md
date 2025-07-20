# Aave V2 Wallet Credit Scoring

## Overview
This repository contains a machine learning solution to assign credit scores (0–1000) to wallets interacting with the Aave V2 protocol on the Polygon network. Scores reflect wallet reliability, with higher scores for responsible users (frequent deposits/repayments, low risk) and lower scores for risky or bot-like behavior (high borrowing, liquidations).

## Methodology
- **Data**: JSON file with transaction records, including wallet address, action (`deposit`, `borrow`, `repay`, `liquidationcall`), amount, USD price, and timestamp.
- **Feature Engineering**:
  - **Counts**: Total transactions, number of deposits, borrows, repays, liquidations.
  - **Volumes**: USD value of deposits, borrows, repays.
  - **Ratios**: Deposit, borrow, repay, and liquidation ratios; debt-to-deposit ratio.
  - **Time Metrics**: Activity span (days), average time between transactions.
  - **Diversity**: Number of unique assets.
- **Model**: Random Forest Regressor trained on a synthetic target that rewards deposits, repayments, and longevity while penalizing liquidations and high leverage.
- **Scoring**: Scores are normalized to [0, 1000]. High scores indicate reliable behavior; low scores indicate risk.

## Architecture
1. **Data Loading**: JSON file is read into a Pandas DataFrame.
2. **Feature Engineering**: Transactions are aggregated by wallet to compute features.
3. **Model Training**: Features are scaled, and a Random Forest is trained on a synthetic target.
4. **Scoring**: Scores are predicted and saved to `wallet_scores.csv`.
5. **Visualization**: A histogram of scores is saved to `score_distribution.png`.

## Processing Flow
1. Place `user-wallet-transactions.json` in the repository root.
2. Run `CtrditScoring.py`:
   ```bash
   python CreditScoring.py
   ```
3. Outputs:
   - `wallet_scores.csv`: Wallet addresses and scores.
   - `score_distribution.png`: Score distribution histogram.

## Extensibility
- Add features (e.g., cross-protocol data) in `engineer_features`.
- Modify the synthetic target weights in `train_and_score` to adjust scoring logic.
- Swap Random Forest for other models (e.g., XGBoost).

## Dependencies
- Python 3.8+
- pandas, numpy, scikit-learn, matplotlib

## Outputs
- `wallet_scores.csv`: Wallet addresses and their credit scores.
- `score_distribution.png`: Histogram of score distribution.
