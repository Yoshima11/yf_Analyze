"""
================================================================================
        ANALIZADOR DE INVERSIÓN CEDEARS - INTEGRADO
        Versión: 1.0 | Fecha: Mayo 2026
        Integra: stock_analyzer.py + free_cash_flow.py
================================================================================
"""

import warnings
from datetime import datetime

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

# ============================================================================
# IMPORTAR FUNCIONES DE stock_analyzer.py
# ============================================================================


def safe_download(ticker: str, period: str = "1y"):
    """Descarga datos con manejo robusto - DESDE stock_analyzer.py"""
    try:
        df = yf.download(
            ticker, period=period, interval="1d", progress=False, auto_adjust=False
        )

        if df.empty:
            df = yf.download(
                ticker, period=period, interval="1d", progress=False, auto_adjust=True
            )

        if df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            if ("Close", ticker) in df.columns:
                df = df[("Close", ticker)].to_frame(name="Close")
            elif ("Adj Close", ticker) in df.columns:
                df = df[("Adj Close", ticker)].to_frame(name="Close")
            elif "Close" in df.columns.get_level_values(0):
                close_cols = df.xs("Close", axis=1, level=0)
                if not close_cols.empty:
                    df = close_cols.iloc[:, 0].to_frame(name="Close")
                else:
                    df = df.iloc[:, 0].to_frame(name="Close")
            else:
                df = df.iloc[:, 0].to_frame(name="Close")
        elif "Close" in df.columns:
            df = df[["Close"]].copy()
        elif "Adj Close" in df.columns:
            df = df[["Adj Close"]].copy()
            df.columns = ["Close"]
        elif len(df.columns) == 1:
            df.columns = ["Close"]

        if df.empty or len(df) < 30:
            return None

        return df
    except Exception as e:
        return None


def calculate_technical_indicators(series, ticker=None):
    """Calcula indicadores técnicos - DESDE stock_analyzer.py"""
    results = {}
    try:
        if series is None or len(series) < 30:
            return results

        if isinstance(series, pd.DataFrame):
            series = series.iloc[:, 0] if len(series.columns) > 0 else pd.Series()

        if len(series) == 0:
            return results

        current_price = series.iloc[-1]
        results["Precio_Actual"] = f"${current_price:.2f}"

        if len(series) >= 20:
            sma_20 = series.rolling(window=20).mean().iloc[-1]
            results["SMA_20"] = f"${sma_20:.2f}"

        if len(series) >= 50:
            sma_50 = series.rolling(window=50).mean().iloc[-1]
            results["SMA_50"] = f"${sma_50:.2f}"

        if len(series) >= 26:
            ema_12_series = series.ewm(span=12, adjust=False).mean()
            ema_26_series = series.ewm(span=26, adjust=False).mean()
            macd_line_series = ema_12_series - ema_26_series
            signal_line_series = macd_line_series.ewm(span=9, adjust=False).mean()
            macd_histogram_series = macd_line_series - signal_line_series

            results["MACD"] = f"{macd_line_series.iloc[-1]:.4f}"
            results["MACD_Signal"] = f"{signal_line_series.iloc[-1]:.4f}"
            results["MACD_Histogram"] = f"{macd_histogram_series.iloc[-1]:.4f}"
            results["EMA_12"] = f"${ema_12_series.iloc[-1]:.2f}"
            results["EMA_26"] = f"${ema_26_series.iloc[-1]:.2f}"

        if len(series) >= 14:
            delta = series.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss.where(loss != 0, 0.001)
            rsi = 100 - (100 / (1 + rs))
            if len(rsi) > 0:
                results["RSI_14"] = f"{rsi.iloc[-1]:.2f}"

        if len(series) >= 20:
            sma_20_full = series.rolling(window=20).mean()
            std_20 = series.rolling(window=20).std()
            upper_band = sma_20_full + (std_20 * 2)
            lower_band = sma_20_full - (std_20 * 2)
            results["BB_Upper"] = f"${upper_band.iloc[-1]:.2f}"
            results["BB_Lower"] = f"${lower_band.iloc[-1]:.2f}"
            bb_position = (
                (current_price - lower_band.iloc[-1])
                / (upper_band.iloc[-1] - lower_band.iloc[-1])
                * 100
            )
            results["BB_Position"] = f"{bb_position:.1f}%"

        # Señales
        signals = []
        if "SMA_20" in results and "SMA_50" in results:
            sma_20_val = float(results["SMA_20"].replace("$", ""))
            sma_50_val = float(results["SMA_50"].replace("$", ""))
            if sma_20_val > sma_50_val:
                signals.append("✅ Tendencia Alcista")
            else:
                signals.append("📉 Tendencia Bajista")

        if "RSI_14" in results:
            rsi_val = float(results["RSI_14"])
            if rsi_val > 70:
                signals.append("⚠️ Sobrecomprado")
            elif rsi_val < 30:
                signals.append("💡 Sobrevenido")
            else:
                signals.append("⚖️ RSI Neutral")

        if "MACD_Histogram" in results:
            hist_val = float(results["MACD_Histogram"])
            if hist_val > 0:
                signals.append("📈 Señal Alcista MACD")
            else:
                signals.append("📉 Señal Bajista MACD")

        results["Señales"] = " | ".join(signals) if signals else "Sin señales"

        if len(series) >= 5:
            returns_5d = (
                ((series.iloc[-1] - series.iloc[-6]) / series.iloc[-6]) * 100
                if len(series) >= 6
                else 0
            )
            results["Retorno_5D"] = f"{returns_5d:.2f}%"

        if len(series) >= 20:
            returns_20d = (
                ((series.iloc[-1] - series.iloc[-21]) / series.iloc[-21]) * 100
                if len(series) >= 21
                else 0
            )
            results["Retorno_20D"] = f"{returns_20d:.2f}%"

        return results
    except Exception as e:
        return results


def calculate_fundamentals(ticker: str):
    """Obtiene métricas fundamentales - DESDE stock_analyzer.py"""
    try:
        ticker_data = yf.Ticker(ticker)
        info = ticker_data.info

        fundamentals = {}
        metrics = {
            "marketCap": "Market_Cap",
            "currentPrice": "Precio_Actual",
            "trailingPE": "P/E_TTM",
            "forwardPE": "P/E_Forward",
            "pegRatio": "PEG_Ratio",
            "dividendYield": "Dividend_Yield",
            "returnOnEquity": "ROE",
            "profitMargins": "Profit_Margin",
            "revenueGrowth": "Revenue_Growth",
            "beta": "Beta",
        }

        for key, name in metrics.items():
            value = info.get(key, None)
            if isinstance(value, (int, float)) and pd.notna(value):
                if key == "marketCap":
                    if value >= 1e12:
                        fundamentals[name] = f"${value / 1e12:.2f}T"
                    elif value >= 1e9:
                        fundamentals[name] = f"${value / 1e9:.2f}B"
                    elif value >= 1e6:
                        fundamentals[name] = f"${value / 1e6:.2f}M"
                    else:
                        fundamentals[name] = f"${value:.0f}"
                elif key in [
                    "dividendYield",
                    "returnOnEquity",
                    "profitMargins",
                    "revenueGrowth",
                ]:
                    if value is not None:
                        fundamentals[name] = f"{value * 100:.2f}%"
                    else:
                        fundamentals[name] = "N/A"
                elif key in ["trailingPE", "forwardPE", "pegRatio", "beta"]:
                    fundamentals[name] = f"{value:.2f}"
                else:
                    fundamentals[name] = f"{value:.2f}"
            else:
                fundamentals[name] = "N/A"

        fundamentals["Sector"] = info.get("sector", "N/A")
        fundamentals["Industria"] = info.get("industry", "N/A")

        return fundamentals
    except Exception as e:
        return {}


# ============================================================================
# CLASE FCF - DESDE free_cash_flow.py
# ============================================================================


class FreeCashFlowCalculator:
    """Clase para cálculo de Free Cash Flow - DESDE free_cash_flow.py"""

    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.ticker_obj = None
        self.info = None
        self.cashflow = None
        self.balance = None

    def fetch_data(self):
        """Obtiene datos financieros"""
        try:
            self.ticker_obj = yf.Ticker(self.ticker)
            self.info = self.ticker_obj.info

            try:
                self.cashflow = self.ticker_obj.cashflow
            except:
                pass

            try:
                self.balance = self.ticker_obj.balance_sheet
            except:
                pass

            return self.info is not None
        except:
            return False

    def get_operating_cash_flow(self):
        """Obtiene Operating Cash Flow"""
        if self.cashflow is None or self.cashflow.empty:
            return None

        try:
            ocf_keywords = [
                "Operating Cash Flow",
                "OperatingCF",
                "Cash Flow from Operating Activities",
            ]
            for keyword in ocf_keywords:
                if keyword in self.cashflow.index:
                    ocf_series = self.cashflow.loc[keyword]
                    if len(ocf_series) > 0:
                        latest_ocf = ocf_series.iloc[0]
                        if latest_ocf and not pd.isna(latest_ocf):
                            return float(latest_ocf)
            return None
        except:
            return None

    def get_capex(self):
        """Obtiene Capital Expenditure"""
        if self.cashflow is None or self.cashflow.empty:
            return None

        try:
            capex_keywords = [
                "Capital Expenditure",
                "Capital Expenditures",
                "Purchase Of Property Plant And Equipment",
            ]
            for keyword in capex_keywords:
                if keyword in self.cashflow.index:
                    capex_series = self.cashflow.loc[keyword]
                    if len(capex_series) > 0:
                        capex_value = capex_series.iloc[0]
                        if capex_value and not pd.isna(capex_value):
                            return abs(float(capex_value))

            if self.balance is not None and not self.balance.empty:
                ppe_keywords = ["Property Plant And Equipment", "Net PPE"]
                for keyword in ppe_keywords:
                    if keyword in self.balance.index:
                        ppe_series = self.balance.loc[keyword]
                        if len(ppe_series) >= 2:
                            ppe_change = abs(ppe_series.iloc[0] - ppe_series.iloc[1])
                            if ppe_change > 0:
                                return float(ppe_change)
            return None
        except:
            return None

    def calculate_free_cash_flow(self):
        """Calcula Free Cash Flow"""
        ocf = self.get_operating_cash_flow()

        if ocf is None:
            return None

        capex = self.get_capex()
        if capex is None:
            capex = ocf * 0.2  # Estimación

        fcf = ocf - capex
        return fcf

    def get_fcf_yield(self):
        """Calcula FCF Yield"""
        fcf = self.calculate_free_cash_flow()
        if fcf is None:
            return None

        market_cap = self.info.get("marketCap", 0)
        if market_cap and market_cap > 0:
            return (fcf / market_cap) * 100
        return None


# ============================================================================
# ANALIZADOR INTEGRADO DE CEDEARS
# ============================================================================

# Lista de CEDEARS más líquidos en Argentina (100 acciones)
CEDEARS_LIST = [
    "STLA",
    "NVO",
    "MELI",
    "FISV",
    "SUZ",
    "PFE",
    "BKNG",
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "NVDA",
    "META",
    "NFLX",
    "TSLA",
    "AMD",
    "INTC",
    "ORCL",
    "CRM",
    "ADBE",
    "CSCO",
    "IBM",
    "QCOM",
    "TXN",
    "AVGO",
    "MU",
    "PYPL",
    "V",
    "MA",
    "JPM",
    "BAC",
    "C",
    "WFC",
    "GS",
    "MS",
    "BLK",
    "AXP",
    "SPGI",
    "SCHW",
    "USB",
    "PNC",
    "COF",
    "BK",
    "STT",
    "TROW",
    "MET",
    "PRU",
    "XOM",
    "CVX",
    "COP",
    "EOG",
    "SLB",
    "OXY",
    "HAL",
    "PSX",
    "MPC",
    "VLO",
    "JNJ",
    "UNH",
    "PFE",
    "MRK",
    "ABBV",
    "BMY",
    "LLY",
    "AMGN",
    "GILD",
    "CVS",
    "WMT",
    "COST",
    "HD",
    "LOW",
    "TGT",
    "KO",
    "PEP",
    "PG",
    "NKE",
    "SBUX",
    "MCD",
    "DIS",
    "CMG",
    "TJX",
    "BA",
    "CAT",
    "GE",
    "HON",
    "UNP",
    "UPS",
    "T",
    "VZ",
    "TMUS",
    "CHTR",
    "CMCSA",
    "FOXA",
    "SPOT",
]


def analyze_cedear_integrated(ticker: str):
    """Analiza un CEDEAR usando ambos scripts integrados"""

    result = {
        "ticker": ticker,
        "fecha": datetime.now().strftime("%Y-%m-%d"),
        "error": None,
    }

    try:
        # 1. DATOS TÉCNICOS (desde stock_analyzer)
        df = safe_download(ticker, period="6mo")

        if df is None or df.empty:
            result["error"] = "Sin datos técnicos"
            return result

        # Extraer precios
        if "Close" in df.columns:
            close_prices = df["Close"]
        else:
            close_prices = df.iloc[:, 0]

        # Calcular indicadores técnicos
        technical = calculate_technical_indicators(close_prices, ticker)

        # 2. FUNDAMENTALES BÁSICOS (desde stock_analyzer)
        fundamentals = calculate_fundamentals(ticker)

        # 3. FREE CASH FLOW (desde free_cash_flow.py)
        fcf_analyzer = FreeCashFlowCalculator(ticker)
        fcf_analyzer.fetch_data()
        fcf = fcf_analyzer.calculate_free_cash_flow()
        fcf_yield = fcf_analyzer.get_fcf_yield()

        # Combinar resultados
        result.update(technical)
        result.update(fundamentals)

        # Agregar métricas FCF
        if fcf:
            result["FCF"] = f"${fcf / 1e9:.2f}B"
            result["FCF_Yield"] = f"{fcf_yield:.2f}%" if fcf_yield else "N/A"
        else:
            result["FCF"] = "N/A"
            result["FCF_Yield"] = "N/A"

        # Calcular SCORE INTEGRADO
        # Técnico (60%) + Fundamental (40%) + Bono FCF
        tech_score = 50
        if "RSI_14" in technical:
            rsi_val = float(technical["RSI_14"])
            if rsi_val < 30:
                tech_score = 80
            elif rsi_val < 40:
                tech_score = 70
            elif rsi_val < 50:
                tech_score = 60
            elif rsi_val < 70:
                tech_score = 50
            else:
                tech_score = 40

        if "MACD_Histogram" in technical:
            macd_val = float(technical["MACD_Histogram"])
            if macd_val > 0:
                tech_score += 10
            else:
                tech_score -= 10

        if "SMA_20" in technical and "SMA_50" in technical:
            sma_20_val = float(technical["SMA_20"].replace("$", ""))
            sma_50_val = float(technical["SMA_50"].replace("$", ""))
            if sma_20_val > sma_50_val:
                tech_score += 10
            else:
                tech_score -= 10

        fund_score = 50
        if fundamentals.get("P/E_TTM", "N/A") != "N/A":
            pe = float(fundamentals["P/E_TTM"])
            if pe < 15:
                fund_score += 20
            elif pe < 25:
                fund_score += 10
            elif pe > 35:
                fund_score -= 10

        if fundamentals.get("ROE", "N/A") != "N/A":
            roe = float(fundamentals["ROE"].replace("%", ""))
            if roe > 20:
                fund_score += 15
            elif roe > 15:
                fund_score += 10

        # Bono por FCF positivo
        fcf_bonus = 0
        if fcf and fcf > 0:
            fcf_bonus = 10
            if fcf_yield and fcf_yield > 5:
                fcf_bonus = 15

        # Score final (Técnico 50% + Fundamental 30% + FCF 20%)
        final_score = (tech_score * 0.5) + (fund_score * 0.3) + (50 + fcf_bonus) * 0.2
        final_score = max(0, min(100, final_score))

        result["Score_Integral"] = round(final_score, 1)

        # Recomendación
        if final_score >= 75:
            result["Recomendacion"] = "🟢 COMPRA FUERTE"
        elif final_score >= 60:
            result["Recomendacion"] = "✅ COMPRA"
        elif final_score >= 45:
            result["Recomendacion"] = "⚪ NEUTRAL"
        elif final_score >= 30:
            result["Recomendacion"] = "🟡 VENTA"
        else:
            result["Recomendacion"] = "🔴 VENTA FUERTE"

        # Retorno esperado
        if "Retorno_20D" in technical:
            ret_20d = float(technical["Retorno_20D"].replace("%", ""))
            expected_return_6m = ret_20d * 3
            expected_return_12m = ret_20d * 5
            result["Retorno_Esperado_6M"] = (
                f"{max(-30, min(50, expected_return_6m)):+.1f}%"
            )
            result["Retorno_Esperado_12M"] = (
                f"{max(-30, min(50, expected_return_12m)):+.1f}%"
            )
        else:
            result["Retorno_Esperado_6M"] = "N/A"
            result["Retorno_Esperado_12M"] = "N/A"

        return result

    except Exception as e:
        result["error"] = str(e)
        return result


def analyze_all_cedeares(max_stocks: int = 100):
    """Analiza todos los CEDEARS de la lista"""

    print("=" * 100)
    print("🚀 ANALIZADOR INTEGRADO DE CEDEARS (stock_analyzer + free_cash_flow)")
    print("=" * 100)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 Total CEDEARS a analizar: {min(len(CEDEARS_LIST), max_stocks)}")
    print("=" * 100 + "\n")

    results = []

    for i, ticker in enumerate(CEDEARS_LIST[:max_stocks], 1):
        print(
            f"[{i:3d}/{min(len(CEDEARS_LIST), max_stocks)}] Analizando {ticker}... ",
            end="",
            flush=True,
        )

        result = analyze_cedear_integrated(ticker)

        if result.get("error") is None:
            results.append(result)
            print(
                f"✅ Score: {result.get('Score_Integral', 'N/A')} | {result.get('Recomendacion', 'N/A')}"
            )
        else:
            print(f"❌ {result['error']}")

    # Convertir a DataFrame
    df = pd.DataFrame(results)

    if not df.empty:
        # Ordenar por score
        df = df.sort_values("Score_Integral", ascending=False).reset_index(drop=True)

        # Guardar CSV
        filename = (
            f"cedear_analysis_integrado_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        )
        df.to_csv(filename, index=False, encoding="utf-8-sig")
        print(f"\n✅ Resultados guardados en: {filename}")

    return df


def print_top_recommendations(df: pd.DataFrame, top_n: int = 20):
    """Imprime las mejores recomendaciones"""

    if df.empty:
        print("No hay resultados para mostrar")
        return

    print("\n" + "=" * 100)
    print(f"🏆 TOP {top_n} RECOMENDACIONES DE INVERSIÓN - CEDEARS ARGENTINA")
    print("=" * 100)

    print("\n🎯 INVERSIÓN A 6 MESES:")
    print("-" * 110)
    print(
        f"{'#':<3} {'Ticker':<8} {'Empresa':<30} {'Score':<6} {'Recomendación':<18} "
        f"{'Precio':<10} {'RSI':<8} {'FCF Yield':<10}"
    )
    print("-" * 110)

    for i, row in df.head(top_n).iterrows():
        empresa = row.get("Sector", row.get("ticker", ""))[:28]
        precio = row.get("Precio_Actual", "N/A")
        rsi = row.get("RSI_14", "N/A")
        fcf_yield = row.get("FCF_Yield", "N/A")

        print(
            f"{i + 1:<3} {row['ticker']:<8} {empresa:<30} "
            f"{row['Score_Integral']:<6} {row['Recomendacion']:<18} "
            f"{precio:<10} {rsi:<8} {fcf_yield:<10}"
        )

    # Mostrar acciones con FCF positivo destacado
    print("\n" + "=" * 100)
    print("💰 TOP 10 - MEJOR GENERACIÓN DE EFECTIVO (FCF Yield)")
    print("=" * 100)

    fcf_stocks = df[df["FCF_Yield"] != "N/A"].copy()
    if not fcf_stocks.empty:
        fcf_stocks["FCF_Yield_Num"] = (
            fcf_stocks["FCF_Yield"].str.replace("%", "").astype(float)
        )
        fcf_stocks = fcf_stocks.sort_values("FCF_Yield_Num", ascending=False).head(10)

        for _, row in fcf_stocks.iterrows():
            print(f"\n📊 {row['ticker']} - {row.get('Sector', row['ticker'])}")
            print(
                f"   FCF: {row.get('FCF', 'N/A')} | FCF Yield: {row['FCF_Yield']} | Score: {row['Score_Integral']}"
            )
            print(f"   {row['Recomendacion']} | RSI: {row.get('RSI_14', 'N/A')}")

    # Resumen estadístico
    print("\n" + "=" * 100)
    print("📊 RESUMEN ESTADÍSTICO DEL ANÁLISIS")
    print("=" * 100)

    compras = df[df["Score_Integral"] >= 60].shape[0]
    neutrales = df[(df["Score_Integral"] >= 45) & (df["Score_Integral"] < 60)].shape[0]
    ventas = df[df["Score_Integral"] < 45].shape[0]

    print(
        f"\n✅ Recomendaciones COMPRA: {compras}/{len(df)} ({compras / len(df) * 100:.1f}%)"
    )
    print(
        f"⚪ Recomendaciones NEUTRAL: {neutrales}/{len(df)} ({neutrales / len(df) * 100:.1f}%)"
    )
    print(
        f"🔴 Recomendaciones VENTA: {ventas}/{len(df)} ({ventas / len(df) * 100:.1f}%)"
    )

    # Oportunidades de sobreventa
    oversold = df[
        df["RSI_14"]
        .astype(str)
        .str.replace("%", "")
        .str.extract(r"(\d+\.?\d*)")
        .astype(float)[0]
        < 35
        if "RSI_14" in df
        else pd.Series([False])
    ]
    if not oversold.empty:
        print("\n⚡ OPORTUNIDADES RSI SOBREVENTA (Posible entrada):")
        for _, row in oversold.head(5).iterrows():
            print(
                f"   {row['ticker']} - RSI: {row.get('RSI_14', 'N/A')} | Score: {row['Score_Integral']} | {row['Recomendacion']}"
            )


# ============================================================================
# EJECUCIÓN PRINCIPAL
# ============================================================================

if __name__ == "__main__":
    print("=" * 100)
    print("🔬 ANALIZADOR DE CEDEARS - VERSIÓN INTEGRADA")
    print("=" * 100)
    print("Componentes integrados:")
    print("   📈 stock_analyzer.py → Análisis técnico (SMA, RSI, MACD, Bollinger)")
    print("   💰 free_cash_flow.py → Free Cash Flow (efectivo real generado)")
    print("   🎯 Score combinado → 50% Técnico + 30% Fundamental + 20% FCF")
    print("=" * 100)

    # Analizar todos los CEDEARS
    resultados = analyze_all_cedeares(max_stocks=100)

    # Mostrar recomendaciones
    if not resultados.empty:
        print_top_recommendations(resultados, top_n=20)

    print("\n" + "=" * 100)
    print("🏁 ANÁLISIS COMPLETADO")
    print("=" * 100)
