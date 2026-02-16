# Trading212 FIFO Tax Calculator for Germany 🇩🇪

A Python script to calculate German FIFO (First In, First Out) tax values for Trading212 transactions, generating values for **Anlage KAP INV** (Investment Income Tax Form).

[![Python Version](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Trading212](https://img.shields.io/badge/Broker-Trading212-00D09C)](https://www.trading212.com/)

## 🎯 Purpose

This script helps German taxpayers calculate capital gains from Trading212 ETF and stock transactions using the mandatory FIFO (First In, First Out) method required by German tax law. It generates the exact values needed for **Anlage KAP INV** lines 50-54.

**⚠️ Important:** This tool is for informational purposes only. Always verify calculations with a tax advisor (Steuerberater).

## ✨ Features

- ✅ **FIFO Calculation**: Correctly implements German First-In-First-Out methodology
- ✅ **Multi-Currency Support**: Handles USD and EUR transactions with proper exchange rate conversion
- ✅ **Currency Fee Handling**: Correctly processes Trading212's currency conversion fees
- ✅ **Multi-Security Support**: Calculates taxes for all securities at once or individually
- ✅ **Detailed Breakdown**: Shows which buy lots were matched to each sale (audit trail)
- ✅ **High Precision**: Uses Decimal arithmetic to avoid floating-point errors
- ✅ **Anlage KAP INV Output**: Generates exact values for lines 50-54

## 📋 Prerequisites

- Python 3.7 or higher
- Trading212 UK Ltd CSV export (full transaction history)
- Basic command line knowledge

## 🚀 Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/trading212-fifo-tax-calculator.git
cd trading212-fifo-tax-calculator
```

2. No additional dependencies required (uses Python standard library only)

## 📥 Exporting Data from Trading212

**Critical:** You must export your **complete transaction history** from account opening, not just the current tax year.

1. Log in to Trading212
2. Go to **History** → **Transactions**
3. Click **Export** button (top right)
4. Select date range: **From account opening** to **End of tax year**
5. Format: CSV
6. Save the file (e.g., `Trading212_Export.csv`)

## 🎮 Usage

### Basic Usage

Run the script and follow the prompts:

```bash
python3 trading212_fifo_calculator_FIXED.py
```

The script will ask for:
1. Path to your CSV file
2. Whether to calculate for all securities or just one (by ISIN)

### Example Session

```
Enter path to Trading212 CSV file: ./Trading212_Export.csv

✓ Found 56 different securities

What would you like to calculate?
  1 - Calculate for a specific security (enter ISIN)
  2 - Calculate for ALL securities

Enter your choice (1 or 2): 2
```

### Output

The script generates:

```
═══════════════════════════════════════════════════════════════
SECURITY: WisdomTree S&P 500 3x Leveraged (3USL)
ISIN: IE00B7Y34M31
═══════════════════════════════════════════════════════════════

ANLAGE KAP INV - TAX FORM VALUES

Zeile 50 - Veräußerungspreis:       41,122.81 EUR (Gross sales proceeds)
Zeile 51 - Anschaffungskosten:      22,421.56 EUR (Acquisition costs via FIFO)
Zeile 52 - Veräußerungskosten:          61.24 EUR (Sales costs/fees)
Zeile 53 - Vorabpauschalen:              0.00 EUR ⚠ (YOU MUST ADD MANUALLY)
Zeile 54 - Veräußerungsgewinn:      18,640.01 EUR (Capital gain)
```

## 📊 Anlage KAP INV Lines Explained

| Line | German Name | Description |
|------|-------------|-------------|
| **50** | Veräußerungspreis | Gross sales proceeds (Total EUR received + currency fees) |
| **51** | Anschaffungskosten | Acquisition costs calculated via FIFO |
| **52** | Veräußerungskosten | Sales costs (currency conversion fees on sales) |
| **53** | Vorabpauschalen | Advance lump sum tax (must be added manually for accumulating ETFs) |
| **54** | Veräußerungsgewinn | Capital gain (Line 50 - 51 - 52 - 53) |

## 🔍 How It Works

### FIFO Method

The script implements German FIFO (First In, First Out):

1. **Chronological Ordering**: All buy transactions are sorted by date (oldest first)
2. **Lot Matching**: When you sell shares, the script matches them against the oldest remaining buy lots
3. **Cost Basis**: The acquisition cost is the sum of costs from matched buy lots
4. **Remaining Shares**: After each sale, remaining shares in each lot are tracked

### Example

```
Buys:
- 2023-01-01: 10 shares @ €100 = €1,000
- 2023-06-01: 10 shares @ €120 = €1,200

Sell:
- 2023-12-01: 15 shares @ €150 = €2,250

FIFO Calculation:
- Use all 10 shares from 2023-01-01 (€1,000)
- Use 5 shares from 2023-06-01 (€600)
- Total cost: €1,600
- Capital gain: €2,250 - €1,600 = €650
```

### Currency Fee Handling

**Trading212 Format (verified):**
- **BUY transactions**: `Total EUR` includes the currency conversion fee
- **SELL transactions**: `Total EUR` + `Currency conversion fee` = Gross proceeds

The script correctly handles this asymmetry.

## ⚠️ Important Notes

### What the Script Does NOT Do

- ❌ Does not calculate Vorabpauschale (advance lump sum tax) for accumulating ETFs
- ❌ Does not apply Teilfreistellung (partial exemption, typically 30% for equity ETFs)
- ❌ Does not apply Sparer-Pauschbetrag (€1,000 tax-free allowance)
- ❌ Does not handle Verlustverrechnungstopf (loss offset pot) across tax years

**These adjustments must be made in your tax software (Elster, WISO, etc.)**

### Vorabpauschale

For **accumulating ETFs** (like VWCE), you must:
1. Calculate Vorabpauschale separately (not in Trading212 data)
2. Enter it manually in Line 53 in your tax software
3. Your tax software will subtract it from Line 54

### Data Accuracy

Always verify:
- ✅ Export includes ALL transactions from account opening
- ✅ No missing buy transactions (script will error if you try to sell shares you don't have)
- ✅ Cross-check a few calculations manually
- ✅ Compare against Trading212 statements

## 🐛 Troubleshooting

### "Insufficient shares" Error

**Problem:** Script shows `CRITICAL ERROR: Insufficient shares for sale`

**Solution:** Your CSV export is incomplete. Export again starting from your account opening date, not just the current tax year.

### Different Values Than Expected

1. Check if you're comparing gross vs. net proceeds
2. Verify Vorabpauschale is not included (must be added separately)
3. Ensure your CSV includes all historical transactions

### DateTime Parsing Error

The script supports multiple Trading212 datetime formats. If you get an error, please open an issue with your CSV format.

## 📁 CSV Format

Expected Trading212 CSV columns:

```
Action, Time, ISIN, Ticker, Name, ID, No. of shares, 
Price / share, Currency (Price / share), Exchange rate, 
Result, Currency (Result), Total, Currency (Total), 
Currency conversion fee, Currency (Currency conversion fee)
```

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/improvement`)
3. Test your changes thoroughly
4. Commit with clear messages
5. Open a Pull Request

### Areas for Contribution

- Vorabpauschale calculation integration
- Support for other brokers (Scalable Capital, Trade Republic, etc.)
- GUI interface
- Automated testing suite
- Support for more complex scenarios (stock splits, dividends, etc.)

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚖️ Legal Disclaimer

**THIS SOFTWARE IS PROVIDED FOR INFORMATIONAL PURPOSES ONLY.**

- Not financial or tax advice
- No warranty of accuracy or completeness
- Author not liable for any tax-related consequences
- Always consult a qualified Steuerberater (tax advisor)
- Verify all calculations before filing taxes
- German tax law is complex and subject to change

You use this tool at your own risk.

## 🙏 Acknowledgments

- Inspired by the need for accurate German FIFO tax calculations
- Thanks to the Trading212 and German expat communities for feedback
- Built with ❤️ for fellow German taxpayers dealing with foreign brokers

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/trading212-fifo-tax-calculator/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/trading212-fifo-tax-calculator/discussions)

## 🔗 Related Resources

- [German Federal Tax Office (Bundesfinanzministerium)](https://www.bundesfinanzministerium.de/)
- [ELSTER (German Tax Filing)](https://www.elster.de/)
- [Trading212](https://www.trading212.com/)

---

**⭐ If this tool helped you, please star the repository!**

Made with 🇩🇪 for German taxpayers | Last updated: 2025
