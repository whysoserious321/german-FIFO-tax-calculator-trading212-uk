#!/usr/bin/env python3
"""
German FIFO Tax Calculator for Trading212 CSV Files
Calculates values for Anlage KAP INV (Investment Income Tax Form)

This script implements the mandatory German FIFO (First In, First Out) method
for calculating capital gains tax on securities sales.

Lines calculated:
- Line 49: Anzahl der veräußerten Anteile (Total shares sold)
- Line 50: Veräußerungspreis (Gross sales proceeds)
- Line 51: Anschaffungskosten (Acquisition costs via FIFO)
- Line 52: Veräußerungskosten (Sales costs/fees)
- Line 53: Vorabpauschalen (User must add manually - not in Trading212 data)
- Line 54: Veräußerungsgewinn (Capital gain = Line 50 - 51 - 52 - 53)
"""

import csv
from datetime import datetime
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

class Transaction:
    """Represents a single Trading212 transaction."""
    
    def __init__(self, row):
        self.action = row['Action'].strip()
        
        # Trading212 exports have different datetime formats, try multiple
        time_str = row['Time'].strip()
        datetime_formats = [
            "%Y-%m-%d %H:%M:%S",  # 2025-01-29 10:09:16
            "%Y-%m-%d %H:%M",     # 2025-12-30 8:46
        ]
        
        self.time = None
        for fmt in datetime_formats:
            try:
                self.time = datetime.strptime(time_str, fmt)
                break
            except ValueError:
                continue
        
        if self.time is None:
            raise ValueError(f"Could not parse datetime: {time_str}")
        
        self.isin = row['ISIN'].strip()
        self.ticker = row['Ticker'].strip()
        self.name = row['Name'].strip()
        
        # Parse numeric values carefully
        self.shares = self._parse_decimal(row['No. of shares'])
        self.price_per_share = self._parse_decimal(row['Price / share'])
        self.currency = row['Currency (Price / share)'].strip()
        self.exchange_rate = self._parse_decimal(row['Exchange rate'])
        self.total_eur = self._parse_decimal(row['Total'])
        
        # Currency conversion fee (in EUR)
        fee_str = row['Currency conversion fee'].strip()
        self.currency_fee = self._parse_decimal(fee_str) if fee_str else Decimal('0')
        
        # Calculate total cost/proceeds including fees
        if self.is_buy():
            # For buys: Total EUR already includes currency fee (Trading212 format)
            self.acquisition_cost_total = self.total_eur
            self.cost_per_share = self.acquisition_cost_total / self.shares if self.shares > 0 else Decimal('0')
        else:  # sell
            # For sells: Currency fee is separate, add it to get gross proceeds
            self.gross_proceeds = self.total_eur + self.currency_fee
            self.sales_costs = self.currency_fee
    
    def is_buy(self):
        return self.action.lower() == 'market buy'
    
    def is_sell(self):
        return self.action.lower() == 'market sell'
    
    @staticmethod
    def _parse_decimal(value_str):
        """Parse a string to Decimal, handling empty strings."""
        if not value_str or value_str.strip() == '':
            return Decimal('0')
        return Decimal(str(value_str).strip())


class BuyLot:
    """Represents a lot of shares from a single purchase, tracking remaining shares for FIFO."""
    
    def __init__(self, transaction):
        if not transaction.is_buy():
            raise ValueError("BuyLot can only be created from buy transactions")
        
        self.transaction = transaction
        self.purchase_date = transaction.time
        self.original_shares = transaction.shares
        self.remaining_shares = transaction.shares
        self.cost_per_share = transaction.cost_per_share
    
    def consume_shares(self, shares_needed):
        """
        Consume shares from this lot for a sale (FIFO).
        Returns: (shares_taken, cost_of_shares_taken)
        """
        if shares_needed <= 0:
            return Decimal('0'), Decimal('0')
        
        shares_taken = min(shares_needed, self.remaining_shares)
        cost = shares_taken * self.cost_per_share
        self.remaining_shares -= shares_taken
        
        return shares_taken, cost
    
    def __repr__(self):
        return f"BuyLot(date={self.purchase_date.date()}, remaining={self.remaining_shares}/{self.original_shares})"


def parse_trading212_csv(file_path):
    """
    Parse Trading212 CSV file and group transactions by ISIN.
    Returns: dict of {ISIN: [Transaction, ...]}
    """
    transactions_by_isin = defaultdict(list)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    # Skip non-market transactions
                    action = row['Action'].strip().lower()
                    if action not in ['market buy', 'market sell']:
                        continue
                    
                    # Skip rows with missing critical data
                    if not row['No. of shares'].strip() or not row['Total'].strip():
                        print(f"Warning: Skipping row {row_num} - missing shares or total")
                        continue
                    
                    trans = Transaction(row)
                    transactions_by_isin[trans.isin].append(trans)
                    
                except Exception as e:
                    print(f"Warning: Error parsing row {row_num}: {e}")
                    continue
        
        if not transactions_by_isin:
            raise ValueError("No valid transactions found in CSV file")
        
        return transactions_by_isin
        
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except Exception as e:
        raise Exception(f"Error reading CSV: {e}")


def calculate_fifo_for_security(transactions):
    """
    Calculate FIFO capital gains for a single security.
    
    Returns dict with:
    - line_50: Veräußerungspreis (gross sales proceeds)
    - line_51: Anschaffungskosten (acquisition costs)
    - line_52: Veräußerungskosten (sales costs)
    - line_53: Vorabpauschalen (must be added manually)
    - line_54: Veräußerungsgewinn (capital gain)
    - details: list of individual sales with FIFO matching details
    """
    
    # Separate and sort transactions by date
    buys = sorted([t for t in transactions if t.is_buy()], key=lambda x: x.time)
    sells = sorted([t for t in transactions if t.is_sell()], key=lambda x: x.time)
    
    if not sells:
        return {
            'line_49': Decimal('0'),
            'line_50': Decimal('0'),
            'line_51': Decimal('0'),
            'line_52': Decimal('0'),
            'line_53': Decimal('0'),
            'line_54': Decimal('0'),
            'details': [],
            'message': 'No sales found for this security'
        }
    
    # Create FIFO queue of buy lots
    buy_lots = [BuyLot(buy) for buy in buys]
    
    # Accumulators for Anlage KAP INV lines
    total_line_49 = Decimal('0')  # Anzahl der veräußerten Anteile
    total_line_50 = Decimal('0')  # Veräußerungspreis
    total_line_51 = Decimal('0')  # Anschaffungskosten
    total_line_52 = Decimal('0')  # Veräußerungskosten
    
    sell_details = []
    
    # Process each sale using FIFO
    for sell in sells:
        shares_to_sell = sell.shares
        acquisition_cost_for_this_sale = Decimal('0')
        fifo_matches = []
        
        # Match this sale against buy lots (FIFO order)
        lot_index = 0
        while shares_to_sell > Decimal('0.0001') and lot_index < len(buy_lots):  # 0.0001 for rounding tolerance
            lot = buy_lots[lot_index]
            
            if lot.remaining_shares < Decimal('0.0001'):  # Lot exhausted
                lot_index += 1
                continue
            
            # Take shares from this lot
            shares_taken, cost_of_shares = lot.consume_shares(shares_to_sell)
            
            acquisition_cost_for_this_sale += cost_of_shares
            shares_to_sell -= shares_taken
            
            fifo_matches.append({
                'buy_date': lot.purchase_date,
                'shares': shares_taken,
                'cost_per_share': lot.cost_per_share,
                'total_cost': cost_of_shares
            })
            
            # Move to next lot if this one is exhausted
            if lot.remaining_shares < Decimal('0.0001'):
                lot_index += 1
        
        # Check if we have enough shares
        if shares_to_sell > Decimal('0.0001'):
            raise ValueError(
                f"CRITICAL ERROR: Insufficient shares for sale on {sell.time.date()}\n"
                f"Trying to sell {sell.shares} shares but only {sell.shares - shares_to_sell:.8f} available.\n"
                f"Please check your CSV file for missing buy transactions."
            )
        
        # Add to totals
        total_line_49 += sell.shares
        total_line_50 += sell.gross_proceeds
        total_line_51 += acquisition_cost_for_this_sale
        total_line_52 += sell.sales_costs
        
        # Calculate gain for this individual sale
        gain_for_this_sale = sell.gross_proceeds - acquisition_cost_for_this_sale - sell.sales_costs
        
        sell_details.append({
            'sale_date': sell.time,
            'shares_sold': sell.shares,
            'gross_proceeds': sell.gross_proceeds,
            'acquisition_cost': acquisition_cost_for_this_sale,
            'sales_costs': sell.sales_costs,
            'gain': gain_for_this_sale,
            'fifo_matches': fifo_matches
        })
    
    # Line 54 = Line 50 - Line 51 - Line 52 - Line 53
    # (Line 53 must be added manually by user)
    total_line_54 = total_line_50 - total_line_51 - total_line_52  # - line_53 (user adds manually)
    
    return {
        'line_49': total_line_49,
        'line_50': total_line_50,
        'line_51': total_line_51,
        'line_52': total_line_52,
        'line_53': Decimal('0'),  # User must add Vorabpauschalen manually
        'line_54': total_line_54,
        'details': sell_details
    }


def format_currency(value):
    """Format Decimal as currency string."""
    return f"{value:>16,.2f} EUR"


def print_results(isin, security_name, ticker, result):
    """Print formatted results for Anlage KAP INV."""
    
    print("\n" + "=" * 85)
    print(f"SECURITY: {security_name} ({ticker})")
    print(f"ISIN: {isin}")
    print("=" * 85)
    
    if result.get('message'):
        print(f"\n{result['message']}")
        return
    
    print("\n" + "█" * 85)
    print("█" + " " * 83 + "█")
    print("█" + " " * 20 + "ANLAGE KAP INV - TAX FORM VALUES" + " " * 29 + "█")
    print("█" + " " * 83 + "█")
    print("█" * 85)
    
    print(f"\nZeile 49 - Anzahl veräußerter Anteile: {result['line_49']:>10.8f}")
    print(f"            (Total shares sold)")

    print(f"\nZeile 50 - Veräußerungspreis:    {format_currency(result['line_50'])}")
    print(f"            (Gross sales proceeds)")
    
    print(f"\nZeile 51 - Anschaffungskosten:   {format_currency(result['line_51'])}")
    print(f"            (Acquisition costs via FIFO)")
    
    print(f"\nZeile 52 - Veräußerungskosten:   {format_currency(result['line_52'])}")
    print(f"            (Sales costs/fees)")
    
    print(f"\nZeile 53 - Vorabpauschalen:      {format_currency(result['line_53'])}  ⚠")
    print(f"            (YOU MUST ADD THIS MANUALLY - not in Trading212 data)")
    
    print(f"\nZeile 54 - Veräußerungsgewinn:   {format_currency(result['line_54'])}")
    print(f"            (Capital gain, before Vorabpauschalen adjustment)")
    
    print("\n" + "─" * 85)
    print("⚠  IMPORTANT: Zeile 54 does not include Vorabpauschalen (Line 53).")
    print("   If you have accumulating ETFs, you must subtract Vorabpauschalen")
    print("   from Line 54 manually in your tax software.")
    print("─" * 85)
    
    # Detailed breakdown
    if result['details']:
        print(f"\n{'─' * 85}")
        print(f"DETAILED BREAKDOWN - {len(result['details'])} Sale(s)")
        print(f"{'─' * 85}")
        
        for i, detail in enumerate(result['details'], 1):
            print(f"\n╔{'═' * 83}╗")
            print(f"║ Sale #{i:<77}║")
            print(f"╠{'═' * 83}╣")
            print(f"║ Date: {detail['sale_date'].strftime('%Y-%m-%d %H:%M:%S'):<73}║")
            print(f"║ Shares sold: {detail['shares_sold']:<68}║")
            print(f"╠{'─' * 83}╣")
            print(f"║ Gross proceeds (Line 50): {detail['gross_proceeds']:>15,.2f} EUR{' ' * 35}║")
            print(f"║ Acquisition costs (Line 51): {detail['acquisition_cost']:>12,.2f} EUR{' ' * 35}║")
            print(f"║ Sales costs (Line 52): {detail['sales_costs']:>18,.2f} EUR{' ' * 35}║")
            print(f"║ ────────────────────────────────────────────{' ' * 35}║")
            print(f"║ Gain for this sale: {detail['gain']:>23,.2f} EUR{' ' * 35}║")
            print(f"╠{'═' * 83}╣")
            print(f"║ FIFO Matching - Used {len(detail['fifo_matches'])} buy lot(s):{' ' * 45}║")
            
            for j, match in enumerate(detail['fifo_matches'], 1):
                print(f"║   Lot {j}: Bought on {match['buy_date'].strftime('%Y-%m-%d'):<55}║")
                print(f"║         {match['shares']:.8f} shares @ {match['cost_per_share']:.6f} EUR/share{' ' * 28}║")
                print(f"║         Total cost: {match['total_cost']:.2f} EUR{' ' * 49}║")
            
            print(f"╚{'═' * 83}╝")


def main():
    """Main entry point."""
    
    print("=" * 85)
    print("║" + " " * 83 + "║")
    print("║" + " " * 15 + "GERMAN FIFO TAX CALCULATOR FOR TRADING212" + " " * 26 + "║")
    print("║" + " " * 83 + "║")
    print("=" * 85)
    print("\nThis script calculates values for Anlage KAP INV (Investment Income Tax Form)")
    print("using the mandatory German FIFO (First In, First Out) method.\n")
    
    # Get CSV file path
    file_path = input("Enter path to Trading212 CSV file: ").strip()
    
    # Remove quotes if user copy-pasted path with quotes
    file_path = file_path.strip('"').strip("'")
    
    try:
        print(f"\nReading CSV file: {file_path}")
        transactions_by_isin = parse_trading212_csv(file_path)
        
        print(f"\n✓ Successfully parsed CSV file")
        print(f"✓ Found {len(transactions_by_isin)} different securit{'y' if len(transactions_by_isin) == 1 else 'ies'}:\n")
        
        # List all securities
        securities_list = []
        for i, (isin, trans_list) in enumerate(sorted(transactions_by_isin.items()), 1):
            first_trans = trans_list[0]
            num_buys = sum(1 for t in trans_list if t.is_buy())
            num_sells = sum(1 for t in trans_list if t.is_sell())
            
            securities_list.append((isin, first_trans.name, first_trans.ticker))
            print(f"  {i}. {first_trans.name} ({first_trans.ticker})")
            print(f"     ISIN: {isin}")
            print(f"     Transactions: {num_buys} buy(s), {num_sells} sell(s)\n")
        
        # Ask user what to calculate
        print("─" * 85)
        print("\nWhat would you like to calculate?")
        print("  1 - Calculate for a specific security (enter ISIN)")
        print("  2 - Calculate for ALL securities")
        
        choice = input("\nEnter your choice (1 or 2): ").strip()
        
        if choice == '1':
            isin_input = input("\nEnter ISIN: ").strip()
            
            if isin_input not in transactions_by_isin:
                print(f"\n✗ ERROR: ISIN '{isin_input}' not found in CSV file.")
                print("  Available ISINs:")
                for isin, name, ticker in securities_list:
                    print(f"    - {isin} ({name})")
                return
            
            securities_to_process = [(isin_input, transactions_by_isin[isin_input])]
        
        elif choice == '2':
            securities_to_process = [(isin, trans_list) 
                                    for isin, trans_list in transactions_by_isin.items()]
        else:
            print("\n✗ Invalid choice. Please enter 1 or 2.")
            return
        
        # Process each selected security
        for isin, transactions in securities_to_process:
            first_trans = transactions[0]
            
            try:
                result = calculate_fifo_for_security(transactions)
                print_results(isin, first_trans.name, first_trans.ticker, result)
                
            except Exception as e:
                print(f"\n✗ ERROR processing {first_trans.name} ({isin}):")
                print(f"  {str(e)}")
                continue
        
        print("\n" + "=" * 85)
        print("Calculation complete!")
        print("=" * 85)
        print("\n⚠  REMEMBER:")
        print("   - These values are for Anlage KAP INV")
        print("   - You must add Vorabpauschalen (Line 53) manually")
        print("   - Double-check all values in your tax software")
        print("   - Keep this CSV file and output for your records")
        print("=" * 85)
        
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
        return


if __name__ == "__main__":
    main()
