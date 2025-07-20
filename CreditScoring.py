import json
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt


with open('user-wallet-transactions.json', 'r') as f:
    data = json.load(f)

df = pd.DataFrame(data)
# Step 1: Flatten the 'actionData' dictionary
action_data_flat = pd.json_normalize(df['actionData'])

# Step 2: Concatenate with the main DataFrame
df = pd.concat([df.drop(columns=['actionData']), action_data_flat], axis=1)

# Step 3: Now you can safely run your assertion
expected_columns = ['userWallet', 'action', 'txHash', 'timestamp', 'assetSymbol', 'assetPriceUSD']
assert all(col in df.columns for col in expected_columns), "Missing required columns"


def engineer_features(df):
    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s',errors='coerce')

    # Ensure numeric types for calculations
    df['amount'] = df['amount'].astype(float)
    df['assetPriceUSD'] = df['assetPriceUSD'].astype(float)

    # USD value per transaction
    df['usd_value'] = df['amount'] * df['assetPriceUSD']

    # Group by wallet to create features
    wallet_features = df.groupby('userWallet').agg({
        'action': [
            ('total_txs', 'count'),
            ('num_deposits', lambda x: (x == 'deposit').sum()),
            ('num_borrows', lambda x: (x == 'borrow').sum()),
            ('num_repays', lambda x: (x == 'repay').sum()),
            ('num_liquidations', lambda x: (x == 'liquidationcall').sum())
        ],
        'usd_value': [
            ('total_deposit_usd', lambda x: x.where(df.loc[x.index, 'action'] == 'deposit', 0).sum()),
            ('total_borrow_usd', lambda x: x.where(df.loc[x.index, 'action'] == 'borrow', 0).sum()),
            ('total_repay_usd', lambda x: x.where(df.loc[x.index, 'action'] == 'repay', 0).sum())
        ],
        'assetSymbol': [('num_assets', 'nunique')],
        'timestamp': [
            ('time_span_days', lambda x: (x.max() - x.min()).days),
            ('avg_time_between_txs', lambda x: (x.max() - x.min()).total_seconds() / max(1, (x.count() - 1)))
        ]
    }).reset_index()

    # Flatten column names
    wallet_features.columns = ['_'.join(col).strip() if isinstance(col, tuple) else col for col in wallet_features.columns.values]

    # Calculate additional features
    wallet_features['deposit_ratio'] = wallet_features['action_num_deposits'] / wallet_features['action_total_txs']
    wallet_features['borrow_ratio'] = wallet_features['action_num_borrows'] / wallet_features['action_total_txs']
    wallet_features['repay_ratio'] = wallet_features['action_num_repays'] / wallet_features['action_total_txs']
    wallet_features['liquidation_ratio'] = wallet_features['action_num_liquidations'] / wallet_features['action_total_txs']

    wallet_features['debt_to_deposit'] = wallet_features['usd_value_total_borrow_usd'] / (
        wallet_features['usd_value_total_deposit_usd'] + 1e-6)

    # Fill NaN values
    wallet_features.fillna(0, inplace=True)
    return wallet_features

def train_and_score(df):
    features = [
        'action_total_txs', 'action_num_deposits', 'action_num_borrows', 'action_num_repays',
        'action_num_liquidations', 'usd_value_total_deposit_usd',
        'usd_value_total_borrow_usd', 'usd_value_total_repay_usd',
        'assetSymbol_num_assets', 'timestamp_time_span_days',
        'timestamp_avg_time_between_txs', 'deposit_ratio', 'borrow_ratio',
        'repay_ratio', 'liquidation_ratio', 'debt_to_deposit'
    ] 
    X = df[features]
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Synthetic target
    synthetic_target_v2 = (
        0.35 * df['repay_ratio'] +  
        0.20 * df['deposit_ratio'] +
        0.10 * np.log1p(df['usd_value_total_deposit_usd']) +
        0.05 * np.log1p(df['timestamp_time_span_days']) - 
        0.10 * df['debt_to_deposit'] -
        0.20 * df['liquidation_ratio'] 
    )
    synthetic_target_v2 = (synthetic_target_v2 - synthetic_target_v2.min()) / (synthetic_target_v2.max() - synthetic_target_v2.min()) * 1000

    # Train Random Forest
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_scaled, synthetic_target_v2)
    
    # Cross-validation
    scores = cross_val_score(model, X_scaled, synthetic_target_v2, cv=5, scoring='r2')
    print(f"Cross-validation R² scores: {scores.mean():.3f} (±{scores.std():.3f})")
    
    # Predict scores
    df['credit_score'] = model.predict(X_scaled).clip(0, 1000)
    return df[['userWallet_', 'credit_score']]

# Generate score distribution plot
def plot_score_distribution(scores_df):
    plt.figure(figsize=(10, 6))
    plt.hist(scores_df['credit_score'], bins=range(0, 1100, 100), edgecolor='black')
    plt.xticks(range(0, 1001, 100))
    plt.title('Credit Score Distribution')
    plt.xlabel('Credit Score')
    plt.ylabel('Number of Wallets')
    plt.savefig('score_distribution.png')
    plt.close()


# Main execution
def main(file_path):
    #df = load_data(file_path)
    features_df = engineer_features(df)
    scores_df = train_and_score(features_df)
    scores_df.to_csv('wallet_scores.csv', index=False)
    plot_score_distribution(scores_df)
    print("Scores saved to wallet_scores.csv and distribution plot saved to score_distribution.png")

if __name__ == "__main__":
    file_path = "user-wallet-transactions.json"  
    main(file_path)
