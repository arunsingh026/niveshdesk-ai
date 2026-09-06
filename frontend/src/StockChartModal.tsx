import React, { useEffect, useRef, useState } from "react";
import { createChart, ColorType, IChartApi, ISeriesApi } from "lightweight-charts";

interface StockChartModalProps {
  symbol: string;
  name: string;
  onClose: () => void;
  apiUrl: string;
}

interface ChartData {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export function StockChartModal({ symbol, name, onClose, apiUrl }: StockChartModalProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [period, setPeriod] = useState("1m");

  useEffect(() => {
    loadChartData();
  }, [period]);

  useEffect(() => {
    return () => {
      if (chartRef.current) {
        chartRef.current.remove();
      }
    };
  }, []);

  const loadChartData = async () => {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${apiUrl}/api/stock/${symbol}/chart?period=${period}`);
      if (!response.ok) throw new Error("Failed to fetch chart data");

      const data: ChartData[] = await response.json();

      if (chartContainerRef.current) {
        // Remove existing chart
        if (chartRef.current) {
          chartRef.current.remove();
        }

        // Create new chart
        const chart = createChart(chartContainerRef.current, {
          layout: {
            background: { type: ColorType.Solid, color: "#ffffff" },
            textColor: "#333",
          },
          width: chartContainerRef.current.clientWidth,
          height: 500,
          grid: {
            vertLines: { color: "#f0f0f0" },
            horzLines: { color: "#f0f0f0" },
          },
          timeScale: {
            timeVisible: true,
            secondsVisible: false,
          },
        });

        chartRef.current = chart;

        // Add candlestick series
        const candlestickSeries = chart.addCandlestickSeries({
          upColor: "#10b981",
          downColor: "#ef4444",
          borderUpColor: "#10b981",
          borderDownColor: "#ef4444",
          wickUpColor: "#10b981",
          wickDownColor: "#ef4444",
        });

        const candleData = data.map((d) => ({
          time: d.time,
          open: d.open,
          high: d.high,
          low: d.low,
          close: d.close,
        }));

        candlestickSeries.setData(candleData);

        // Add volume series
        const volumeSeries = chart.addHistogramSeries({
          color: "#26a69a",
          priceFormat: {
            type: "volume",
          },
          priceScaleId: "",
        });

        chart.priceScale("").applyOptions({
          scaleMargins: {
            top: 0.8,
            bottom: 0,
          },
        });

        const volumeData = data.map((d) => ({
          time: d.time,
          value: d.volume,
          color: d.close >= d.open ? "#10b98180" : "#ef444480",
        }));

        volumeSeries.setData(volumeData);

        chart.timeScale().fitContent();
      }
    } catch (err) {
      setError("Failed to load chart data");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const periods = [
    { label: "1D", value: "1d" },
    { label: "5D", value: "5d" },
    { label: "1M", value: "1m" },
    { label: "3M", value: "3m" },
    { label: "6M", value: "6m" },
    { label: "1Y", value: "1y" },
    { label: "5Y", value: "5y" },
    { label: "Max", value: "max" },
  ];

  return (
    <div className="chart-modal-overlay" onClick={onClose}>
      <div className="chart-modal" onClick={(e) => e.stopPropagation()}>
        <div className="chart-modal-header">
          <div className="chart-modal-title">
            <h2>{symbol}</h2>
            <p>{name}</p>
          </div>
          <button onClick={onClose} className="chart-modal-close">
            <i className="fas fa-times"></i>
          </button>
        </div>

        <div className="chart-period-selector">
          {periods.map((p) => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              className={`period-btn ${period === p.value ? "active" : ""}`}
            >
              {p.label}
            </button>
          ))}
        </div>

        <div className="chart-container">
          {loading && (
            <div className="chart-loading">
              <i className="fas fa-spinner fa-spin"></i> Loading chart...
            </div>
          )}
          {error && <div className="chart-error">{error}</div>}
          <div ref={chartContainerRef} style={{ width: "100%", height: "500px" }}></div>
        </div>

        <div className="chart-modal-footer">
          <p className="chart-disclaimer">
            <i className="fas fa-info-circle"></i> Chart data is for informational purposes only.
            Verify with NSE before trading.
          </p>
        </div>
      </div>
    </div>
  );
}