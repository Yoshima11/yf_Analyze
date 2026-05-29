"""
================================================================================
        ANALIZADOR DE ACCIONES - VERSIÓN 9.1 - MACD CORREGIDO
================================================================================
"""

import warnings
from datetime import datetime

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")


def safe_download(ticker: str, period: str = "1y"):
    """Descarga datos con manejo robusto - VERSIÓN SIMPLIFICADA Y CORREGIDA"""

    try:
        # Descargar datos con parámetros específicos para evitar MultiIndex
        df = yf.download(
            ticker, period=period, interval="1d", progress=False, auto_adjust=False
        )

        # Si es vacío, intentar con auto_adjust=True
        if df.empty:
            df = yf.download(
                ticker, period=period, interval="1d", progress=False, auto_adjust=True
            )

        # Si sigue vacío, retornar None
        if df.empty:
            print(f"  ❌ {ticker}: No se obtuvieron datos")
            return None

        # Caso: DataFrame con MultiIndex en columnas (formato nuevo de yfinance)
        if isinstance(df.columns, pd.MultiIndex):
            print(f"  ℹ️ {ticker}: Formato MultiIndex detectado, extrayendo datos...")
            # Extraer 'Close' del primer ticker si es MultiIndex
            if ("Close", ticker) in df.columns:
                df = df[("Close", ticker)].to_frame(name="Close")
            elif ("Adj Close", ticker) in df.columns:
                df = df[("Adj Close", ticker)].to_frame(name="Close")
            elif "Close" in df.columns.get_level_values(0):
                # Tomar el primer nivel 'Close' sin importar el ticker
                close_cols = df.xs("Close", axis=1, level=0)
                if not close_cols.empty:
                    df = close_cols.iloc[:, 0].to_frame(name="Close")
                else:
                    df = df.iloc[:, 0].to_frame(name="Close")
            else:
                # Último recurso: tomar primera columna
                df = df.iloc[:, 0].to_frame(name="Close")

        # Caso: DataFrame normal con columna 'Close'
        elif "Close" in df.columns:
            df = df[["Close"]].copy()

        # Caso: No hay 'Close' pero sí 'Adj Close'
        elif "Adj Close" in df.columns:
            df = df[["Adj Close"]].copy()
            df.columns = ["Close"]

        # Caso: Solo una columna
        elif len(df.columns) == 1:
            df.columns = ["Close"]

        # Verificar que tenemos datos
        if df.empty or len(df) < 30:
            print(f"  ❌ {ticker}: Datos insuficientes ({len(df)} registros)")
            return None

        print(f"  ✅ {ticker}: {len(df)} días de datos descargados")
        return df

    except Exception as e:
        print(f"  ❌ Error descargando {ticker}: {e}")
        return None


def calculate_technical_indicators(series, ticker=None):
    """Calcula indicadores técnicos de forma robusta - VERSIÓN CORREGIDA"""
    results = {}

    try:
        if series is None or len(series) < 30:
            print(f"  ⚠️ Datos insuficientes para análisis técnico")
            return results

        # Asegurar que series es una Serie de pandas
        if isinstance(series, pd.DataFrame):
            series = series.iloc[:, 0] if len(series.columns) > 0 else pd.Series()

        if len(series) == 0:
            return results

        print(f"  📊 Calculando indicadores técnicos...")

        # Precio Actual
        current_price = series.iloc[-1]
        results["Precio_Actual"] = f"${current_price:.2f}"

        # SMA 20 y SMA 50
        if len(series) >= 20:
            sma_20 = series.rolling(window=20).mean().iloc[-1]
            results["SMA_20"] = f"${sma_20:.2f}"

        if len(series) >= 50:
            sma_50 = series.rolling(window=50).mean().iloc[-1]
            results["SMA_50"] = f"${sma_50:.2f}"

        # MACD (corregido: usar series completas, no valores escalares)
        if len(series) >= 26:
            # Calcular EMAs como series completas
            ema_12_series = series.ewm(span=12, adjust=False).mean()
            ema_26_series = series.ewm(span=26, adjust=False).mean()

            # MACD Line = EMA12 - EMA26
            macd_line_series = ema_12_series - ema_26_series

            # Signal Line = EMA9 de MACD Line
            signal_line_series = macd_line_series.ewm(span=9, adjust=False).mean()

            # MACD Histogram = MACD Line - Signal Line
            macd_histogram_series = macd_line_series - signal_line_series

            # Obtener últimos valores
            macd_line = macd_line_series.iloc[-1]
            signal_line = signal_line_series.iloc[-1]
            macd_histogram = macd_histogram_series.iloc[-1]

            results["MACD"] = f"{macd_line:.4f}"
            results["MACD_Signal"] = f"{signal_line:.4f}"
            results["MACD_Histogram"] = f"{macd_histogram:.4f}"

            # También guardar EMA12 y EMA26 actuales
            results["EMA_12"] = f"${ema_12_series.iloc[-1]:.2f}"
            results["EMA_26"] = f"${ema_26_series.iloc[-1]:.2f}"

        # RSI (Relative Strength Index)
        if len(series) >= 14:
            delta = series.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()

            # Evitar división por cero
            rs = gain / loss.where(loss != 0, 0.001)
            rsi = 100 - (100 / (1 + rs))

            if len(rsi) > 0:
                results["RSI_14"] = f"{rsi.iloc[-1]:.2f}"

        # Bollinger Bands
        if len(series) >= 20:
            sma_20_full = series.rolling(window=20).mean()
            std_20 = series.rolling(window=20).std()

            upper_band = sma_20_full + (std_20 * 2)
            lower_band = sma_20_full - (std_20 * 2)

            results["BB_Upper"] = f"${upper_band.iloc[-1]:.2f}"
            results["BB_Lower"] = f"${lower_band.iloc[-1]:.2f}"

            # Posición actual en Bollinger Bands
            bb_position = (
                (current_price - lower_band.iloc[-1])
                / (upper_band.iloc[-1] - lower_band.iloc[-1])
                * 100
            )
            results["BB_Position"] = f"{bb_position:.1f}%"

        # ATR (Average True Range) - para volatilidad
        if len(series) >= 14:
            high_low = series.diff().abs()
            high_close = (series.shift(1) - series).abs()
            low_close = (series.shift(1) - series).abs()

            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = tr.rolling(window=14).mean()

            if len(atr) > 0:
                results["ATR_14"] = f"${atr.iloc[-1]:.2f}"

        # Señales básicas
        signals = []

        # Señal SMA
        if "SMA_20" in results and "SMA_50" in results:
            sma_20_val = float(results["SMA_20"].replace("$", ""))
            sma_50_val = float(results["SMA_50"].replace("$", ""))
            if sma_20_val > sma_50_val:
                signals.append("✅ Tendencia Alcista (SMA20 > SMA50)")
            else:
                signals.append("📉 Tendencia Bajista (SMA20 < SMA50)")

        # Señal RSI
        if "RSI_14" in results:
            rsi_val = float(results["RSI_14"])
            if rsi_val > 70:
                signals.append("⚠️ Sobrecomprado (RSI > 70)")
            elif rsi_val < 30:
                signals.append("💡 Sobrevenido (RSI < 30)")
            else:
                signals.append("⚖️ RSI Neutral")

        # Señal MACD
        if "MACD_Histogram" in results:
            hist_val = float(results["MACD_Histogram"])
            if hist_val > 0:
                signals.append("📈 Señal Alcista (MACD > Signal)")
            else:
                signals.append("📉 Señal Bajista (MACD < Signal)")

        # Señal Bollinger Bands
        if "BB_Position" in results:
            bb_pos = float(results["BB_Position"].replace("%", ""))
            if bb_pos > 80:
                signals.append("📊 Cerca de Banda Superior")
            elif bb_pos < 20:
                signals.append("📊 Cerca de Banda Inferior")

        results["Señales"] = " | ".join(signals) if signals else "Sin señales claras"

        # Calcular rendimiento
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
        print(f"  ❌ Error calculando indicadores: {e}")
        import traceback

        traceback.print_exc()
        return results


def calculate_fundamentals(ticker: str):
    """Obtiene métricas fundamentales"""
    try:
        ticker_data = yf.Ticker(ticker)
        info = ticker_data.info

        fundamentals = {}

        # Métricas clave
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
            "52WeekChange": "Cambio_52S",
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
                    "52WeekChange",
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

        # Información adicional
        sector = info.get("sector", "N/A")
        industry = info.get("industry", "N/A")
        fundamentals["Sector"] = sector
        fundamentals["Industria"] = industry

        return fundamentals

    except Exception as e:
        print(f"  ❌ Error fundamentales: {e}")
        return {}


# ============================================================================
# SCRIPT PRINCIPAL - VERSIÓN CORREGIDA
# ============================================================================

if __name__ == "__main__":
    # Tickers a analizar
    tickers_to_analyze = ["AAPL", "MSFT", "GOOGL", "NVDA", "V", "AMZN", "META"]

    print("\n" + "=" * 90)
    print("🚀 ANALIZADOR DE ACCIONES - VERSIÓN 9.1")
    print("=" * 90 + "\n")

    all_results = []
    technical_summary = []

    for ticker in tickers_to_analyze:
        print("\n" + "=" * 90)
        print(f"📊 ANALIZANDO: {ticker}")
        print("=" * 90)

        # Descargar datos
        df = safe_download(ticker, period="6mo")

        if df is None or df.empty:
            print(f"  ❌ No se pudo analizar {ticker}\n")
            continue

        # Extraer serie de precios de cierre
        if "Close" in df.columns:
            close_prices = df["Close"]
        else:
            close_prices = df.iloc[:, 0]  # Primera columna como precio

        # Calcular indicadores técnicos
        technical = calculate_technical_indicators(close_prices, ticker)

        # Calcular fundamentales
        fundamentals = calculate_fundamentals(ticker)

        # Almacenar resultados
        result = {
            "Ticker": ticker,
            "Fecha": datetime.now().strftime("%Y-%m-%d"),
            **technical,
            **fundamentals,
        }

        all_results.append(result)

        # Mostrar resumen en consola
        print("\n" + "-" * 90)
        print(f"📈 RESUMEN PARA {ticker}:")
        print("-" * 90)

        # Mostrar precio y tendencia básica
        if "Precio_Actual" in technical:
            print(f"  💰 Precio Actual: {technical['Precio_Actual']}")

        if "SMA_20" in technical and "SMA_50" in technical:
            print(f"  📊 SMA20: {technical['SMA_20']} | SMA50: {technical['SMA_50']}")

        if "EMA_12" in technical and "EMA_26" in technical:
            print(f"  📈 EMA12: {technical['EMA_12']} | EMA26: {technical['EMA_26']}")

        if "RSI_14" in technical:
            print(f"  📈 RSI(14): {technical['RSI_14']}")

        if "MACD" in technical and "MACD_Signal" in technical:
            print(
                f"  📉 MACD: {technical['MACD']} | Signal: {technical['MACD_Signal']}"
            )
            print(f"  📊 Histograma MACD: {technical['MACD_Histogram']}")

        if "BB_Upper" in technical and "BB_Lower" in technical:
            print(
                f"  📊 Bollinger Bands: Upper {technical['BB_Upper']} | Lower {technical['BB_Lower']}"
            )
            print(f"  📍 Posición BB: {technical['BB_Position']}")

        if "ATR_14" in technical:
            print(f"  📊 ATR(14): {technical['ATR_14']}")

        if "Retorno_5D" in technical and "Retorno_20D" in technical:
            print(
                f"  📈 Retorno: 5D: {technical['Retorno_5D']} | 20D: {technical['Retorno_20D']}"
            )

        if "Señales" in technical:
            print(f"\n  🎯 SEÑALES:")
            for signal in technical["Señales"].split(" | "):
                print(f"     {signal}")

        print("\n  📊 FUNDAMENTALES:")
        print(f"     Sector: {fundamentals.get('Sector', 'N/A')}")
        print(f"     Industria: {fundamentals.get('Industria', 'N/A')}")
        print(f"     Market Cap: {fundamentals.get('Market_Cap', 'N/A')}")
        print(f"     P/E (TTM): {fundamentals.get('P/E_TTM', 'N/A')}")
        print(f"     P/E Forward: {fundamentals.get('P/E_Forward', 'N/A')}")
        print(f"     PEG Ratio: {fundamentals.get('PEG_Ratio', 'N/A')}")
        print(f"     Beta: {fundamentals.get('Beta', 'N/A')}")
        print(f"     Dividend Yield: {fundamentals.get('Dividend_Yield', 'N/A')}")
        print(f"     ROE: {fundamentals.get('ROE', 'N/A')}")
        print(f"     Profit Margin: {fundamentals.get('Profit_Margin', 'N/A')}")
        print(f"     Revenue Growth: {fundamentals.get('Revenue_Growth', 'N/A')}")
        print(f"     Cambio 52 Semanas: {fundamentals.get('Cambio_52S', 'N/A')}")

        technical_summary.append(
            {
                "Ticker": ticker,
                "Precio": technical.get("Precio_Actual", "N/A"),
                "SMA20": technical.get("SMA_20", "N/A"),
                "SMA50": technical.get("SMA_50", "N/A"),
                "RSI14": technical.get("RSI_14", "N/A"),
                "Retorno_20D": technical.get("Retorno_20D", "N/A"),
                "Señal_Principal": technical.get("Señales", "N/A").split(" | ")[0]
                if "Señales" in technical
                else "N/A",
            }
        )

    # ========================================================================
    # EXPORTAR RESULTADOS
    # ========================================================================

    if all_results:
        # Guardar CSV completo
        df_results = pd.DataFrame(all_results)
        csv_filename = f"analisis_acciones_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        df_results.to_csv(csv_filename, index=False, encoding="utf-8-sig")

        # Guardar resumen simplificado
        df_summary = pd.DataFrame(technical_summary)
        summary_filename = (
            f"resumen_acciones_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        )
        df_summary.to_csv(summary_filename, index=False, encoding="utf-8-sig")

        print("\n" + "=" * 90)
        print("✅ ANÁLISIS COMPLETADO EXITOSAMENTE")
        print("=" * 90)
        print(f"\n📁 Archivos generados:")
        print(f"   • {csv_filename} - Análisis completo")
        print(f"   • {summary_filename} - Resumen rápido")
        print(f"\n📊 Total empresas analizadas: {len(all_results)}")

        # Mostrar tabla resumen
        print("\n" + "=" * 90)
        print("📋 TABLA RESUMEN:")
        print("=" * 90)
        print(df_summary.to_string(index=False))

    else:
        print("\n❌ No se pudo analizar ninguna empresa")

    print("\n" + "=" * 90)
    print("🏁 FIN DEL ANÁLISIS")
    print("=" * 90 + "\n")
