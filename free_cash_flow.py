"""
================================================================================
        SCRIPT COMPLETO PARA CALCULAR FREE CASH FLOW (FCF)
        Versión: 2.0 | Fecha: Mayo 2026 - TOTALMENTE CORREGIDO
        Objetivo: Calcular y analizar FCF para análisis de inversión
================================================================================
"""

import warnings
from datetime import datetime

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

print("=" * 80)
print("CALCULADOR DE FREE CASH FLOW (FCF) PROFESIONAL - YFINANCE")
print("=" * 80)
print(f"Fecha de análisis: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80 + "\n")


class FreeCashFlowCalculator:
    """Clase principal para cálculo de Free Cash Flow"""

    def __init__(self, ticker: str):
        """Inicializa el calculador con un ticker específico"""
        self.ticker = ticker.upper()
        self.ticker_obj = None
        self.info = None
        self.cashflow = None
        self.balance = None
        self.income = None

    def fetch_data(self):
        """Obtiene todos los datos financieros disponibles"""
        print(f"📊 Obteniendo datos para {self.ticker}...")

        try:
            self.ticker_obj = yf.Ticker(self.ticker)
            self.info = self.ticker_obj.info

            # Intentar obtener los diferentes estados financieros
            try:
                self.cashflow = self.ticker_obj.cashflow
                if self.cashflow is not None and not self.cashflow.empty:
                    print(f"  ✅ Cash Flow obtenido")
            except:
                print(f"  ⚠️ Cash Flow no disponible")

            try:
                self.balance = self.ticker_obj.balance_sheet
                if self.balance is not None and not self.balance.empty:
                    print(f"  ✅ Balance Sheet obtenido")
            except:
                print(f"  ⚠️ Balance Sheet no disponible")

            try:
                self.income = self.ticker_obj.income_stmt
                if self.income is not None and not self.income.empty:
                    print(f"  ✅ Income Statement obtenido")
            except:
                print(f"  ⚠️ Income Statement no disponible")

            # Verificar si tenemos al menos algo de datos
            if self.info:
                print(f"  ✅ Información básica obtenida")
                return True
            else:
                print(f"  ❌ No se pudo obtener información")
                return False

        except Exception as e:
            print(f"  ❌ Error al obtener datos: {e}")
            return False

    def get_operating_cash_flow(self):
        """Obtiene el Operating Cash Flow del cashflow statement"""
        if self.cashflow is None or self.cashflow.empty:
            return None

        try:
            # Buscar Operating Cash Flow en el índice
            ocf_keywords = [
                "Operating Cash Flow",
                "OperatingCF",
                "Cash Flow from Operating Activities",
            ]

            for keyword in ocf_keywords:
                if keyword in self.cashflow.index:
                    ocf_series = self.cashflow.loc[keyword]
                    if len(ocf_series) > 0:
                        # Tomar el valor más reciente (primer columna usualmente)
                        latest_ocf = ocf_series.iloc[0] if len(ocf_series) > 0 else None
                        if latest_ocf and not pd.isna(latest_ocf):
                            return float(latest_ocf)

            # Si no encuentra, intentar calcular: Net Income + Depreciation + Non-cash items
            return None

        except Exception as e:
            print(f"  ⚠️ Error obteniendo OCF: {e}")
            return None

    def get_capex(self):
        """Obtiene el Capital Expenditure del cashflow statement"""
        if self.cashflow is None or self.cashflow.empty:
            return None

        try:
            # Buscar Capex en diferentes nombres
            capex_keywords = [
                "Capital Expenditure",
                "Capital Expenditures",
                "Purchase Of Property Plant And Equipment",
                "CapitalExpenditure",
                "InvestingCashFlow",
            ]

            for keyword in capex_keywords:
                if keyword in self.cashflow.index:
                    capex_series = self.cashflow.loc[keyword]
                    if len(capex_series) > 0:
                        capex_value = capex_series.iloc[0]
                        if capex_value and not pd.isna(capex_value):
                            # Capex suele ser negativo, tomamos valor absoluto
                            return abs(float(capex_value))

            # Método alternativo: buscar en balance sheet (cambio en PPE)
            if self.balance is not None and not self.balance.empty:
                # Buscar Property Plant and Equipment
                ppe_keywords = ["Property Plant And Equipment", "Net PPE", "PPE"]
                for keyword in ppe_keywords:
                    if keyword in self.balance.index:
                        ppe_series = self.balance.loc[keyword]
                        if len(ppe_series) >= 2:
                            # Cambio en PPE de un año a otro aproxima Capex
                            ppe_change = abs(ppe_series.iloc[0] - ppe_series.iloc[1])
                            if ppe_change > 0:
                                return float(ppe_change)

            return None

        except Exception as e:
            print(f"  ⚠️ Error obteniendo Capex: {e}")
            return None

    def calculate_free_cash_flow(self):
        """Calcula Free Cash Flow = Operating Cash Flow - Capex"""
        print(f"\n💰 Calculando FCF para {self.ticker}...")

        ocf = self.get_operating_cash_flow()
        capex = self.get_capex()

        if ocf is None:
            print(f"  ❌ No se pudo obtener Operating Cash Flow")
            # Intentar método alternativo usando datos de info
            return self.calculate_fcf_from_info()

        print(f"  📊 Operating Cash Flow: ${ocf / 1e9:.2f}B")

        if capex is None:
            print(f"  ⚠️ No se encontró Capex, estimando...")
            # Estimar Capex como 20% del OCF (promedio de mercado)
            capex = ocf * 0.2
            print(f"  📊 Capex estimado: ${capex / 1e9:.2f}B")
        else:
            print(f"  📊 Capex: ${capex / 1e9:.2f}B")

        fcf = ocf - capex

        print(f"\n" + "=" * 60)
        print(f"🎯 FREE CASH FLOW - {self.ticker}")
        print("=" * 60)
        print(f"   Operating Cash Flow:  ${ocf / 1e9:.2f}B")
        print(f"   Capital Expenditure:  ${capex / 1e9:.2f}B")
        print(f"   ─────────────────────")
        print(f"   FREE CASH FLOW:       ${fcf / 1e9:.2f}B")

        return fcf

    def calculate_fcf_from_info(self):
        """Método alternativo usando datos de info cuando no hay cashflow"""
        print(f"  📊 Usando método alternativo desde info...")

        try:
            # Obtener métricas desde info
            market_cap = self.info.get("marketCap", 0)
            pe_ratio = self.info.get("trailingPE", 0)
            profit_margins = self.info.get("profitMargins", 0)
            revenue = self.info.get("totalRevenue", 0)

            if revenue and revenue > 0 and profit_margins and profit_margins > 0:
                # Estimar Net Income
                net_income = revenue * profit_margins

                # Estimar OCF (Net Income + Depreciación aproximada)
                depreciation_rate = 0.1  # Suposición: 10% de depreciación
                depreciation = revenue * depreciation_rate

                ocf = net_income + depreciation

                # Estimar Capex (normalmente 60-80% de depreciación)
                capex = depreciation * 0.7

                fcf = ocf - capex

                print(f"  📊 Revenue: ${revenue / 1e9:.2f}B")
                print(f"  📊 Profit Margin: {profit_margins * 100:.1f}%")
                print(f"  📊 OCF Estimado: ${ocf / 1e9:.2f}B")
                print(f"  📊 Capex Estimado: ${capex / 1e9:.2f}B")

                print(f"\n" + "=" * 60)
                print(f"🎯 FREE CASH FLOW (ESTIMADO) - {self.ticker}")
                print("=" * 60)
                print(f"   FREE CASH FLOW:       ${fcf / 1e9:.2f}B")

                return fcf

            return None

        except Exception as e:
            print(f"  ❌ Error en método alternativo: {e}")
            return None

    def get_fcf_yield(self):
        """Calcula el FCF Yield"""
        fcf = self.calculate_free_cash_flow()

        if fcf is None:
            return None

        market_cap = self.info.get("marketCap", 0)

        if market_cap and market_cap > 0:
            fcf_yield = (fcf / market_cap) * 100
            print(f"\n📊 FCF YIELD:")
            print("=" * 40)
            print(f"   FCF:           ${fcf / 1e9:.2f}B")
            print(f"   Market Cap:    ${market_cap / 1e9:.2f}B")
            print(f"   FCF YIELD:     {fcf_yield:.2f}%")
            return fcf_yield

        return None


# ============================================================================
# FUNCIONES DE ANÁLISIS
# ============================================================================


def analyze_single_stock(ticker: str):
    """Analiza una sola acción en detalle"""
    print("\n" + "=" * 80)
    print(f"📊 ANÁLISIS DETALLADO: {ticker}")
    print("=" * 80)

    analyzer = FreeCashFlowCalculator(ticker)

    if not analyzer.fetch_data():
        print(f"❌ No se pudo analizar {ticker}")
        return None

    # Calcular FCF
    fcf = analyzer.calculate_free_cash_flow()

    if fcf:
        # Calcular FCF Yield
        fcf_yield = analyzer.get_fcf_yield()

        # Mostrar métricas adicionales
        print(f"\n📈 MÉTRICAS ADICIONALES:")
        print("=" * 40)

        metrics = {
            "sector": "Sector",
            "industry": "Industria",
            "trailingPE": "P/E Ratio",
            "forwardPE": "Forward P/E",
            "profitMargins": "Margen de Beneficio",
            "returnOnEquity": "ROE",
            "revenueGrowth": "Crecimiento Ingresos",
        }

        for key, name in metrics.items():
            value = analyzer.info.get(key)
            if value:
                if key in ["profitMargins", "returnOnEquity", "revenueGrowth"]:
                    print(f"   {name}: {value * 100:.1f}%")
                elif key in ["trailingPE", "forwardPE"]:
                    print(f"   {name}: {value:.2f}")
                else:
                    print(f"   {name}: {value}")

        # Evaluación cualitativa
        print(f"\n🔍 EVALUACIÓN:")
        print("=" * 40)

        if fcf > 0:
            print(f"   ✅ FCF POSITIVO - La empresa genera efectivo")
            if fcf_yield and fcf_yield > 5:
                print(f"   ⭐ EXCELENTE - Alto rendimiento de efectivo")
            elif fcf_yield and fcf_yield > 3:
                print(f"   👍 BUENO - Rendimiento de efectivo sólido")
            else:
                print(f"   📊 MODERADO - Rendimiento de efectivo aceptable")
        else:
            print(f"   ❌ FCF NEGATIVO - La empresa consume efectivo")

        return {"ticker": ticker, "fcf": fcf, "fcf_yield": fcf_yield}

    return None


def analyze_multiple_stocks(tickers: list):
    """Analiza múltiples acciones y genera ranking"""
    print("\n" + "=" * 80)
    print("🎯 ANÁLISIS MÚLTIPLE DE FREE CASH FLOW")
    print("=" * 80)

    results = []

    for ticker in tickers:
        print(f"\n{'=' * 60}")
        print(f"📊 Procesando {ticker}...")
        print(f"{'=' * 60}")

        analyzer = FreeCashFlowCalculator(ticker)

        if not analyzer.fetch_data():
            print(f"  ❌ Saltando {ticker} - No hay datos")
            continue

        fcf = analyzer.calculate_free_cash_flow()

        if fcf:
            market_cap = analyzer.info.get("marketCap", 0)
            fcf_yield = (fcf / market_cap * 100) if market_cap > 0 else None

            pe_ratio = analyzer.info.get("trailingPE", None)
            if pe_ratio and isinstance(pe_ratio, (int, float)):
                pe_ratio = round(pe_ratio, 2)

            # Calcular score
            score = 0
            if fcf > 0:
                score += 40
                if fcf > 10e9:  # > $10B
                    score += 20
                elif fcf > 5e9:  # > $5B
                    score += 15
                elif fcf > 1e9:  # > $1B
                    score += 10

                if fcf_yield and fcf_yield > 5:
                    score += 25
                elif fcf_yield and fcf_yield > 3:
                    score += 15
                elif fcf_yield and fcf_yield > 0:
                    score += 10

            if pe_ratio and pe_ratio < 25 and pe_ratio > 0:
                score += 15
            elif pe_ratio and pe_ratio < 35:
                score += 5

            results.append(
                {
                    "ticker": ticker,
                    "fcf_billions": fcf / 1e9,
                    "fcf_yield": fcf_yield,
                    "pe_ratio": pe_ratio,
                    "score": score,
                }
            )

    # Ordenar por score
    results.sort(key=lambda x: x["score"], reverse=True)

    # Mostrar ranking
    print("\n" + "=" * 80)
    print("🏆 RANKING DE FREE CASH FLOW")
    print("=" * 80)

    for i, r in enumerate(results, 1):
        badge = (
            "👑 EXCELENTE"
            if r["score"] >= 70
            else "⭐ BUENO"
            if r["score"] >= 50
            else "📊 MEDIO"
            if r["score"] >= 30
            else "⚠️ BAJO"
        )

        print(f"\n{i}. {r['ticker']} - Score: {r['score']}/100")
        print(f"   └─ FCF: ${r['fcf_billions']:.2f}B")
        if r["fcf_yield"]:
            print(f"   └─ FCF Yield: {r['fcf_yield']:.2f}%")
        if r["pe_ratio"]:
            print(f"   └─ P/E Ratio: {r['pe_ratio']}")
        print(f"   └─ Calificación: {badge}")

    # Guardar resultados
    if results:
        df = pd.DataFrame(results)
        df["fcf_billions"] = df["fcf_billions"].round(2)
        df["fcf_yield"] = df["fcf_yield"].round(2) if "fcf_yield" in df else None
        filename = f"fcf_ranking_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        df.to_csv(filename, index=False, encoding="utf-8-sig")
        print(f"\n✅ Resultados guardados en: {filename}")

    return results


# ============================================================================
# SCRIPT PRINCIPAL
# ============================================================================

if __name__ == "__main__":
    # Lista de acciones a analizar
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "JPM", "V"]

    print("\n" + "=" * 80)
    print("🚀 ANALIZADOR DE FREE CASH FLOW v2.0")
    print("=" * 80)
    print(f"\n📋 Empresas a analizar: {', '.join(tickers)}")

    # Ejecutar análisis múltiple
    results = analyze_multiple_stocks(tickers)

    # Análisis detallado del top performer
    if results:
        print("\n" + "=" * 80)
        print("📊 ANÁLISIS DETALLADO - TOP PERFORMER")
        print("=" * 80)
        analyze_single_stock(results[0]["ticker"])

    print("\n" + "=" * 80)
    print("🏁 ANÁLISIS COMPLETADO")
    print("=" * 80)
