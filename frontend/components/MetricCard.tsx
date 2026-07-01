import React from "react";
import SkeletonLoader from "./SkeletonLoader";
import "../styles/dashboard_components.css";

interface MetricCardProps {
  title: string;
  value: string | number;
  change?: string;
  isLoading?: boolean;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  change,
  isLoading = false,
}) => {
  if (isLoading) {
    return (
      <div className="metric-card-container loading">
        <SkeletonLoader width="60%" height="14px" />
        <div style={{ height: "12px" }} />
        <SkeletonLoader width="40%" height="28px" />
      </div>
    );
  }

  const isPositive = change?.startsWith("+");

  return (
    <div className="metric-card-container">
      <div className="metric-card-title">{title}</div>
      <div className="metric-card-value-row">
        <div className="metric-card-value">{value}</div>
        {change && (
          <span className={`metric-card-change ${isPositive ? "positive" : "negative"}`}>
            {change}
          </span>
        )}
      </div>
    </div>
  );
};

export default MetricCard;
