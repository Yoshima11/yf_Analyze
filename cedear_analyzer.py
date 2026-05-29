"""
================================================================================
        ANALIZADOR DE INVERSIÓN - CEDEAR ARGENTINA (VERSIÓN 3.0 CORREGIDA)
        Versión: 3.0 | Fecha: Mayo 2026
================================================================================
"""

import time
import warnings
from datetime import datetime
from typing import Dict, List

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

# ============================================================================
# LISTA DE CEDEARS (50 más líquidos para pruebas rápidas)
# ============================================================================

CEDEARS_LIST = [
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
]


# ============================================================================
# CLASE PRINCIPAL DE ANÁLISIS (VERSIÓN CORREGIDA)
# ============================================================================


class CedearInvestmentAnalyzer:
    """Analizador de inversiones para CEDEARs argentinos"""

    def __init__(self, ticker: str):
        self.ticker = ticker
        self.info = None
        self.historical_data = None
        self.current_price = 0

    def fetch_all_data(self) -> bool:
        """Obtiene todos los datos necesarios"""
        try:
            time.sleep(0.3)  # Pausa para respetar la API

            # Descargar datos históricos
            self.historical_data = yf.download(
                self.ticker,
                period="6mo",
                interval="1d",
                progress=False,
                auto_adjust=True,  # Esto simplifica las columnas
            )

            if self.historical_data is None or self.historical_data.empty:
                return False

            # Verificar que tenemos suficientes datos
            if len(self.historical_data) < 20:
                return False

            # Obtener precio actual
            try:
                # Método 1: Último precio de cierre
                if "Close" in self.historical_data.columns:
                    last_close = self.historical_data["Close"].iloc[-1]
                    if not pd.isna(last_close):
                        self.current_price = float(last_close)
                elif len(self.historical_data.columns) > 0:
                    # Si no hay 'Close', usar la primera columna
                    last_close = self.historical_data.iloc[-1, 0]
                    if not pd.isna(last_close):
                        self.current_price = float(last_close)
            except:
                pass

            # Obtener información fundamental
            try:
                ticker_obj = yf.Ticker(self.ticker)
                self.info = ticker_obj.info
            except:
                self.info = {}

            return True

        except Exception as e:
            return False

    def get_close_prices(self):
        """Extrae precios de cierre como array numpy"""
        try:
            if self.historical_data is None or self.historical_data.empty:
                return np.array([])

            if "Close" in self.historical_data.columns:
                prices = self.historical_data["Close"].values
            else:
                # Usar la primera columna
                prices = self.historical_data.iloc[:, 0].values

            # Limpiar NaN
            prices = prices[~np.isnan(prices)]
            return prices
        except:
            return np.array([])

    def calculate_technical_score(self) -> Dict:
        """Calcula puntaje técnico - VERSIÓN CORREGIDA"""

        prices = self.get_close_prices()

        if len(prices) < 20:
            return {
                "score_6m": 50,
                "score_12m": 50,
                "signals": ["Datos insuficientes"],
                "current_price": self.current_price,
                "volatility": 20.0,
                "rsi": 50.0,
                "momentum_1m": 0,
                "momentum_3m": 0,
            }

        signals = []
        score_6m = 50
        score_12m = 50
        current_price = prices[-1]

        # === MOMENTUM 1 MES (21 días) ===
        if len(prices) >= 21:
            price_1m = prices[-21]
            ret_1m = ((current_price - price_1m) / price_1m) * 100
        else:
            ret_1m = 0

        if ret_1m > 5:
            score_6m += 12
            score_12m += 6
            signals.append(f"🚀 Momentum +1M: {ret_1m:.1f}%")
        elif ret_1m > 0:
            score_6m += 6
            score_12m += 3
            signals.append(f"📈 Momentum +1M: {ret_1m:.1f}%")
        elif ret_1m < -5:
            score_6m -= 10
            signals.append(f"📉 Momentum -1M: {ret_1m:.1f}%")
        else:
            signals.append(f"⚖️ Momentum 1M: {ret_1m:.1f}%")

        # === MOMENTUM 3 MESES (63 días) ===
        if len(prices) >= 63:
            price_3m = prices[-63]
            ret_3m = ((current_price - price_3m) / price_3m) * 100
        else:
            ret_3m = 0

        if ret_3m > 10:
            score_6m += 15
            score_12m += 12
            signals.append(f"🚀 Momentum +3M: {ret_3m:.1f}%")
        elif ret_3m > 0:
            score_6m += 8
            score_12m += 6
            signals.append(f"📈 Momentum +3M: {ret_3m:.1f}%")
        elif ret_3m < -10:
            score_6m -= 12
            signals.append(f"📉 Momentum -3M: {ret_3m:.1f}%")
        else:
            signals.append(f"⚖️ Momentum 3M: {ret_3m:.1f}%")

        # === SMA 20 vs SMA 50 ===
        if len(prices) >= 50:
            sma_20 = np.mean(prices[-20:])
            sma_50 = np.mean(prices[-50:])

            if sma_20 > sma_50:
                score_6m += 15
                score_12m += 10
                signals.append(f"✅ SMA20({sma_20:.0f}) > SMA50({sma_50:.0f})")
            else:
                score_6m -= 8
                signals.append(f"⚠️ SMA20({sma_20:.0f}) < SMA50({sma_50:.0f})")

        # === RSI ===
        if len(prices) >= 15:
            # Calcular ganancias y pérdidas
            deltas = np.diff(prices[-15:])
            gains = deltas[deltas > 0]
            losses = -deltas[deltas < 0]

            avg_gain = np.mean(gains) if len(gains) > 0 else 0.001
            avg_loss = np.mean(losses) if len(losses) > 0 else 0.001

            if avg_loss > 0:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            else:
                rsi = 100
        else:
            rsi = 50

        if rsi < 30:
            score_6m += 20
            score_12m += 15
            signals.append(f"💡 RSI SOBREVENTA: {rsi:.1f}")
        elif rsi > 70:
            score_6m -= 15
            signals.append(f"⚠️ RSI SOBRECOMPRA: {rsi:.1f}")
        else:
            signals.append(f"⚖️ RSI Neutral: {rsi:.1f}")

        # === MACD simplificado ===
        if len(prices) >= 35:
            # EMA12
            k1 = 2 / 13  # 2/(12+1)
            ema12 = prices[0]
            for price in prices[1:]:
                ema12 = price * k1 + ema12 * (1 - k1)

            # EMA26
            k2 = 2 / 27  # 2/(26+1)
            ema26 = prices[0]
            for price in prices[1:]:
                ema26 = price * k2 + ema26 * (1 - k2)

            macd = ema12 - ema26

            # Señal (EMA9 del MACD - simplificado)
            k_signal = 2 / 10  # 2/(9+1)
            signal_line = macd
            for i in range(1, len(prices)):
                signal_line = macd * k_signal + signal_line * (1 - k_signal)

            if macd > signal_line:
                score_6m += 12
                score_12m += 8
                signals.append("✅ MACD ALCISTA")
            else:
                score_6m -= 8
                signals.append("📉 MACD BAJISTA")

        # === Volatilidad ===
        if len(prices) >= 20:
            returns = np.diff(prices[-20:]) / prices[-20:-1]
            volatility = np.std(returns) * np.sqrt(252) * 100

            if volatility < 25:
                score_6m += 8
                score_12m += 8
                signals.append(f"✅ Baja volatilidad: {volatility:.1f}%")
            elif volatility > 50:
                score_6m -= 8
                signals.append(f"⚠️ Alta volatilidad: {volatility:.1f}%")
        else:
            volatility = 25

        # Ajustar scores dentro de rango 0-100
        score_6m = max(0, min(100, score_6m))
        score_12m = max(0, min(100, score_12m))

        return {
            "score_6m": score_6m,
            "score_12m": score_12m,
            "signals": signals[:5],
            "current_price": current_price,
            "volatility": volatility,
            "rsi": rsi,
            "momentum_1m": ret_1m,
            "momentum_3m": ret_3m,
        }

    def calculate_fundamental_score(self) -> Dict:
        """Calcula puntaje fundamental"""
        score = 50
        metrics = {}

        try:
            if not self.info:
                return {"score": score, "metrics": metrics}

            # P/E Ratio
            pe = self.info.get("trailingPE")
            if pe and isinstance(pe, (int, float)) and pe > 0:
                if pe < 15:
                    score += 15
                    metrics["pe"] = f"{pe:.1f} (Excelente)"
                elif pe < 25:
                    score += 10
                    metrics["pe"] = f"{pe:.1f} (Bueno)"
                elif pe < 35:
                    score += 5
                    metrics["pe"] = f"{pe:.1f} (Normal)"
                else:
                    score -= 10
                    metrics["pe"] = f"{pe:.1f} (Caro)"

            # Profit Margin
            margin = self.info.get("profitMargins")
            if margin and isinstance(margin, (int, float)) and margin > 0:
                if margin > 0.2:
                    score += 12
                    metrics["margin"] = f"{margin * 100:.1f}%"
                elif margin > 0.1:
                    score += 8
                    metrics["margin"] = f"{margin * 100:.1f}%"
                else:
                    score += 4
                    metrics["margin"] = f"{margin * 100:.1f}%"

            # Revenue Growth
            growth = self.info.get("revenueGrowth")
            if growth and isinstance(growth, (int, float)):
                if growth > 0.15:
                    score += 15
                    metrics["growth"] = f"{growth * 100:.1f}%"
                elif growth > 0.05:
                    score += 10
                    metrics["growth"] = f"{growth * 100:.1f}%"
                elif growth > 0:
                    score += 5
                    metrics["growth"] = f"{growth * 100:.1f}%"

            # ROE
            roe = self.info.get("returnOnEquity")
            if roe and isinstance(roe, (int, float)) and roe > 0:
                if roe > 0.2:
                    score += 10
                    metrics["roe"] = f"{roe * 100:.1f}%"
                elif roe > 0.1:
                    score += 5
                    metrics["roe"] = f"{roe * 100:.1f}%"

            return {"score": min(100, max(0, score)), "metrics": metrics}

        except:
            return {"score": 50, "metrics": metrics}

    def calculate_final_score(self) -> Dict:
        """Calcula puntaje final"""
        tech = self.calculate_technical_score()
        fund = self.calculate_fundamental_score()

        # Combinar scores
        final_6m = (tech["score_6m"] * 0.6) + (fund["score"] * 0.4)
        final_12m = (tech["score_12m"] * 0.4) + (fund["score"] * 0.6)

        # Recomendación
        def get_rec(score):
            if score >= 75:
                return "COMPRA FUERTE", "🟢"
            if score >= 60:
                return "COMPRA", "✅"
            if score >= 45:
                return "NEUTRAL", "⚪"
            if score >= 30:
                return "VENTA", "🟡"
            return "VENTA FUERTE", "🔴"

        rec_6m, emoji_6m = get_rec(final_6m)
        rec_12m, emoji_12m = get_rec(final_12m)

        # Retorno esperado
        exp_6m = tech["momentum_3m"] * 1.2 + tech["momentum_1m"] * 0.3
        exp_12m = tech["momentum_3m"] * 1.5 + tech["momentum_1m"] * 0.5
        exp_6m = max(-30, min(50, exp_6m))
        exp_12m = max(-30, min(50, exp_12m))

        company = self.info.get("longName", self.ticker) if self.info else self.ticker
        sector = self.info.get("sector", "N/A") if self.info else "N/A"

        return {
            "ticker": self.ticker,
            "company_name": company[:35],
            "sector": sector,
            "current_price": round(tech["current_price"], 2),
            "score_6m": round(final_6m, 1),
            "score_12m": round(final_12m, 1),
            "rec_6m": f"{emoji_6m} {rec_6m}",
            "rec_12m": f"{emoji_12m} {rec_12m}",
            "return_6m": f"{exp_6m:+.1f}%",
            "return_12m": f"{exp_12m:+.1f}%",
            "volatility": f"{tech['volatility']:.0f}%",
            "rsi": round(tech["rsi"], 1),
            "pe": fund["metrics"].get("pe", "N/A"),
            "top_signal": tech["signals"][0] if tech["signals"] else "N/A",
        }


# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================


def analyze_all_stocks(tickers: List[str]) -> pd.DataFrame:
    """Analiza todas las acciones"""

    print("\n" + "=" * 90)
    print("📊 ANALIZANDO CEDEARS ARGENTINOS")
    print("=" * 90)
    print(f"📈 Total: {len(tickers)} acciones\n")

    results = []

    for i, ticker in enumerate(tickers, 1):
        print(f"[{i:2d}/{len(tickers)}] {ticker:<6} ", end="", flush=True)

        analyzer = CedearInvestmentAnalyzer(ticker)

        if analyzer.fetch_all_data():
            result = analyzer.calculate_final_score()
            results.append(result)

            # Mostrar resultado
            if result["score_6m"] >= 60:
                print(f"✅ {result['score_6m']:.0f} - {result['rec_6m']}")
            elif result["score_6m"] >= 45:
                print(f"⚪ {result['score_6m']:.0f} - {result['rec_6m']}")
            else:
                print(f"⚠️ {result['score_6m']:.0f} - {result['rec_6m']}")
        else:
            print("❌ Sin datos")

    df = pd.DataFrame(results)

    if not df.empty:
        df = df.sort_values("score_6m", ascending=False).reset_index(drop=True)

    return df


def print_report(df: pd.DataFrame):
    """Imprime reporte formateado"""

    if df.empty:
        print("\n❌ No hay resultados")
        return

    # Guardar CSV
    filename = f"cedear_analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    df.to_csv(filename, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 90)
    print("📈 TOP 20 RECOMENDACIONES")
    print("=" * 90)

    print("\n🎯 INVERSIÓN A 6 MESES:")
    print("-" * 95)
    print(
        f"{'#':<3} {'Ticker':<8} {'Empresa':<32} {'Score':<6} {'Recomendación':<18} {'Retorno':<10} {'RSI':<8}"
    )
    print("-" * 95)

    for i, row in df.head(20).iterrows():
        print(
            f"{i + 1:<3} {row['ticker']:<8} {row['company_name'][:30]:<32} "
            f"{row['score_6m']:<6} {row['rec_6m']:<18} {row['return_6m']:<10} {row['rsi']:<8}"
        )

    print("\n🎯 INVERSIÓN A 12 MESES:")
    print("-" * 95)
    df_12m = df.sort_values("score_12m", ascending=False)

    for i, row in df_12m.head(20).iterrows():
        print(
            f"{i + 1:<3} {row['ticker']:<8} {row['company_name'][:30]:<32} "
            f"{row['score_12m']:<6} {row['rec_12m']:<18} {row['return_12m']:<10} {row['rsi']:<8}"
        )

    # Mejores para comprar
    print("\n" + "=" * 90)
    print("💎 MEJORES OPORTUNIDADES (COMPRA/COMPRA FUERTE)")
    print("=" * 90)

    top_buys = df[df["score_6m"] >= 60].head(10)

    if not top_buys.empty:
        for _, row in top_buys.iterrows():
            print(f"\n📊 {row['ticker']} - {row['company_name']}")
            print(
                f"   Precio: ${row['current_price']:.2f} | Score: {row['score_6m']} | {row['rec_6m']}"
            )
            print(
                f"   RSI: {row['rsi']} | Volatilidad: {row['volatility']} | Retorno esperado: {row['return_6m']}"
            )
            print(f"   Señal: {row['top_signal']}")
    else:
        print("\n⚠️ No hay recomendaciones de COMPRA en este momento")

    # Sobreventa
    print("\n" + "=" * 90)
    print("⚡ OPORTUNIDADES RSI SOBREVENTA (Posible entrada)")
    print("=" * 90)

    oversold = df[df["rsi"] < 35].head(10)
    if not oversold.empty:
        for _, row in oversold.iterrows():
            print(
                f"   {row['ticker']:<8} RSI: {row['rsi']:<6} Score: {row['score_6m']:<6} {row['company_name'][:40]}"
            )
    else:
        print("   No se encontraron acciones en sobreventa")

    print(f"\n✅ Reporte guardado: {filename}")


# ============================================================================
# EJECUCIÓN
# ============================================================================

if __name__ == "__main__":
    print("=" * 90)
    print("🚀 ANALIZADOR DE INVERSIÓN CEDEARS ARGENTINA v3.0")
    print("=" * 90)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 90)

    # Analizar
    df_results = analyze_all_stocks(CEDEARS_LIST)

    # Mostrar reporte
    if not df_results.empty:
        print_report(df_results)

    print("\n" + "=" * 90)
    print("🏁 ANÁLISIS COMPLETADO")
    print("=" * 90)
